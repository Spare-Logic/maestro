# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, get_origin, get_type_hints

import yaml

from .config_models import Config

log = logging.getLogger("maestro").getChild("cfg")


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        log.warning(f"Ignoring non-mapping YAML root in {path.as_posix()!r}")
        return {}
    return data


def _coerce_path(value: Any) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _apply(config: Any, updates: dict[str, Any]) -> None:
    hints = get_type_hints(type(config))
    field_map = {f.name.lower(): f.name for f in fields(config)}

    for key, value in updates.items():
        name = field_map.get(key.lower())
        if name is None:
            log.warning(f"Unknown configuration field {key!r}")
            continue
        elif name.startswith("_"):
            log.debug(f"Ignoring attempt to set private field {name!r}")
            continue

        hint = hints.get(name, type(getattr(config, name)))
        current = getattr(config, name)

        if is_dataclass(hint) and isinstance(value, dict):
            _apply(current, value)
            continue

        # Plain dict fields (e.g. executors / commands) replace wholesale.
        if (hint is dict or get_origin(hint) is dict) and isinstance(value, dict):
            setattr(config, name, value)
            continue

        if isinstance(value, dict):
            log.debug(f"Ignoring nested dict for non-dataclass field {name!r}")
            continue

        try:
            if hint is Path:
                coerced: Any = _coerce_path(value)
            elif hint is bool:
                coerced = (
                    value
                    if isinstance(value, bool)
                    else str(value).lower() in ("true", "1", "yes")
                )
            elif hint is int:
                coerced = int(value)
            elif hint is float:
                coerced = float(value)
            else:
                coerced = value
            setattr(config, name, coerced)
        except (TypeError, ValueError) as exc:
            log.warning(f"Could not set {name!r}={value!r}: {exc}")


def load_config(invocation_dir: Path | None = None) -> Config:
    invocation_dir = Path.cwd() if invocation_dir is None else Path(invocation_dir)
    updates: dict[str, Any] = {}

    log.info(
        f"Loading configuration from invocation directory {invocation_dir.as_posix()!r}"
    )

    config_file = invocation_dir / "maestro.yml"
    if config_file.is_file():
        log.info(f"Found configuration in {config_file.as_posix()!r}")
        updates = _load_yaml(config_file)

    local_file = invocation_dir / "maestro.local.yml"
    if local_file.is_file():
        log.info(f"Found local configuration in {local_file.as_posix()!r}")
        updates = _deep_merge(updates, _load_yaml(local_file))

    _apply(global_config, updates)
    global_config.paths._invocation_dir = invocation_dir
    return global_config


global_config = Config()
load_config()
