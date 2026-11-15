# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import replace
from pathlib import Path

from ..models import CommandError
from .base import Commands


class GitCommands(Commands):
    """Wrap common ``git`` operations in the working directory."""

    def checkout(self, ref: str) -> None:
        """
        Check out a branch, tag or commit.

        Args:
            ref: Branch, tag or commit to check out.
        """
        self.run("git", "checkout", ref)

    def clone(
        self,
        repo_url: str,
        dest: Path,
        checkout: str | None = None,
        submodule_update: bool = False,
    ) -> "GitCommands":
        """
        Clone a repository.

        Args:
            repo_url: URL of the repository.
            dest: Directory to clone into.
            checkout: Ref to check out after cloning.
            submodule_update: Init and update submodules recursively after cloning.

        Returns:
            Git commands for the cloned repository.
        """
        dest = dest.resolve()

        self.run("git", "clone", repo_url, dest.as_posix())

        dest_cmds = GitCommands(replace(self.cfg, cwd=dest), executor=self.executor)

        if checkout:
            dest_cmds.checkout(checkout)

        if submodule_update:
            dest_cmds.submodule_update()

        return dest_cmds

    def submodule_add(
        self,
        repo_url: str,
        dest: Path,
        checkout: str | None = None,
    ) -> "GitCommands":
        """
        Add a repository as a submodule.

        Args:
            repo_url: URL of the repository.
            dest: Submodule path.
            checkout: Ref to check out in the submodule.

        Returns:
            Git commands for the submodule.
        """
        self.run("git", "submodule", "add", repo_url, str(dest))

        dest_cmds = GitCommands(
            replace(self.cfg, cwd=self.path / dest), executor=self.executor
        )

        if checkout:
            dest_cmds.checkout(checkout)

        return dest_cmds

    def submodule_update(self) -> None:
        """Init and update all submodules recursively."""
        self.run("git", "submodule", "update", "--init", "--recursive")

    def apply_patch(self, patch_file: Path) -> None:
        """
        Apply a patch with ``git apply``. Skips it if it is already applied.

        Args:
            patch_file: Patch file to apply.

        Raises:
            CommandError: The patch neither applies nor is already applied.
        """
        patch_file_str = patch_file.resolve().as_posix()

        # Check if patch is applicable
        try:
            self.run("git", "apply", "--check", patch_file_str)
        except Exception as e:
            # Check if patch is already applied
            try:
                self.run("git", "apply", "--check", "--reverse", patch_file_str)
                self.log.info(f"Patch {patch_file_str!r} is already applied, skipping")
                return
            except Exception:
                self.log.error(f"Patch {patch_file_str!r} cannot be applied: {e}")
                raise

        self.run("git", "apply", patch_file_str)

    def sha(self, short: bool = False, length: int | None = None) -> str:
        """
        Get the commit hash of ``HEAD``.

        Args:
            short: Abbreviate the hash (7 characters unless ``length`` is set).
            length: Abbreviate the hash to this many characters.

        Returns:
            The commit hash.
        """
        args = ["git", "rev-parse"]
        if short:
            length = length or 7
        if short or length:
            args.append(f"--short={length}")
        return self.run(*args, "HEAD").output[-1].strip()

    def dirty(self) -> bool:
        """
        Check for unstaged changes in tracked files.

        Returns:
            True if ``git diff`` is not empty.
        """
        try:
            self.run("git", "diff", "--quiet")
            return False
        except CommandError:
            return True
