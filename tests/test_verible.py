# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from maestro.commands.verible import (
    DEFAULT_FORMAT_FILE,
    DEFAULT_LINT_RULES,
    VeribleCommands,
    parse_file_patterns,
)
from maestro.models import CommandConfig


def test_parse_file_patterns_glob(tmp_path: Path) -> None:
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    (rtl / "a.sv").write_text("module a; endmodule\n")
    (rtl / "b.sv").write_text("module b; endmodule\n")
    (rtl / "c.v").write_text("module c; endmodule\n")

    paths = parse_file_patterns(["rtl/*.sv"], base_path=tmp_path)
    assert set(paths) == {(rtl / "a.sv").resolve(), (rtl / "b.sv").resolve()}


def test_parse_file_patterns_file(tmp_path: Path) -> None:
    f = tmp_path / "top.sv"
    f.write_text("module top; endmodule\n")

    assert parse_file_patterns([f], base_path=tmp_path) == [f.resolve()]


def test_parse_file_patterns_no_match(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_file_patterns(["missing/*.sv"], base_path=tmp_path)


def test_parse_file_patterns_exclude(tmp_path: Path) -> None:
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    (rtl / "a.sv").write_text("module a; endmodule\n")
    (rtl / "b.sv").write_text("module b; endmodule\n")
    (rtl / "tb.sv").write_text("module tb; endmodule\n")

    paths = parse_file_patterns(
        ["rtl/*.sv"],
        base_path=tmp_path,
        exclude=["rtl/tb.sv"],
    )
    assert set(paths) == {(rtl / "a.sv").resolve(), (rtl / "b.sv").resolve()}


def test_parse_file_patterns_exclude_all(tmp_path: Path) -> None:
    (tmp_path / "a.sv").write_text("module a; endmodule\n")
    with pytest.raises(FileNotFoundError):
        parse_file_patterns(["*.sv"], base_path=tmp_path, exclude=["*.sv"])


def test_default_config_files_exist() -> None:
    assert DEFAULT_FORMAT_FILE.is_file()
    assert DEFAULT_LINT_RULES.is_file()


def test_verible_format_and_lint(tmp_path: Path) -> None:
    src = tmp_path / "top.sv"
    src.write_text("module top;endmodule\n")

    cmds = VeribleCommands(CommandConfig(cwd=tmp_path))
    fmt = cmds.format(["*.sv"])
    assert fmt.returncode == 0
    assert "module top;" in src.read_text()

    lint = cmds.lint(["*.sv"])
    assert lint.returncode == 0


def test_default_lint_allows_all_caps_localparam(tmp_path: Path) -> None:
    src = tmp_path / "top.sv"
    src.write_text("module top;\n  localparam int TEST_WIDTH = 8;\nendmodule\n")

    lint = VeribleCommands(CommandConfig(cwd=tmp_path)).lint(["*.sv"])
    assert not any("parameter-name-style" in line for line in lint.output)
