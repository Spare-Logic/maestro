<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Yocto and Apptainer

Yocto builds run inside an Apptainer image built from Maestro's built-in
`yocto.def`. `ApptainerExecutor` builds/caches the SIF and remaps host paths;
`YoctoCommands` runs `repo` and `source setupsdk && ...` in that environment.

## Prerequisites

- Apptainer
- For full Kria builds: an XSA and RPU ELF, plus binds for site tools
  (e.g. `/usr/pack` and PetaLinux/Vitis pack paths)

## Smoke test

A minimal script that only checks that the container runs:

```python
from pathlib import Path

from maestro.commands import Commands
from maestro.executors import ApptainerExecutor, apptainer_def
from maestro.logging import setup_logging
from maestro.models import CommandConfig

log = setup_logging()
root = Path(__file__).parent

apptainer = ApptainerExecutor().configure(
    def_file=apptainer_def("yocto"),
    workdir_host=root,
)
commands = Commands(CommandConfig(cwd=root), executor=apptainer)
commands.run("ls", "-lah")
```

`apptainer_def("yocto")` finds the packaged definition. The SIF is cached under
`.maestro/cache/apptainer/yocto.sif` (see [Configuration](../concepts/configuration.md)).

## Full Yocto workflow

```python
from pathlib import Path

from maestro.config_global import global_config
from maestro.commands import YoctoCommands
from maestro.executors import ApptainerExecutor, apptainer_def

root = Path("yocto")
cache = global_config.yocto_cache_dir

apptainer = ApptainerExecutor().configure(
    def_file=apptainer_def("yocto"),
    workdir_host=root,
    binds=[
        (Path("/usr/pack"), Path("/usr/pack"), "ro"),
        (
            cache / "build" / "downloads",
            Path("/workspace/yocto/2025.2/build/downloads"),
            "rw",
        ),
        (
            cache / "build" / "sstate-cache",
            Path("/workspace/yocto/2025.2/build/sstate-cache"),
            "rw",
        ),
    ],
)

yocto = YoctoCommands(yocto_workdir=root / "yocto/2025.2", executor=apptainer)
yocto.repo_init()
yocto.bitbake("petalinux-image-minimal")
```

Bind mounts keep downloads and sstate on the host cache while the container
workdir maps to `/workspace`. `bitbake(target)` is shorthand for
`run_environment(f"bitbake {target}")`, which runs after sourcing `setupsdk`.

## Configure in `maestro.yml` instead

You can declare the executor and work directory in YAML instead of building
them in code:

```yaml
executors:
  yocto_env:
    type: apptainer
    def_file: yocto
    workdir_host: yocto
    binds:
      - [/usr/pack, /usr/pack, ro]

commands:
  yocto:
    executor: yocto_env
    yocto_workdir: yocto/2025.2
```

`YoctoCommands()` then needs no arguments, and the CLI works the same way:

```bash
uv run maestro yocto bitbake --target petalinux-image-minimal
```

See [Executors](../concepts/executors.md).
