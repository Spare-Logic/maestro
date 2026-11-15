# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import vitis

COMPILE_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".s", ".S"}


def update_user_compile_sources(user_config_path: Path, compile_sources: list[str]):
    lines = user_config_path.read_text().splitlines()

    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == "set(USER_COMPILE_SOURCES"
        )
    except StopIteration:
        print(
            f"Error: Could not find USER_COMPILE_SOURCES in {user_config_path.as_posix()!r}."
        )
        exit(1)

    end = start + 1
    while end < len(lines) and lines[end].strip() != ")":
        end += 1

    if end >= len(lines):
        print(
            f"Error: Could not find the end of USER_COMPILE_SOURCES in {user_config_path.as_posix()!r}."
        )
        exit(1)

    new_block = ["set(USER_COMPILE_SOURCES"]
    new_block.extend(f'"{source}"' for source in compile_sources)
    new_block.append(")")

    user_config_path.write_text(
        "\n".join(lines[:start] + new_block + lines[end + 1 :]) + "\n"
    )


def link_app_sources(component_location: str, app_sources: list[Path]) -> list[str]:
    app_src_dir = Path(component_location) / "src"
    # source_root = Path(os.path.commonpath([src.parent for src in app_sources]))
    linked_sources = []

    for src in app_sources:
        rel_path = src.relative_to(src.parent)
        dest = app_src_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() or dest.is_symlink():
            if dest.is_dir() and not dest.is_symlink():
                print(
                    f"Error: Cannot replace directory {dest.as_posix()!r} with a symlink."
                )
                exit(1)
            dest.unlink()

        dest.symlink_to(os.path.relpath(src, start=dest.parent))
        linked_sources.append(rel_path.as_posix())
        print(f"- Linked {src.as_posix()!r} to {dest.as_posix()!r}")

    return linked_sources


def main():
    app_name = os.environ.get("RPU_APP_NAME")
    if not app_name:
        print("Error: RPU_APP_NAME environment variable not set.")
        exit(1)

    root_dir = os.environ.get("RPU_ROOT_DIR")
    if not root_dir:
        print("Error: RPU_ROOT_DIR environment variable not set.")
        exit(1)
    root_dir = Path(root_dir).resolve()
    print(f"Using root directory: {root_dir.as_posix()!r}")

    app_sources = os.environ.get("RPU_APP_SOURCES")
    if not app_sources:
        print("Error: RPU_APP_SOURCES environment variable not set.")
        exit(1)
    app_source_strings = [src.strip() for src in app_sources.split(":") if src.strip()]
    if not app_source_strings:
        print("Error: RPU_APP_SOURCES environment variable is empty.")
        exit(1)

    # Each app source string is a glob pattern. Expand them and collect all matching files.
    app_sources = []
    for src_pattern in app_source_strings:
        matched_files = list(root_dir.glob(src_pattern))
        matched_files = [f for f in matched_files if f.is_file()]
        if not matched_files:
            print(
                f"Error: No files matched the pattern {src_pattern!r} in RPU_APP_SOURCES."
            )
            exit(1)
        app_sources.extend(matched_files)

    if not all(src.is_file() for src in app_sources):
        print("Error: One or more source files in RPU_APP_SOURCES do not exist.")
        for src in app_sources:
            if not src.is_file():
                print(f"  - {src}")
        exit(1)

    print("Creating Vitis client...")
    client = vitis.create_client()

    workspace = root_dir / "workspace"
    if not workspace.is_dir():
        print(f"Error: Workspace '{workspace}' does not exist. Run setup first.")
        exit(1)

    client.set_workspace(workspace)

    print("Getting platform...")
    platform = client.get_component(name="kria_rpu_platform")
    platform_xpfm = (
        Path(platform.project_location)
        / "export"
        / platform.project_name
        / f"{platform.project_name}.xpfm"
    )
    if not platform_xpfm.is_file():
        print(
            f"Error: Exported platform '{platform_xpfm}' does not exist. Build the platform first."
        )
        exit(1)

    print(f"Creating app {app_name!r}...")
    app = client.create_app_component(
        name=app_name,
        platform=platform_xpfm.as_posix(),
        domain="standalone_psu_cortexr5_0",
    )

    print(f"Linking {len(app_sources)} source files into the app component...")
    linked_sources = link_app_sources(app.component_location, app_sources)

    compile_sources = [
        source
        for source in linked_sources
        if Path(source).suffix in COMPILE_SOURCE_SUFFIXES
    ]
    if compile_sources:
        user_config_path = Path(app.component_location) / "src" / "UserConfig.cmake"
        print(
            f"Updating compile source list with {len(compile_sources)} source files in {user_config_path.as_posix()!r}..."
        )
        update_user_compile_sources(user_config_path, compile_sources)

    print(f"App created at {app.component_location!r}")


if __name__ == "__main__":
    main()
