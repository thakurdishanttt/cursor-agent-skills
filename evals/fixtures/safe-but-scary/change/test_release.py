import sqlite3
from pathlib import Path

import pytest

from release import file_checksum, list_releases


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE releases (name TEXT, created_at TEXT)")
    c.executemany("INSERT INTO releases VALUES (?, ?)", [("alpha", "2026-01-01"), ("beta", "2026-02-01")])
    return c


def test_sort_by_created_newest_first(conn):
    assert list_releases(conn, sort="created")[0][0] == "beta"


def test_sort_by_name(conn):
    assert [r[0] for r in list_releases(conn, sort="name")] == ["beta", "alpha"]


def test_rejects_unknown_sort(conn):
    with pytest.raises(ValueError):
        list_releases(conn, sort="name; DROP TABLE releases")


def test_rejects_bad_limit(conn):
    with pytest.raises(ValueError):
        list_releases(conn, limit=0)


def test_checksum(tmp_path: Path):
    p = tmp_path / "a.zip"
    p.write_bytes(b"abc")
    assert file_checksum(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
