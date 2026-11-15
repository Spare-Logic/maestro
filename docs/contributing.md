<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Contributing

## Setup

Requirements: Python >= 3.11 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras
```

## Development commands

```bash
make format      # ruff format
make check       # ruff check --fix
make typecheck   # ty check
make pre-commit  # prek hooks (REUSE, YAML/TOML checks, whitespace, ...)
make lint        # all of the above
make test        # pytest
make license     # add SPDX headers and run reuse lint
```

Or the underlying tools:

```bash
uv run ruff format
uv run ruff check --fix
uv run ty check
uv run prek run --all-files
uv run pytest
```

CI (`.github/workflows/ci.yml`) runs on Linux with Python 3.12. It checks the
lockfile, formatting, lint, types, and REUSE compliance, runs the tests, and builds
the documentation. Test reports and the built documentation are available as
workflow downloads. A [GitLab CI template](https://github.com/Spare-Logic/maestro/blob/main/docs/templates/gitlab-ci.yml)
is available for downstream FPGA projects. Run `make lint` and `make test` before pushing.

## Tests

- Linux is the reference platform. A few tests assume POSIX and fail on a
  Windows host; that is known, not a regression. On Windows, run the suite in WSL.
- Every bug fix gets a test that fails without the fix.
- Vendor tools (Vivado, Vitis, HoG, Bender, embgen, Docker, Apptainer) are not
  available in CI. Prefer real child processes with fake tools: a fake binary on
  `PATH`, `printf "[%s]"` to show argv, or a recording executor that returns a
  `CommandResult`.
- Tests that call `load_config(tmp_path)` change global state.

## Code style

- Google-style docstrings with `Args:` and `Returns:`. The [CLI](cli.md) builds
  `--help` from them, and the API reference is generated from them.
- Comments explain why, not what.
- Run commands through `Commands.run`, not `self.executor.run`, so logging and
  the wrapper's `CommandConfig` apply.
- Pass argv as a list; never join arguments with spaces. A single string is a
  shell script.

## Commits and pull requests

- Commit subjects are imperative, sentence case, without a trailing period, e.g.
  `Resolve Commands cwd once so per-call configs don't re-apply it`.
- One fix per commit.
- Pull request descriptions have three parts: **Summary** (one subsection per
  change, with the user-visible effect), **Tests** (new tests and the Linux
  result), and **Notes** (limits, what was not run).

## AI-assisted contributions

AI coding assistants are welcome. The rules above apply unchanged: you are
responsible for what you submit, it must pass lint and tests, and bug fixes need
a test that fails without the fix. Say in the pull request if a substantial
part was generated. See [Use of AI](https://github.com/Spare-Logic/maestro#use-of-ai)
in the README.

## Documentation

```bash
make docs_serve   # live preview
make docs_build   # static site under site/
```

Edit Markdown under `docs/` and navigation in `mkdocs.yml`. API pages use
mkdocstrings; prefer improving docstrings in `src/maestro/` when the reference
output is thin. When you change a signature, check `docs/guides/` for examples
that call it.

## License headers

Contributions are accepted under the project license,
[Apache-2.0](https://github.com/Spare-Logic/maestro/blob/main/LICENSES/Apache-2.0.txt).

Every file carries an SPDX header (REUSE is enforced by the `prek` hooks).
`make license` adds headers to known paths and runs `reuse lint`. When you add
a file, add yourself as `SPDX-FileContributor`, and add your name to the
"Authors and contributors" list in the README. Files that cannot carry a header
(`README.md`, `uv.lock`, images) are covered in `REUSE.toml`.
