# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Removable media: list disks and flash images with bmaptool."""

import json
from pathlib import Path

from isozap.devices import Disk, all_disks, unmount
from isozap.platforms.linux import parse_lsblk
from isozap.utils import IsoZapError, run

from .base import Commands


def _old_lsblk_disks() -> list[Disk]:
    """Discover disks with util-linux < 2.37, which lacks PATH and MOUNTPOINTS."""
    out = run(
        [
            "lsblk",
            "--json",
            "--bytes",
            "-p",
            "-o",
            "NAME,SIZE,MODEL,SERIAL,WWN,TRAN,TYPE,RM,MOUNTPOINT",
        ],
        capture=True,
    )

    def fix(node: dict) -> dict:
        node["path"] = node["name"]
        node["mountpoints"] = [node.get("mountpoint")]
        node["children"] = [fix(c) for c in node.get("children", [])]
        return node

    return parse_lsblk(
        json.dumps({"blockdevices": [fix(n) for n in json.loads(out)["blockdevices"]]})
    )


class MediaCommands(Commands):
    """Discover removable disks and flash images with ``bmaptool``."""

    @staticmethod
    def _fmt(d: Disk) -> str:
        mounts = ", ".join(d.mounted) if d.mounted else "not mounted"
        return f"{d.path}  {d.name}  {d.size} bytes  {d.transport}  [{mounts}]"

    def _disks(self) -> list[Disk]:
        try:
            disks = all_disks()
        except IsoZapError:
            disks = _old_lsblk_disks()
        # isozap 0.1.0 misreads macOS ``WholeDisk`` as ``Whole``, so its
        # ``safe_disks()`` filter drops every Darwin disk (incl. built-in SD).
        return [
            d
            for d in disks
            if d.size > 0
            and not d.system
            and not d.boot
            and (d.removable or d.external)
        ]

    def _select(self, device: str | None = None) -> Disk:
        disks = self._disks()
        if device:
            for d in disks:
                raw = d.path.replace("/dev/disk", "/dev/rdisk", 1)
                if d.path == device or raw == device:
                    return d
            known = ", ".join(d.path for d in disks) or "(none)"
            raise RuntimeError(f"Device {device!r} not found. Known: {known}")
        if not disks:
            raise RuntimeError("No removable disks found.")
        if len(disks) == 1:
            return disks[0]
        listing = "\n".join(f"  {self._fmt(d)}" for d in disks)
        raise RuntimeError("Multiple removable disks; pass --device:\n" + listing)

    def disk(self) -> str:
        """List removable whole disks (SD cards, USB sticks, …)."""

        disks = self._disks()
        return (
            "\n".join(self._fmt(d) for d in disks)
            if disks
            else "No removable disks found."
        )

    def flash(
        self,
        image: Path | str,
        device: str,
        bmap: Path | None = None,
        yes: bool = False,
    ) -> None:
        """
        Write *image* to *device* with ``bmaptool copy`` (requires ``--yes``).

        Args:
            image: Image file to write.
            device: Target disk, e.g. ``/dev/sdb``.
            bmap: Block map file. Without it, the whole image is written (``--nobmap``).
            yes: Confirm overwriting the device.
        """
        if not yes:
            raise RuntimeError(
                f"Refusing to overwrite {device} without --yes (image={image!r})."
            )
        image = Path(image).expanduser().resolve()
        if not image.is_file():
            raise RuntimeError(f"Image does not exist: {image}")
        disk = self._select(device)
        dest = unmount(disk)
        cmd = ["bmaptool", "copy"]
        if bmap is not None:
            cmd.extend(["--bmap", Path(bmap).expanduser().resolve().as_posix()])
        else:
            cmd.append("--nobmap")
        if self.system == "Linux":
            cmd.append("--removable-device")
        cmd.extend([image.as_posix(), dest])

        self.run(*cmd, privileged=True)

        unmount(disk)
