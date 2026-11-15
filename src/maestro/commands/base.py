# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import platform
from dataclasses import replace
from pathlib import Path

from ..config_global import global_config
from ..executors.base import Executor
from ..models import CommandConfig, CommandResult


class Commands:
    """Base class for tool wrappers that run commands through an executor."""

    @staticmethod
    def resolve_executor_id(command_name: str) -> str:
        """
        Look up the executor bound to a command in ``maestro.yml``.

        Args:
            command_name: Command name, e.g. ``git`` or ``vitis``.

        Returns:
            The executor id, or ``default`` if none is configured.
        """
        binding = global_config.commands.get(command_name)
        if isinstance(binding, dict):
            binding = binding.get("executor")
        return binding or "default"

    def __init__(
        self,
        cfg: CommandConfig | None = None,
        executor: Executor | None = None,
        executor_id: str | None = None,
    ):
        """
        Args:
            cfg: Working directory, environment and output settings.
            executor: Executor to run commands with. Overrides ``executor_id``.
            executor_id: Executor from ``maestro.yml``. Defaults to the one bound to this command.
        """
        # Resolve once, so per-call copies via replace(self.cfg, ...) don't re-apply a relative cwd
        self.cfg = replace(cfg, cwd=cfg.cwd.resolve()) if cfg else CommandConfig()
        self.name = self.__class__.__name__.lower().replace("commands", "")
        self.log = logging.getLogger("maestro").getChild("cmd").getChild(self.name)
        # Explicit executor= wins; otherwise resolve from maestro.yml / maestro.local.yml
        self.executor_id = executor_id or self.resolve_executor_id(self.name)
        self.executor = executor or Executor.factory(self.executor_id)

    @property
    def system(self) -> str:
        """Host OS name, e.g. ``Linux``."""
        return platform.system()

    @property
    def path(self) -> Path:
        """Absolute working directory."""
        return self.cfg.cwd.resolve()

    def run(
        self,
        *args: str,
        cfg: CommandConfig | None = None,
        pipe: Path | None = None,
        privileged: bool = False,
    ) -> CommandResult:
        """
        Run a command with the executor and log its output.

        Args:
            args: Command and its arguments.
            cfg: Settings for this call. A relative ``cwd`` is resolved against the default one.
            pipe: File to append the command output to.
            privileged: Prefix the command with ``sudo`` (not on Windows).

        Returns:
            The command result.
        """
        # Path / absolute is the absolute path, so this only anchors relative cwds
        cwd = self.path if cfg is None else (self.path / cfg.cwd).resolve()
        cfg = replace(cfg or self.cfg, cwd=cwd)

        args: list[str] = list(args)

        if privileged:
            self.log.info("Privileged command might require password")
            if self.system != "Windows":
                args.insert(0, "sudo")

        result = self.executor.run(cfg, *args)

        log_file = global_config.log_dir / f"{self.name}.log"

        args_str = " ".join(args) if isinstance(args, list) else args
        with log_file.open(mode="a", encoding="utf-8") as f:
            f.write(f"\n$ {args_str}\n\n")
            for line, time in zip(result.output, result.times):
                f.write(f"[{time}] {line}\n")

        if pipe is not None:
            pipe = pipe.resolve()
            with pipe.open(mode="a", encoding="utf-8") as f:
                for line in result.output:
                    f.write(f"{line}\n")

            if not cfg.suppress:
                self.log.info(f"Output piped to {pipe.as_posix()}")

        return result
