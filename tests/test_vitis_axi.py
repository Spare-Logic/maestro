# Copyright 2026 ETH Zurich
# SPDX-FileCopyrightText: 2026 ETH Zurich
# SPDX-FileContributor: Cedric Hirschi <cehirschi@ethz.ch>
# SPDX-FileContributor: Tim Frey <timfrey@ethz.ch>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from pathlib import Path

import pytest

from maestro.commands.vitis import AxiRead, AxiTransactionFailed, VitisCommands
from maestro.models import CommandError, CommandResult


@pytest.mark.parametrize(
    "detail",
    ["AXI_TRANSACTION_FAILED at 40000000", "ERROR: [Labtoolstcl 44-140] AXI timeout"],
)
def test_jtag_axi_failed_or_timeout_is_a_python_exception(monkeypatch, detail):
    def fail(self, script, *args):
        raise CommandError(f"vitis command failed:\n{detail}")

    monkeypatch.setattr(VitisCommands, "run_vivado_tcl", fail)

    with pytest.raises(AxiTransactionFailed, match="clock or reset"):
        VitisCommands().jtag_axi(AxiRead(0x40000000))


def test_jtag_axi_other_failures_stay_command_errors(monkeypatch):
    def fail(self, script, *args):
        raise CommandError("vitis command failed:\nexpected read or write, got: foo")

    monkeypatch.setattr(VitisCommands, "run_vivado_tcl", fail)

    with pytest.raises(CommandError) as exc_info:
        VitisCommands().jtag_axi(AxiRead(0))
    assert type(exc_info.value) is CommandError


def test_jtag_axi_returns_read_data(monkeypatch):
    def ok(self, script, *args):
        return CommandResult(
            args=["vivado"],
            returncode=0,
            output=["AXI_READ deadbeef"],
            times=[datetime.now()],
            cwd=Path("."),
        )

    monkeypatch.setattr(VitisCommands, "run_vivado_tcl", ok)

    assert VitisCommands().jtag_axi(AxiRead(0x10)) == [0xDEADBEEF]
