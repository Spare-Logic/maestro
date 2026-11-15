# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import shlex
from subprocess import PIPE, STDOUT, Popen

from ..models import CommandConfig
from .base import Executor


class BashExecutor(Executor):
    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        if isinstance(args, str):
            args = ["bash", "-lc", args]
        else:
            args = ["bash", "-c", shlex.join(args)]

        return Popen(
            args, stdout=PIPE, stderr=STDOUT, text=True, cwd=cfg.cwd, env=self._env(cfg)
        )
