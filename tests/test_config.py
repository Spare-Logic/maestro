# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from maestro.config_global import global_config, load_config
from maestro.config_models import (
    ApptainerConfig,
    LogConfig,
    PathsConfig,
    YoctoConfig,
)


@pytest.fixture(autouse=True)
def reset_config():
    global_config.paths = PathsConfig()
    global_config.log = LogConfig()
    global_config.apptainer = ApptainerConfig()
    global_config.yocto = YoctoConfig()
    global_config.executors = {}
    global_config.commands = {}
    yield


def test_defaults_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.paths._invocation_dir == tmp_path
    assert cfg.paths.root == ".maestro"
    assert cfg.paths.root_dir == tmp_path / ".maestro"
    assert cfg.log.level == "INFO"
    assert cfg.apptainer.cache_subdir == "apptainer"
    assert cfg.yocto.cache_subdir == "yocto"


def test_maestro_yml_ignored_unknown_keys(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text("foo: bar\nbaz: 42\n")
    cfg = load_config(tmp_path)
    assert cfg.log.level == "INFO"


def test_maestro_yml_applies_known_fields(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text(
        "paths:\n  root: custom-data\nlog:\n  level: DEBUG\n"
    )
    cfg = load_config(tmp_path)
    assert cfg.paths._invocation_dir == tmp_path
    assert cfg.paths.root == "custom-data"
    assert cfg.paths.root_dir == tmp_path / "custom-data"
    assert cfg.log.level == "DEBUG"


def test_maestro_yml_sections(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text(
        "log:\n  level: WARNING\napptainer:\n  cache_subdir: custom_apptainer\n"
    )
    cfg = load_config(tmp_path)
    assert cfg.log.level == "WARNING"
    assert cfg.apptainer.cache_subdir == "custom_apptainer"


def test_maestro_yml_log_format_with_percent(tmp_path: Path):
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    (tmp_path / "maestro.yml").write_text(f'log:\n  format: "{fmt}"\n')
    cfg = load_config(tmp_path)
    assert cfg.log.format == fmt


def test_local_overrides_maestro_yml(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text("log:\n  level: INFO\n")
    (tmp_path / "maestro.local.yml").write_text("log:\n  level: DEBUG\n")
    cfg = load_config(tmp_path)
    assert cfg.log.level == "DEBUG"


def test_precedence(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text("log:\n  level: INFO\n")
    (tmp_path / "maestro.local.yml").write_text("log:\n  level: WARNING\n")
    cfg = load_config(tmp_path)
    assert cfg.log.level == "WARNING"


def test_in_place_singleton(tmp_path: Path):
    before = id(global_config)
    load_config(tmp_path)
    assert id(global_config) == before


def test_empty_yaml_file(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text("")
    cfg = load_config(tmp_path)
    assert cfg.log.level == "INFO"


def test_executors_and_commands_from_yml(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text("""\
executors:
  default:
    type: base
  uv: uv
  boxed:
    type: prefix
    prefix: 'echo'
commands:
  embgen:
    executor: uv
  yocto: boxed
""")
    cfg = load_config(tmp_path)
    assert cfg.executors["default"] == {"type": "base"}
    assert cfg.executors["uv"] == "uv"
    assert cfg.executors["boxed"]["prefix"] == "echo"
    assert cfg.commands["embgen"] == {"executor": "uv"}
    assert cfg.commands["yocto"] == "boxed"


def test_local_overrides_executor_binds(tmp_path: Path):
    (tmp_path / "maestro.yml").write_text("""\
executors:
  box:
    type: apptainer
    def_file: yocto
    workdir_host: .
    binds:
      - [/usr/pack, /usr/pack, ro]
""")
    (tmp_path / "maestro.local.yml").write_text("""\
executors:
  box:
    binds:
      - [/local/pack, /usr/pack, ro]
""")
    cfg = load_config(tmp_path)
    assert cfg.executors["box"]["def_file"] == "yocto"
    assert cfg.executors["box"]["binds"] == [["/local/pack", "/usr/pack", "ro"]]
