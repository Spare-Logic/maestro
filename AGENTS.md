<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# AGENTS.md

Instructions for coding agents working on maestro. Humans: see `docs/contributing.md`.

## Project

maestro orchestrates embedded Linux workflows for AMD ZynqMP SoCs (Vivado/HoG, Vitis, Yocto,
embgen, Verible, SD-card flashing). Python ≥3.11, built with `uv`.

- `src/maestro/commands/`: tool wrappers (`GitCommands`, `VitisCommands`, …), all subclasses of `Commands`.
- `src/maestro/executors/`: how a command is started (`BaseExecutor`, `PrefixExecutor`, `BashExecutor`,
  `UVExecutor`, `DockerExecutor`, `ApptainerExecutor`), built from YAML by `Executor.factory`.
- `src/maestro/cli/`: argparse built from method signatures and Google docstrings.
- `src/maestro/config_global.py`: `maestro.yml` + `maestro.local.yml`, loaded at import time.
- `src/maestro/assets/`: Tcl, Vitis Python scripts and the Apptainer definition shipped in the wheel.

## Commands

```sh
uv sync --all-extras   # set up
make lint              # ruff format, ruff check --fix, ty check, prek (REUSE headers etc.)
make test              # uv run pytest
```

CI (`.github/workflows/ci.yml`) runs on Linux with Python 3.12 and uv 0.13.4.
It checks the lockfile, formatting, lint, types, and REUSE compliance, runs the tests,
and builds the documentation. `docs/templates/gitlab-ci.yml` provides a template
for downstream FPGA projects on GitLab. Linux is the reference platform for test results.

## Contracts that must not regress

Keep these behavior contracts when changing wrappers and executors.

- **Argv.** `run(a, b, …)` passes each element as exactly one argument. A single string is a shell
  script (`bash -lc` in Bash/Apptainer, the host shell in Base). Never join a list with spaces:
  use `join_args` (`executors/base.py`), `shlex.join` for `bash -c`. Pass "no value" to Tcl as
  `-`, not `""`.
- **Working directory.** `Commands.__init__` resolves `cfg.cwd` once. A per-call `cfg` with a
  relative cwd resolves against the wrapper's cwd. Derive per-call configs with
  `replace(self.cfg, …)`; don't build a fresh `CommandConfig` and lose cwd, env or flags.
- **Path arguments** to wrapper methods are relative to the process cwd (intended). Where such a
  path reaches a tool running in another directory, resolve it first.
- **Environment.** `cfg.env` overlays the inherited environment; `isolated=True` drops it.
  Container executors pass `--env`.
- **Containers.** A host path that a command sees inside a container goes through
  `self.executor.container_path(path)` (identity on host executors).
- **Logging.** Run commands through `Commands.run`, not `self.executor.run`, so the per-tool log
  and the wrapper's config apply. `silent=True` hides output lines only; the command line is still logged.
- **Windows.** On Windows the host shell is `cmd.exe`. `list2cmdline` does not escape
  `& | > ^ %`, so arguments with those characters are still unsafe there.

## Tests

- Every bug fix gets a test that fails without the fix. Prefer real child processes with fake
  tools: a fake binary on `PATH`, `printf "[%s]"` to show argv, or a recording executor that
  returns a `CommandResult`. Vendor tools (Vivado, HoG, bender, embgen, Docker, Apptainer) are not
  available in CI.
- Tests must pass on Linux. Several tests in `tests/test_executor_factory.py` and `tests/test_yocto.py`
  assume POSIX and fail on a Windows host; that is known, not a regression.
- Tests that call `load_config(tmp_path)` change global state; the suite has no reset fixture yet.

## Style

- Every file starts with the SPDX header used in the repo (REUSE is enforced by `prek`).
- Google-style docstrings with `Args:` and `Returns:`; the CLI builds `--help` from them.
- Match the surrounding code: comments only for the why, no speculative options.
- Commit subjects: imperative, sentence case, no trailing period
  (`Resolve Commands cwd once so per-call configs don't re-apply it`). One fix per commit.
- Pull request descriptions: Summary (one subsection per fix, with the user-visible effect),
  Tests (new tests and the Linux result), Notes (limits, what was not run).

## Before calling a change done

- `make lint` is clean and `make test` passes on Linux. On Windows, use WSL.
- New behavior or a bug fix has a test that fails without it.
- Every caller of a changed function was checked (`rg`), including `docs/guides/`.
- Report limits honestly: vendor tools are not available in CI, and Windows shell quoting
  needs verification on a Windows host.
