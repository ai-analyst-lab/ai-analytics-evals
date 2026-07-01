# Skill: Connect to Live Snowflake (NovaMart)

## Purpose
Connect to the live Snowflake NovaMart warehouse and run a query, from this repo
(`ai-analytics-evals`). Self-contained: it uses `snowflake.connector` directly and
reads the credentials you already set up in pre-work. Use it whenever you need real
NovaMart data here, for example to pull revenue to make a chart.

## When to Use
Trigger on any request to use the live data, e.g. "connect to snowflake",
"query snowflake", "query NovaMart", "get the 2024 revenue", "use the live warehouse".

## Where the credentials are
The read-only `bootcamp_student` credentials live in the standard pre-work location,
`~/projects/ai-analyst-plus/.env` (the same file the analyst uses). This skill reads
them from there. If your `.env` is somewhere else, point the loader at that path.

## Instructions

### Run a query
Run this, substituting your SQL. Tables are **unqualified** in the `NOVAMART` schema
(`orders`, `order_items`, `products`, `users`, `sessions`, `events`, `memberships`, `promotions`, `experiments`, `experiment_assignments`, `nps_responses`, `support_tickets`, `calendar`).
Use Snowflake dialect (`DATE_TRUNC('month', col)`, etc.).

```bash
python3 -W ignore -c "
import warnings, pathlib; warnings.filterwarnings('ignore')
env = {}
for line in open(pathlib.Path.home()/'projects/ai-analyst-plus/.env'):
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1); env[k] = v.strip().strip('\"').strip(\"'\")
import snowflake.connector
cur = snowflake.connector.connect(
    account=env['SNOWFLAKE_ACCOUNT'], user=env['SNOWFLAKE_USER'],
    password=env['SNOWFLAKE_PASSWORD'], warehouse=env['SNOWFLAKE_WAREHOUSE'],
    database=env['SNOWFLAKE_DATABASE'], role=env['SNOWFLAKE_ROLE'], login_timeout=20).cursor()
cur.execute('use schema BOOTCAMP_DB.NOVAMART')
cur.execute('''
    select date_trunc('month', order_date) m, round(sum(total_amount)) rev
    from orders where status='completed' and year(order_date)=2024 group by 1 order by 1
''')
for row in cur.fetchall(): print(row)
"
```

### Verify you landed on Snowflake
Confirm `SELECT CURRENT_ACCOUNT(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()`
returns `TQ49857 / BOOTCAMP_WH / BOOTCAMP_DB / NOVAMART`.

## Notes
- Read-only. The `bootcamp_student` role cannot write.
- Do not commit query results or data to git; pull live each time.
