# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
from pathlib import Path

import vitis


def main():
    root_dir = os.environ.get("RPU_ROOT_DIR")
    if not root_dir:
        print("Error: RPU_ROOT_DIR environment variable not set.")
        exit(1)
    root_dir = Path(root_dir).resolve()
    print(f"Using root directory: {root_dir.as_posix()!r}")

    xsa_filename = os.environ.get("RPU_XSA_FILE")
    if not xsa_filename:
        print("Error: RPU_XSA_FILE environment variable not set.")
        exit(1)
    xsa_path = Path(xsa_filename).resolve()
    if not xsa_path.is_file():
        print(f"Error: XSA file '{xsa_path}' does not exist.")
        exit(1)
    print(f"Using XSA file: {xsa_path.as_posix()!r}")

    domain_libraries = os.environ.get("RPU_DOMAIN_LIBRARIES", "")
    domain_libraries = [
        lib.strip() for lib in domain_libraries.split(":") if lib.strip()
    ]

    print("Creating Vitis client...")
    client = vitis.create_client()

    workspace = root_dir / "workspace"
    if workspace.is_dir():
        shutil.rmtree(workspace)
        print(f"Deleted existing workspace {workspace}")

    client.set_workspace(workspace)

    print("Creating platform component...")
    platform = client.create_platform_component(
        name="kria_rpu_platform",
        hw_design=xsa_path.as_posix(),
        os="standalone",
        cpu="psu_cortexr5_0",
    )

    print("Getting domain...")
    domain = platform.get_domain(name="standalone_psu_cortexr5_0")

    # print("Applicable libraries:")
    # domain.get_applicable_libs()

    # add libraries
    print("Adding libraries to domain...")
    for lib in domain_libraries:
        print(f"- Adding {lib}...")
        domain.set_lib(lib)

    # print("List of configured libraries:")
    # domain.get_libs()

    print("Building platform...")
    platform.build()

    # # create application component
    # app = client.create_app_component(
    #     name="timer_control",
    #     platform=platform,
    #     domain="standalone_psu_cortexr5_0",
    # )

    print("Setup complete.")


if __name__ == "__main__":
    main()
