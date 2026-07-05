# Exercise: context diagnosis

"The AI got it wrong" is not a diagnosis. Six cards, each one an observed failure; four of them
happened to this cohort and two are constructed scenarios (each card says which it is). Your job,
per card: name the class and the fix route. The six fixes are completely different actions, and
two of them are not context edits at all.

## The drill

Cards are shown one at a time (`cards/card-1.md` through `cards/card-6.md`). For each:

1. Read the excerpt. Nothing on the card is hypothetical unless the card says "scenario".
2. Post **class + fix** in chat.
3. Resolve as a room, then the next card.

The two reads that make it mechanical: **did it arrive and did it help** (recall vs effect), and
**does it reproduce**.

## The six classes

| Class | The signal | The fix |
|---|---|---|
| No definition | Independent runs drift; no contract exists | Write the contract (plus its case) |
| Supply failure | The context never arrived: not cited, not loaded | Placement or trigger fix; relocate or re-route |
| Use failure | It arrived and was discounted (cited channel, ignored content) | Channel authority: relocate it resident, re-state near the point of action |
| Noise | The failure does not reproduce | No action; repeats before belief |
| Meaning error | Runs converge, the number is wrong against the business meaning | Human meaning review; no mechanism exists, say so |
| Ill-posed question | The question cannot be answered as asked (missing data, ambiguous ask) | Clarify or escalate at intake; gate methods whose required data does not exist |

## Files

- `cards/card-1.md` ... `cards/card-6.md` — the six failures, one per file, shown one at a time.
- `INSTRUCTOR-KEY.md` — class + fix per card. Do not open before the drill.
