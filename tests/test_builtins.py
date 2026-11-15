# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from maestro.commands import VitisCommands
from maestro.executors.apptainer import apptainer_def


def test_get_builtin_script_finds_rpu_scripts():
    for name in ("rpu_setup", "rpu_create", "rpu_build"):
        script = VitisCommands.get_builtin(name)
        assert script.is_file()
        assert script.stem == name


def test_get_builtin_script_can_be_called_multiple_times():
    VitisCommands.get_builtin("rpu_setup")
    VitisCommands.get_builtin("rpu_create")
    VitisCommands.get_builtin("rpu_build")


def test_get_builtin_script_unknown_raises():
    with pytest.raises(ValueError, match="No built-in script found"):
        VitisCommands.get_builtin("nonexistent_script")


def test_get_builtin_def_finds_yocto():
    definition = apptainer_def("yocto")
    assert definition.is_file()
    assert definition.stem == "yocto"


def test_get_builtin_def_can_be_called_multiple_times():
    apptainer_def("yocto")
    apptainer_def("yocto")


def test_get_builtin_def_unknown_raises():
    with pytest.raises(ValueError, match="No built-in definition found"):
        apptainer_def("nonexistent_container")
