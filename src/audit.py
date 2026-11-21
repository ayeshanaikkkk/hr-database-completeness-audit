#!/usr/bin/env python3
"""
Reusable audit procedure (SQLite has no stored procedures, so this script is the "stored procedure":
it runs every check in checks.py against ANY snapshot DB and writes results to an audit log DB).

Usage:
  python3 audit.py --db data/snapshot_A.db --label A --log data/audit_log.db [--snap 2026-11-01]

Audit log tables:
  audit_run    one row per execution
  audit_result one row per (run, check): count, denominator, rate, score, severity, examples (JSON)
  audit_score  roll-ups per run: level = overall | table | dimension | table_dim | field | field_dim
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import CHECKS, DIMENSIONS  # noqa: E402

LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_run (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, db_path TEXT, snap_date TEXT, run_ts TEXT,
  employees INTEGER, overall_score REAL, checks_run INTEGER, checks_failed INTEGER);
CREATE TABLE IF NOT EXISTS audit_result (
  run_id INTEGER, check_id TEXT, tbl TEXT, field TEXT, dimension TEXT, severity TEXT, weight INTEGER,
  description TEXT, fail_count INTEGER, denominator INTEGER, fail_rate REAL, score REAL,
  root_cause TEXT, examples_json TEXT, error TEXT, PRIMARY KEY (run_id, check_id));
CREATE TABLE IF NOT EXISTS audit_score (
  run_id INTEGER, level TEXT, key TEXT, score REAL, weight_sum REAL, PRIMARY KEY (run_id, level, key));
"""


def weighted_score(rows):
    """Score = 100 * (1 - sum(w*rate)/sum(w)).  rows: iterable of (weight, rate)."""
    rows = list(rows)
    ws = sum(w for w, _ in rows)
    if not ws:
        return None, 0
    return round(100 * (1 - sum(w * r for w, r in rows) / ws), 2), ws


def run_audit(db_path, label, log_path, snap="2026-11-01"):
    src = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)  # never modifies the snapshot
    log = sqlite3.connect(log_path)
    log.executescript(LOG_SCHEMA)
    params = {"snap": snap}
    n_emp = src.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    cur = log.execute("INSERT INTO audit_run (label, db_path, snap_date, run_ts, employees) VALUES (?,?,?,?,?)",
                      (label, os.path.basename(db_path), snap, dt.datetime.now().isoformat(timespec="seconds"), n_emp))
    run_id = cur.lastrowid
    results = []
    for c in CHECKS:
        err, fails, den, ex = None, None, None, None
        try:
            fails = src.execute(c["count"], params).fetchone()[0]
            den = src.execute(c["denom"], params).fetchone()[0]
            q = src.execute(c["example"], params)
            cols = [d[0] for d in q.description]
            ex = [dict(zip(cols, r)) for r in q.fetchall()]
        except Exception as e:  # keep auditing even if one check fails on an odd snapshot
            err = str(e)
        rate = (fails / den) if (den and fails is not None) else (0.0 if fails == 0 else None)
        score = round(100 * (1 - rate), 2) if rate is not None else None
        results.append(dict(c, fails=fails, den=den, rate=rate, score=score))
        log.execute("INSERT INTO audit_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, c["id"], c["table"], c["field"], c["dim"], c["sev"], c["weight"], c["desc"], fails, den,
                     rate, score, c["cause"], json.dumps(ex, default=str), err))
    ok = [r for r in results if r["rate"] is not None]

    def put(level, key, rows):
        s, ws = weighted_score(rows)
        if s is not None:
            log.execute("INSERT INTO audit_score VALUES (?,?,?,?,?)", (run_id, level, key, s, ws))

    put("overall", "ALL", [(r["weight"], r["rate"]) for r in ok])
    for t in sorted({r["table"] for r in ok}):
        sub = [r for r in ok if r["table"] == t]
        put("table", t, [(r["weight"], r["rate"]) for r in sub])
        # completeness score vs consistency score (everything that is not completeness)
        put("table_dim", f"{t}|COMPLETENESS_SCORE", [(r["weight"], r["rate"]) for r in sub if r["dim"] == "COMP"])
        put("table_dim", f"{t}|CONSISTENCY_SCORE", [(r["weight"], r["rate"]) for r in sub if r["dim"] != "COMP"])
        for d in DIMENSIONS:
            put("table_dim", f"{t}|{d}", [(r["weight"], r["rate"]) for r in sub if r["dim"] == d])
        for f in sorted({r["field"] for r in sub}):
            fs = [r for r in sub if r["field"] == f]
            put("field", f"{t}.{f}", [(r["weight"], r["rate"]) for r in fs])
            for d in DIMENSIONS:
                put("field_dim", f"{t}.{f}|{d}", [(r["weight"], r["rate"]) for r in fs if r["dim"] == d])
    for d in DIMENSIONS:
        put("dimension", d, [(r["weight"], r["rate"]) for r in ok if r["dim"] == d])
    overall = log.execute("SELECT score FROM audit_score WHERE run_id=? AND level='overall'", (run_id,)).fetchone()[0]
    log.execute("UPDATE audit_run SET overall_score=?, checks_run=?, checks_failed=? WHERE run_id=?",
                (overall, len(results), sum(1 for r in ok if r["fails"]), run_id))
    log.commit()
    log.close()
    src.close()
    return run_id, overall, results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--log", default="data/audit_log.db")
    ap.add_argument("--snap", default="2026-11-01")
    a = ap.parse_args()
    rid, overall, res = run_audit(a.db, a.label, a.log, a.snap)
    print(f"run_id={rid} label={a.label} overall_score={overall}  failed_checks={sum(1 for r in res if r['fails'])}/{len(res)}")
    for r in sorted(res, key=lambda r: -(r["weight"] * (r["fails"] or 0)))[:8]:
        print(f"  {r['id']} [{r['sev']:8}] {r['fails']:>5} / {r['den']:<6} ({(r['rate'] or 0)*100:5.2f}%)  {r['desc'][:70]}")
