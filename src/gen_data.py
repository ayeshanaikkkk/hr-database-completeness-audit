#!/usr/bin/env python3
"""
Synthetic HR database generator for the Database Completeness Check project.

Builds a CLEAN, internally consistent 5000-employee dataset (fixed seed), then injects
realistic defects according to an error PROFILE.  Snapshot A = baseline defects,
Snapshot B = a later snapshot where some problems were cleaned and others got worse.
A CLEAN snapshot (zero defects) is also produced to prove the audit queries have no
false positives.

Usage:  python3 gen_data.py <out_dir>
"""
import datetime as dt
import json
import os
import random
import sqlite3
import sys

N_EMP = 5000
SNAP_DATE = dt.date(2026, 11, 1)
CLEAN_SEED = 42

FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Sahil", "Kunal", "Nikhil", "Siddharth", "Omkar",
         "Pratik", "Rahul", "Amit", "Sagar", "Tushar", "Yash", "Ketan", "Mihir", "Varun", "Harsh",
         "Priya", "Sneha", "Neha", "Pooja", "Anjali", "Kavita", "Shruti", "Meera", "Isha", "Divya",
         "Rutuja", "Ashwini", "Swati", "Manasi", "Gauri", "Tanvi", "Riya", "Sakshi", "Nidhi", "Aditi"]
LAST = ["Patil", "Deshmukh", "Joshi", "Kulkarni", "Jadhav", "Pawar", "Shinde", "More", "Gaikwad", "Kale",
        "Bhosale", "Chavan", "Sawant", "Mane", "Thakur", "Iyer", "Nair", "Sharma", "Verma", "Gupta",
        "Mehta", "Shah", "Desai", "Naik", "Phadke", "Apte", "Bhide", "Gokhale", "Ranade", "Karve",
        "Wagh", "Salunkhe", "Kamble", "Waghmare", "Nimbalkar", "Ghule", "Dixit", "Bapat", "Limaye", "Tilak"]
DEPTS = [("Engineering", "Hinjewadi"), ("Human Resources", "Kalyani Nagar"), ("Finance", "Baner"),
         ("Sales", "Viman Nagar"), ("Marketing", "Koregaon Park"), ("Operations", "Magarpatta"),
         ("Customer Support", "Kharadi"), ("Legal", "Shivajinagar"), ("IT Infrastructure", "Hinjewadi"),
         ("Product", "Baner"), ("Procurement", "Hadapsar"), ("Quality", "Pimpri")]
GRADES = ["G1", "G2", "G3", "G4", "G5"]
TITLES = {"G1": "Associate", "G2": "Senior Associate", "G3": "Lead", "G4": "Manager", "G5": "Senior Manager"}

# ----------------------------------------------------------------------------------------------
# Error profiles: rate = share of the relevant population that receives the defect
# ----------------------------------------------------------------------------------------------
PROFILE_A = dict(
    # completeness
    email_null=.040, phone_null=.070, dob_null=.020, pan_null=.050, join_null=.004, dept_null=.010,
    mgr_null=.015, name_blank=.004, sal_null=.008, sal_from_null=.003, pos_title_null=.010,
    pos_start_null=.004, checkout_null=.040, leave_end_null=.020, leave_type_null=.010,
    # referential integrity
    orphan_dept=.012, orphan_mgr=.006, orphan_pos=.004, orphan_sal=.003, orphan_att=.002,
    orphan_leave=.004, orphan_posdept=.003,
    # uniqueness
    dup_emp=.020, dup_email=.010, dup_pan=.004, dup_att=.005,
    # consistency / validity
    term_before_join=.008, active_with_term=.010, term_missing=.012, underage=.006,
    sal_overlap=.030, pos_overlap=.020, bad_salary=.007, sal_to_before_from=.004,
    leave_end_before_start=.008, leave_days_mismatch=.015, checkout_before_in=.006,
    att_outside_emp=.010, sal_before_join=.012, bad_email=.012, bad_status=.005,
    # business rules
    no_cur_pos=.015, multi_cur_pos=.012, no_cur_sal=.010, multi_cur_sal=.014,
    term_cur=.030, cur_with_end=.008,
)
B_FACTORS = dict(email_null=.5, phone_null=.6, dob_null=.5, pan_null=.7, orphan_dept=1.8, orphan_mgr=2.0,
                 orphan_pos=2.5, orphan_sal=2.2, orphan_att=3.0, orphan_leave=1.5, sal_overlap=1.6,
                 pos_overlap=1.4, no_cur_sal=.3, multi_cur_pos=2.0, dup_emp=.5, term_before_join=.5,
                 bad_salary=.4, checkout_null=.5, sal_before_join=1.7, bad_email=.3, term_cur=.6,
                 att_outside_emp=1.3, name_blank=.5, join_null=1.5)
