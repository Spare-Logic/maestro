# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PathsConfig:
    _invocation_dir: Path = field(default_factory=Path.cwd, init=False)
    _run_timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"), init=False
    )
    root: str = ".maestro"

    @property
    def root_dir(self) -> Path:
        dir = self._invocation_dir / self.root
        dir.mkdir(parents=True, exist_ok=True)
        return dir

    @property
    def run_dir(self) -> Path:
        dir = self.root_dir / "runs" / self._run_timestamp
        dir.mkdir(parents=True, exist_ok=True)
        return dir

    @property
    def cache_dir(self) -> Path:
        dir = self.root_dir / "cache"
        dir.mkdir(parents=True, exist_ok=True)
        return dir


@dataclass
class LogConfig:
    level: str = "INFO"
    subdir: str = "logs"
    format: str = "%(name)s: %(message)s"
    format_file: str = "%(asctime)s %(name)s %(levelname)s - %(message)s"
    datefmt: str = "[%X]"
    datefmt_file: str = "[%Y-%m-%d %H:%M:%S]"


@dataclass
class ApptainerConfig:
    cache_subdir: str = "apptainer"


@dataclass
class YoctoConfig:
    cache_subdir: str = "yocto"


@dataclass
class Config:
    paths: PathsConfig = field(default_factory=PathsConfig)
    log: LogConfig = field(default_factory=LogConfig)
    apptainer: ApptainerConfig = field(default_factory=ApptainerConfig)
    yocto: YoctoConfig = field(default_factory=YoctoConfig)
    executors: dict[str, Any] = field(default_factory=dict)
    commands: dict[str, Any] = field(default_factory=dict)

    @property
    def log_dir(self) -> Path:
        dir = self.paths.run_dir / self.log.subdir
        dir.mkdir(parents=True, exist_ok=True)
        return dir

    @property
    def apptainer_cache_dir(self) -> Path:
        dir = self.paths.cache_dir / self.apptainer.cache_subdir
        dir.mkdir(parents=True, exist_ok=True)
        return dir

    @property
    def yocto_cache_dir(self) -> Path:
        dir = self.paths.cache_dir / self.yocto.cache_subdir
        dir.mkdir(parents=True, exist_ok=True)
        return dir
