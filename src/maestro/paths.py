# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path


def norm_path(path: str | Path, cwd: Path) -> Path:
    result = Path(path)
    if not result.is_absolute():
        result = cwd / result
    return result.resolve()


def norm_path_str(path: str | Path, cwd: Path) -> str:
    return norm_path(path, cwd).as_posix()
