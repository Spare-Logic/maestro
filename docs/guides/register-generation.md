<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Register generation

Generate HDL, software, simulation, and Markdown register artifacts with
`EmbGenCommands`, typically through `UVExecutor` so `embgen` runs via `uv`.

## Prerequisites

- Git access to the hardware repo
- `embgen` available to `uv` (Maestro already depends on it)

## Pattern

Replace the example repository URL with your hardware repository and adapt the
YAML and output paths to its layout.

```python
from pathlib import Path

from maestro.commands import EmbGenCommands, GitCommands
from maestro.executors import UVExecutor
from maestro.logging import setup_logging
from maestro.models import CommandConfig

log = setup_logging()
root = Path("project")

git = GitCommands()
git.clone("git@example.com:your-group/axis_windowing.git", root)

embgen = EmbGenCommands(CommandConfig(cwd=root), executor=UVExecutor())
yml = root / "sources" / "embgen" / "axis_windowing.yml"

embgen.generate(yml, ["hjson"], root / "sources/hdl/regs")
embgen.generate(yml, ["h", "py"], root / "sources/sw/regs")
embgen.generate(yml, ["md"], root / "docs")
```

`generate` takes an embgen YAML config, a list of target flags (`hjson`, `h`,
`py`, `md`, ...), and an output directory.
