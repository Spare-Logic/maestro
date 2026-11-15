<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Vivado and HoG

FPGA flows use Bender for dependency scripts and CERN HoG (`./Hog/Do`) for
project create and workflow. Maestro wraps both.

## Prerequisites

- Vivado on `PATH` (or your site's module/`/usr/pack` setup)
- Git, Bender, HoG as a submodule of the hardware project

## Pattern

```python
from pathlib import Path

from maestro.commands import BenderCommands, GitCommands, HoGCommands
from maestro.logging import setup_logging
from maestro.models import CommandConfig

log = setup_logging()
root = Path("vivado")

git = GitCommands()
git.clone("git@example.com:group/vivado.git", root, submodule_update=True)

bender = BenderCommands(CommandConfig(cwd=root))
hog = HoGCommands(CommandConfig(cwd=root))

bender.update()
bender.script("flist", root / "Top/vivado/proj/list/bender.src")

hog.create("vivado/proj")
hog.workflow("vivado/proj")

bits = hog.get_output_files("vivado/proj", "*.bit")
xsas = hog.get_output_files("vivado/proj", "*.xsa")
```

`get_describe` / `get_output_files` resolve HoG's `bin/<group>/<project>-<describe>/`
layout so you can copy bitstreams and XSAs into a shared folder for later stages.

Pass `recreate=True` to `workflow` to rebuild an existing project from scratch
(HoG `-recreate`). From the shell: `maestro --cwd vivado hog workflow --project vivado/proj --recreate`.
