# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

"""CLI: ``GitCommands.clone`` → ``maestro git clone URL DEST`` or ``--repo-url …``."""

import argparse
import inspect
import re
import types
import typing
from pathlib import Path

import maestro.commands as commands_pkg
from maestro.commands import Commands

from ..discover import discover_classes
from ..logging import setup_logging
from ..models import CommandConfig, CommandResult

_SKIP_ARGS = frozenset({
    "self",
    "cfg",
    "executor",
})
_SKIP_METHODS = frozenset({
    # "run",
})


def _members(ann: object) -> set:
    """Flatten (nested) unions into their member types, dropping None."""
    if typing.get_origin(ann) in (typing.Union, types.UnionType):
        return {m for a in typing.get_args(ann) for m in _members(a)}
    return set() if ann is type(None) else {ann}


def _path_type(members: set) -> type:
    # `str | Path` accepts strings as-is, so only convert when str isn't an option
    return Path if Path in members and str not in members else str


def _value_types(param: inspect.Parameter) -> tuple[set, bool]:
    """Types of a parameter's value(s), and whether it takes a list."""
    members = _members(param.annotation)
    lists = [m for m in members if m is list or typing.get_origin(m) is list]
    if not lists:  # list[A] | list[B] -> elements A | B
        return members, False
    return {e for l in lists for a in typing.get_args(l) for e in _members(a)}, True


def _fillable(param: inspect.Parameter) -> bool:
    """Whether a method parameter can be given by position instead of by flag."""
    types = _value_types(param)[0]
    return (
        param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and param.default is inspect.Parameter.empty
        and bool(types)
        and types <= {str, Path}
    )


def _varargs(params: typing.Mapping[str, inspect.Parameter]) -> str | None:
    """Name of the ``*args`` parameter, if there is one."""
    return next(
        (n for n, p in params.items() if p.kind is inspect.Parameter.VAR_POSITIONAL),
        None,
    )


def _flag(name: str) -> str:
    return f"--{'show-help' if name == 'help' else name.replace('_', '-')}"


def _doc(obj: object) -> tuple[str | None, dict[str, str]]:
    """Summary and ``Args:`` entries of a Google-style docstring (``{}`` if absent)."""
    doc = inspect.getdoc(obj)
    if not doc:
        return None, {}
    summary = " ".join(doc.split("\n\n")[0].split())
    args: dict[str, str] = {}
    block = re.search(r"^Args:\n((?:[ \t]+.*\n?|\n)*)", doc, re.MULTILINE)
    if block:
        lines = [l for l in block[1].splitlines() if l.strip()]
        indent = len(lines[0]) - len(lines[0].lstrip()) if lines else 0
        name = None
        for line in lines:
            entry = re.match(r"(\*{0,2}\w+)(?: \(.*?\))?:\s*(.*)", line.strip())
            if len(line) - len(line.lstrip()) == indent and entry:
                name = entry[1].lstrip("*")
                args[name] = entry[2]
            elif name:
                args[name] += " " + line.strip()
    # argparse %-formats help strings
    return summary.replace("%", "%%"), {
        k: v.strip().replace("%", "%%") for k, v in args.items()
    }


def _add(
    parser: argparse.ArgumentParser,
    name: str,
    param: inspect.Parameter,
    help: str | None = None,
    positional: bool = False,
) -> None:
    """Add `inspect` based arg to (sub)parser. `positional` waives the flag's `required`."""
    if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL):
        return
    flag = _flag(name)
    req = param.default is inspect.Parameter.empty
    default = None if req else param.default
    types, is_list = _value_types(param)
    if types == {bool} and not is_list:
        parser.add_argument(
            flag,
            dest=name,
            help=help,
            action=argparse.BooleanOptionalAction,
            default=False if req else default,  # None stays "not given"
        )
    elif is_list:
        parser.add_argument(
            flag,
            dest=name,
            help=help,
            nargs="+" if req else "*",
            default=default,
            required=req and not positional,
            type=_path_type(types),
        )
    else:
        parser.add_argument(
            flag,
            dest=name,
            help=help,
            default=default,
            required=req and not positional,
            type=_path_type(types),
        )


class _HelpFormatter(argparse.HelpFormatter):
    """Show the catch-all's parameter names as they are, without argparse's ``...``."""

    def _format_args(self, action: argparse.Action, default_metavar: str) -> str:
        if action.dest == "_positionals":
            return f"[{action.metavar}]"
        return super()._format_args(action, default_metavar)


