# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import shutil
from collections.abc import Generator
from pathlib import Path

from maestro.commands import GitCommands

from ..models import CommandResult
from .base import Commands


def parse_hog_src_files(
    src_path: list[Path],
    src_suffixes: list[str] | None = None,
    base_path: Path = Path("."),
) -> list[Path]:
    """
    Parse .src files into a list of paths.

    Args:
        src_path: Paths to process: .src files, files, directories or glob patterns.
        src_suffixes: Suffixes of HoG list files (default ``[".src"]``).
        base_path: Base for the paths listed inside list files.

    Returns:
        Resolved file paths.

    Raises:
        ValueError: A path matches no file.
    """

    if src_suffixes is None:
        src_suffixes = [".src"]

    def _process_file(file: Path) -> Generator[Path]:
        if file.suffix in src_suffixes:
            with file.open("r") as f:
                for line in f.readlines():
                    line = line.split("#")[0]
                    line = line.strip()
                    if line == "":
                        continue
                    yield from _process_file(base_path / line)
        else:
            if file.is_file():
                yield file.resolve()
            elif file.is_dir():
                for f in file.iterdir():
                    yield from _process_file(f)
            else:
                files = list(file.parent.glob(file.name))
                if len(files) == 0:
                    raise ValueError(f"Invalid file: {file}")
                for f in files:
                    yield from _process_file(f)

    def _process_files(files: list[Path]) -> Generator[Path]:
        for file in files:
            yield from _process_file(file)

    return list(_process_files(src_path))