PROFILE_B = {k: round(v * B_FACTORS.get(k, 1.0), 5) for k, v in PROFILE_A.items()}
PROFILES = {
    "A": dict(PROFILE_A, dept_head_orphan=1, dept_head_null=1, inj_seed=1001),
    "B": dict(PROFILE_B, dept_head_orphan=2, dept_head_null=1, inj_seed=2002),
    "CLEAN": dict({k: 0.0 for k in PROFILE_A}, dept_head_orphan=0, dept_head_null=0, inj_seed=3003),
}

SCHEMA = """
CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, location TEXT, head_emp_id INTEGER);
CREATE TABLE employees (
  emp_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, phone TEXT, dob TEXT,
  gender TEXT, pan_number TEXT, join_date TEXT, termination_date TEXT, status TEXT,
  dept_id INTEGER, manager_id INTEGER);
CREATE TABLE positions (
  position_id INTEGER PRIMARY KEY, emp_id INTEGER, dept_id INTEGER, title TEXT, grade TEXT,
  start_date TEXT, end_date TEXT, is_current INTEGER);
CREATE TABLE salaries (
  salary_id INTEGER PRIMARY KEY, emp_id INTEGER, base_salary REAL, currency TEXT,
  effective_from TEXT, effective_to TEXT, is_current INTEGER);
CREATE TABLE attendance (
  att_id INTEGER PRIMARY KEY, emp_id INTEGER, att_date TEXT, status TEXT, check_in TEXT, check_out TEXT);
CREATE TABLE leave (
  leave_id INTEGER PRIMARY KEY, emp_id INTEGER, leave_type TEXT, start_date TEXT, end_date TEXT,
  days INTEGER, status TEXT);
"""
# NOTE: deliberately no FOREIGN KEY constraints and no UNIQUE constraints (except PKs): the point
# of the audit is to measure what a legacy system without enforcement has let through.
INDEXES = """
CREATE INDEX ix_pos_emp ON positions(emp_id);
CREATE INDEX ix_sal_emp ON salaries(emp_id);
CREATE INDEX ix_att_emp ON attendance(emp_id);
CREATE INDEX ix_lv_emp ON leave(emp_id);
"""

td = dt.timedelta


def iso(d):
    return d.isoformat() if d else None


def D(s):
    return dt.date.fromisoformat(s)


def segments(start, end, rng, thresholds):
    """Contiguous, non-overlapping date segments between start and end."""
    span = (end - start).days
    nmax = 1 + sum(span > t for t in thresholds)
    n = rng.randint(1, nmax)
    cuts = sorted(rng.sample(range(120, span - 60), n - 1)) if n > 1 else []
    starts = [start] + [start + td(c) for c in cuts]
    return [(s, (starts[i + 1] - td(1)) if i + 1 < len(starts) else None) for i, s in enumerate(starts)]


