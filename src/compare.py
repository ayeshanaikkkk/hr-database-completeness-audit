#!/usr/bin/env python3
"""Compare two audit runs (by label) from the audit log: which issues improve / worsen.
Usage: python3 compare.py --log data/audit_log.db --a A --b B --out outputs"""
import argparse, os, sqlite3, csv
import pandas as pd

def latest_run(con, label):
    return con.execute("SELECT run_id FROM audit_run WHERE label=? ORDER BY run_id DESC LIMIT 1", (label,)).fetchone()[0]

def compare(log, a, b, tol_pp=0.05):
    con = sqlite3.connect(log)
    ra, rb = latest_run(con, a), latest_run(con, b)
    q = "SELECT check_id, tbl, field, dimension, severity, weight, description, fail_count, denominator, fail_rate FROM audit_result WHERE run_id=?"
    cols = ["check_id","tbl","field","dimension","severity","weight","description","count","denom","rate"]
    A = pd.DataFrame(con.execute(q, (ra,)).fetchall(), columns=cols)
    B = pd.DataFrame(con.execute(q, (rb,)).fetchall(), columns=cols)
    m = A.merge(B[["check_id","count","denom","rate"]], on="check_id", suffixes=(f"_{a}", f"_{b}"))
    m["delta_count"] = m[f"count_{b}"] - m[f"count_{a}"]
    m["delta_pp"] = (m[f"rate_{b}"] - m[f"rate_{a}"]) * 100
    m["trend"] = m["delta_pp"].apply(lambda d: "Worsening" if d > tol_pp else ("Improving" if d < -tol_pp else "Stable"))
    m["weighted_impact_change"] = m["weight"] * m["delta_count"]
    m = m.sort_values("weighted_impact_change", ascending=False)
    scores = {}
    for r, lab in ((ra, a), (rb, b)):
        for lvl, key, s in con.execute("SELECT level,key,score FROM audit_score WHERE run_id=? AND level IN ('overall','table','dimension')", (r,)):
            scores.setdefault((lvl, key), {})[lab] = s
    sc = pd.DataFrame([(l, k, v.get(a), v.get(b)) for (l, k), v in scores.items()], columns=["level","key",f"score_{a}",f"score_{b}"])
    sc["delta"] = sc[f"score_{b}"] - sc[f"score_{a}"]
    sc["trend"] = sc["delta"].apply(lambda d: "Improving" if d > .1 else ("Worsening" if d < -.1 else "Stable"))
    return m, sc

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="data/audit_log.db"); ap.add_argument("--a", default="A"); ap.add_argument("--b", default="B")
    ap.add_argument("--out", default="outputs")
    x = ap.parse_args()
    os.makedirs(x.out, exist_ok=True)
    m, sc = compare(x.log, x.a, x.b)
    m.to_csv(f"{x.out}/snapshot_comparison_checks.csv", index=False, float_format="%.5f")
    sc.to_csv(f"{x.out}/snapshot_comparison_scores.csv", index=False)
    print(m.trend.value_counts().to_string()); print(sc.to_string(index=False))
