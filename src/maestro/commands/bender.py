# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import replace
from pathlib import Path

from .base import Commands


class BenderCommands(Commands):
    """Wrap the ``bender`` hardware dependency manager."""

    def update(self, force: bool = True) -> None:
        """
        Update dependencies with ``bender update``.

        Args:
            force: Force-fetch Git dependencies with ``-f`` (default True).
        """
        cmd = ["bender", "update"]
        if force:
            cmd.append("-f")
        self.run(*cmd)

    def script(self, script: str, output: Path, template: Path | None = None) -> None:
        """
        Generate a source script with ``bender script``.

        Args:
            script: Script format, e.g. ``vivado`` or ``flist``.
            output: File to append the generated script to.
            template: Custom template, passed as ``--template``.
        """
        output = output.resolve()
        template = template.resolve() if template is not None else None

        cmd = ["bender", "script", script]
        if template is not None:
            cmd.extend(["--template", template.as_posix()])

        self.run(*cmd, cfg=replace(self.cfg, silent=True), pipe=output)
