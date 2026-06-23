"""Gold answers, computed in SQL at eval time, never hardcoded.

A GoldCase is a question, the SQL that computes its answer, a snapshot tag, and a schema
checksum. At eval time you recompute the gold from the SQL against the live data and compare the
analyst's number to it. The snapshot tag and checksum exist so a REAL answer drift is told apart
from the data or schema changing underneath: if the checksum at eval time does not match the one
bound to the gold, the gold is stale and must be re-derived, rather than the analyst being failed
for a number that moved because the table changed.

The connection is always supplied by the caller. The eval tool never embeds a credential or an
analyst-private path; it is handed a DuckDB path (local practice data) or a DBAPI connection
(the analyst's warehouse) and runs the recorded SQL through it.
"""
import hashlib
from dataclasses import dataclass


@dataclass
class GoldCase:
    question: str
    sql: str                     # computes the single gold value, or a small gold table
    tables: tuple = ()           # the tables the SQL reads, for the schema checksum binding
    snapshot_tag: str = None     # which data snapshot this gold was derived against
    schema_checksum: str = None  # checksum of the tables the SQL reads, bound at derivation
    note: str = ""


def duckdb_connect(db_path):
    """Open a read-only DuckDB connection to a local file. Used for local practice data
    (NovaMart). Read-only so an eval never mutates the analyst's data."""
    import duckdb
    return duckdb.connect(str(db_path), read_only=True)


def _scalar(conn, sql):
    """Run SQL and return the first column of the first row (the single gold value)."""
    cur = conn.execute(sql)
    row = cur.fetchone()
    return None if row is None else row[0]


def compute_gold(conn, sql):
    """Compute the gold value from SQL against the supplied connection. The number is computed
    here, never estimated or stored as a literal in the tool."""
    return _scalar(conn, sql)


def schema_checksum(conn, tables):
    """A stable checksum of the named tables' column shape (name + type), so a schema change
    invalidates a bound gold instead of silently changing the answer. Order-independent per
    table; deterministic across runs."""
    parts = []
    for t in sorted(tables):
        try:
            rows = conn.execute(f"DESCRIBE {t}").fetchall()
        except Exception:
            # An absent table is itself part of the shape: record it as missing, do not crash.
            parts.append(f"{t}:MISSING")
            continue
        cols = sorted(f"{r[0]}:{r[1]}" for r in rows)   # (column_name, column_type)
        parts.append(f"{t}(" + ",".join(cols) + ")")
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
