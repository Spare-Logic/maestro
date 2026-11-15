# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from ..models import CommandResult
from .base import Commands

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "verible"
DEFAULT_FORMAT_FILE = _ASSETS / "format.flags"
DEFAULT_LINT_RULES = _ASSETS / "lint.rules"


def parse_file_patterns(
    patterns: list[str | Path],
    base_path: Path = Path("."),
    exclude: list[str | Path] | None = None,
) -> list[Path]:
    """
    Expand simple file patterns into concrete file paths.

    Patterns may be existing files or globs relative to ``base_path``
    (e.g. ``"**/*.sv"``, ``"rtl/*.v"``). ``exclude`` uses the same forms.

    Args:
        patterns: File paths or glob patterns.
        base_path: Base directory for globs.
        exclude: Paths or glob patterns to skip.

    Returns:
        Sorted, resolved file paths.

    Raises:
        FileNotFoundError: No files match.
    """
    base_path = base_path.resolve()

    def expand(pats: list[str | Path]) -> set[Path]:
        files: set[Path] = set()
        for pat in pats:
            path = Path(pat)
            matches = (
                [path]
                if path.is_file()
                else [p for p in base_path.glob(str(pat)) if p.is_file()]
            )
            files.update(p.resolve() for p in matches)
        return files

    files = expand(patterns) - expand(exclude or [])
    if not files:
        raise FileNotFoundError(
            f"No files found for the specified patterns: {', '.join(map(str, patterns))}"
        )
    return sorted(files)


class VeribleCommands(Commands):
    """Format and lint SystemVerilog/Verilog with Verible."""

    def format(
        self,
        patterns: list[str | Path],
        exclude: list[str | Path] | None = None,
        inplace: bool = True,
        flagfile: Path | None = None,
    ) -> CommandResult:
        """
        Format SystemVerilog/Verilog files with ``verible-verilog-format``.

        Args:
            patterns: File paths or glob patterns (expanded in Python).
            exclude: Optional paths or glob patterns to skip.
            inplace: Overwrite files in place (default True).
            flagfile: Formatter flag file. Defaults to the bundled format file.
        """
        files = parse_file_patterns(patterns, base_path=self.cfg.cwd, exclude=exclude)
        if flagfile is None:
            flagfile = DEFAULT_FORMAT_FILE

        cmd = [
            "verible-cli",
            "verible-verilog-format",
            f"--flagfile={flagfile.resolve().as_posix()}",
        ]
        if inplace:
            cmd.append("--inplace")
        cmd.extend(f.as_posix() for f in files)
        return self.run(*cmd)

    def lint(
        self,
        patterns: list[str | Path],
        exclude: list[str | Path] | None = None,
        rules_config: Path | None = None,
    ) -> CommandResult:
        """
        Lint SystemVerilog/Verilog files with ``verible-verilog-lint``.

        Args:
            patterns: File paths or glob patterns (expanded in Python).
            exclude: Optional paths or glob patterns to skip.
            rules_config: Lint rules file. Defaults to the bundled lint rules.
        """
        files = parse_file_patterns(patterns, base_path=self.cfg.cwd, exclude=exclude)
        if rules_config is None:
            rules_config = DEFAULT_LINT_RULES

        cmd = [
            "verible-cli",
            "verible-verilog-lint",
            f"--rules_config={rules_config.resolve().as_posix()}",
        ]
        cmd.extend(f.as_posix() for f in files)
        return self.run(*cmd)
