"""Data access. All queries are parameterized."""
import sqlite3

DB_PATH = "billing.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_invoices_for_tenant(tenant_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, number, amount_cents FROM invoices WHERE tenant_id = ?", (tenant_id,)).fetchall()
    return [dict(r) for r in rows]
