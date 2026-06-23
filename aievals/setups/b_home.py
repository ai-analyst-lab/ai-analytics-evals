"""B-home Storage home (cross-cutting axis, layer=None): WHERE a layer's context LIVES.

Every layer-by-layer B unit asks which layer of context to stage. This one asks a different
question that students test by hand: given one layer's content, does it matter WHERE that content
lives (a repo file, a warehouse table row, a Notion page), and what does each home cost to read
from and how governable is it? The natural content is the proven retention contract, so the home
is the only thing that changes.

Why the format is held constant. FRAMEWORK_v0 section 4 Rule B is emphatic that an executable
warehouse semantic view and a declarative repo file are NOT interchangeable. If this unit staged
the definition as a Snowflake semantic view (executable) against a repo file (declarative), it
would change home AND format at once and confound the result. So every home here carries the SAME
meaning-only contract TEXT, declarative, format held constant. The executable-versus-declarative
question is real and worth running, but it belongs to B-format, not here.

Why the home-readers hold no credentials. The eval tool declares only pyyaml and stays
credential-free. The warehouse and Notion credentials live analyst-side. So the readers below
take a SUPPLIED connection (the warehouse reader) or would take an analyst-side token (the Notion
reader); neither holds a secret. The eval setup only flips which home the analyst reads from and
measures the result through the adapter.

The homes, with their honest status carried in code:
  - Repo (files): BUILT, the baseline. Read via the existing FileReader on the canonical fixture.
  - Snowflake (the contract text in a metrics-table row): buildable-now ONCE a fixture is seeded.
    The WarehouseReader reads the contract TEXT from a row over a connection the caller supplies;
    the metrics table that holds the text must first be written analyst-side, the same seeded-
    fixture dependency as B5 and B6.
  - Notion (a page the analyst reads): BLOCKED. No token is configured and there is no live page-
    read connector, so the NotionReader reports blocked rather than silently returning empty.
  - S3 / blob and a vector store: described only, no hands-on setup (S3 not worth the run cost, a
    vector store returns similar-not-correct and is never the home for a governed definition).
"""
from aievals.harness.setups import Setup, SourceReader, register_reader
from aievals.setups import FIXTURES
from aievals.setups.base import SetupSpec, register_setup

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# The canonical meaning-only contract, the same content every home carries. A single file (not the
# whole fixtures dir) so the repo home reads exactly the one contract the warehouse row mirrors.
CONTRACT_FILE = FIXTURES / "retention_contract.yaml"

# Default coordinates of the seeded metrics table in the warehouse home. The caller overrides these
# for a real analyst; they name a table, not an analyst-private path or credential.
DEFAULT_WAREHOUSE_TABLE = "metric_contracts"
DEFAULT_TEXT_COLUMN = "contract_text"
DEFAULT_WAREHOUSE_WHERE = "metric = 'retention_rate'"


class WarehouseReader(SourceReader):
    """Read a layer's content from a warehouse table ROW, over a connection the caller supplies.

    The contract TEXT lives in one column of one row (the meaning-only YAML, format held constant
    with the repo home). This reader holds NO credentials: the connection is passed in via the spec
    by the analyst-side caller. It parses the row's text exactly as the FileReader parses a file, so
    the same meaning composes the same way regardless of which home it came from.

    spec is a dict: {"conn": <dbapi connection>, "table": str, "text_column": str, "where": str}.
    A missing connection means the analyst-side warehouse home is not wired yet, and a missing row
    means the metrics table has not been seeded; both raise a clear error rather than returning
    empty, so a not-seeded warehouse is never mistaken for an empty-but-valid overlay.
    """
    name = "warehouse"

    def read(self, spec):
        if yaml is None:
            raise RuntimeError("pyyaml required for the warehouse reader")
        if spec is None:
            return []
        conn = (spec or {}).get("conn")
        if conn is None:
            raise RuntimeError(
                "warehouse home not wired: no connection supplied. The connection is passed in "
                "analyst-side; the eval tool holds no warehouse credentials (Snowflake home is "
                "buildable-now once the metrics-table fixture is seeded)")
        table = spec.get("table", DEFAULT_WAREHOUSE_TABLE)
        text_column = spec.get("text_column", DEFAULT_TEXT_COLUMN)
        where = spec.get("where", DEFAULT_WAREHOUSE_WHERE)
        sql = f"SELECT {text_column} FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += " LIMIT 1"
        row = conn.execute(sql).fetchone()
        if row is None or row[0] is None:
            raise RuntimeError(
                f"warehouse home not seeded: no contract row in {table} matching {where!r}. "
                "Write the retention contract text into a metrics-table row first (same seeded-"
                "fixture dependency as B5 and B6)")
        return [yaml.safe_load(row[0]) or {}]


