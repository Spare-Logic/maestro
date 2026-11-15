<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Configuration

Configuration loads when `maestro.config_global` is imported. By default Maestro
reads from the invocation directory (current working directory), unless you pass
a path to `load_config()`.

```python
from pathlib import Path

from maestro.config_global import load_config

cfg = load_config(Path("/path/to/project"))
```

## Sources and override order

Later sources win:

1. Dataclass defaults in `Config`
2. `maestro.yml`
3. `maestro.local.yml`

| File | Purpose |
|---|---|
| `maestro.yml` | Shared project defaults (committed) |
| `maestro.local.yml` | Machine-specific overrides (gitignored) |

Copy `maestro.local.yml.example` to `maestro.local.yml` for local overrides.

## Fields

| Field | Default | Notes |
|---|---|---|
| `paths.root` | `.maestro` | Root directory for Maestro-generated state |
| `log.level` | `INFO` | Console and root logger level |
| `log.subdir` | `logs` | Log directory inside each run directory |
| `log.format` | `%(name)s: %(message)s` | Console format |
| `log.format_file` | `%(asctime)s %(name)s %(levelname)s - %(message)s` | File format |
| `log.datefmt` | `[%X]` | Console date format |
| `log.datefmt_file` | `[%Y-%m-%d %H:%M:%S]` | File date format |
| `apptainer.cache_subdir` | `apptainer` | Under `paths.cache_dir` |
| `yocto.cache_subdir` | `yocto` | Under `paths.cache_dir` |
| `executors` | `{}` | Named executor definitions, see [Executors](executors.md) |
| `commands` | `{}` | Per-command executor binding and options (e.g. `yocto.yocto_workdir`) |

## Layout on disk

```text
<invocation_dir>/<paths.root>/
  runs/<timestamp>/<log.subdir>/   # maestro.log + per-command logs
  cache/apptainer/                 # built .sif images
  cache/yocto/                     # optional download/sstate binds
```

Derived helpers on `Config`:

- `paths.root_dir`, `paths.run_dir`, `paths.cache_dir`
- `log_dir`, `apptainer_cache_dir`, `yocto_cache_dir`

## Example YAML

`maestro.yml`:

```yaml
paths:
  root: .maestro

log:
  level: INFO
```

`maestro.local.yml`:

```yaml
log:
  level: DEBUG

executors:
  yocto_env:
    type: apptainer
    def_file: yocto
    workdir_host: yocto

commands:
  yocto:
    executor: yocto_env
    yocto_workdir: yocto/2025.2
```

`maestro.local.yml` is deep-merged over `maestro.yml`. Lists are replaced, not appended.

Subprocess environment variables (Vitis/RPU/RAUC, ...) are not part of these
files. Set them in the workflow script, or per command with
`CommandConfig(env={...})`. That dict is merged over the host environment, and
with `isolated=True` it *replaces* the host environment, including `PATH`.
