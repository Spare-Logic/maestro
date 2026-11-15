# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from pathlib import Path

from .. import assets
from ..models import CommandError, CommandResult
from .base import Commands

_DEFAULT_PART = "xck26-sfvc784-2LV-c"


class VivadoMode(StrEnum):
    """Vivado ``-mode`` values."""

    BATCH = "batch"
    INTERACTIVE = "tcl"
    GUI = "gui"


@dataclass
class AxiRead:
    """
    AXI read of one 32-bit word.

    Attributes:
        addr: Byte address.
    """

    addr: int

    def as_args(self) -> list[str]:
        return ["read", f"{self.addr:x}"]


@dataclass
class AxiWrite:
    """
    AXI write of one 32-bit word.

    Attributes:
        addr: Byte address.
        value: Value to write.
    """

    addr: int
    value: int
    byte_width: int = 4

    def as_args(self) -> list[str]:
        return ["write", f"{self.addr:x}", f"{self.value:0{self.byte_width * 2}x}"]


AxiOp = AxiRead | AxiWrite


class AxiTransactionFailed(CommandError):
    """JTAG AXI transaction failed. Clock or reset may not be configured correctly."""


class VitisCommands(Commands):
    """Run AMD Vivado and Vitis tools."""

    @staticmethod
    def get_builtin(name: str) -> Path:
        """
        Get the path of a built-in Vitis Python script in ``assets/vitis``.

        Args:
            name: Script name without ``.py``.

        Returns:
            Path to the script.

        Raises:
            ValueError: No built-in script has that name.
        """
        builtin = (Path(__file__).parent.parent / "assets" / "vitis").glob("*.py")

        for script_file in builtin:
            if script_file.stem == name or script_file.stem == name + ".py":
                return script_file
        raise ValueError(
            f"No built-in script found for '{name}'. Available scripts: {[f.stem for f in builtin]}"
        )

    def run_vivado(
        self, *args: str, mode: VivadoMode = VivadoMode.BATCH
    ) -> CommandResult:
        """
        Run Vivado without journal, log or trace files.

        Args:
            args: Extra arguments for Vivado.
            mode: Vivado mode (default batch).

        Returns:
            The command result.
        """
        cmd = ["vivado", "-nojournal", "-nolog", "-notrace", "-mode", str(mode), *args]
        return self.run(*cmd)

    def run_vivado_tcl(self, script: Path, *args: str) -> CommandResult:
        """
        Run a Tcl script in Vivado batch mode.

        Args:
            script: Tcl script to run.
            args: Arguments for the script, passed with ``-tclargs``.

        Returns:
            The command result.
        """
        cmd = ["-script", script.resolve().as_posix()]
        if args:
            cmd.extend(["-tclargs", *args])
        return self.run_vivado(*cmd)

    def jtag_axi(
        self,
        *ops: AxiOp,
        device: str = "xck26_0",
        hw_axi: str = "hw_axi_1",
    ) -> list[int]:
        """
        Run AXI transactions over JTAG in one Vivado session.

        This is a debug tool.

        Args:
            ops: List of AXI operations to perform. Each operation is either a read or a write.

            device: Target device name (e.g., "xck26_0").

            hw_axi: Name of the AXI interface in the hardware design (e.g., "hw_axi_1").

        Returns:
            List of read values (32-bit words) in the same order as the operations.

        Raises:
            AxiTransactionFailed: The Vivado output contains "failed" or "timeout".
                Clock or reset may not be configured correctly.
            ValueError: No operations were given.
        """
        if not ops:
            raise ValueError("at least one operation required")

        tclargs: list[str] = [device, hw_axi]
        for op in ops:
            tclargs.extend(op.as_args())

        with resources.as_file(
            resources.files(assets) / "tcl" / "jtag_axi.tcl"
        ) as script:
            try:
                result = self.run_vivado_tcl(script, *tclargs)
            except CommandError as exc:
                message = str(exc)
                # The executor prefixes every failure with "command failed".
                body = message.split("\n", 1)[1] if "\n" in message else ""
                lowered = body.lower()
                if "failed" in lowered or "timeout" in lowered:
                    raise AxiTransactionFailed(
                        "AXI transaction failed: clock or reset may not be configured correctly\n"
                        f"{message}"
                    ) from exc
                raise

        reads = [  # parse response
            int(line.split()[-1][:8], 16)
            for line in result.output
            if line.strip().startswith("AXI_READ")
        ]

        return reads

    def program_fpga(self, bitfile: Path, device: str = "xck26_0") -> CommandResult:
        """
        Program a bitstream over JTAG.

        Args:
            bitfile: Bitstream file.
            device: Target device name (e.g., "xck26_0").

        Returns:
            The command result.
        """
        with resources.as_file(
            resources.files(assets) / "tcl" / "program.tcl"
        ) as script:
            return self.run_vivado_tcl(
                script,
                bitfile.resolve().as_posix(),
                device,
            )

    def run_python_script(self, script: Path) -> CommandResult:
        """
        Run a Python script with ``vitis -s``.

        Args:
            script: Python script to run.

        Returns:
            The command result.
        """
        return self.run("vitis", "-s", script.resolve().as_posix())

    def sdtgen(
        self,
        xsa: Path,
        sdt_dir: Path,
        board_dts: Path | str | None = None,
        user_dts: Path | None = None,
        debug: bool | None = None,
        trace: bool | None = None,
        zocl: bool | None = None,
        help: bool = False,
    ) -> CommandResult:
        """
        Runs the SDTGen tool to generate device tree files from a Vivado hardware design file (.xsa).

        Args:
            xsa: Vivado hardware design file.
            sdt_dir: Directory for the generated device tree files.
            board_dts: Board-specific dtsi from AMD (name or path).
            user_dts: DTS file to include in the final device tree.
            debug: Enable SDTGen debug output (SDTGen default: disabled).
            trace: Enable SDTGen traces (SDTGen default: disabled).
            zocl: Add zocl nodes for the extended interrupts use case (SDTGen default: disabled).
            help: Show the SDTGen help and exit.
        """

        args = [
            "sdtgen",
            "-xsa",
            xsa.as_posix(),
            "-dir",
            sdt_dir.as_posix(),
        ]
        if board_dts is not None:
            args.extend(["-board_dts", str(board_dts)])
        if user_dts is not None:
            args.extend(["-user_dts", user_dts.as_posix()])
        if debug is not None:
            args.extend(["-debug", "enable" if debug else "disable"])
        if trace is not None:
            args.extend(["-trace", "enable" if trace else "disable"])
        if zocl is not None:
            args.extend(["-zocl", "enable" if zocl else "disable"])
        if help is True:
            args.append("--help")
        return self.run(*args)

    def package_ip(
        self,
        sources: list[Path],
        top_module: str,
        ip_out_dir: Path,
        work_dir: Path | None = None,
        ip_name: str | None = None,
        vendor: str = "user.org",
        library: str = "user",
        version: str = "1.0",
        part: str = _DEFAULT_PART,
        ip_repo_paths: list[Path] | None = None,
    ) -> CommandResult:
        """
        Package RTL as a Vivado user IP.

        Args:
            sources: RTL source files.
            top_module: Top-level module name.
            ip_out_dir: Output directory for the packaged IP.
            work_dir: Vivado project directory. Defaults to ``Projects/<ip_name>``.
            ip_name: IP name. Defaults to ``top_module``.
            vendor: IP vendor.
            library: IP library.
            version: IP version.
            part: FPGA part.
            ip_repo_paths: Extra IP repositories, e.g. for IPs the RTL instantiates.

        Returns:
            The command result.
        """

        ip_name = ip_name or top_module
        work_dir = (work_dir or Path("Projects") / ip_name).resolve()
        repo_paths = (
            ";".join(path.resolve().as_posix() for path in ip_repo_paths)
            if ip_repo_paths
            else "-"
        )

        tclargs = [
            ip_name,
            top_module,
            ip_out_dir.as_posix(),
            work_dir.as_posix(),
            vendor,
            library,
            version,
            part,
            repo_paths,
            *[path.resolve().as_posix() for path in sources],
        ]

        with resources.as_file(
            resources.files(assets) / "tcl" / "package_verilog_ip.tcl"
        ) as script:
            return self.run_vivado_tcl(script, *tclargs)
