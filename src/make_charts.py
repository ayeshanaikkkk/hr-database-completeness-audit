#!/usr/bin/env python3
"""Completeness/consistency heatmaps + snapshot comparison chart from the audit log."""
import os, sqlite3, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import DIMENSIONS, CHECKS
from compare import compare, latest_run

SEQ = LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
DLAB = {"COMP": "Completeness", "REF": "Ref. integrity", "UNIQ": "Uniqueness", "CONS": "Consistency", "RULE": "Business rules"}
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": MUTED})

def scores(con, label, level):
    rid = latest_run(con, label)
    return {k: s for k, s in con.execute("SELECT key,score FROM audit_score WHERE run_id=? AND level=?", (rid, level))}

def heat(ax, rows, cols, M, vmax, title):
    data = np.ma.masked_invalid(M)
    ax.set_facecolor("#efeeea")
    im = ax.imshow(data, cmap=SEQ, vmin=0, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=9, color=MUTED)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=8.5)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-.5, len(cols)), minor=True); ax.set_yticks(np.arange(-.5, len(rows)), minor=True)
    ax.grid(which="minor", color="white", linewidth=2); ax.tick_params(which="minor", length=0)
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = M[i, j]
            if np.isnan(v): continue
            ax.text(j, i, f"{v:.1f}%" if v >= .05 else "0", ha="center", va="center", fontsize=8,
                    color="white" if v > vmax * .55 else INK)
    ax.set_title(title, fontsize=11, loc="left", pad=28, fontweight="bold")
    return im

def field_heatmap(con, label, path):
    fs, fd = scores(con, label, "field"), scores(con, label, "field_dim")
    keys = []
    for c in CHECKS:
        k = f"{c['table']}.{c['field']}"
        if k not in keys: keys.append(k)
    M = np.full((len(keys), 5), np.nan)
    for i, k in enumerate(keys):
        for j, d in enumerate(DIMENSIONS):
            if f"{k}|{d}" in fd: M[i, j] = 100 - fd[f"{k}|{d}"]
    fig, ax = plt.subplots(figsize=(7.6, 0.27 * len(keys) + 1.8))
    im = heat(ax, [f"{k}  ({fs[k]:.1f})" for k in keys], [DLAB[d] for d in DIMENSIONS], M, 10,
              f"Snapshot {label}: failure rate by field and dimension (field score in brackets)")
    cb = fig.colorbar(im, ax=ax, fraction=.03, pad=.02); cb.set_label("weighted failure rate, % (capped colour scale at 10%)", fontsize=8, color=MUTED)
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=8, length=0)
    fig.text(.01, .005, "Grey = no check defined for that field/dimension.", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(path, dpi=160, bbox_inches="tight"); plt.close(fig)

def table_heatmap(con, labels, path):
    tables = ["employees", "salaries", "positions", "attendance", "leave", "departments"]
    fig, axes = plt.subplots(1, len(labels), figsize=(5.4 * len(labels), 3.6))
    for ax, lab in zip(np.atleast_1d(axes), labels):
        td = scores(con, lab, "table_dim"); ts = scores(con, lab, "table")
        M = np.full((len(tables), 5), np.nan)
        for i, t in enumerate(tables):
            for j, d in enumerate(DIMENSIONS):
                if f"{t}|{d}" in td: M[i, j] = 100 - td[f"{t}|{d}"]
        im = heat(ax, [f"{t} ({ts[t]:.1f})" for t in tables], [DLAB[d] for d in DIMENSIONS], M, 10, f"Snapshot {lab}")
        ax.set_xticklabels([DLAB[d] for d in DIMENSIONS], fontsize=8, rotation=20, ha="left", color=MUTED)
    fig.suptitle("Failure rate (%) by table and dimension; table score in brackets", x=.01, ha="left", fontsize=11, fontweight="bold", y=1.02)
    fig.tight_layout(); fig.savefig(path, dpi=160, bbox_inches="tight"); plt.close(fig)

def delta_chart(log, a, b, path, top=16):
    m, _ = compare(log, a, b)
    m = m[m.trend != "Stable"].copy()
    m["mag"] = m.weighted_impact_change.abs()
    m = m.sort_values("mag", ascending=False).head(top).sort_values("weighted_impact_change")
    fig, ax = plt.subplots(figsize=(8.2, 0.34 * len(m) + 1.4))
    colors = ["#e34948" if v > 0 else "#2a78d6" for v in m.weighted_impact_change]
    y = np.arange(len(m))
    ax.barh(y, m.delta_pp, color=colors, height=.58)
    ax.set_yticks(y); ax.set_yticklabels([f"{r.check_id}  {r.tbl}.{r.field}" for r in m.itertuples()], fontsize=8.5)
    for yi, r in zip(y, m.itertuples()):
        ax.text(r.delta_pp + (.04 if r.delta_pp >= 0 else -.04), yi, f"{r.delta_count:+d} rows", va="center",
                ha="left" if r.delta_pp >= 0 else "right", fontsize=8, color=MUTED)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlabel(f"Change in failure rate, percentage points ({a} to {b}).  Red = worsening, blue = improving", fontsize=8.5)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0); ax.grid(axis="x", color=GRID, lw=.8); ax.set_axisbelow(True)
    lo, hi = m.delta_pp.min(), m.delta_pp.max(); pad = (hi - lo) * .18
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_title(f"Snapshot {a} vs {b}: biggest movers (ranked by weighted impact)", fontsize=11, loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(path, dpi=160, bbox_inches="tight"); plt.close(fig)

if __name__ == "__main__":
    log, out = "data/audit_log.db", "outputs"
    con = sqlite3.connect(log); os.makedirs(out, exist_ok=True)
    for lab in ("A", "B"): field_heatmap(con, lab, f"{out}/heatmap_fields_{lab}.png")
    table_heatmap(con, ["A", "B"], f"{out}/heatmap_tables.png")
    delta_chart(log, "A", "B", f"{out}/snapshot_delta.png")
    print("ok")
