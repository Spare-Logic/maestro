# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import replace
from pathlib import Path

from maestro.commands import Commands
from maestro.models import CommandConfig


class DummyCommands(Commands):
    def run_cmd(self, *args, cfg=None):
        return self.run(*args, cfg=cfg)


def test_relative_cwd_resolution(tmp_path: Path):
    # Set up dummy commands with a temporary directory as cwd
    cmd_dir = tmp_path / "my_project"
    cmd_dir.mkdir()

    # Create a subdirectory within it
    sub_dir_name = "sub_dir"
    sub_dir = cmd_dir / sub_dir_name
    sub_dir.mkdir()

    # Create a dummy file in the sub-directory
    test_file = sub_dir / "test.txt"
    test_file.write_text("hello world")

    commands = DummyCommands(CommandConfig(cwd=cmd_dir))
    cfg = CommandConfig(cwd=Path(sub_dir_name))

    # Run a command using the relative sub_dir name as cwd
    # Since we are using standard tools, let's run git status or just cat the file.
    # We can use "cat" or "python" to read the file, or check git repository.
    # Since we want it to be cross-platform/clean, let's read the file using python or cat.
    result = commands.run_cmd("cat", "test.txt", cfg=cfg)

    assert "hello world" in result.output


def test_default_cwd_is_resolved(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "rel").mkdir()
    result = DummyCommands(CommandConfig(cwd=Path("rel"))).run_cmd("pwd")
    assert result.cwd == (tmp_path / "rel").resolve()


def test_per_call_copy_of_relative_cwd_is_not_applied_twice(
    tmp_path: Path, monkeypatch
):
    # C06: replace(self.cfg, ...) must not join a relative cwd onto itself
    monkeypatch.chdir(tmp_path)
    (tmp_path / "project").mkdir()
    commands = DummyCommands(CommandConfig(cwd=Path("project")))
    result = commands.run_cmd("pwd", cfg=replace(commands.cfg, silent=True))
    assert result.cwd == (tmp_path / "project").resolve()
