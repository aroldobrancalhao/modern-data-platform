from __future__ import annotations

from integrations.aws.storage.helpers import join_key
from integrations.aws.storage.helpers import normalize_key


def test_normalize_key_without_changes() -> None:

    assert normalize_key(
        "folder/file.csv",
    ) == "folder/file.csv"


def test_normalize_key_removes_leading_slash() -> None:

    assert normalize_key(
        "/folder/file.csv",
    ) == "folder/file.csv"


def test_normalize_key_removes_trailing_slash() -> None:

    assert normalize_key(
        "folder/file.csv/",
    ) == "folder/file.csv"


def test_normalize_key_removes_duplicate_slashes() -> None:

    assert normalize_key(
        "folder//sub///file.csv",
    ) == "folder/sub/file.csv"


def test_normalize_key_root_returns_empty_string() -> None:

    assert normalize_key("/") == ""


def test_normalize_key_empty_string() -> None:

    assert normalize_key("") == ""


def test_join_key() -> None:

    assert join_key(
        "folder",
        "file.csv",
    ) == "folder/file.csv"


def test_join_key_normalizes_slashes() -> None:

    assert join_key(
        "/folder/",
        "/sub/",
        "file.csv",
    ) == "folder/sub/file.csv"


def test_join_key_ignores_empty_parts() -> None:

    assert join_key(
        "",
        "folder",
        "",
        "file.csv",
    ) == "folder/file.csv"


def test_join_key_multiple_parts() -> None:

    assert join_key(
        "a",
        "b",
        "c",
        "d.csv",
    ) == "a/b/c/d.csv"