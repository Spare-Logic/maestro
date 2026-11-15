# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import vitis
from rpu_create import (
    COMPILE_SOURCE_SUFFIXES,
    link_app_sources,
    update_user_compile_sources,
)


def get_app_sources(root_dir: Path) -> list[Path]:
    app_sources = os.environ.get("RPU_APP_SOURCES")
    if not app_sources:
        print("Error: RPU_APP_SOURCES environment variable not set.")
        exit(1)

    app_source_patterns = [src.strip() for src in app_sources.split(":") if src.strip()]
    if not app_source_patterns:
        print("Error: RPU_APP_SOURCES environment variable is empty.")
        exit(1)

    resolved_sources = []
    for src_pattern in app_source_patterns:
        matched_files = [path for path in root_dir.glob(src_pattern) if path.is_file()]
        if not matched_files:
            print(
                f"Error: No files matched the pattern {src_pattern!r} in RPU_APP_SOURCES."
            )
            exit(1)
        resolved_sources.extend(matched_files)
        print(f"- Pattern {src_pattern!r} matched {len(matched_files)} files.")

    return resolved_sources


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

    print("Creating Vitis client...")
    client = vitis.create_client()

    workspace = root_dir / "workspace"
    if not workspace.is_dir():
        print(f"Error: Workspace '{workspace}' does not exist. Run setup first.")
        exit(1)

    client.set_workspace(workspace)

    print("Getting app...")
    app = client.get_component(name=app_name)
    if not app:
        print(f"Error: App '{app_name}' does not exist. Create the app first.")
        exit(1)

    print("Syncing app sources...")
    app_sources = get_app_sources(root_dir)
    linked_sources = link_app_sources(app.component_location, app_sources)
    compile_sources = [
        source
        for source in linked_sources
        if Path(source).suffix in COMPILE_SOURCE_SUFFIXES
    ]
    if compile_sources:
        user_config_path = Path(app.component_location) / "src" / "UserConfig.cmake"
        update_user_compile_sources(user_config_path, compile_sources)

    print("Cleaning and building app...")
    app.clean()
    app.build(target="hw")


if __name__ == "__main__":
    main()