def build_clean(seed=CLEAN_SEED):
    rng = random.Random(seed)
    depts = [dict(dept_id=i + 1, dept_name=n, location=l, head_emp_id=None) for i, (n, l) in enumerate(DEPTS)]
    emps, used_names, used_pan = [], set(), set()
    for eid in range(1, N_EMP + 1):
        while True:
            fn, ln = rng.choice(FIRST), rng.choice(LAST)
            join = dt.date(2010, 1, 1) + td(rng.randint(0, (dt.date(2026, 9, 30) - dt.date(2010, 1, 1)).days))
            dob = join - td(rng.randint(22 * 365, 45 * 365))
            if (fn, ln, dob) not in used_names:
                used_names.add((fn, ln, dob))
                break
        while True:
            pan = "".join(rng.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=5)) + f"{rng.randint(0, 9999):04d}" + rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ")
            if pan not in used_pan:
                used_pan.add(pan)
                break
        status, term = "Active", None
        roll = rng.random()
        if roll < .09 and (SNAP_DATE - join).days > 200:
            status = "Terminated"
            term = join + td(rng.randint(90, (SNAP_DATE - td(30) - join).days))
        elif roll < .12:
            status = "On Leave"
        emps.append(dict(
            emp_id=eid, first_name=fn, last_name=ln,
            email=f"{fn}.{ln}{eid}@punefirm.in".lower(), phone="9" + "".join(rng.choices("0123456789", k=9)),
            dob=iso(dob), gender=rng.choice(["M", "F"]), pan_number=pan, join_date=iso(join),
            termination_date=iso(term), status=status, dept_id=rng.randint(1, len(depts)),
            manager_id=None if eid == 1 else (1 if eid <= 60 else rng.randint(2, 60))))
    for d in depts:
        d["head_emp_id"] = rng.randint(2, 60)

    positions, salaries, attendance, leave = [], [], [], []
    pid = sid = aid = lid = 0
    for e in emps:
        join = D(e["join_date"])
        term = D(e["termination_date"]) if e["termination_date"] else None
        end = term or SNAP_DATE
        is_active = e["status"] != "Terminated"
        # positions
        segs = segments(join, end, rng, [400, 1200])
        for i, (s, en) in enumerate(segs):
            pid += 1
            g = GRADES[min(i + rng.randint(0, 1), 4)]
            last = i == len(segs) - 1
            positions.append(dict(
                position_id=pid, emp_id=e["emp_id"], dept_id=e["dept_id"], title=TITLES[g], grade=g,
                start_date=iso(s), end_date=iso(term) if (last and term) else iso(en),
                is_current=1 if (last and is_active) else 0))
        # salaries
        segs = segments(join, end, rng, [400, 1200, 2400])
        amt = rng.randint(300000, 2500000)
        for i, (s, en) in enumerate(segs):
            sid += 1
            last = i == len(segs) - 1
            salaries.append(dict(
                salary_id=sid, emp_id=e["emp_id"], base_salary=float(round(amt, -2)), currency="INR",
                effective_from=iso(s), effective_to=iso(term) if (last and term) else iso(en),
                is_current=1 if (last and is_active) else 0))
            amt *= 1 + rng.uniform(.05, .15)
        # attendance (10 sampled days within employment window)
        span = (end - join).days
        for off in rng.sample(range(0, span + 1), min(10, span + 1)):
            aid += 1
            st = rng.choices(["Present", "WFH", "Absent", "Leave"], [.78, .12, .05, .05])[0]
            ci = co = None
            if st in ("Present", "WFH"):
                ci = f"{rng.randint(8, 10):02d}:{rng.randint(0, 59):02d}"
                co = f"{rng.randint(17, 19):02d}:{rng.randint(0, 59):02d}"
            attendance.append(dict(att_id=aid, emp_id=e["emp_id"], att_date=iso(join + td(off)),
                                   status=st, check_in=ci, check_out=co))
        # leave
        if span >= 15:
            for _ in range(rng.choice([0, 0, 1, 1, 2, 3])):
                lid += 1
                ln_ = rng.randint(1, 10)
                s = join + td(rng.randint(0, span - 12))
                leave.append(dict(leave_id=lid, emp_id=e["emp_id"], leave_type=rng.choice(["CL", "SL", "PL", "ML"]),
                                  start_date=iso(s), end_date=iso(s + td(ln_ - 1)), days=ln_,
                                  status=rng.choice(["Approved", "Approved", "Pending", "Rejected"])))
    return dict(departments=depts, employees=emps, positions=positions, salaries=salaries,
                attendance=attendance, leave=leave)


