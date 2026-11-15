<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Getting started

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for install and development

Tooling used by the workflow guides (install what your workflow needs):

- Git, [Bender](https://github.com/pulp-platform/bender), [embgen](https://github.com/CedricHirschi/embgen)
- AMD Vitis / Vivado (for FPGA and RPU workflows)
- Apptainer (for Yocto-in-container workflows)
- CERN [HoG](https://gitlab.com/hog-cern/Hog) (pulled as a submodule in FPGA projects)

The guide snippets need your own project repositories and tool paths. Complete
workflow examples will be published in [separate repositories](examples/index.md).

## Install

From the repository root:

```bash
uv sync
```

That installs Maestro, its Python dependencies, and the development tools.

## Minimal script

```python
from pathlib import Path

from maestro.commands import BenderCommands, GitCommands, VitisCommands
from maestro.logging import setup_logging
from maestro.models import CommandConfig

log = setup_logging()

project_dir = Path("project")
git = GitCommands()
repo = git.clone("git@example.com:group/project.git", project_dir)

bender = BenderCommands(CommandConfig(cwd=repo.path))
bender.update()

vitis = VitisCommands()
vitis.run_python_script(VitisCommands.get_builtin("rpu_build"))
```

Every command wrapper runs subprocesses in a configured working directory,
captures stdout/stderr, raises `CommandError` on failure (unless configured
otherwise), and appends command output under the current Maestro run directory.

## Use the CLI

The same wrappers are available from the shell:

```bash
uv run maestro --help
uv run maestro --cwd project git sha --short
```

See [CLI](cli.md) for how Python signatures map to flags.

## Configuration

Optional YAML next to where you invoke the script:

| File | Purpose |
|---|---|
| `maestro.yml` | Shared project defaults (committed) |
| `maestro.local.yml` | Machine-specific overrides (gitignored) |

Copy `maestro.local.yml.example` to `maestro.local.yml` for local overrides.
See [Configuration](concepts/configuration.md) and, for running commands in
containers, [Executors](concepts/executors.md).

## Browse these docs locally

```bash
make docs_serve
```

Or build once with `make docs_build`.
