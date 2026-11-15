# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import functools
import inspect
import sys
from pathlib import Path
from typing import Optional

import pytest

from maestro.cli import dispatcher
from maestro.commands.git import GitCommands
from maestro.commands.hog import HoGCommands
from maestro.commands.verible import VeribleCommands
from maestro.commands.vitis import VitisCommands


def _capture(
    monkeypatch: pytest.MonkeyPatch, cls: type, name: str, argv: list[str]
) -> dict:
    """Run the CLI with `argv` and return the arguments `cls.name` received."""
    seen: dict = {}
    orig = getattr(cls, name)

    @functools.wraps(orig)  # keeps the real signature for the dispatcher
    def fake(self, *args, **kwargs):
        seen.update(inspect.signature(orig).bind(self, *args, **kwargs).arguments)

    monkeypatch.setattr(cls, name, fake)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)  # global state
    monkeypatch.setattr(sys, "argv", ["maestro", *argv])
    assert dispatcher.dispatch() == 0
    return seen


def test_optional_list_of_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    kw = _capture(
        monkeypatch,
        VeribleCommands,
        "lint",
        [
            "verible",
            "lint",
            "--patterns",
            "a.sv",
            "--exclude",
            "b.sv",
            "c.sv",
            "--rules-config",
            "r.rules",
        ],
    )
    assert kw["patterns"] == ["a.sv"]  # list[str | Path] keeps strings
    assert kw["exclude"] == ["b.sv", "c.sv"]
    assert kw["rules_config"] == Path("r.rules")


@pytest.mark.parametrize(
    ("ann", "want"),  # Path("a") != "a", so == also checks the type
    [
        (Path, Path("a")),
        (Path | None, Path("a")),
        (Optional[Path], Path("a")),  # noqa: UP045  typing.Union, not X | None
        (str | Path, "a"),
        (str | Path | None, "a"),
        (list[Path] | None, [Path("a")]),
        (list[str | Path], ["a"]),
        (list[str] | list[Path], ["a"]),
        (Optional[list[Path]], [Path("a")]),  # noqa: UP045
    ],
)
def test_annotation_types(ann: object, want: object) -> None:
    parser = argparse.ArgumentParser()
    param = inspect.Parameter("x", inspect.Parameter.KEYWORD_ONLY, annotation=ann)
    dispatcher._add(parser, "x", param)
    assert parser.parse_args(["--x", "a"]).x == want


def test_optional_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    base = ["vitis", "sdtgen", "--xsa", "x.xsa", "--sdt-dir", "out"]
    kw = _capture(monkeypatch, VitisCommands, "sdtgen", [*base, "--no-debug"])
    assert kw["debug"] is False
    assert kw["trace"] is None
    assert kw["xsa"] == Path("x.xsa")


@pytest.mark.parametrize(
    "argv",
    [
        ["git", "clone", "url", "out"],
        ["git", "clone", "--repo-url", "url", "--dest", "out"],
        ["git", "clone", "--repo-url", "url", "out"],
        ["git", "clone", "url", "--dest", "out"],
        ["git", "clone", "--dest", "out", "url"],
    ],
)
def test_required_by_position_or_flag(monkeypatch, argv: list[str]) -> None:
    kw = _capture(monkeypatch, GitCommands, "clone", argv)
    assert kw["repo_url"] == "url"
    assert kw["dest"] == Path("out")  # Path("out") != "out", so the type counts


def test_missing_required_value(monkeypatch, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        _capture(monkeypatch, GitCommands, "clone", ["git", "clone", "url"])
    assert exc.value.code == 2
    assert "required: --dest" in capsys.readouterr().err


def test_too_many_positionals(monkeypatch, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        _capture(monkeypatch, GitCommands, "checkout", ["git", "checkout", "a", "b"])
    assert exc.value.code == 2
    assert "unrecognized arguments: b" in capsys.readouterr().err


def test_split_positionals_rejected(monkeypatch, capsys) -> None:
    argv = ["git", "clone", "url", "--checkout", "main", "out"]
    with pytest.raises(SystemExit) as exc:
        _capture(monkeypatch, GitCommands, "clone", argv)
    assert exc.value.code == 2
    assert "unrecognized arguments: out" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["hog", "run-command", "--command", "x", "a", "b"],
        ["hog", "run-command", "x", "a", "b"],
        ["hog", "run-command", "--command", "x", "--", "a", "b"],
    ],
)
def test_varargs_after_required(monkeypatch, argv: list[str]) -> None:
    kw = _capture(monkeypatch, HoGCommands, "run_command", argv)
    assert kw["command"] == "x"
    assert kw["args"] == ("a", "b")


