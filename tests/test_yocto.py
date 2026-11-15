# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import shlex
from pathlib import Path

import pytest

from maestro.commands import YoctoCommands
from maestro.config_global import load_config
from maestro.executors import DockerExecutor
from maestro.models import CommandConfig, CommandResult


def test_repo_init_sets_git_ceiling_to_workdir(tmp_path: Path):
    load_config(tmp_path)
    (tmp_path / "work").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "ceiling.log"
    repo = bin_dir / "repo"
    repo.write_text(f'#!/bin/sh\necho "$GIT_CEILING_DIRECTORIES" >> {log}\n')
    repo.chmod(0o755)

    # Only PATH: cfg.env is merged into the host environment
    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    # Relative workdir: must resolve against cfg.cwd, not the process cwd
    YoctoCommands("work", cfg=CommandConfig(cwd=tmp_path, env=env)).repo_init()

    workdir = (tmp_path / "work").resolve().as_posix()
    assert log.read_text().splitlines() == [workdir, workdir]


def test_repo_init_maps_git_ceiling_into_container(tmp_path: Path, monkeypatch):
    load_config(tmp_path)
    executor = DockerExecutor().configure(
        "image", workdir_host=tmp_path, workdir_container="/workspace"
    )
    calls = []

    def record(cfg, *args):
        calls.append(args)
        return CommandResult(list(args), 0, [], [], cfg.cwd)

    monkeypatch.setattr(executor, "run", record)

    YoctoCommands(
        "work", cfg=CommandConfig(cwd=tmp_path), executor=executor
    ).repo_init()

    # The container sees the workdir under /workspace, not at its host path
    assert executor.workdir_container is not None
    ceiling = (executor.workdir_container / "work").as_posix()
    assert [args[1] for args in calls] == [f"GIT_CEILING_DIRECTORIES={ceiling}"] * 2


def fake_workdir(root: Path) -> Path:
    """Create a work directory whose ``setupsdk`` enters ``build/`` like the real one, with a fake tool."""
    workdir = root / "work"
    (workdir / "build").mkdir(parents=True)
    (workdir / "setupsdk").write_text('PATH="$PWD:$PATH"\ncd build\n')
    tool = workdir / "gen-machine-conf"
    tool.write_text('#!/bin/sh\nprintf "[%s]\\n" "$PWD" "$@"\n')
    tool.chmod(0o755)
    return workdir


def test_gen_machine_config_passes_each_value_as_one_argument(tmp_path: Path):
    load_config(tmp_path)
    workdir = fake_workdir(tmp_path)
    hw = tmp_path / "my sdt"
    hw.mkdir()
    bit = tmp_path / "top.bit"
    bit.touch()
    template = tmp_path / "template.yaml"
    template.touch()
    macros = tmp_path / "macros.cfg"
    macros.touch()
    macro = 'CONFIG_YOCTO_EXTRA="a b"'

    result = YoctoCommands(workdir, cfg=CommandConfig(cwd=tmp_path)).gen_machine_config(
        "machine",
        hw_description_dir=hw,
        add_config=[macro, str(macros)],
        template=template,
        require_machine="zynqmp-generic",
        machine_overrides="one:two",
        gen_pl_overlay="full",
        pl=bit,
        localconf=tmp_path / "out.conf",
    )

    assert result.output == [
        f"[{p}]"
        for p in [
            (workdir / "build").resolve(),
            "--hw-description",
            hw.resolve(),
            "--machine-name",
            "machine",
            "--template",
            template.resolve(),
            "--pl",
            bit.resolve(),
            "--require-machine",
            "zynqmp-generic",
            "--machine-overrides",
            "one:two",
            "--gen-pl-overlay",
            "full",
            "--add-config",
            macro,
            "--add-config",
            macros.resolve(),
            "--localconf",
            (tmp_path / "out.conf").resolve(),
        ]
    ]


def test_gen_machine_config_maps_paths_into_container(tmp_path: Path, monkeypatch):
    load_config(tmp_path)
    executor = DockerExecutor().configure(
        "image", workdir_host=tmp_path, workdir_container="/workspace"
    )
    scripts = []

    def record(cfg, *args):
        scripts.extend(args)
        return CommandResult(list(args), 0, [], [], cfg.cwd)

    monkeypatch.setattr(executor, "run", record)
    (tmp_path / "sdt").mkdir()
    for name in ("top.bit", "template.yaml", "macros.cfg"):
        (tmp_path / name).touch()
    (tmp_path / "conf").mkdir()
    (tmp_path / "out").mkdir()

    YoctoCommands(
        "work/sub", cfg=CommandConfig(cwd=tmp_path), executor=executor
    ).gen_machine_config(
        "machine",
        hw_description_dir=tmp_path / "sdt",
        config_dir=tmp_path / "conf",
        output_dir=tmp_path / "out",
        add_config=[tmp_path / "macros.cfg", "CONFIG_A=y"],
        template=tmp_path / "template.yaml",
        pl=tmp_path / "top.bit",
        localconf=tmp_path / "local.conf",
    )

    argv = shlex.split(scripts[0].split(" && ", 1)[1])
    flags = dict(zip(argv[1::2], argv[2::2]))
    assert flags["--hw-description"] == "/workspace/sdt"
    assert flags["--config-dir"] == "/workspace/conf"
    assert flags["--output"] == "/workspace/out"
    assert flags["--template"] == "/workspace/template.yaml"
    assert flags["--pl"] == "/workspace/top.bit"
    assert flags["--localconf"] == "/workspace/local.conf"
    assert argv.count("/workspace/macros.cfg") == 1
    assert "CONFIG_A=y" in argv


