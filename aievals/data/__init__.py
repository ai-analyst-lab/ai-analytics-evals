"""Data helpers for graders that need a gold answer computed in SQL.

The gold is never hardcoded: it is computed from SQL at eval time against a connection the
caller supplies. The eval tool holds no credentials and no analyst-private path; the connection
(a DuckDB file path or any DBAPI connection) is passed in by the side that owns the data.
"""
from aievals.data.gold import (  # noqa: F401
    GoldCase,
    compute_gold,
    schema_checksum,
    duckdb_connect,
)
