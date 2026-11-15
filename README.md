# maestro

Python helpers for orchestrating embedded Linux and FPGA workflows, especially
AMD ZynqMP / Kria projects that combine Git, Bender, embgen, Vitis, Vivado/HoG,
Apptainer, and Yocto.

The package is a **library** with a generated **CLI**. Workflow scripts import wrappers from
`maestro.commands`, compose them in Python, and get consistent subprocess
execution, logging, path handling, and configuration. The same wrappers are available from the shell
as `maestro <tool> <method>`.

## Installation

Requirements: [`uv`](https://docs.astral.sh/uv/)

**Setup:**

```bash
uv sync
```

## Documentation

Full docs (CLI, concepts, guides, examples, API reference):

```bash
make docs_serve
```

Or build a static site with `make docs_build`.

## Quick example

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

Or from the shell (`meastro` and `mao` are aliases):

```bash
uv run maestro --help
uv run maestro --cwd project git sha --short
uv run maestro hog workflow --project vivado/abacus --recreate
```

## Use of AI

Parts of maestro were written or reviewed with AI coding assistants
(Claude Code, Codex, GitHub Copilot).

- **Code.** AI-generated changes are reviewed by a maintainer before merge and
  go through the same checks as any other change: `make lint`, `make test`, and
  a regression test for every bug fix.
- **Audit.** In October 2026 a multi-agent correctness audit flagged suspected
  bugs. Each fix was verified by a test that fails without it; findings that
  could not be reproduced were not acted on.
- **Docs.** Documentation drafts may be AI-assisted and are checked against the
  code.
- **Contributors.** AI tools are welcome. You are responsible for what you
  submit: understand it, test it, and say in the pull request if a substantial
  part was generated. Agent instructions live in `AGENTS.md`.

Vendor-tool behavior (Vivado, Vitis, HoG, Yocto) cannot be tested in CI;
claims about it, AI-written or not, are only trusted once run on real tools.

## Development

```bash
uv sync --all-extras   # dev tools and the optional Verible extra
make lint              # ruff format, ruff check --fix, ty check, prek hooks
make test              # pytest
```

GitHub Actions checks formatting, lint, types, licenses, and tests on Linux,
which is the reference platform for test results, and builds the documentation.
A [GitLab CI template](docs/templates/gitlab-ci.yml) is provided for downstream
FPGA projects. See [Contributing](docs/contributing.md) for tests, license headers,
commit and pull request conventions, and the docs workflow.

## Authors and contributors

- Cedric Hirschi
- Tim Frey

## License

maestro is licensed under the [Apache License 2.0](LICENSES/Apache-2.0.txt).
Copyright 2026 Maestro authors and contributors.

The project follows the [REUSE](https://reuse.software/) specification: every
file carries an SPDX header or is covered by `REUSE.toml`, and the license texts
live in `LICENSES/`. Some documentation figures are licensed under
[CC BY 4.0](LICENSES/CC-BY-4.0.txt); `REUSE.toml` lists which.
