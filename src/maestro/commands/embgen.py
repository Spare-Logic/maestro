# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import replace
from pathlib import Path

from ..commands import Commands
from ..executors.base import Executor
from ..models import CommandConfig


class EmbGenCommands(Commands):
    """Generate register files (HJSON, C headers, Python, Markdown) with ``embgen``."""

    def __init__(
        self,
        cfg: CommandConfig | None = None,
        executor: Executor | None = None,
    ):
        """
        Check that ``embgen`` is available.

        Args:
            cfg: Working directory, environment and output settings.
            executor: Executor to run commands with.

        Raises:
            RuntimeError: ``embgen --version`` fails.
        """
        super().__init__(cfg, executor)

        if (
            self.run(
                "embgen",
                "--version",
                cfg=replace(self.cfg, silent=True, ignore_errors=True),
            ).returncode
            != 0
        ):
            raise RuntimeError("embgen command is not available")

    def generate(
        self,
        config: Path,
        targets: list[str],
        output_dir: Path,
        domain: str = "auto",
        silent: bool = True,
    ) -> None:
        """
        Generate files from an embgen YAML config.

        Args:
            config: embgen YAML config file.
            targets: Output formats, each passed as ``--<target>`` (e.g. ``hjson``, ``h``, ``py``, ``md``).
            output_dir: Directory for the generated files.
            domain: embgen domain. ``auto`` detects it from the config.
            silent: Pass ``-s`` to embgen (default True).
        """
        config = config.resolve()
        output_dir = output_dir.resolve()

        cmd = ["embgen"]
        if silent:
            cmd.append("-s")
        cmd.append(domain)
        cmd.extend(["-o", output_dir.as_posix()])
        cmd.append(config.as_posix())
        for target in targets:
            cmd.append("--" + target)

        self.run(*cmd)
