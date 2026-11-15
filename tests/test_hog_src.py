# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from maestro.commands.hog import parse_hog_src_files


def test_parse_hog_src_files_expands_nested_src(tmp_path: Path) -> None:
    """
    Test Directory Structure:
    - rtl/
        - leaf.v
    - nested.src -> points to rtl/leaf.v
    - top.src -> points to nested.src
    """
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "leaf.v").write_text("// leaf\n")
    (tmp_path / "nested.src").write_text(f"{tmp_path / 'rtl' / 'leaf.v'}\n")
    (tmp_path / "top.src").write_text(f"# comment\n{tmp_path / 'nested.src'}\n")

    assert parse_hog_src_files([tmp_path / "top.src"]) == [
        (tmp_path / "rtl" / "leaf.v").resolve()
    ]


def test_parse_hog_src_files(tmp_path: Path) -> None:
    """
    Test Directory Structure:
    - rtl/
        - a.v
        - b.v
    - list.src -> points to rtl/a.v and rtl/b.v
    """
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "a.v").write_text("")
    (tmp_path / "rtl" / "b.v").write_text("")
    (tmp_path / "list.src").write_text(
        f"{tmp_path / 'rtl' / 'a.v'}\n{tmp_path / 'rtl' / 'b.v'}"
    )

    paths = parse_hog_src_files([tmp_path / "list.src"])
    assert set(paths) == {
        (tmp_path / "rtl" / "a.v"),
        (tmp_path / "rtl" / "b.v"),
    }


def test_parse_hog_src_files_glob(tmp_path: Path) -> None:
    """
    Test Directory Structure:
    - rtl/
        - a.v
        - b.v
    - list.src -> points to rtl/*.v
    """
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "a.v").write_text("")
    (tmp_path / "rtl" / "b.v").write_text("")
    (tmp_path / "list.src").write_text(f"{tmp_path / 'rtl' / '*.v'}\n")

    paths = parse_hog_src_files([tmp_path / "list.src"])
    assert set(paths) == {
        (tmp_path / "rtl" / "a.v"),
        (tmp_path / "rtl" / "b.v"),
    }


def test_parse_hog_src_files_dir(tmp_path: Path) -> None:
    """
    Test Directory Structure:
    - rtl/
        - a.v
        - b.v
    - list.src -> points to rtl
    """
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "a.v").write_text("")
    (tmp_path / "rtl" / "b.v").write_text("")
    (tmp_path / "list.src").write_text(f"{tmp_path / 'rtl'}\n")

    paths = parse_hog_src_files([tmp_path / "list.src"])
    assert set(paths) == {
        (tmp_path / "rtl" / "a.v"),
        (tmp_path / "rtl" / "b.v"),
    }


def test_parse_hog_src_files_suffix(tmp_path: Path) -> None:
    """
    Test Directory Structure:
    - rtl/
        - a.v
        - b.v
    - list.f -> points to rtl
    """
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "a.v").write_text("")
    (tmp_path / "rtl" / "b.v").write_text("")
    (tmp_path / "list.f").write_text(f"{tmp_path / 'rtl'}\n")

    paths = parse_hog_src_files([tmp_path / "list.f"], src_suffixes=[".f"])
    assert set(paths) == {
        (tmp_path / "rtl" / "a.v"),
        (tmp_path / "rtl" / "b.v"),
    }
