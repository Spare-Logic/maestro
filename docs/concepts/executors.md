<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Executors

An executor decides **where** a command runs: on the host, through `uv run`,
or inside a Docker or Apptainer container. Command wrappers stay the same. Only
the executor changes.

| Type | Class | Options |
|---|---|---|
| `default` / `base` / `-` | `BaseExecutor` | none: host shell |
| `uv` | `UVExecutor` | none: prefixes `uv run` |
| `bash` | `BashExecutor` | none: runs through `bash -c` |
| `prefix` | `PrefixExecutor` | `prefix` |
| `docker` | `DockerExecutor` | `image`, `workdir_host`, `workdir_container`, `binds`, `cli` |
| `apptainer` | `ApptainerExecutor` | `def_file`, `workdir_host`, `workdir_container`, `binds` |

## Choosing an executor

Highest priority first:

1. `executor=` passed to the command constructor (an executor instance)
2. `executor_id=` passed to the command constructor (an id from `maestro.yml`)
3. The binding under `commands.<name>` in `maestro.yml` / `maestro.local.yml`
4. `default` (`BaseExecutor`)

### In code

```python
from maestro.commands import EmbGenCommands
from maestro.executors import UVExecutor

embgen = EmbGenCommands(executor=UVExecutor())
```

### In YAML

```yaml
executors:
  vitis_env:            # full definition: type + options
    type: docker
    image: vitis:2025.2
    workdir_host: .
    workdir_container: /workspace
    binds:
      - [../cache, /cache, rw]
  yocto_env:
    type: apptainer
    def_file: yocto     # built-in definition, or a path to a .def file
    workdir_host: yocto
  hog_exe: vitis_env    # alias of another id
  py: uv                # shortcut for {type: uv}
  host: default         # explicit host executor

commands:
  vitis: vitis_env      # short form
  hog: hog_exe
  embgen:
    executor: py        # long form, leaves room for per-command options
  yocto:
    executor: yocto_env
    yocto_workdir: yocto/2025.2
```

With this config, `HoGCommands()` runs in the Docker container without any
code change, and so does `maestro hog ...` from the [CLI](../cli.md).

## Resolution rules

- A string value is an **alias** if it names another executor id. Otherwise it
  is a **type** shortcut (`py: uv` is the same as `py: {type: uv}`).
- `default`, `base` and `-` always mean `BaseExecutor`, even if no id is defined
- Alias cycles (`a: b`, `b: a`) raise `ValueError`
- Options are passed to the executor's `configure()` (or `__init__` if it has no `configure()`).
  Unknown options and missing required ones raise `ValueError`.
- An unknown id raises `KeyError`. An unknown type raises `ValueError` that lists the known types.
- `maestro.local.yml` is deep-merged over `maestro.yml`. A list (such as `binds`) is
  **replaced**, not appended, so repeat the full list in the local file.

Executor types are discovered automatically: any `*Executor` class in
`maestro.executors` can be used as a `type:`.
