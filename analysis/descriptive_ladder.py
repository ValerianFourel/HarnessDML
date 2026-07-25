"""Descriptive ladder (§5): naive cell means → per-component marginals with
task-clustered SEs → two-way interactions. NO DoubleML here — this is the
descriptive tier; tidy frames for estimation are exported by `aggregate`.

Balanced-factorial identities make the ladder exact without regression
machinery: with every (config, task, seed) crossed, the marginal effect of
component s is mean(y | s on) − mean(y | s off), and its task-clustered SE
comes from the per-task paired differences (tasks are the only dependence
cluster; seeds are nested within task).

Usage:
  python -m analysis.descriptive_ladder results/mvp_grid_*/panel.parquet
"""

from __future__ import annotations

import sys
from glob import glob

import numpy as np
import pandas as pd

COMPONENTS = ["P", "T", "M", "SR", "R"]


def _clustered_effect(df: pd.DataFrame, flag: pd.Series, y: str = "y"):
    """Effect of flag (bool) on y with task-clustered SE via per-task deltas."""
    per_task = df.assign(_on=flag).groupby(["task_id", "_on"])[y].mean().unstack("_on")
    per_task = per_task.dropna()
    delta = per_task.get(True) - per_task.get(False)
    return delta.mean(), delta.std(ddof=1) / np.sqrt(len(delta)), len(delta)


def component_marginals(df: pd.DataFrame, y: str = "y") -> pd.DataFrame:
    rows = []
    for c in COMPONENTS:
        est, se, n = _clustered_effect(df, df[f"comp_{c}"], y)
        rows.append({"component": c, "effect": est, "se": se,
                     "t": est / se if se > 0 else np.nan, "n_tasks": n})
    return pd.DataFrame(rows)


def two_way_interactions(df: pd.DataFrame, y: str = "y") -> pd.DataFrame:
    """Factorial interaction contrast per component pair, task-clustered."""
    rows = []
    combos = [(True, True), (True, False), (False, True), (False, False)]
    for i, a in enumerate(COMPONENTS):
        for b in COMPONENTS[i + 1:]:
            cell = (df.groupby(["task_id", f"comp_{a}", f"comp_{b}"])[y]
                      .mean().unstack([f"comp_{a}", f"comp_{b}"]).dropna())
            if not all(c in cell.columns for c in combos):
                continue  # partial designs (pilot, thin arm) lack some cells
            delta = (cell[(True, True)] - cell[(True, False)]
                     - cell[(False, True)] + cell[(False, False)])
            rows.append({"pair": f"{a}x{b}", "interaction": delta.mean(),
                         "se": delta.std(ddof=1) / np.sqrt(len(delta))})
    out = pd.DataFrame(rows)
    if len(out):
        out["t"] = out["interaction"] / out["se"]
    return out


def slice_summary(path: str) -> dict:
    p = pd.read_parquet(path)
    ident = p.iloc[0]
    cells = p.groupby("config_id").agg(y=("y", "mean"), answered=("answered", "mean"))
    answered = p[p.answered]
    return {
        "slice": f"{ident['model_id']} x {ident['benchmark']}",
        "panel": p,
        "n": len(p),
        "bare": cells.y.get("BARE", np.nan),
        "best_cfg": cells.y.idxmax(),
        "best_y": cells.y.max(),
        "worst_cfg": cells.y.idxmin(),
        "worst_y": cells.y.min(),
        "allin_y": cells.y.get("P+T+M+SR+R", np.nan),
        "marginals": component_marginals(p),
        "marginals_answered": component_marginals(p, "answered"),
        "success_given_answered": component_marginals(answered)
        if len(answered) else None,
        "interactions": two_way_interactions(p),
    }


def main(patterns: list[str]) -> int:
    paths = sorted(set(sum((glob(g) for g in patterns), [])))
    if not paths:
        print("no panels matched", file=sys.stderr)
        return 2
    summaries = [slice_summary(p) for p in paths]

    print("=" * 78)
    print("CELL EXTREMES (naive means — argmax is winner's-cursed, see ESTIMANDS)")
    print("=" * 78)
    for s in summaries:
        print(f"{s['slice']:34s} n={s['n']:6d} BARE={s['bare']:.3f} "
              f"best={s['best_cfg']}({s['best_y']:.3f}) "
              f"worst={s['worst_cfg']}({s['worst_y']:.3f}) All-In={s['allin_y']:.3f}")

    print()
    print("=" * 78)
    print("COMPONENT MARGINALS on y  (task-clustered; * = |t|>2, ** = |t|>3)")
    print("=" * 78)
    header = f"{'slice':34s}" + "".join(f"{c:>12s}" for c in COMPONENTS)
    print(header)
    for s in summaries:
        m = s["marginals"].set_index("component")
        row = f"{s['slice']:34s}"
        for c in COMPONENTS:
            e, t = m.loc[c, "effect"], m.loc[c, "t"]
            star = "**" if abs(t) > 3 else "*" if abs(t) > 2 else ""
            row += f"{e:+10.3f}{star:<2s}"
        print(row)

    print()
    print("=" * 78)
    print("Y-DECOMPOSITION: same marginals on P(answered)  [grader-interface channel]")
    print("=" * 78)
    print(header)
    for s in summaries:
        m = s["marginals_answered"].set_index("component")
        row = f"{s['slice']:34s}"
        for c in COMPONENTS:
            e, t = m.loc[c, "effect"], m.loc[c, "t"]
            star = "**" if abs(t) > 3 else "*" if abs(t) > 2 else ""
            row += f"{e:+10.3f}{star:<2s}"
        print(row)

    print()
    print("=" * 78)
    print("TOP |t| TWO-WAY INTERACTIONS per slice (the CCI sign-flip machinery)")
    print("=" * 78)
    for s in summaries:
        if not len(s["interactions"]):
            print(f"{s['slice']:34s} (partial design — no full 2x2 cells)")
            continue
        ix = s["interactions"].reindex(
            s["interactions"].t.abs().sort_values(ascending=False).index)
        top = ix.head(3)
        cells = ", ".join(f"{r.pair}={r.interaction:+.3f}(t={r.t:+.1f})"
                          for r in top.itertuples())
        print(f"{s['slice']:34s} {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["results/mvp_grid_*/panel.parquet"]))
