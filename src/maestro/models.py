# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


class CommandError(RuntimeError):
    """A command exited non-zero; the message holds its last 10 output lines."""


@dataclass
class CommandResult:
    """Outcome of a finished command: argv, exit code, and timestamped output lines."""

    args: list[str] | str
    returncode: int
    output: list[str]
    times: list[datetime]
    cwd: Path

    def __str__(self) -> str:
        return "\n".join(self.output)


@dataclass
class CommandConfig:
    cwd: Path = field(default_factory=Path.cwd)
    """Current working directory for the command. Can be relative or absolute. If relative, it will be resolved based on the command's cwd. If not provided, it defaults to the command's cwd."""
    env: dict = field(default_factory=dict)
    """Environment variables to set for the command. This will be merged with the existing environment variables."""
    suppress: bool = field(default=False)
    """If True, suppress all logging output from the command execution."""
    silent: bool = field(default=False)
    """If True, do not log the command's output lines. The command line and errors are still logged."""
    ignore_errors: bool = field(default=False)
    """If True, do not raise an exception if the command returns a non-zero exit code."""
    isolated: bool = field(default=False)
    """If True, do not inherit the host environment (including ``PATH``): the command only sees ``env``. Pass ``PATH`` in ``env`` to keep it."""
