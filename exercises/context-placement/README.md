# Exercise: context placement

Six real pieces of NovaMart knowledge. Every one of them exists in our stack today, word for word.
Your job, per card: name the home it should live in, defend the placement with one clause of the
placement rule, and say what breaks if it goes in the wrong home.

## The drill

1. Claim a card in chat (one card per person to start; challenge anyone's placement after that).
2. Post your placement in this shape:
   **home + the clause that got you there + what breaks in the wrong home.**
3. The room challenges. The rule decides, not the loudest voice.

A placement without a what-breaks is half an answer. "It goes in a skill" is a guess; "it goes in
a skill, and if it were resident it would burn budget on the 90% of sessions that never touch
Snowflake" is a placement.

## The homes (the menu)

Build-with tier: **resident rules** (CLAUDE.md / system prompt / `custom_instructions.md`),
**skills** (procedures that load on demand), **meaning contracts** (`metrics/index.yaml`),
**semantic layer** (the declarative YAMLs: entities, relationships, dimensions, measures, filters),
**verified examples** (`verified_queries.yaml`).
Recognize tier: **retrieval** (data and long tail behind describe-tools), **agent memory**
(agent-written accumulation), tools-as-context, isolation.

## The placement rule

- **Resident** if ALL of: always-true rule or definition (you cannot afford a failed retrieval);
  applies to most sessions; fits the budget (every line passes "would removing this cause a
  mistake?"); byte-stable so caching makes it near-free.
- **Skill** if: a nameable procedure used in a minority of sessions; a directive description can
  trigger it; a missed trigger is recoverable, not catastrophic.
- **Retrieved** if: data or long-tail reference, not a rule; and the agent can verify what it
  fetched.

Rules ride along and data gets fetched. The failure modes go opposite directions: a resident rule
fades over a long session, a retrieved rule can simply never show up.

---

## Card 1

> Revenue is completed orders only. Filter `orders.status = 'completed'`. Cancelled (4,596) and
> returned (2,369) orders are excluded from revenue; keep all statuses for funnel conversion.

## Card 2

> How to connect to Snowflake and run a query against NovaMart: read the read-only
> `bootcamp_student` credentials from `~/projects/ai-analyst-plus/.env`, open a
> `snowflake.connector` session, `use schema BOOTCAMP_DB.NOVAMART`, tables are unqualified
> (`orders`, `order_items`, `products`, `users`, `sessions`, `events`, ...), Snowflake dialect
> (`DATE_TRUNC('month', col)`, etc.).

## Card 3

> `sessions.had_purchase` is wrong for 1,089 sessions in Nov-Dec 2024 (923 in November, 166 in
> December), concentrated around the Black Friday week (2024-11-25 onward): those sessions have a
> `purchase_complete` event AND a completed order, but `had_purchase = false`. Derive purchase
> outcome from `events.event_type = 'purchase_complete'` or by joining `orders` on `session_id`.

## Card 4

> The full column list and sample values of the `events` table: 6,510,093 rows. EVENT_ID (PK),
> USER_ID (FK users), SESSION_ID (FK sessions), EVENT_TIMESTAMP, EVENT_DATE, EVENT_TYPE (10 values,
> including `page_view`, `product_view`, `add_to_cart`, `checkout_started`, `payment_attempted`,
> `purchase_complete`), DEVICE, PRODUCT_ID (nullable FK products), PAGE_URL, SEARCH_QUERY
> (populated on search events), APP_VERSION (NULL means web; 2.4.0 / 3.2.0 are the mobile app
> versions).

## Card 5

> The verified SQL for checkout conversion, human-verified and re-runnable:
>
> ```sql
> WITH checkout AS (SELECT DISTINCT session_id FROM events WHERE event_type = 'checkout_started'),
>      purchase AS (SELECT DISTINCT session_id FROM events WHERE event_type = 'purchase_complete')
> SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM checkout)
> FROM checkout c
> WHERE c.session_id IN (SELECT session_id FROM purchase)
> ```
>
> Question it answers: "What is our checkout conversion rate?" Session grain, event-based, does
> not use `sessions.had_purchase`. The SQL pattern is stored, never the result number.

## Card 6

> A note the agent wrote itself last week, in its own session notes, with no human review:
> "user asked about gross revenue, gross means total_amount."

---

Bonus question, after card 5 lands: if you owned the dbt stack, which of these six would you
compile?