def _add_positionals(
    parser: argparse.ArgumentParser,
    params: typing.Mapping[str, inspect.Parameter],
    docs: dict[str, str],
) -> None:
    """Add the single catch-all that `_fill` hands out; one per parameter would
    bind `--script s.tcl a` to the script's slot."""
    names = [
        f"{n.upper()}..." if _value_types(p)[1] else n.upper()
        for n, p in params.items()
        if _fillable(p)
    ]
    text = f"{', '.join(names)} can also be given by flag." if names else ""
    varargs = _varargs(params)
    if varargs:
        names.append(f"{varargs.upper()}...")
    if names:
        parser.add_argument(
            "_positionals",
            nargs="*",
            default=[],
            metavar=" ".join(names),
            help=" ".join(filter(None, [text, docs.get(varargs or "")])) or None,
        )
    parser.set_defaults(_parser=parser)


def _fill(
    ns: argparse.Namespace, params: typing.Mapping[str, inspect.Parameter]
) -> None:
    """Hand positional values to the required parameters not given by flag, in order.

    A list takes what the parameters after it don't need; the rest goes to `*args`.
    """
    # shortcut: assumes one list and no list next to *args, split rules if a method has both
    values = list(getattr(ns, "_positionals", []))
    missing = [
        p for p in params.values() if _fillable(p) and getattr(ns, p.name) is None
    ]
    if len(values) < len(missing):
        names = ", ".join(_flag(p.name) for p in missing[len(values) :])
        ns._parser.error(f"the following arguments are required: {names}")
    for i, param in enumerate(missing):
        types, is_list = _value_types(param)
        count = len(values) - (len(missing) - i - 1) if is_list else 1
        taken, values = values[:count], values[count:]
        convert = _path_type(types)
        setattr(
            ns,
            param.name,
            [convert(v) for v in taken] if is_list else convert(taken[0]),
        )
    varargs = _varargs(params)
    if varargs:
        setattr(ns, varargs, values)
    elif values:
        ns._parser.error(f"unrecognized arguments: {' '.join(values)}")


def dispatch() -> int:
    log = setup_logging()
    classes = discover_classes(commands_pkg, "Commands", cls=Commands)

    # Setup Parser
    parser = argparse.ArgumentParser(prog="maestro")
    parser.add_argument("--cwd", type=Path, default=None)
    tools = parser.add_subparsers(dest="tool", required=True)

    for tool, cls in sorted(classes.items()):
        # Create a subparser per tool
        # cls.__doc__ check: don't inherit the base Commands docstring
        summary, cls_args = _doc(cls) if cls.__doc__ else (None, {})
        init_args = {**cls_args, **_doc(cls.__init__)[1]}
        tool_p = tools.add_parser(tool, help=summary, description=summary)
        for name, param in inspect.signature(cls.__init__).parameters.items():
            if name not in _SKIP_ARGS:
                _add(tool_p, name, param, init_args.get(name))
        methods = tool_p.add_subparsers(dest="method", required=True)

        for name, obj in cls.__dict__.items():
            # Create a subparser per method
            if name.startswith("_") or name in _SKIP_METHODS:
                continue
            fn = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
            if not inspect.isfunction(fn):
                continue
            summary, args = _doc(fn)
            method_p = methods.add_parser(
                name.replace("_", "-"),
                help=summary,
                description=summary,
                formatter_class=_HelpFormatter,
            )
            params = inspect.signature(fn).parameters
            for pname, param in params.items():
                if pname != "self":
                    _add(method_p, pname, param, args.get(pname), _fillable(param))
            _add_positionals(method_p, params, args)

    # parse command into method call
    ns = parser.parse_args()
    cls = classes[ns.tool]
    attr = ns.method.replace("-", "_")
    _fill(ns, inspect.signature(getattr(cls, attr)).parameters)
    constructor_args = {
        n: getattr(ns, n)
        for n in inspect.signature(cls.__init__).parameters
        if n not in _SKIP_ARGS and hasattr(ns, n)
    }
    try:
        obj = cls(
            cfg=CommandConfig(cwd=ns.cwd) if ns.cwd else None,
            **constructor_args,
        )
        method = getattr(obj, attr)

        args, kwargs = [], {}
        for name, param in inspect.signature(method).parameters.items():
            if name == "self" or param.kind is inspect.Parameter.VAR_KEYWORD:
                continue
            if param.kind is inspect.Parameter.VAR_POSITIONAL:
                args.extend(getattr(ns, name))
            elif param.kind is param.POSITIONAL_OR_KEYWORD:
                # as keywords these would collide with the values in *args
                args.append(getattr(ns, name))
            elif hasattr(ns, name):
                kwargs[name] = getattr(ns, name)

        # Execute command
        result = method(*args, **kwargs)
    except Exception as exc:
        log.error(f"{type(exc).__name__}: {exc}")
        # Console shows the message, file keeps the traceback
        log.debug("Traceback:", exc_info=True)
        return 1

    # Output of a CommandResult was already streamed via logging; only values go to stdout
    if isinstance(result, CommandResult):
        return result.returncode
    if isinstance(result, (list, tuple, set, frozenset)):
        items = (
            sorted(result, key=str) if isinstance(result, (set, frozenset)) else result
        )
        for item in items:
            print(item)
    elif result is not None:
        print(result)
    return 0