class HoGCommands(Commands):
    """Run HoG (HDL on Git) ``Hog/Do`` commands."""

    def run_command(self, command: str, *args: str) -> CommandResult:
        """
        Run ``./Hog/Do <command> <args>``.

        Args:
            command: HoG command, e.g. ``CREATE`` or ``WORKFLOW``.
            args: Extra arguments for the command.

        Returns:
            The command result.
        """
        return self.run("./Hog/Do", command, *args)

    def create(self, project: str) -> CommandResult:
        """
        Create the Vivado project with HoG.

        Args:
            project: Project name (path relative to Top/), e.g. "vivado/abacus".

        Returns:
            The command result.
        """
        return self.run_command("CREATE", project)

    def workflow(self, project: str, recreate: bool = False) -> CommandResult:
        """
        Run the full HoG workflow: create, synthesize, implement and write the bitstream.

        Args:
            project: Project name (path relative to Top/), e.g. "vivado/abacus".
            recreate: Recreate the project even if it already exists.

        Returns:
            The command result.
        """
        args: list[str] = []
        if recreate:
            args += ["-recreate"]
        return self.run_command("WORKFLOW", project, *args)

    def get_describe(
        self,
        project: str,
    ) -> str:
        """
        Get the HoG describe string of a project.

        The format is 'v<version>-<hash>', with '-dirty' appended if there are
        uncommitted changes in project dependencies.

        Args:
            project: Project name (Path relative to Top/), e.g. "vivado/abacus".

        Returns:
            The describe string, e.g. "v1.2.0-3a4b56g" or "v1.2.0-3a4b56g-dirty".
        """

        res = self.run_command("VERSION", project, "-describe")

        lines = res.output

        if not any(line.startswith("v") for line in lines):
            # Logging mode activated, whose output looks like this:
            #
            # *INFO     : [Hog:loadUserConf] Hog project configuration file /home/user/HogEnv.conf exists.
            # *INFO     : [Hog:Logger_Init] PROJECT_FOLDER vivado/abacus
            # *INFO     : [Hog:Logger_Init] Color Scheme set to clear
            # INFO     : [Hog:Logger_Init] LOG_INFO_FILE /workspace/project/hog_info.log
            # INFO     : [Hog:Logger_Init] LOG_WAR_ERR_FILE /workspace/project/hog_warning_errors.log
            # INFO     : [Hog:Logger_Init] Hog configuration setup done!!!
            # -INFO     : [Hog:CheckLatestHogRelease] Checking for latest Hog release, can take up to 5 seconds...
            # ·WARNING  : redirecting to https://gitlab.com/hog-cern/Hog.git/
            # -INFO     : [Hog:CheckLatestHogRelease] Latest official version is Hog2026.1-4, nothing to do.
            # -INFO     : [Hog:InitLauncher] Project vivado/abacus uses vivado IDE
            # -INFO     : [Hog:GetRepoVersions] Hog submodule /workspace/project/Hog clean.
            # -INFO     : [Hog:GetRepoVersions] This project does not use IPbus XMLs
            # -CRITICAL : [Hog:GetRepoVersions] Project-relevant files not clean, commit hash and version will be set to 0.
            # -INFO     : [Hog:GetRepoVersions] Hog submodule /workspace/project/Hog clean.
            # -INFO     : [Hog:GetRepoVersions] This project does not use IPbus XMLs
            # -CRITICAL : [Hog:GetRepoVersions] Project-relevant files not clean, commit hash and version will be set to 0.
            # -INFO     : v0.0.0-2058281-dirty
            # ================ RESUME ================
            # # of Total messages: 17
            # # of Info messages: 14
            # # of warning messages : 1
            # # of critical warning messages : 2
            # # of Errors messages : 0
            # ========================================
            # *** Hog finished with Critical Warnings ***

            # Filter by lines starting with "-", which are the log lines, and find the one that contains the describe string
            lines = [line for line in lines if line.startswith("-")]

            # Split the line by ": " and take the last part, which contains the describe string
            lines = [line.split(": ")[-1] for line in lines]

        return lines[-1]

    def get_output_files(
        self,
        project: str,
        glob_pattern: str,
    ) -> list[Path]:
        """
        Find output files of the current describe in the project's ``bin/`` directory.

        Args:
            project: Project name (path relative to Top/), e.g. "vivado/abacus".
            glob_pattern: Pattern inside the output directory, e.g. ``*.bit``.

        Returns:
            Matching files.
        """
        describe = self.get_describe(project)
        group_path = "/".join(project.split("/")[:-1])
        project_name = project.split("/")[-1]

        bin_dir = (self.cfg.cwd / "bin" / group_path).resolve()
        pattern = f"{project_name}-{describe}/{glob_pattern}"
        self.log.debug(
            f"Looking for output files in {bin_dir.as_posix()} matching '{pattern}'"
        )
        return list(bin_dir.glob(pattern))

    def copy_output_files(
        self,
        project: str,
        dest_dir: Path,
    ) -> None:
        """
        Copy the project's ``.bit``, ``.xsa`` and ``.ltx`` outputs to a directory.

        Files are named after the project, e.g. "vivado/abacus" -> ``vivado-abacus.bit``.

        Args:
            project: Project name (path relative to Top/), e.g. "vivado/abacus".
            dest_dir: Destination directory, created if missing.
        """
        output_files = self.get_output_files(project, "*")
        bit_files = [f for f in output_files if f.suffix == ".bit"]
        xsa_files = [f for f in output_files if f.suffix == ".xsa"]
        ltx_files = [f for f in output_files if f.suffix == ".ltx"]

        dest_dir.mkdir(parents=True, exist_ok=True)

        project_name = "-".join(project.split("/"))

        if len(bit_files) == 0:
            self.log.warning("No .bit files found in HoG output")
        elif len(bit_files) > 1:
            self.log.warning("Multiple .bit files found in HoG output")
            for bit_file in bit_files:
                self.log.info(f"- {bit_file.as_posix()!r}")
                if "pld" in bit_file.name:
                    self.log.info(
                        f"  Full bitstream copied to {(dest_dir / f'{project_name}.bit').as_posix()!r}"
                    )
                    shutil.copy(bit_file, dest_dir / f"{project_name}.bit")
                elif "boot" in bit_file.name:
                    self.log.info(
                        f"  Default partial bitstream copied to {(dest_dir / f'{project_name}_default_partial.bit').as_posix()!r}"
                    )
                    shutil.copy(
                        bit_file, dest_dir / f"{project_name}_default_partial.bit"
                    )
                elif "partial" in bit_file.name:
                    self.log.info(
                        f"  Partial bitstream copied to {(dest_dir / bit_file.name).as_posix()!r}"
                    )
                    shutil.copy(bit_file, dest_dir / bit_file.name)
                else:
                    self.log.warning("  Unknown bitstream type, not copied")
        else:
            self.log.info(
                f"Bitstream copied to {(dest_dir / f'{project_name}.bit').as_posix()!r}"
            )
            shutil.copy(bit_files[0], dest_dir / f"{project_name}.bit")

        if len(xsa_files) == 0:
            self.log.warning("No .xsa files found in HoG output")
        elif len(xsa_files) > 1:
            self.log.warning("Multiple .xsa files found in HoG output")
            for xsa_file in xsa_files:
                self.log.info(f"- {xsa_file.as_posix()!r}")
        else:
            self.log.info(
                f"XSA file copied to {(dest_dir / f'{project_name}.xsa').as_posix()!r}"
            )
            shutil.copy(xsa_files[0], dest_dir / f"{project_name}.xsa")
            shutil.copy(xsa_files[0], dest_dir / f"{project_name}.xsa")

        if len(ltx_files) == 0:
            self.log.warning("No .ltx files found in HoG output")
        elif len(ltx_files) > 1:
            self.log.warning("Multiple .ltx files found in HoG output")
            for ltx_file in ltx_files:
                self.log.info(f"- {ltx_file.as_posix()!r}")
        else:
            self.log.info(
                f"LTX file copied to {(dest_dir / f'{project_name}.ltx').as_posix()!r}"
            )
            shutil.copy(ltx_files[0], dest_dir / f"{project_name}.ltx")

    def setup(self, git: GitCommands | None):
        """
        Add HoG as a submodule at ``Hog/`` and initialize it.

        Args:
            git: Git commands to use. Defaults to the current directory.
        """
        git = git or GitCommands()
        git.submodule_add("https://gitlab.cern.ch/hog/Hog.git", Path("Hog"))
        git.submodule_update()
