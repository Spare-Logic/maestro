# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import maestro.logging as logging_module
from maestro.config_global import load_config
from maestro.logging import setup_logging


def test_log_buffer_installed_before_setup():
    assert logging_module._buffer in logging_module._maestro_logger.handlers


def test_setup_logging_replays_buffered_config_logs(capsys):
    load_config()
    setup_logging()
    assert logging_module._buffer not in logging_module._maestro_logger.handlers
    assert "Loading configuration" in capsys.readouterr().err


def test_buffered_logs_reach_log_file(tmp_path, monkeypatch):
    from maestro.config_global import global_config

    monkeypatch.setattr(global_config.paths, "_invocation_dir", tmp_path)
    logging_module._maestro_logger.addHandler(logging_module._buffer)
    logging_module._maestro_logger.debug("early debug line")
    setup_logging()
    log_file = global_config.paths.run_dir / global_config.log.subdir / "maestro.log"
    assert "early debug line" in log_file.read_text()


def test_dispatch_error_logged_with_traceback(tmp_path, monkeypatch):
    from maestro.cli.dispatcher import dispatch
    from maestro.config_global import global_config

    monkeypatch.setattr(global_config.paths, "_invocation_dir", tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    monkeypatch.setattr("sys.argv", ["maestro", "--cwd", str(tmp_path), "git", "sha"])
    assert dispatch() == 1
    log_file = global_config.paths.run_dir / global_config.log.subdir / "maestro.log"
    text = log_file.read_text()
    assert "CommandError" in text and "Traceback" in text


def test_fallback_skipped_when_root_configured(monkeypatch):
    import logging

    record = logging.makeLogRecord({"levelno": logging.WARNING})
    monkeypatch.setattr(logging.root, "handlers", [])
    assert logging_module._fallback.filter(record)
    monkeypatch.setattr(logging.root, "handlers", [logging.NullHandler()])
    assert not logging_module._fallback.filter(record)
