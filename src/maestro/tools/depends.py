# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def file_newer_than_any(file: Path, directory: Path) -> bool:
    if not file.is_file():
        return True
    file_mtime = file.stat().st_mtime
    for dir_file in directory.rglob("*"):
        if dir_file.is_file() and dir_file.stat().st_mtime < file_mtime:
            log.debug(f"File {file.as_posix()!r} is newer than {dir_file.as_posix()!r}")
            return True
    return False


def file_newer_than_file(file: Path, other_file: Path) -> bool:
    if not file.is_file():
        return True
    if not other_file.is_file():
        return True
    file_mtime = file.stat().st_mtime
    other_file_mtime = other_file.stat().st_mtime
    if file_mtime > other_file_mtime:
        log.debug(f"File {file.as_posix()!r} is newer than {other_file.as_posix()!r}")
        return True
    return False
