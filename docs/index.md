<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# maestro

Python helpers for orchestrating embedded Linux and FPGA workflows, especially
AMD ZynqMP / Kria projects that combine Git, Bender, embgen, Vitis, Vivado/HoG,
Apptainer, and Yocto.

Maestro is a **library** with a generated **CLI**. Workflow scripts import command wrappers,
compose them in Python, and get consistent subprocess execution, logging, path
handling, and configuration. The same wrappers are available from the shell
as `maestro <tool> <method>`.

## What is included

- Command wrappers for `git`, `bender`, `embgen`, `vitis` / Vivado, CERN HoG, Verible, Yocto,
  and disk flashing (`bmaptool`)
- Executors for host shells, `uv run`, Docker, and Apptainer containers, selectable
  per command in `maestro.yml`
- A `maestro` CLI generated from the command wrappers (aliases `meastro`, `mao`)
- Built-in Vitis helper scripts for RPU firmware setup, application creation, and builds
- A built-in Apptainer definition for Yocto workflows
- Shared configuration from `maestro.yml` and `maestro.local.yml`
- Rich console logging plus per-run log files under `.maestro/runs/`

## Who this is for

Engineers who already run ZynqMP toolchains and want Python scripts that clone
repos, generate registers, build FPGA bitstreams, compile RPU firmware, and bake
Yocto images without reinventing subprocess and logging plumbing each time.

## Next steps

- [Getting started](getting-started.md) - install and run a minimal script
- [CLI](cli.md) - run any wrapper from the shell
- [Architecture](concepts/architecture.md) - how commands, executors, and config fit together
- [Executors](concepts/executors.md) - run commands on the host or in containers
- [Guides](guides/register-generation.md) - registers, Vivado/HoG, RPU firmware, Yocto
- [API reference](reference/commands.md) - generated from the package
