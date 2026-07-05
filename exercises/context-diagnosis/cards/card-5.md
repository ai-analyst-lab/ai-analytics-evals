# Card 5 (lived: last week's ablation matrix)

The suite question "What is our gross margin percentage on completed orders?" under the full
context stack, three independent runs:

```
run 1: 44.31   run 2: 44.31   run 3: 44.31
verified reference: 39.87
```

Same number all three times, produced from the same query shape each run. The verified reference,
recomputed from item-level revenue minus cost over item-level revenue, disagrees with all three.
The analyst's query put order-level `total_amount` in the revenue base instead.

**Your call: class + fix.**