class NotionReader(SourceReader):
    """Read a layer's content from a Notion page. BLOCKED, and it says so.

    No Notion token is configured and there is no live page-READ connector (the existing notion-
    ingest skill is a one-directional crawler to local files, which collapses to the repo home by
    another name, not a distinct live read). So this reader raises a clear blocked error rather
    than guessing or silently returning an empty overlay: a blocked home must never look like an
    empty-but-valid one. When a token and a live page-read are configured, the read runs analyst-
    side, the same as the warehouse reader.
    """
    name = "notion"
    blocked_on = ("Notion home blocked: no token configured and no live page-read connector. "
                  "Needs (i) a configured Notion token and (ii) a live page-READ setup (not the "
                  "ingest-to-files crawler, which is just the repo home renamed)")

    def read(self, spec):
        raise RuntimeError(self.blocked_on)


register_reader(WarehouseReader())
register_reader(NotionReader())


def repo_home(contract_file=None):
    """The repo home (BUILT, the baseline): the contract as a declarative file, read by FileReader."""
    spec = str(contract_file) if contract_file is not None else str(CONTRACT_FILE)
    return Setup(name="home-repo", layer="L3", reader="file", spec=spec)


def warehouse_home(conn=None, table=None, text_column=None, where=None):
    """The Snowflake home (buildable-now once seeded): the SAME contract text in a metrics-table
    row. `conn` is supplied analyst-side; with conn=None the arm is defined but reading it reports
    the not-wired error, so the buildable-once-seeded status is visible rather than silently empty.
    """
    return Setup(name="home-snowflake", layer="L3", reader="warehouse", spec={
        "conn": conn,
        "table": table or DEFAULT_WAREHOUSE_TABLE,
        "text_column": text_column or DEFAULT_TEXT_COLUMN,
        "where": where if where is not None else DEFAULT_WAREHOUSE_WHERE,
    })


def notion_home():
    """The Notion home (BLOCKED): defined so the menu is complete, but reading it raises blocked."""
    return Setup(name="home-notion", layer="L3", reader="notion", spec={})


def build(contract_file=None, warehouse_conn=None, warehouse_table=None,
          warehouse_text_column=None, warehouse_where=None, **ctx):
    """Return the home arms as a list the comparison run toggles, one per storage home, all carrying
    the SAME meaning-only contract text (format held constant, so home is the only variable).

    The repo arm runs hermetically off the canonical fixture. The Snowflake arm runs once a metrics
    table is seeded and a connection is supplied analyst-side (`warehouse_conn`). The Notion arm is
    blocked and reports it on read. No analyst-private path or credential is embedded here.
    """
    return [
        repo_home(contract_file),
        warehouse_home(warehouse_conn, warehouse_table, warehouse_text_column, warehouse_where),
        notion_home(),
    ]


register_setup(SetupSpec(
    key="B-home",
    layer=None,  # cross-cutting axis: WHERE a layer's context lives, not which layer
    status="partial",
    summary=("Stage the same meaning-only contract from different homes (repo built; Snowflake "
             "buildable-once-seeded analyst-side; Notion blocked; S3/vector described-only) and "
             "measure whether the home changes the answer, its read cost, and its governability."),
    blocked_on=("Snowflake needs a seeded metrics-table fixture, and seeding it is itself blocked: "
                "the bootcamp_student role is read-only (verified: cannot CREATE TABLE in BOOTCAMP_DB "
                "for insufficient privileges, and the personal database disallows tables), so the "
                "contract text cannot be written to a Snowflake table with current credentials. "
                "Notion needs a token plus a live page-read. The warehouse-reader mechanism itself is "
                "built and tested against a DuckDB stand-in."),
    source="C-store.md, CONTEXT-DECISION-GRID §1A, FRAMEWORK_v0 §4 Rule B",
    build=build,
))
