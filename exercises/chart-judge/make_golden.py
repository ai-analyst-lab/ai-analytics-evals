#!/usr/bin/env python3
"""Generate the 12-chart golden set with known SWD-compliance profiles, and write the gold labels.
A chart is gold PASS only if it satisfies ALL five SWD axes. Plain matplotlib (NOT Plus SWD helpers,
which would auto-pass everything). Real 2024 NovaMart revenue from get_revenue.py.
"""
import warnings, pathlib, csv
warnings.filterwarnings("ignore")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mticker
from get_revenue import revenue_2024

HERE = pathlib.Path(__file__).parent
GOLD = HERE / "golden"; GOLD.mkdir(exist_ok=True)
months, rev = revenue_2024()
growth = round((rev[-1]-rev[0])/rev[0]*100)

def make(name, *, action_title, accent, direct_label, declutter, zero_base):
    fig, ax = plt.subplots(figsize=(7,4))
    if accent:
        fig.patch.set_facecolor("#F7F6F2"); ax.set_facecolor("#F7F6F2"); color="#D97706"
    else:
        color="#1f77b4"
    ax.plot(months, rev, color=color, lw=2.5 if accent else 2, marker=(None if declutter else "o"))
    ax.set_ylim(0 if zero_base else min(rev)*0.9, max(rev)*1.1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1e6:.1f}M"))
    if action_title: ax.set_title(f"Revenue grew {growth}% across 2024", loc="left", fontweight="bold")
    else: ax.set_title("Revenue by Month")
    if declutter:
        for sp in ["top","right"]: ax.spines[sp].set_visible(False)
        ax.grid(axis="y", alpha=0.25, color="#E5E7EB"); ax.tick_params(length=0)
    else:
        ax.grid(True, alpha=0.6)
    if direct_label:
        ax.annotate(f"${rev[-1]/1e6:.1f}M", (len(months)-1, rev[-1]), textcoords="offset points",
                    xytext=(6,4), color=color, fontweight="bold")
    fig.savefig(GOLD/f"{name}.png", dpi=100, bbox_inches="tight"); plt.close(fig)
    return all([action_title, accent, direct_label, declutter, zero_base])


def make_special(name, kind):
    """SWD-clean on the 5 current axes, but bad in a way none of them catches (for the alignment lesson)."""
    fig, ax = plt.subplots(figsize=(7,4)); fig.patch.set_facecolor("#F7F6F2"); ax.set_facecolor("#F7F6F2")
    ax.plot(months, rev, color="#D97706", lw=2.5)
    ax.set_ylim(0, max(rev)*1.1)
    for sp in ["top","right"]: ax.spines[sp].set_visible(False)
    ax.grid(axis="y", alpha=0.25, color="#E5E7EB"); ax.tick_params(length=0)
    if kind == "overclaim":
        # action-title PASSES (it's a takeaway) but the claim is false/exaggerated (real growth ~447%)
        ax.set_title("Revenue exploded 900% across 2024", loc="left", fontweight="bold")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1e6:.1f}M"))
        ax.annotate(f"${rev[-1]/1e6:.1f}M", (len(months)-1, rev[-1]), textcoords="offset points",
                    xytext=(6,4), color="#D97706", fontweight="bold")
    elif kind == "overprecise":
        # clean on the 5 axes, but every number is absurdly over-precise
        ax.set_title(f"Revenue grew {round((rev[-1]-rev[0])/rev[0]*100,4)}% across 2024", loc="left", fontweight="bold")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x:,.2f}"))
        ax.annotate(f"${rev[-1]:,.2f}", (len(months)-1, rev[-1]), textcoords="offset points",
                    xytext=(6,4), color="#D97706", fontweight="bold")
    fig.savefig(GOLD/f"{name}.png", dpi=100, bbox_inches="tight"); plt.close(fig)

# 12 charts with varied profiles (T=has-the-good-thing). PASS only if all 5.
profiles = [
    ("chart-01", dict(action_title=1,accent=1,direct_label=1,declutter=1,zero_base=1)),  # all good -> pass
    ("chart-02", dict(action_title=1,accent=1,direct_label=1,declutter=1,zero_base=1)),  # all good -> pass
    ("chart-03", dict(action_title=1,accent=1,direct_label=1,declutter=1,zero_base=1)),  # all good -> pass
    ("chart-04", dict(action_title=0,accent=1,direct_label=1,declutter=1,zero_base=1)),  # descriptive title -> fail
    ("chart-05", dict(action_title=1,accent=0,direct_label=1,declutter=1,zero_base=1)),  # default color -> fail
    ("chart-06", dict(action_title=1,accent=1,direct_label=0,declutter=1,zero_base=1)),  # no direct label -> fail
    ("chart-07", dict(action_title=1,accent=1,direct_label=1,declutter=0,zero_base=1)),  # cluttered -> fail
    ("chart-08", dict(action_title=1,accent=1,direct_label=1,declutter=1,zero_base=0)),  # truncated -> fail
    ("chart-09", dict(action_title=0,accent=0,direct_label=1,declutter=1,zero_base=1)),  # title+color -> fail
    ("chart-10", dict(action_title=1,accent=1,direct_label=1,declutter=0,zero_base=0)),  # clutter+truncated -> fail
    ("chart-11", dict(action_title=1,accent=1,direct_label=1,declutter=1,zero_base=1)),  # all good -> pass
    ("chart-12", dict(action_title=0,accent=0,direct_label=0,declutter=0,zero_base=1)),  # mostly bad -> fail
]
rows=[]
for name, prof in profiles:
    good = make(name, **prof)
    rows.append((f"{name}.png", "pass" if good else "fail"))
# two "uncovered flaw" charts: SWD-clean on the 5 axes, but a human fails them (alignment lesson)
make_special("chart-13", "overclaim");   rows.append(("chart-13.png","fail"))
make_special("chart-14", "overprecise"); rows.append(("chart-14.png","fail"))

with open(GOLD/"golden-labels.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["chart","gold_verdict"]); w.writerows(rows)
npass=sum(1 for _,v in rows if v=="pass")
print(f"wrote {len(rows)} golden charts + golden-labels.csv ({npass} pass, {len(rows)-npass} fail)")
