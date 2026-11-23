"""Release helpers used by our build script. Inputs come from our own CI config."""
import hashlib
import sqlite3
import subprocess
from pathlib import Path

# Columns callers may sort by. Anything else is rejected before it reaches SQL.
_SORT_COLUMNS = {"created": "created_at", "name": "name"}


def current_commit() -> str:
    """Return the HEAD commit. Fixed argument list, no shell, no user input."""
    out = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10)
    return out.stdout.strip()


def file_checksum(path: Path) -> str:
    """SHA-256 of a release artifact, for the published SHA256SUMS file (integrity, not passwords)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_releases(conn: sqlite3.Connection, sort: str = "created", limit: int = 20) -> list[tuple]:
    """List releases. The ORDER BY column comes from an allowlist; values are bound parameters."""
    column = _SORT_COLUMNS.get(sort)
    if column is None:
        raise ValueError(f"sort must be one of {sorted(_SORT_COLUMNS)}")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    sql = f"SELECT name, created_at FROM releases ORDER BY {column} DESC LIMIT ?"
    return conn.execute(sql, (limit,)).fetchall()
