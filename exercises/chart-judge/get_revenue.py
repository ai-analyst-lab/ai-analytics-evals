#!/usr/bin/env python3
"""Return the 2024 monthly completed-revenue series from the live NovaMart warehouse.
No data is committed to git; this queries Snowflake using the same creds the eval harness uses
(ai-analyst-plus/.env). Import it, or run it to print the series.

    from get_revenue import revenue_2024
    months, revenue = revenue_2024()
"""
import warnings, pathlib
warnings.filterwarnings("ignore")
ENV = pathlib.Path.home() / "projects/ai-analyst-plus/.env"

def revenue_2024():
    env = {}
    for line in open(ENV):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1); env[k] = v.strip().strip('"').strip("'")
    import snowflake.connector
    cur = snowflake.connector.connect(
        account=env["SNOWFLAKE_ACCOUNT"], user=env["SNOWFLAKE_USER"],
        password=env["SNOWFLAKE_PASSWORD"], warehouse=env["SNOWFLAKE_WAREHOUSE"],
        database=env["SNOWFLAKE_DATABASE"], role=env["SNOWFLAKE_ROLE"], login_timeout=20).cursor()
    cur.execute("use schema BOOTCAMP_DB.NOVAMART")
    cur.execute("""select date_trunc('month',order_date) m, round(sum(total_amount)) rev
                   from orders where status='completed' and year(order_date)=2024 group by 1 order by 1""")
    rows = cur.fetchall()
    return [r[0].strftime("%b") for r in rows], [float(r[1]) for r in rows]

if __name__ == "__main__":
    m, r = revenue_2024()
    print("2024 monthly completed revenue:", list(zip(m, r)))
