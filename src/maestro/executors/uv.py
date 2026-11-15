# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from subprocess import PIPE, STDOUT, Popen

from ..models import CommandConfig
from .base import Executor


class UVExecutor(Executor):
    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        if isinstance(args, str):
            args = ["uv", "run", args]
        else:
            args = ["uv", "run"] + args

        return Popen(
            args, stdout=PIPE, stderr=STDOUT, text=True, cwd=cfg.cwd, env=self._env(cfg)
        )