# ----------------------------------------------------------------------------------------------
def inject(db, prof, rng):
    E, P, S, A, L, DP = (db[k] for k in ("employees", "positions", "salaries", "attendance", "leave", "departments"))
    m = {}

    def n(key, pop):
        return int(round(prof[key] * pop))

    def pick(pop, k):
        return rng.sample(pop, min(k, len(pop)))

    emp = {e["emp_id"]: e for e in E}
    pos_by, sal_by = {}, {}
    for p in P:
        pos_by.setdefault(p["emp_id"], []).append(p)
    for s in S:
        sal_by.setdefault(s["emp_id"], []).append(s)
    next_id = dict(position_id=max(p["position_id"] for p in P), salary_id=max(s["salary_id"] for s in S),
                   att_id=max(a["att_id"] for a in A), leave_id=max(l["leave_id"] for l in L))

    def nid(k):
        next_id[k] += 1
        return next_id[k]

    # --- uniqueness: duplicate employees (identity copied onto a later record, own history kept) ---
    k = n("dup_emp", N_EMP)
    targets = list(range(N_EMP - k + 1, N_EMP + 1))
    for t, src in zip(targets, pick(list(range(1, 4000)), k)):
        s, d = emp[src], emp[t]
        for f in ("first_name", "last_name", "dob", "pan_number", "gender", "phone"):
            d[f] = s[f]
        d["first_name"] = d["first_name"].upper() if rng.random() < .3 else d["first_name"]
        d["status"] = "Active" if d["status"] == "Terminated" else d["status"]
        d["termination_date"] = None
    m["dup_emp"] = k
    protected = set(targets)  # keep later injections off these to keep counts interpretable

    ids = [i for i in emp if i not in protected]
    k = n("dup_email", N_EMP)
    for a, b in zip(pick(ids, k), pick(ids, k)):
        if a != b:
            emp[a]["email"] = emp[b]["email"]
    m["dup_email"] = k
    k = n("dup_pan", N_EMP)
    for a, b in zip(pick(ids, k), pick(ids, k)):
        if a != b:
            emp[a]["pan_number"] = emp[b]["pan_number"]
    m["dup_pan"] = k
    k = n("dup_att", len(A))
    for r in pick(A, k):
        A.append(dict(r, att_id=nid("att_id")))
    m["dup_att"] = k

    # --- completeness ---
    k = n("email_null", N_EMP)
    for i in pick(ids, k):
        emp[i]["email"] = None if rng.random() < .5 else ""
    m["email_null"] = k
    for key, fld in (("phone_null", "phone"), ("dob_null", "dob"), ("pan_null", "pan_number"),
                     ("join_null", "join_date"), ("dept_null", "dept_id")):
        k = n(key, N_EMP)
        for i in pick(ids, k):
            emp[i][fld] = None
        m[key] = k
    k = n("mgr_null", N_EMP)
    for i in pick([i for i in ids if i != 1], k):
        emp[i]["manager_id"] = None
    m["mgr_null"] = k
    k = n("name_blank", N_EMP)
    for i in pick(ids, k):
        emp[i][rng.choice(["first_name", "last_name"])] = rng.choice(["", None])
    m["name_blank"] = k
    for key, tbl, fld in (("sal_null", S, "base_salary"), ("sal_from_null", S, "effective_from"),
                          ("pos_title_null", P, "title"), ("pos_start_null", P, "start_date"),
                          ("leave_end_null", L, "end_date"), ("leave_type_null", L, "leave_type")):
        k = n(key, len(tbl))
        for r in pick(tbl, k):
            r[fld] = None
        m[key] = k
    present = [a for a in A if a["status"] == "Present" and a["check_out"]]
    k = n("checkout_null", len(present))
    for r in pick(present, k):
        r["check_out"] = None
    m["checkout_null"] = k

    # --- referential integrity ---
    k = n("orphan_dept", N_EMP)
    for i in pick(ids, k):
        emp[i]["dept_id"] = rng.randint(90, 99)
    m["orphan_dept"] = k
    k = n("orphan_mgr", N_EMP)
    for i in pick([i for i in ids if i != 1], k):
        emp[i]["manager_id"] = rng.randint(90000, 99999)
    m["orphan_mgr"] = k
    k = n("orphan_posdept", len(P))
    for r in pick(P, k):
        r["dept_id"] = rng.randint(90, 99)
    m["orphan_posdept"] = k
    for key, tbl, idk in (("orphan_pos", P, "position_id"), ("orphan_sal", S, "salary_id"),
                          ("orphan_att", A, "att_id"), ("orphan_leave", L, "leave_id")):
        k = n(key, len(tbl))
        for r in pick(tbl[:], k):
            tbl.append(dict(r, **{idk: nid(idk), "emp_id": rng.randint(900000, 999999),
                                  **({"is_current": 0} if "is_current" in r else {})}))
        m[key] = k
    ok = [d for d in DP]
    for d in pick(ok, prof["dept_head_orphan"]):
        d["head_emp_id"] = 99999
    for d in pick([d for d in ok if d["head_emp_id"] != 99999], prof["dept_head_null"]):
        d["head_emp_id"] = None
    m["dept_head_orphan"], m["dept_head_null"] = prof["dept_head_orphan"], prof["dept_head_null"]

    # --- consistency ---
    terminated = [i for i in ids if emp[i]["status"] == "Terminated" and emp[i]["join_date"]]
    k = n("term_before_join", len(terminated))
    for i in pick(terminated, k):
        emp[i]["termination_date"] = iso(D(emp[i]["join_date"]) - td(rng.randint(1, 400)))
    m["term_before_join"] = k
    active = [i for i in ids if emp[i]["status"] == "Active"]
    k = n("active_with_term", len(active))
    for i in pick(active, k):
        emp[i]["termination_date"] = iso(D(emp[i]["join_date"]) + td(rng.randint(100, 1000))) if emp[i]["join_date"] else "2025-01-01"
    m["active_with_term"] = k
    good_term = [i for i in terminated if emp[i]["termination_date"] and emp[i]["termination_date"] >= emp[i]["join_date"]]
    k = n("term_missing", len(good_term))
    for i in pick(good_term, k):
        emp[i]["termination_date"] = None
    m["term_missing"] = k
    k = n("underage", N_EMP)
    for i in pick([i for i in ids if emp[i]["join_date"] and emp[i]["dob"]], k):
        emp[i]["dob"] = iso(D(emp[i]["join_date"]) - td(rng.randint(10 * 365, 17 * 365)))
    m["underage"] = k
    multi_sal = [i for i in sal_by if len(sal_by[i]) >= 2 and i not in protected]
    k = n("sal_overlap", len(sal_by))
    for i in pick(multi_sal, k):
        rows = sorted(sal_by[i], key=lambda r: r["effective_from"] or "")
        if rows[1]["effective_from"]:
            rows[0]["effective_to"] = iso(D(rows[1]["effective_from"]) + td(rng.randint(20, 90)))
    m["sal_overlap"] = k
    multi_pos = [i for i in pos_by if len(pos_by[i]) >= 2 and i not in protected]
    k = n("pos_overlap", len(pos_by))
    for i in pick(multi_pos, k):
        rows = sorted(pos_by[i], key=lambda r: r["start_date"] or "")
        if rows[1]["start_date"]:
            rows[0]["end_date"] = iso(D(rows[1]["start_date"]) + td(rng.randint(20, 90)))
    m["pos_overlap"] = k
    k = n("bad_salary", len(S))
    for r in pick(S, k):
        r["base_salary"] = rng.choice([0.0, -float(rng.randint(100000, 900000)), 900000000.0])
    m["bad_salary"] = k
    closed = [s for s in S if s["effective_to"] and s["effective_from"]]
    k = n("sal_to_before_from", len(closed))
    for r in pick(closed, k):
        r["effective_to"] = iso(D(r["effective_from"]) - td(rng.randint(2, 30)))
    m["sal_to_before_from"] = k
    lv = [l for l in L if l["start_date"] and l["end_date"]]
    k = n("leave_end_before_start", len(lv))
    for r in pick(lv, k):
        r["end_date"] = iso(D(r["start_date"]) - td(rng.randint(1, 5)))
    m["leave_end_before_start"] = k
    lv = [l for l in L if l["start_date"] and l["end_date"] and l["end_date"] >= l["start_date"] and l["days"]]
    k = n("leave_days_mismatch", len(lv))
    for r in pick(lv, k):
        r["days"] += rng.randint(1, 5)
    m["leave_days_mismatch"] = k
    both = [a for a in A if a["check_in"] and a["check_out"]]
    k = n("checkout_before_in", len(both))
    for r in pick(both, k):
        r["check_out"] = f"{rng.randint(5, 7):02d}:{rng.randint(0, 59):02d}"
    m["checkout_before_in"] = k
    inwin = [a for a in A if a["emp_id"] in emp and a["emp_id"] not in protected and emp[a["emp_id"]]["join_date"]]
    k = n("att_outside_emp", len(A))
    for r in pick(inwin, k):
        r["att_date"] = iso(D(emp[r["emp_id"]]["join_date"]) - td(rng.randint(30, 200)))
    m["att_outside_emp"] = k
    firsts = [min(v, key=lambda r: r["effective_from"] or "9") for v in sal_by.values()]
    firsts = [r for r in firsts if r["effective_from"] and emp[r["emp_id"]]["join_date"]]
    k = n("sal_before_join", len(sal_by))
    for r in pick(firsts, k):
        r["effective_from"] = iso(D(emp[r["emp_id"]]["join_date"]) - td(rng.randint(30, 365)))
    m["sal_before_join"] = k
    k = n("bad_email", N_EMP)
    for i in pick([i for i in ids if emp[i]["email"]], k):
        emp[i]["email"] = emp[i]["email"].replace("@", "")
    m["bad_email"] = k

    # --- business rules (Active employees) ---
    def cur(by, i):
        return [r for r in by.get(i, []) if r["is_current"] == 1]
    act = [i for i in active if i in pos_by]
    k = n("no_cur_pos", len(act))
    for i in pick(act, k):
        for r in cur(pos_by, i):
            r["is_current"] = 0
    m["no_cur_pos"] = k
    k = n("multi_cur_pos", len(act))
    for i in pick([i for i in act if cur(pos_by, i)], k):
        c = cur(pos_by, i)[0]
        P.append(dict(c, position_id=nid("position_id"), title="Acting " + (c["title"] or "Role"), is_current=1))
    m["multi_cur_pos"] = k
    k = n("no_cur_sal", len(act))
    for i in pick(act, k):
        for r in cur(sal_by, i):
            r["is_current"] = 0
    m["no_cur_sal"] = k
    k = n("multi_cur_sal", len(act))
    for i in pick([i for i in act if cur(sal_by, i)], k):
        c = cur(sal_by, i)[0]
        S.append(dict(c, salary_id=nid("salary_id"), base_salary=round(c["base_salary"] * 1.1, -2)))
    m["multi_cur_sal"] = k
    term_ids = [i for i in ids if emp[i]["status"] == "Terminated" and i in pos_by and i in sal_by]
    k = n("term_cur", len(term_ids))
    for i in pick(term_ids, k):
        for by in (pos_by, sal_by):
            last = max(by[i], key=lambda r: r.get("start_date") or r.get("effective_from") or "")
            last["is_current"] = 1
            last["end_date" if "end_date" in last else "effective_to"] = None
    m["term_cur"] = k
    k = n("cur_with_end", len(act))
    for i in pick(act, k):
        by, fld = rng.choice([(pos_by, "end_date"), (sal_by, "effective_to")])
        for r in cur(by, i)[:1]:
            r[fld] = iso(SNAP_DATE - td(rng.randint(10, 300)))
    m["cur_with_end"] = k

    # --- status domain errors (last, so earlier rules keep their intended populations) ---
    k = n("bad_status", N_EMP)
    for i in pick([i for i in ids if emp[i]["status"] == "Active"], k):
        emp[i]["status"] = rng.choice(["Actve", "ACTIVE ", "Resigned", ""])
    m["bad_status"] = k
    return m


def write_db(path, db):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    for t, rows in db.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        con.executemany(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [tuple(r.get(c) for c in cols) for r in rows])
    con.executescript(INDEXES)
    con.commit()
    con.close()


def main(out):
    os.makedirs(out, exist_ok=True)
    import copy
    base = build_clean()
    for label, prof in PROFILES.items():
        db = copy.deepcopy(base)
        manifest = inject(db, prof, random.Random(prof["inj_seed"]))
        path = os.path.join(out, f"snapshot_{label}.db")
        write_db(path, db)
        with open(os.path.join(out, f"injected_{label}.json"), "w") as f:
            json.dump(manifest, f, indent=1)
        print(label, {t: len(r) for t, r in db.items()})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
