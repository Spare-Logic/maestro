<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# RPU firmware

Build RPU applications with Bender dependencies and Maestro's built-in Vitis
Python scripts (`rpu_setup`, `rpu_create`, `rpu_build`).

## Prerequisites

- Vitis on `PATH`
- An exported hardware XSA (e.g. from the [Vivado / HoG](vivado-and-hog.md) step)
- Git + Bender

## Environment variables

The built-in scripts read process environment, not `maestro.yml`. Set them in
the workflow before calling Vitis:

| Variable | Role |
|---|---|
| `RPU_ROOT_DIR` | Firmware project root |
| `RPU_XSA_FILE` | Path to the XSA |
| `RPU_DOMAIN_LIBRARIES` | Colon-separated domain libraries |
| `RPU_APP_NAME` | Application name |
| `RPU_APP_SOURCES` | Colon-separated source globs / paths |

## Pattern

```python
import os
from pathlib import Path

from maestro.commands import BenderCommands, GitCommands, VitisCommands
from maestro.logging import setup_logging
from maestro.models import CommandConfig

log = setup_logging()
root = Path("rpu_firmware")

os.environ["RPU_ROOT_DIR"] = root.as_posix()
os.environ["RPU_XSA_FILE"] = (root / "hardware/design.xsa").as_posix()
os.environ["RPU_APP_NAME"] = "test_app"
# ... other RPU_* ...

git = GitCommands()
bender = BenderCommands(CommandConfig(cwd=root))
vitis = VitisCommands()

bender.update()
vitis.run_python_script(VitisCommands.get_builtin("rpu_setup"))
vitis.run_python_script(VitisCommands.get_builtin("rpu_create"))
vitis.run_python_script(VitisCommands.get_builtin("rpu_build"))
```

`VitisCommands.get_builtin(name)` resolves scripts shipped under
`maestro.assets.vitis`.
