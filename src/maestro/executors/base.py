# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import inspect
import logging
import os
import platform
import re
import shlex
from datetime import datetime
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, list2cmdline
from typing import Protocol, runtime_checkable

from ..config_global import global_config
from ..models import CommandConfig, CommandError, CommandResult

# Regex pattern to match ANSI escape sequences
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


DEFAULT_NAMES = frozenset({"default", "base", "-"})


def join_args(args: list[str] | str) -> str:
    """Build a command line for the host shell used by ``Popen(..., shell=True)``.

    On Windows that shell is ``cmd.exe``, so arguments are quoted with
    ``subprocess.list2cmdline``; elsewhere it is ``/bin/sh`` and ``shlex.join``
    is used.

    Args:
        args: Command as an argument list, or as a ready shell command string.

    Returns:
        The command line. A string ``args`` is returned unchanged, since it is
        assumed to already be valid for the host shell.
    """
    if isinstance(args, str):
        return args
    return list2cmdline(args) if platform.system() == "Windows" else shlex.join(args)


@runtime_checkable
class Executor(Protocol):
    """Starts a command's process and streams its output; subclasses implement ``_start_process``."""

    name: str
    log: logging.Logger

    def __post_init__(self) -> None:
        """Optional post-initialization hook for executors to perform setup or validation after the instance is created."""
        return

    def __init__(self):
        self.name = self.__class__.__name__.lower().replace("executor", "")
        self.log = logging.getLogger("maestro").getChild("exec").getChild(self.name)

        self.__post_init__()  # Call the post-init hook for any additional setup

    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        """Start a subprocess with the given command and configuration.

        Args:
            cfg: CommandConfig containing execution settings like cwd, env, etc.
            args: The command to execute, either as a list of strings or a single string.

        Returns:
            A Popen object representing the started process.
        """
        raise NotImplementedError("Subclasses must implement _start_process()")

    def container_path(self, path: Path) -> Path:
        """Map a host path to where the command sees it. Host executors return it unchanged."""
        return path

    def _env(self, cfg: CommandConfig) -> dict[str, str] | None:
        """Host environment overlaid with ``cfg.env``, or ``None`` to inherit it unchanged."""
        if cfg.isolated:
            return dict(cfg.env)
        return {**os.environ, **cfg.env} if cfg.env else None

    def run(
        self,
        cfg: CommandConfig,
        *args,
    ) -> CommandResult:
        if len(args) > 1:
            args = [str(a) for a in args]  # Ensure all args are strings
        elif len(args) == 1:
            args = str(args[0])  # Unwrap single argument to a string
        else:
            raise ValueError("At least one argument must be provided to run()")

        if not cfg.suppress:
            args_str = " ".join(args) if isinstance(args, list) else args
            self.log.info(f"Running {args_str!r} in {cfg.cwd}")
        process = self._start_process(cfg, args)

        output_lines = []
        times = []
        if process.stdout is not None:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line_clean = ANSI_ESCAPE.sub("", line.strip()).strip()
                    output_lines.append(line_clean)
                    times.append(datetime.now())
                    if not cfg.suppress and not cfg.silent and line_clean:
                        self.log.debug("  | " + line_clean)
        elif not cfg.suppress:
            self.log.warning("No stdout captured for command")

        returncode = process.wait()
        if returncode != 0 and not cfg.ignore_errors:
            if not cfg.suppress:
                self.log.error(
                    f"{self.name} command failed with return code {returncode}"
                )
            last_10_lines = "\n".join(output_lines[-10:])
            raise CommandError(f"{self.name} command failed:\n{last_10_lines}")

        # Return a structure matching your original signature
        return CommandResult(
            args=args,
            returncode=returncode,
            output=output_lines,
            times=times,
            cwd=cfg.cwd,
        )

    _types: dict[str, type["Executor"]] | None = None

    @classmethod
    def types(cls) -> dict[str, type["Executor"]]:
        if cls._types is None:
            from .. import executors as executors_pkg
            from ..discover import discover_classes

            cls._types = discover_classes(
                executors_pkg,
                "Executor",
                cls=Executor,
            )
        return cls._types

    @classmethod
    def factory(
        c,
        executor_id: str,
        _seen: frozenset[str] | None = None,
    ) -> "Executor":
        """
        Build an executor from config (``default``, aliases, or ``type`` + options).

        The maestro.yml should be of the format

        ```yml
        executors:
            vitis_env:
                type: docker
                image: vitis:2025.2
                ...
                binds:
                    - [../cache, /cache, rw]
            hog_exe: vitis_env    # alias
            some_exe_id: default  # executor_id can be defined, but use default exe

        commands:
            uv: some_exe_id       # assign an executor_id
            git: default          # directly use default
            vitis: vitis_env      #
            hog: hog_exe          # use alias executor_id
        ```
        """

        # the _seen is used to avoid an alias cycle
        seen = _seen or frozenset()
        if executor_id in seen:
            raise ValueError(
                f"Executor alias cycle: {' → '.join([*seen, executor_id])}"
            )

        if executor_id not in global_config.executors:
            if executor_id.lower() in DEFAULT_NAMES:
                # Set to default executor
                return BaseExecutor()
            raise KeyError(f"Unknown executor id {executor_id!r}")

        definition = global_config.executors[executor_id]
        if isinstance(definition, str):
            if definition in global_config.executors and definition != executor_id:
                # Found an alias
                return c.factory(definition, _seen=seen | {executor_id})
            if definition in DEFAULT_NAMES:
                # Alias to default executor
                return BaseExecutor()

            # otherwise assume it is a shortcut to an executor type
            #
            #   executor_id: executor
            #
            # instead of:
            #   executor_id:
            #     type: executor
            definition = {"type": definition}
        if not isinstance(definition, dict):
            raise TypeError(
                f"Executor definition must be a mapping or type string, got {type(definition).__name__}"
            )

        spec = dict(definition)
        type_name: str = str(spec.pop("type", "base")).lower().removesuffix("executor")
        cls = c.types().get(type_name)
        if cls is None:
            raise ValueError(
                f"Unknown executor type {type_name!r} (known: {', '.join(sorted(c.types()))})"
            )

        # An executor is either configured using
        # the constructor or if existing the `configure` function
        # extract and apply the args
        configure = getattr(cls, "configure", None)
        target = configure if callable(configure) else cls.__init__
        params = {
            n: p for n, p in inspect.signature(target).parameters.items() if n != "self"
        }
        if unknown := sorted(spec.keys() - params.keys()):
            raise ValueError(
                f"Unknown option(s) {unknown}; allowed: {sorted(params)}"
                if params
                else f"{cls.__name__} does not accept options: {unknown}"
            )
        for name, param in params.items():
            if name not in spec and param.default is inspect.Parameter.empty:
                raise ValueError(f"{cls.__name__} requires {name!r}")
        kwargs = {n: spec[n] for n in params if n in spec}
        if callable(configure):
            obj = cls()
            configure(obj, **kwargs)
            return obj
        return cls(**kwargs)


class BaseExecutor(Executor):
    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        # Quote rather than shell=False, so a missing tool still exits 127 instead of raising
        return Popen(
            join_args(args),
            cwd=cfg.cwd,
            env=self._env(cfg),
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
            shell=True,
        )
