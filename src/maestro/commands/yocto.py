# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import shlex
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Literal, get_args

from ..config_global import global_config
from ..executors import Executor
from ..models import CommandConfig, CommandResult
from .base import Commands

PlOverlay = Literal["full", "dfx"]


class YoctoCommands(Commands):
    """Set up and run an AMD Yocto build (``repo``, ``bitbake-layers``, ``gen-machine-conf``)."""

    def __init__(
        self,
        yocto_workdir: str | Path | None = None,
        cfg: CommandConfig | None = None,
        executor: Executor | None = None,
    ):
        """
        Args:
            yocto_workdir: Yocto work directory. Defaults to ``commands.yocto.yocto_workdir`` in ``maestro.yml``.
            cfg: Working directory, environment and output settings.
            executor: Executor to run commands with.

        Raises:
            TypeError: No work directory is given or configured.
        """
        super().__init__(cfg=cfg, executor=executor)
        if yocto_workdir is None:
            binding = global_config.commands.get("yocto")
            yocto_workdir = (
                binding.get("yocto_workdir") if isinstance(binding, dict) else None
            )
        if not isinstance(yocto_workdir, (str, Path)):
            raise TypeError(
                "yocto_workdir is required: pass it to YoctoCommands(...) "
                "or set commands.yocto.yocto_workdir in maestro.yml"
            )
        self.yocto_workdir = Path(yocto_workdir)
        self.yocto_workdir_cfg = replace(self.cfg, cwd=self.yocto_workdir)
        self.log.debug(f"Yocto workdir config: {self.yocto_workdir_cfg}")

    def repo_init(
        self,
        checkout: str = "rel-v2025.2",
        repo_url: str = "https://github.com/Xilinx/yocto-manifests.git",
        prefix: list[str] | None = None,
    ) -> None:
        """
        Fetch the Yocto sources with ``repo init`` and ``repo sync``.

        Args:
            checkout: Manifest branch.
            repo_url: Manifest repository.
            prefix: Command prefix for both repo calls. Defaults to setting ``GIT_CEILING_DIRECTORIES`` to the work directory, as seen by the executor (the container path for Docker and Apptainer). Items are passed literally, without shell expansion.
        """
        if prefix is None:
            workdir = self.executor.container_path(
                (self.cfg.cwd / self.yocto_workdir).resolve()
            )
            prefix = ["env", f"GIT_CEILING_DIRECTORIES={workdir.as_posix()}"]
        self.run(
            *prefix,
            "repo",
            "init",
            "-u",
            repo_url,
            "-b",
            checkout,
            cfg=self.yocto_workdir_cfg,
        )
        self.run(*prefix, "repo", "sync", cfg=self.yocto_workdir_cfg)

    def run_environment(
        self,
        script: str,
    ) -> CommandResult:
        """
        Run a shell command in the work directory after sourcing ``setupsdk``.

        Args:
            script: Shell command to run.

        Returns:
            The command result.
        """
        return self.run(f". ./setupsdk && {script}", cfg=self.yocto_workdir_cfg)

    def bitbake(self, target: str) -> CommandResult:
        """
        Run a bitbake build for the specified target.

        Args:
            target: Bitbake target to build.

        Returns:
            The command result.
        """
        return self.run_environment(f"bitbake {target}")

    def add_layer(self, layer_dir: Path) -> CommandResult:
        """
        Add a layer with ``bitbake-layers add-layer``.

        Args:
            layer_dir: Layer directory.

        Returns:
            The command result.
        """
        return self.run_environment(f"bitbake-layers add-layer {layer_dir.as_posix()}")

    def _tool_path(self, path: Path) -> str:
        """
        Convert a path argument to what a tool sees: ``setupsdk`` moves it to ``build/``, possibly in a container.

        Args:
            path: Host path, relative to the process cwd.

        Returns:
            The absolute path as seen by the executor.
        """
        return self.executor.container_path(path.resolve()).as_posix()

    def gen_machine_config(
        self,
        machine_name: str,
        hw_description_dir: Path | None = None,
        config_dir: Path | None = None,
        output_dir: Path | None = None,
        add_config: list[str | Path] | None = None,
        template: Path | None = None,
        require_machine: str | None = None,
        machine_overrides: str | None = None,
        gen_pl_overlay: PlOverlay | None = None,
        pl: Path | None = None,
        localconf: Path | None = None,
    ) -> CommandResult:
        """
        Generate a machine config with ``gen-machine-conf``.

        Args:
            machine_name: Name of the machine.
            hw_description_dir: Hardware description (SDT) directory. Defaults to ``sdt/`` in the work directory.
            config_dir: Config directory. Uses gen-machine-conf internal default if not specified.
            output_dir: Output directory, deleted first if it exists. Uses gen-machine-conf internal default if not specified.
            add_config: Config macros (``CONFIG_<macro>=y``) or files of macros, applied on top of the default configs. A ``Path`` is always a file.
            template: YAML template file with default arguments.
            require_machine: Machine to require instead of the generic one.
            machine_overrides: Additional overrides for the generated machine.
            gen_pl_overlay: PL overlay type, ``full`` or ``dfx``. SDT flow only.
            pl: Bitstream or PDI file, or a directory containing one, inside the hardware description directory: the machine config refers to it by file name only. SDT flow only.
            localconf: File to write the ``local.conf`` changes to.

        Returns:
            The command result.

        Raises:
            FileNotFoundError: The hardware description, config directory, template, PL path or a macro file is missing.
            ValueError: ``gen_pl_overlay`` is invalid, or a path is outside the executor's work directory.
        """
        if gen_pl_overlay not in (None, *get_args(PlOverlay)):
            raise ValueError(f"Invalid PL overlay type: {gen_pl_overlay}")

        if hw_description_dir is None:
            hw_description_dir = self.path / self.yocto_workdir / "sdt"
            self.log.debug(
                f"Using default hardware description directory: {hw_description_dir.as_posix()}"
            )

        if not hw_description_dir.exists():
            raise FileNotFoundError(
                f"Hardware description directory not found: {hw_description_dir}"
            )

        args = [
            "gen-machine-conf",
            "--hw-description",
            self._tool_path(hw_description_dir),
            "--machine-name",
            machine_name,
        ]

        for flag, path, label in (
            ("--config-dir", config_dir, "Config directory"),
            ("--template", template, "Template file"),
            ("--pl", pl, "PL path"),
        ):
            if path is None:
                continue
            if not path.exists():
                raise FileNotFoundError(f"{label} not found: {path}")
            args += [flag, self._tool_path(path)]

        for flag, value in (
            ("--require-machine", require_machine),
            ("--machine-overrides", machine_overrides),
            ("--gen-pl-overlay", gen_pl_overlay),
        ):
            if value is not None:
                args += [flag, value]

        for config in add_config or []:
            # Same check as the tool, which reads a value as a file if one exists
            if os.path.isfile(config):
                config = self._tool_path(Path(config))
            elif isinstance(config, Path) or "CONFIG_" not in config:
                raise FileNotFoundError(f"Config macro file not found: {config}")
            args += ["--add-config", config]

        if localconf is not None:
            args += ["--localconf", self._tool_path(localconf)]

        if output_dir is not None:
            # Delete last, so that invalid arguments leave the previous output intact
            args += ["--output", self._tool_path(output_dir)]
            if output_dir.exists():
                shutil.rmtree(output_dir)

        return self.run_environment(shlex.join(args))
