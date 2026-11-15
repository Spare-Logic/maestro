# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from subprocess import Popen

from ..models import CommandConfig
from .base import BaseExecutor, join_args


class PrefixExecutor(BaseExecutor):
    def __init__(self):
        super().__init__()
        self.prefix: str = ""

    def configure(self, prefix: str):
        self.prefix = prefix

    def _start_process(
        self,
        cfg: CommandConfig,
        args: list[str] | str,
    ) -> Popen:
        return super()._start_process(cfg, f"{self.prefix} {join_args(args)}")
