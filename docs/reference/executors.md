<!--
SPDX-FileCopyrightText: 2026 Maestro authors and contributors
SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>

SPDX-License-Identifier: Apache-2.0
-->

# Executors

Executors start subprocesses for command wrappers. Pass an instance as
`executor=` when constructing a `Commands` subclass, or bind them in `maestro.yml` (see
[Executors](../concepts/executors.md)).

::: maestro.executors.base.Executor

::: maestro.executors.base.BaseExecutor

::: maestro.executors.uv.UVExecutor

::: maestro.executors.docker.DockerExecutor

::: maestro.executors.apptainer.ApptainerExecutor

::: maestro.executors.apptainer.apptainer_def

::: maestro.executors.bash.BashExecutor

::: maestro.executors.prefix.PrefixExecutor
