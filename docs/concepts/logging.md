<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Logging

Call `setup_logging()` once at the start of a workflow script.

```python
from maestro.logging import setup_logging

log = setup_logging()
log.info("starting workflow")
```

## What it does

1. Reads `log.*` settings from the loaded [configuration](configuration.md)
2. Creates the run directory's log folder
3. Attaches a Rich console handler (writing to **stderr**) and a file handler writing `maestro.log`
4. Replays records logged before the call (they are buffered) onto both handlers

Because the console goes to stderr, stdout stays free for results. The
[CLI](../cli.md) relies on this. If `setup_logging()` is never called, warnings
and errors still reach stderr through a fallback handler.

Logger hierarchy uses the `maestro` root. Command wrappers add children such as
`maestro.cmd.git` and `maestro.cmd.hog`.

## Command logs

Each `Commands.run(...)` appends argv and captured lines to:

```text
.maestro/runs/<timestamp>/logs/<commandname>.log
```

for example `git.log`, `hog.log`, `yocto.log`. These files are always written.
Console noise can be reduced through `CommandConfig`:

| Flag | Effect on the console |
|---|---|
| `silent=True` | Hide the command's output lines. The command line and errors are still logged. |
| `suppress=True` | Log nothing at all for the command |

Pass a `CommandConfig` as the wrapper's default, or as `cfg=` to `run(...)` for a single call.

## Levels

`log.level` controls the console and root logger (default `INFO`). The run file
handler always records at `DEBUG` so a quiet console still leaves a detailed
trace on disk.
