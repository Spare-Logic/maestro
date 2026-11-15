# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import shlex
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen

from ..config_global import global_config
from ..models import CommandConfig
from .base import Executor

APPTAINER_DEF_DIR = Path(__file__).resolve().parent.parent / "assets" / "containers"


def apptainer_def(name: str | Path, dir: Path = APPTAINER_DEF_DIR) -> Path:
    builtin = dir.glob("*.def")

    for def_file in builtin:
        if def_file.name == name or def_file.stem == name:
            return def_file

    def_file = Path(name)
    if def_file.exists():
        return def_file
    raise ValueError(
        f"No built-in definition found for '{name}'. Available definitions: {[f.stem for f in builtin]}"
    )


class ApptainerExecutor(Executor):
    def __post_init__(self):
        self.sif_file: Path | None = None
        self.def_file: Path | None = None
        self.workdir_host: Path | None = None
        self.workdir_container: Path | None = None
        self.binds: list[tuple[str | Path, str | Path, str]] = []

    def configure(
        self,
        def_file: str | Path,
        workdir_host: str | Path,
        workdir_container: str | Path = Path("/workspace"),
        binds: list[tuple[str | Path, str | Path, str]] | None = None,
    ) -> "ApptainerExecutor":
        self.def_file = apptainer_def(def_file)
        self.workdir_host = Path(workdir_host).resolve()
        self.workdir_container = Path(workdir_container).resolve()
        self.binds = list(binds) if binds else []

        if self.binds:
            self.log.debug(f"Configuring {len(self.binds)} bind mounts:")
            for host_dir, container_dir, mode in self.binds:
                self.log.debug(f"- {host_dir} -> {container_dir} ({mode})")

        self.sif_file = global_config.apptainer_cache_dir / f"{self.def_file.stem}.sif"

        workdir = (
            self.workdir_host.as_posix(),
            self.workdir_container.as_posix(),
            "rw",
        )
        if workdir not in self.binds:
            self.log.debug(f"Adding bind mount for working directory: {workdir!r}")
            self.binds.append(workdir)

        return self

    def _up_to_date(self) -> bool:
        if self.sif_file is None or self.def_file is None:
            raise ValueError("ApptainerExecutor is not properly configured")
        if not self.sif_file.exists():
            return False
        return self.sif_file.stat().st_mtime >= self.def_file.stat().st_mtime

    def _build(self) -> None:
        if self.sif_file is None or self.def_file is None:
            raise ValueError("ApptainerExecutor is not properly configured")

        cmd = [
            "apptainer",
            "build",
            self.sif_file.as_posix(),
            self.def_file.as_posix(),
        ]

        # Copy old sif file if existing:
        if self.sif_file.exists():
            backup_sif = self.sif_file.with_suffix(".sif.bak")
            self.log.debug(f"Backing up existing SIF file to {backup_sif}")
            self.sif_file.replace(backup_sif)

        self.log.info(
            f"Building Apptainer container from {self.def_file} to {self.sif_file}..."
        )
        build_proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True)
        build_output = []
        while True:
            line = (
                build_proc.stdout.readline() if build_proc.stdout is not None else None
            )
            if not line and build_proc.poll() is not None:
                break
            if line:
                build_output.append(line.strip())
                self.log.debug(f"  | {line.strip()}")

        if build_proc.returncode != 0:
            self.log.error("Apptainer build failed with output:")
            for line in build_output:
                self.log.error(f"  | {line}")
            raise RuntimeError("Apptainer build failed")

    def container_path(self, path: Path) -> Path:
        if self.workdir_host is None or self.workdir_container is None:
            raise ValueError("ApptainerExecutor is not properly configured")

        host_relative = (
            path.relative_to(self.workdir_host) if path.is_absolute() else path
        )
        result = self.workdir_container / host_relative
        self.log.debug(f"Mapping host path {path.as_posix()} -> {result.as_posix()}")
        return result

    def _setup(self, cfg: CommandConfig):
        if self.workdir_container is None or self.sif_file is None:
            raise ValueError("ApptainerExecutor is not properly configured")

        if not self._up_to_date():
            self._build()

        self.log.debug(
            f"Executing with pwd {self.container_path(cfg.cwd).as_posix()} inside container {self.sif_file.as_posix()}"
        )

        appt_args = [
            "apptainer",
            "exec",
            "--pwd",
            self.container_path(cfg.cwd).as_posix(),
            "--ipc",
            "--writable-tmpfs",
        ]
        if cfg.isolated:
            appt_args.append("--cleanenv")

        for host_path, container_path, mode in self.binds:
            bind_path = (
                f"{Path(host_path).resolve().as_posix()}:"
                f"{Path(container_path).resolve().as_posix()}:{mode}"
            )
            appt_args.extend(["--bind", bind_path])

        for key, value in cfg.env.items():
            appt_args.extend(["--env", f"{key}={value}"])

        appt_args.append(self.sif_file.as_posix())

        return appt_args

    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        appt_args = self._setup(cfg)

        if isinstance(args, str):
            args = ["bash", "-lc", args]
        else:
            args = ["bash", "-c", shlex.join(args)]

        return Popen(appt_args + args, stdout=PIPE, stderr=STDOUT, text=True)
