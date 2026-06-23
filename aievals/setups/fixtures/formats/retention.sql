-- Retention rate, the executable form: the figure computed BY NAME from live data, never stored.
-- Same meaning as the structured contract (retention_contract.yaml) and the prose note
-- (retention_prose.md): the share of a month's new customers who make at least one more completed
-- purchase within ninety days of their first. No result value is written here, by design; the
-- warehouse computes the number each run. This is the "computed by name, not described" format:
-- the agent calls retention_rate and gets proven SQL rather than authoring its own.
WITH first_orders AS (
    SELECT
        customer,
        MIN(ordered_at) AS first_order_at,
        date_trunc('month', MIN(ordered_at)) AS cohort_month
    FROM orders
    WHERE status = 'completed'
      AND NOT is_internal
    GROUP BY customer
),
returned AS (
    SELECT f.customer
    FROM first_orders f
    JOIN orders o
      ON o.customer = f.customer
     AND o.status = 'completed'
     AND o.ordered_at > f.first_order_at
     AND o.ordered_at <= f.first_order_at + INTERVAL '90 days'
    GROUP BY f.customer
)
SELECT
    f.cohort_month,
    count(DISTINCT r.customer) * 1.0 / count(DISTINCT f.customer) AS retention_rate
FROM first_orders f
LEFT JOIN returned r ON r.customer = f.customer
GROUP BY f.cohort_month
ORDER BY f.cohort_month;
