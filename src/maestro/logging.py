# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from logging.handlers import MemoryHandler

from rich.console import Console
from rich.logging import RichHandler

_maestro_logger = logging.getLogger("maestro")
# Fallback so warnings still reach stderr (at exit / when full) if setup_logging() never runs.
# Skipped when the host app configured root logging itself, to avoid duplicates.
_fallback = logging.StreamHandler()
_fallback.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
_fallback.addFilter(
    lambda record: record.levelno >= logging.WARNING and not logging.root.handlers
)
_buffer = MemoryHandler(
    capacity=1024, flushLevel=logging.CRITICAL + 1, target=_fallback
)
_maestro_logger.addHandler(_buffer)
_maestro_logger.setLevel(logging.DEBUG)

from .config_global import global_config


def setup_logging() -> logging.Logger:
    level = getattr(logging, str(global_config.log.level).upper(), logging.INFO)
    log_dir = global_config.paths.run_dir / global_config.log.subdir
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RichHandler(console=Console(stderr=True), show_path=False)
    handler.setFormatter(
        logging.Formatter(global_config.log.format, datefmt=global_config.log.datefmt)
    )

    file_handler = logging.FileHandler(log_dir / "maestro.log")
    file_handler.setFormatter(
        logging.Formatter(
            global_config.log.format_file, datefmt=global_config.log.datefmt_file
        )
    )

    handler.setLevel(level)
    file_handler.setLevel(logging.DEBUG)

    records, _buffer.buffer = _buffer.buffer, []
    _maestro_logger.removeHandler(_buffer)

    logging.basicConfig(level=level, handlers=[handler, file_handler], force=True)
    # Keep DEBUG on the logger so the file gets everything; the console filters by level.
    _maestro_logger.setLevel(logging.DEBUG)

    # Replay startup logs; Logger.handle() applies each handler's level.
    for record in records:
        _maestro_logger.handle(record)

    return _maestro_logger