def test_varargs_dash_value(monkeypatch) -> None:
    argv = ["hog", "run-command", "x", "--", "-mode", "batch"]
    kw = _capture(monkeypatch, HoGCommands, "run_command", argv)
    assert kw["command"] == "x"
    assert kw["args"] == ("-mode", "batch")


def test_list_takes_what_later_parameters_leave(monkeypatch) -> None:
    argv = ["vitis", "package-ip", "a.v", "b.v", "top", "out"]
    kw = _capture(monkeypatch, VitisCommands, "package_ip", argv)
    assert kw["sources"] == [Path("a.v"), Path("b.v")]
    assert kw["top_module"] == "top"
    assert kw["ip_out_dir"] == Path("out")


def test_list_with_later_parameter_by_flag(monkeypatch) -> None:
    argv = ["vitis", "package-ip", "--top-module", "top", "a.v", "b.v", "out"]
    kw = _capture(monkeypatch, VitisCommands, "package_ip", argv)
    assert kw["sources"] == [Path("a.v"), Path("b.v")]
    assert kw["top_module"] == "top"
    assert kw["ip_out_dir"] == Path("out")


def test_list_by_position(monkeypatch) -> None:
    argv = ["verible", "format", "a.sv", "b.sv"]
    kw = _capture(monkeypatch, VeribleCommands, "format", argv)
    assert kw["patterns"] == ["a.sv", "b.sv"]


@pytest.mark.parametrize(
    ("argv", "want"),
    [
        (["media", "flash"], "[IMAGE DEVICE]"),
        (["vitis", "package-ip"], "[SOURCES... TOP_MODULE IP_OUT_DIR]"),
        (["hog", "run-command"], "[COMMAND ARGS...]"),
    ],
)
@pytest.mark.parametrize("columns", ["200", "30"])  # wrapped usage takes another path
def test_help_names_positionals(
    monkeypatch, capsys, argv: list[str], want: str, columns: str
) -> None:
    monkeypatch.setenv("COLUMNS", columns)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(sys, "argv", ["maestro", *argv, "--help"])
    with pytest.raises(SystemExit) as exc:
        dispatcher.dispatch()
    assert exc.value.code == 0
    assert want in " ".join(capsys.readouterr().out.split())


def test_required_non_path_stays_a_flag(monkeypatch) -> None:
    with pytest.raises(SystemExit) as exc:
        _capture(monkeypatch, HoGCommands, "setup", ["hog", "setup", "x"])
    assert exc.value.code == 2


@pytest.mark.parametrize(
    ("result", "want"),
    [
        ("v1.2.0-abc", "v1.2.0-abc\n"),
        (False, "False\n"),
        (set(), ""),
        ({Path("b"), Path("a")}, "a\nb\n"),
        (None, ""),
    ],
)
def test_result_printing(monkeypatch, capsys, result: object, want: str) -> None:
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(sys, "argv", ["maestro", "git", "sha"])
    monkeypatch.setattr("maestro.commands.git.GitCommands.sha", lambda self: result)
    assert dispatcher.dispatch() == 0
    assert capsys.readouterr().out == want


def test_command_result_not_printed(monkeypatch, capsys) -> None:
    from datetime import datetime

    from maestro.models import CommandResult

    res = CommandResult(["x"], 3, ["log line"], [datetime.now()], Path())
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(sys, "argv", ["maestro", "git", "sha"])
    monkeypatch.setattr("maestro.commands.git.GitCommands.sha", lambda self: res)
    assert dispatcher.dispatch() == 3
    assert capsys.readouterr().out == ""


def test_doc_google() -> None:
    def fn(a, b, c):
        """
        Do a thing
        at 100%.

        More detail.

        Args:
            a: First arg.
            b (int): Second arg,
                     continued here.

            c: Third arg.

        Returns:
            Nothing.
        """

    assert dispatcher._doc(fn) == (
        "Do a thing at 100%%.",
        {"a": "First arg.", "b": "Second arg, continued here.", "c": "Third arg."},
    )


def test_doc_incompatible() -> None:
    def plain():
        """Summary only.

        :param x: reST style is ignored.
        """

    def bare():
        pass

    assert dispatcher._doc(plain) == ("Summary only.", {})
    assert dispatcher._doc(bare) == (None, {})