def test_gen_machine_config_default_sdt_follows_workdir(tmp_path: Path, monkeypatch):
    load_config(tmp_path)
    workdir = fake_workdir(tmp_path / "project")
    sdt = workdir / "sdt"
    sdt.mkdir()
    # The work directory is relative to cfg.cwd, whatever the process cwd is
    monkeypatch.chdir(tmp_path)

    result = YoctoCommands(
        "work", cfg=CommandConfig(cwd=workdir.parent)
    ).gen_machine_config("machine")

    assert f"[{sdt.resolve()}]" in result.output


def test_gen_machine_config_keeps_output_on_invalid_arguments(tmp_path: Path):
    load_config(tmp_path)
    workdir = fake_workdir(tmp_path)
    hw = tmp_path / "sdt"
    hw.mkdir()
    output = tmp_path / "out"
    output.mkdir()

    with pytest.raises(FileNotFoundError, match="PL path"):
        YoctoCommands(workdir, cfg=CommandConfig(cwd=tmp_path)).gen_machine_config(
            "machine",
            hw_description_dir=hw,
            output_dir=output,
            pl=tmp_path / "missing.bit",
        )

    assert output.exists()


def test_gen_machine_config_keeps_output_outside_container_workdir(
    tmp_path: Path, monkeypatch
):
    load_config(tmp_path)
    workspace = tmp_path / "workspace"
    (workspace / "sdt").mkdir(parents=True)
    output = tmp_path / "outside"
    output.mkdir()
    executor = DockerExecutor().configure(
        "image", workdir_host=workspace, workdir_container="/workspace"
    )
    monkeypatch.setattr(executor, "run", lambda *_: pytest.fail("ran the tool"))

    with pytest.raises(ValueError):
        YoctoCommands(
            "work", cfg=CommandConfig(cwd=workspace), executor=executor
        ).gen_machine_config(
            "machine", hw_description_dir=workspace / "sdt", output_dir=output
        )

    assert output.exists()


def test_gen_machine_config_accepts_macro_longer_than_a_file_name(tmp_path: Path):
    load_config(tmp_path)
    workdir = fake_workdir(tmp_path)
    hw = tmp_path / "sdt"
    hw.mkdir()
    macro = f'CONFIG_SUBSYSTEM_USER_CMDLINE="{"a" * 300}"'

    result = YoctoCommands(workdir, cfg=CommandConfig(cwd=tmp_path)).gen_machine_config(
        "machine", hw_description_dir=hw, add_config=[macro]
    )

    assert f"[{macro}]" in result.output


def test_gen_machine_config_rejects_invalid_overlay_keeping_output(tmp_path: Path):
    load_config(tmp_path)
    workdir = fake_workdir(tmp_path)
    hw = tmp_path / "sdt"
    hw.mkdir()
    output = tmp_path / "out"
    output.mkdir()

    with pytest.raises(ValueError, match="fulll"):
        YoctoCommands(workdir, cfg=CommandConfig(cwd=tmp_path)).gen_machine_config(
            "machine",
            hw_description_dir=hw,
            output_dir=output,
            gen_pl_overlay="fulll",  # ty: ignore[invalid-argument-type]
        )

    assert output.exists()


@pytest.mark.parametrize(
    "config",
    ["cfg/missing.cfg", Path("cfg/CONFIG_missing.cfg")],
    ids=["string", "path-named-like-a-macro"],
)
def test_gen_machine_config_rejects_missing_macro_file(
    tmp_path: Path, config: str | Path
):
    load_config(tmp_path)
    workdir = fake_workdir(tmp_path)
    hw = tmp_path / "sdt"
    hw.mkdir()

    with pytest.raises(FileNotFoundError, match="missing"):
        YoctoCommands(workdir, cfg=CommandConfig(cwd=tmp_path)).gen_machine_config(
            "machine", hw_description_dir=hw, add_config=[config]
        )
