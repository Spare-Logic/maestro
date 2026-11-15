# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Find concrete ``*Suffix`` classes in a package (``GitCommands`` → ``git``)."""

import importlib
import pkgutil
from types import ModuleType
from typing import TypeVar

T = TypeVar("T")


def discover_classes(
    package: ModuleType,
    suffix: str,
    cls: type[T],
    skip_modules: frozenset[str] | set[str] = frozenset(),
) -> dict[str, type[T]]:
    """Generates a mapping short names to classes with a given *suffix* within a *package*.

    Walks immediate submodules of ``package`` (via ``pkgutil.iter_modules``),
    imports each one, and collects types whose names end with ``suffix`` and
    that are defined in that module (not re-exported imports). Protocol classes
    and private modules (names starting with ``_``) are skipped.

    Short names are derived by lowercasing the class name and stripping
    ``suffix`` (case-insensitive), e.g. ``GitCommands`` with suffix
    ``"Commands"`` yields ``"git"``.

    Args:
        package: Package module whose submodules are scanned (must have
            ``__path__``).
        suffix: Class-name suffix to match (e.g. ``"Commands"``,
            ``"Executor"``).
        cls: Base type used to parameterize the returned class map.
        skip_modules: Submodule names to ignore during discovery.

    Returns:
        Mapping from short name to discovered class.

    Examples:
        >>> from maestro import commands
        >>> from maestro.commands.base import Commands
        >>> discover_classes(commands, "Commands", Commands)
        {'git': <class 'maestro.commands.git.GitCommands'>, ...}
    """
    found: dict[str, type[T]] = {}
    needle = suffix.lower()
    for info in pkgutil.iter_modules(package.__path__):
        if info.name in skip_modules or info.name.startswith("_"):
            continue
        module = importlib.import_module(f".{info.name}", package.__name__)
        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                # and issubclass(obj, cls)
                and not getattr(obj, "_is_protocol", False)
                and obj.__name__.endswith(suffix)
                and obj.__module__ == module.__name__
            ):
                found[obj.__name__.lower().removesuffix(needle)] = obj
    return found
