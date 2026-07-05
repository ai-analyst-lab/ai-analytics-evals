# Card 2 (scenario, built on the real had_purchase quirk)

A November 2024 funnel question: "How did checkout conversion do over Black Friday week?"

The store holds the caveat, word for word: "Do not trust `sessions.had_purchase` for Nov-Dec 2024.
1,089 sessions are wrong (around Black Friday). Derive purchase from `events`."

The run's trace shows the caveat never loaded: it is not quoted, not cited, not in the loaded
context at any point. The final SQL computes November conversion from
`sessions.had_purchase = true`, and the answer comes back low, confidently, with a clean
methodology section.

**Your call: class + fix.**
