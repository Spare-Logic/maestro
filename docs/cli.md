<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# CLI

Every command wrapper is also reachable from the shell. The CLI is generated
from the `*Commands` classes in `maestro.commands`: their signatures become the
flags, and their Google-style docstrings become the `--help` text.

```bash
uv run maestro --help
```

`meastro` and `mao` are aliases for `maestro`.

## Command shape

```text
maestro [--cwd DIR] <tool> [constructor flags] <method> [method flags] [positionals]
```

| Python | CLI |
|---|---|
| `GitCommands` | `maestro git` |
| `GitCommands.sha(short=True)` | `maestro git sha --short` |
| `HoGCommands.workflow("vivado/abacus", recreate=True)` | `maestro hog workflow vivado/abacus --recreate` |
| `GitCommands.clone(url, "out")` | `maestro git clone URL out` or `maestro git clone --repo-url URL --dest out` |
| `YoctoCommands("yocto/2025.2").bitbake("petalinux-image-minimal")` | `maestro yocto --yocto-workdir yocto/2025.2 bitbake petalinux-image-minimal` |
| `CommandConfig(cwd=DIR)` | `--cwd DIR` (before the tool) |

Mapping rules:

- Method and argument names: `snake_case` becomes `kebab-case` (`submodule_update` -> `submodule-update`, `--repo-url`)
- Every parameter is a flag. Parameters without a default are required.
- Required method parameters can also be given by position, in signature order. Flags and positional values can be combined, but positional values must stay together (`clone URL --dest out` works, `clone URL --checkout main out` does not). A list takes every value the required parameters after it don't need. Put `--` before values that start with `-`.
- Constructor parameters and required values that are not strings, paths or lists of them stay flags.
- `bool` parameters become `--x` / `--no-x`
- `list[...]` parameters accept several values (`maestro verible format --patterns 'rtl/*.sv' 'tb/*.sv'`)
- `*args` parameters take the positional values left over.
- `Path` parameters are converted. `str | Path` stays a string.
- A parameter named `help` is exposed as `--show-help`
- Constructor parameters such as `--executor-id` go between the tool and the method

## Output and exit codes

- Logs go to **stderr**, and command output is streamed there as well
- Return values go to **stdout**, so the CLI pipes cleanly: `maestro git sha --short > rev.txt`. Lists are printed one item per line, and sets are sorted first.
- A method that returns a `CommandResult` exits with its return code
- Any exception is logged as one line, exits with `1`, and the traceback goes to the run's `maestro.log`

Executors come from `maestro.yml` (see [Executors](concepts/executors.md)), so
the same CLI call can run on the host or in a container without code changes.
