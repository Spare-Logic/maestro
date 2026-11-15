# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from maestro.commands import Commands
from maestro.config_global import global_config, load_config
from maestro.executors import (
    ApptainerExecutor,
    BaseExecutor,
    DockerExecutor,
    Executor,
    PrefixExecutor,
    UVExecutor,
)
from maestro.executors.apptainer import APPTAINER_DEF_DIR
from maestro.executors.base import join_args
from maestro.executors.bash import BashExecutor
from maestro.models import CommandConfig


def test_resolve_executor_id_command(tmp_path: Path):
    load_config(tmp_path)

    global_config.commands["cmdA"] = "executor_a"
    global_config.commands["cmdB"] = {"executor": "executor_b"}

    assert Commands.resolve_executor_id("blabla") == "default"
    assert Commands.resolve_executor_id("cmdA") == "executor_a"
    assert Commands.resolve_executor_id("cmdB") == "executor_b"


def test_rejects_unknown_executor_id(tmp_path: Path):
    load_config(tmp_path)
    with pytest.raises(KeyError, match="Unknown executor id"):
        Executor.factory(
            "bad",
        )


def test_rejects_unknown_executor_type(tmp_path: Path):
    load_config(tmp_path)
    global_config.executors["box"] = "bad"
    with pytest.raises(ValueError, match="Unknown executor type"):
        Executor.factory(
            "box",
        )


def test_discovers_builtin_executor_types(tmp_path: Path):
    load_config(invocation_dir=tmp_path)
    types = Executor.types()
    assert "base" in types
    assert "uv" in types
    assert "docker" in types
    assert "apptainer" in types
    assert "prefix" in types


def test_executor_prefix(tmp_path: Path):
    load_config(invocation_dir=tmp_path)
    global_config.executors["box"] = {
        "type": "prefix",
        "prefix": "uv run",
    }
    executor = Executor.factory(
        "box",
    )
    assert isinstance(executor, PrefixExecutor)
    executor_prefix: PrefixExecutor = executor
    assert executor_prefix.prefix == "uv run"


def test_executor_default(tmp_path: Path):
    load_config(invocation_dir=tmp_path)
    global_config.executors["box"] = "default"

    executor = Executor.factory(
        "box",
    )
    assert isinstance(executor, BaseExecutor)


def test_executor_shortcut(tmp_path: Path):
    load_config(invocation_dir=tmp_path)
    global_config.executors["box"] = "uv"

    executor = Executor.factory(
        "box",
    )
    assert isinstance(executor, UVExecutor)


def test_executor_alias(tmp_path: Path):
    load_config(invocation_dir=tmp_path)

    global_config.executors["alias"] = "aliased"
    global_config.executors["aliased"] = {
        "type": "apptainer",
        "workdir_host": str(tmp_path),
        "def_file": "yocto",
        "binds": [
            (tmp_path / "data", "/data", "rw"),
            (tmp_path / "cache", "/cache", "rw"),
        ],
    }

    executor = Executor.factory("alias")
    assert isinstance(executor, ApptainerExecutor)

    assert executor.def_file == APPTAINER_DEF_DIR / "yocto.def"
    assert executor.workdir_host == tmp_path


def test_executor_alias_cycle(tmp_path: Path):
    load_config(invocation_dir=tmp_path)

    global_config.executors["alias"] = "aliased"
    global_config.executors["aliased"] = "alias"

    with pytest.raises(ValueError, match="Executor alias cycle"):
        Executor.factory(
            "alias",
        )


def test_config_with_binds(tmp_path: Path):
    # create maestro.local.yml
    file = tmp_path / "maestro.local.yml"

    file.write_text("""
executors:
    box:
        type: docker
        image: alpine
        binds:
            - [test, test, rw]
""")
    load_config(tmp_path)

    assert global_config.executors["box"] == {
        "type": "docker",
        "image": "alpine",
        "binds": [["test", "test", "rw"]],
    }

    executor = Executor.factory(
        "box",
    )
    assert isinstance(executor, DockerExecutor)
    assert executor.image == "alpine"


def _prefix_env() -> PrefixExecutor:
    executor = PrefixExecutor()
    executor.configure("env")
    return executor


class _LocalApptainer(ApptainerExecutor):
    # Drop the container wrapper so only the bash -c quoting is exercised
    def _setup(self, cfg):
        return []


@pytest.mark.parametrize(
    "make", [BaseExecutor, _prefix_env, BashExecutor, _LocalApptainer]
)
def test_argv_fidelity(make, tmp_path: Path):
    # Spaces, empty strings and shell metacharacters must reach the child unchanged
    result = make().run(
        CommandConfig(cwd=tmp_path), "printf", "[%s]", "a b", "", "x;y", "$HOME", "#z"
    )
    assert str(result) == "[a b][][x;y][$HOME][#z]"


def test_argv_fidelity_flash_paths(tmp_path: Path):
    # Image names from C44 that used to redirect or inject into `bmaptool copy`
    result = BaseExecutor().run(
        CommandConfig(cwd=tmp_path),
        "printf",
        "[%s]",
        "/work/src /dev/sda #x/image.wic",
        "/work/a;echo INJECTED/image.wic",
        "/dev/sdb",
    )
    assert result.output == [
        "[/work/src /dev/sda #x/image.wic][/work/a;echo INJECTED/image.wic][/dev/sdb]"
    ]


def test_missing_tool_returns_127(tmp_path: Path):
    # EmbGenCommands relies on a non-zero code rather than an exception
    result = BaseExecutor().run(
        CommandConfig(cwd=tmp_path, ignore_errors=True), "maestro-no-such-tool", "x"
    )
    assert result.returncode == 127


@pytest.mark.parametrize("make", [BaseExecutor, _prefix_env, BashExecutor])
def test_env_is_merged_into_host_env(make, tmp_path: Path):
    # cfg.env overlays os.environ; replacing it would drop PATH
    result = make().run(
        CommandConfig(cwd=tmp_path, env={"MAESTRO_FOO": "x"}),
        "sh",
        "-c",
        'echo "$MAESTRO_FOO"; command -v ls >/dev/null && echo path-ok',
    )
    assert result.output == ["x", "path-ok"]


@pytest.mark.parametrize("make", [BaseExecutor, _prefix_env, BashExecutor])
def test_isolated_drops_host_env(make, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MAESTRO_HOSTONLY", "leak")
    result = make().run(
        CommandConfig(cwd=tmp_path, env={"MAESTRO_FOO": "x"}, isolated=True),
        "sh",
        "-c",
        'echo "[${MAESTRO_HOSTONLY-unset}][$MAESTRO_FOO]"',
    )
    assert result.output == ["[unset][x]"]


def test_single_string_keeps_shell_semantics(tmp_path: Path):
    result = BaseExecutor().run(CommandConfig(cwd=tmp_path), "echo a && echo b")
    assert result.output == ["a", "b"]


if __name__ == "__main__":
    from pathlib import Path
    from tempfile import TemporaryDirectory

    tmp_dir = TemporaryDirectory()
    test_config_with_binds(Path(tmp_dir.name))

    tmp_dir.cleanup()


@pytest.mark.parametrize(
    ("system", "expected"),
    [("Linux", "tool 'a b' 'q\"x'"), ("Windows", 'tool "a b" q\\"x')],
)
def test_join_args_quotes_for_host_shell(monkeypatch, system, expected):
    monkeypatch.setattr("platform.system", lambda: system)
    assert join_args(["tool", "a b", 'q"x']) == expected
    assert join_args("echo $HOME | cat") == "echo $HOME | cat"
