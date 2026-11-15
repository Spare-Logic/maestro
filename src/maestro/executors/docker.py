# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen

from ..models import CommandConfig
from .base import Executor

DOCKERFILE_DIR = Path(__file__).resolve().parent.parent / "assets" / "containers"


class DockerExecutor(Executor):
    def __post_init__(self):
        self.image: str | None = None
        self.workdir_host: Path | None = None
        self.workdir_container: Path | None = None
        self.binds: list[tuple[str | Path, str | Path, str]] = []
        self.cli: str | None = None

    def configure(
        self,
        image: str,
        workdir_host: Path | str | None = None,
        workdir_container: Path | str | None = None,
        binds: list[tuple[str | Path, str | Path, str]] | None = None,
        cli: str | None = None,
    ) -> "DockerExecutor":
        self.image = image
        self.workdir_host = Path(workdir_host or Path()).resolve()
        self.workdir_container = Path(workdir_container or Path()).resolve()
        self.binds = list(binds) if binds else []
        self.cli = cli or os.environ.get("DOCKER_CMD", "docker")

        if self.binds:
            self.log.debug(f"Configuring {len(self.binds)} bind mounts:")
            for host_dir, container_dir, mode in self.binds:
                self.log.debug(f"- {host_dir} -> {container_dir} ({mode})")

        workdir = (
            self.workdir_host.as_posix(),
            self.workdir_container.as_posix(),
            "rw",
        )
        if workdir not in self.binds:
            self.log.debug(f"Adding bind mount for working directory: {workdir!r}")
            self.binds.append(workdir)

        return self

    def container_path(self, path: Path) -> Path:
        if self.workdir_host is None or self.workdir_container is None:
            raise ValueError("DockerExecutor is not properly configured")

        host_relative = (
            path.relative_to(self.workdir_host) if path.is_absolute() else path
        )
        result = self.workdir_container / host_relative
        self.log.debug(f"Mapping host path {path.as_posix()} -> {result.as_posix()}")
        return result

    def _setup(self, cfg: CommandConfig):
        if self.workdir_container is None or self.image is None or self.cli is None:
            raise ValueError("DockerExecutor is not properly configured")
        self.log.debug(
            f"Executing with pwd {self.container_path(cfg.cwd).as_posix()} inside container of image {self.image}"
        )

        docker_args = [
            self.cli,
            "run",
            "--rm",
            "--workdir",
            self.container_path(cfg.cwd).as_posix(),
        ]

        for host_path, container_path, mode in self.binds:
            bind_path = (
                f"{Path(host_path).resolve().as_posix()}:"
                f"{Path(container_path).resolve().as_posix()}:{mode}"
            )
            docker_args.extend(["--volume", bind_path])

        for key, value in cfg.env.items():
            docker_args.extend(["--env", f"{key}={value}"])

        docker_args.append(self.image)

        return docker_args

    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        docker_args = self._setup(cfg)

        if isinstance(args, str):
            args = [args]

        return Popen(docker_args + args, stdout=PIPE, stderr=STDOUT, text=True)
