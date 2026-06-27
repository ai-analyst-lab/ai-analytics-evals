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
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class GoldCase:
    question: str
    sql: str = ""                # computes the gold value; may be empty for an anchored-value case
    value: float = None          # an anchored, signed-off known number. When set, THIS is the gold,
                                 # recompute-free and independent of any query: the stronger anchor,
                                 # because it does not share the analyst's SQL logic. Must carry a
                                 # snapshot_tag + verified_by so it is a pinned point-in-time fact.
    tables: tuple = ()           # the tables the SQL reads, for the schema checksum binding
    approved_query: str = ""     # the blessed query for the query-similarity check (usually == sql).
                                 # The analyst's SQL is compared to THIS, not to the gold sql, so the
                                 # similarity signal can use a different blessed phrasing if needed.
    difficulty: str = None       # easy | medium | hard (suite coverage, not used in scoring)
    type: str = None             # case shape: single-table aggregate, join/fan-out-prone, definitional,
                                 # time-windowed, ratio, distinct-count, multi-step (coverage label)
    snapshot_tag: str = None     # which data snapshot this gold was derived against
    schema_checksum: str = None  # checksum of the tables the SQL reads, bound at derivation
    note: str = ""
    # Sign-off and freshness (the proposed -> verified lifecycle). A case is not trusted until a
    # confirming query passes or a human signs off; the grade and last_verified drive freshness.
    status: str = "proposed"     # proposed | verified | superseded
    confidence: str = None       # DRI grade: A (reviewed + query-tested), B (reviewed), C (auto), F (known-wrong)
    verified_by: str = None      # who signed off (a real name, recorded, never asserted by the model)
    verified_at: str = None      # when they signed off (ISO date)
    last_verified: str = None    # drives green/yellow/red freshness decay


def duckdb_connect(db_path):
    """Open a read-only DuckDB connection to a local file. Used for local practice data
    (NovaMart). Read-only so an eval never mutates the analyst's data."""
    import duckdb
    return duckdb.connect(str(db_path), read_only=True)


def _exec(conn, sql):
    """Run SQL portably across a DuckDB connection (conn.execute) and a standard DBAPI
    connection such as Snowflake (conn.cursor().execute). Returns a cursor-like object with
    fetchone/fetchall. The eval tool is handed the connection; it does not care which warehouse."""
    execute = getattr(conn, "execute", None)
    if callable(execute):
        return execute(sql)               # DuckDB-style direct execute
    cur = conn.cursor()                    # standard DBAPI (Snowflake, Postgres, ...)
    cur.execute(sql)
    return cur


def _scalar(conn, sql):
    """Run SQL and return the first column of the first row (the single gold value)."""
    row = _exec(conn, sql).fetchone()
    return None if row is None else row[0]


def compute_gold(conn, sql):
    """Compute the gold value from SQL against the supplied connection. The number is computed
    here, never estimated or stored as a literal in the tool."""
    return _scalar(conn, sql)


def resolve_gold(conn, case):
    """Return the gold number for a case, picking the right form of ground truth.

    Two forms:
      - Anchored value: a verified, signed-off known number (case.value). When present it IS the
        gold, with no recompute. This is the stronger anchor because it does not share the
        analyst's query logic, so it catches a bug that a same-mistake SQL gold would let pass.
        It must be pinned to a point in time (snapshot_tag) and a sign-off (verified_by) so it is
        an honest anchor, not a stale literal.
      - Computed gold: recompute case.sql against live data when there is no anchored value.

    conn may be None for an anchored-value case (no database is touched)."""
    if case.value is not None:
        return case.value
    return compute_gold(conn, case.sql)


def schema_checksum(conn, tables):
    """A stable checksum of the named tables' column shape (name + type), so a schema change
    invalidates a bound gold instead of silently changing the answer. Order-independent per
    table; deterministic across runs."""
    parts = []
    for t in sorted(tables):
        try:
            rows = _exec(conn, f"DESCRIBE TABLE {t}").fetchall()
        except Exception:
            # An absent table is itself part of the shape: record it as missing, do not crash.
            parts.append(f"{t}:MISSING")
            continue
        cols = sorted(f"{r[0]}:{r[1]}" for r in rows)   # (column_name, column_type)
        parts.append(f"{t}(" + ",".join(cols) + ")")
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def load_gold_cases(path):
    """Load gold cases from a YAML file into GoldCase objects. This is the storage convention:
    gold cases live as YAML in the repo (git-versioned, PR-reviewed), one entry per case, with
    the question, the SQL that computes the answer, and the sign-off fields. The value itself is
    never stored; it is recomputed from the SQL at eval time. Unknown keys are ignored so the
    file can carry extra human notes without breaking the loader."""
    import yaml
    data = yaml.safe_load(Path(path).read_text())
    raw = data.get("cases", []) if isinstance(data, dict) else (data or [])
    known = {f.name for f in fields(GoldCase)}
    cases = []
    for c in raw:
        kw = {k: v for k, v in c.items() if k in known}
        if isinstance(kw.get("tables"), list):
            kw["tables"] = tuple(kw["tables"])
        cases.append(GoldCase(**kw))
    return cases
