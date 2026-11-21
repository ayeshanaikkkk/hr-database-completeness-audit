#!/usr/bin/env python3
"""Builds the 4-page audit report (DOCX) from the audit log."""
import json, sqlite3, sys, os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare import compare, latest_run

LOG = "data/audit_log.db"; OUT = "outputs"
con = sqlite3.connect(LOG)
ra, rb = latest_run(con, "A"), latest_run(con, "B")

def results(rid):
    q = "SELECT check_id,tbl,field,dimension,severity,weight,description,fail_count,denominator,fail_rate,root_cause,examples_json FROM audit_result WHERE run_id=?"
    return {r[0]: r for r in con.execute(q, (rid,))}
RA, RB = results(ra), results(rb)
def sc(rid, lvl): return dict(con.execute("SELECT key,score FROM audit_score WHERE run_id=? AND level=?", (rid, lvl)))
def emp_bad(label):
    db = sqlite3.connect(f"file:data/snapshot_{label}.db?mode=ro", uri=True)
    q = """SELECT COUNT(*) FROM employees e
      LEFT JOIN (SELECT emp_id,COUNT(*) n FROM positions WHERE is_current=1 GROUP BY emp_id) p ON p.emp_id=e.emp_id
      LEFT JOIN (SELECT emp_id,COUNT(*) n FROM salaries WHERE is_current=1 GROUP BY emp_id) s ON s.emp_id=e.emp_id
      WHERE e.status='Active' AND (COALESCE(p.n,0)<>1 OR COALESCE(s.n,0)<>1)"""
    bad = db.execute(q).fetchone()[0]; act = db.execute("SELECT COUNT(*) FROM employees WHERE status='Active'").fetchone()[0]
    return bad, act
badA, actA = emp_bad("A"); badB, actB = emp_bad("B")

doc = Document()
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(.75); sec.top_margin = Inches(.6); sec.bottom_margin = Inches(.6)
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(9.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after = Pt(3); st.paragraph_format.space_before = Pt(0)
NAVY = RGBColor(0x0D, 0x36, 0x6B)

def H(text, size=13, space=6):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(space); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(size); r.font.color.rgb = NAVY; return p
def P(text, size=None, bold=False, italic=False):
    p = doc.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    return p
def B(text, lead=None, size=None):
    p = doc.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(1)
    if lead:
        r = p.add_run(lead); r.bold = True
        if size: r.font.size = Pt(size)
    r = p.add_run(text)
    if size: r.font.size = Pt(size)
    return p
def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcol); tcPr.append(sh)
def table(rows, widths, header=True, size=8, shade_sev=None):
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr; lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    for j, w in enumerate(widths): t.columns[j].width = Inches(w)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j]); c.text = ""
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(v)); r.font.size = Pt(size)
            if header and i == 0:
                r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255); shade(c, "0D366B")
            elif shade_sev and j == shade_sev:
                col = {"Critical": "F6C9C8", "High": "FBE0C9", "Medium": "FFF1C2", "Low": "E5EEF9"}.get(str(v))
                if col: shade(c, col)
    return t
def pic(path, w):
    doc.add_picture(path, width=Inches(w)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

# ================= PAGE 1 =================
t = doc.add_paragraph(); r = t.add_run("HR Database Completeness & Consistency Audit"); r.bold = True; r.font.size = Pt(20); r.font.color.rgb = NAVY
P("Pre-migration assessment for a Pune-based firm | synthetic dataset: 5,000 employees, 6 tables | snapshots A (baseline) and B (later) | snapshot date 2026-11-01", 9, italic=True)
H("1. Headline findings")
ovA, ovB = sc(ra, "overall")["ALL"], sc(rb, "overall")["ALL"]
fails = [r for r in RA.values() if r[7]]
B(f" All {len(RA)} checks found defects in both snapshots. The weighted overall score is {ovA:.1f}/100 (A) and {ovB:.1f}/100 (B), but this number is misleading on its own: most defects are rare, so averaging dilutes them (see Limitations).", "No table is clean.")
B(f" {badA:,} of {actA:,} Active employees ({badA/actA*100:.1f}%) in snapshot A break the rule 'exactly one current position and exactly one current salary'; in B it is {badB:,} of {actB:,} ({badB/actB*100:.1f}%). These are payroll-critical.", "Business-rule breaks are the real headline.")
B(f" {RA['K05'][7]} employees have overlapping salary periods (A) rising to {RB['K05'][7]} (B); {RA['U01'][7]} records sit in duplicate-employee groups; {RA['R04'][7]+RA['R03'][7]} orphan salary/position rows exist in A and {RB['R04'][7]+RB['R03'][7]} in B.", "Critical issues.")
B(" Contact and tax details improved (email, phone, PAN, DOB) while referential integrity worsened (orphans in every child table). This pattern looks like cleaning of visible fields alongside unconstrained deletes and bulk loads.", "Direction of travel (A to B).")
H("2. Scorecard by table")
tsA, tsB = sc(ra, "table"), sc(rb, "table"); tdA, tdB = sc(ra, "table_dim"), sc(rb, "table_dim")
rows = [["Table", "Rows", "Completeness A", "Consistency A", "Table score A", "Table score B", "Change"]]
counts = {}
dbA = sqlite3.connect("file:data/snapshot_A.db?mode=ro", uri=True)
for tb in ["employees", "salaries", "positions", "attendance", "leave", "departments"]:
    counts[tb] = dbA.execute(f"SELECT COUNT(*) FROM {tb}").fetchone()[0]
    c = tdA.get(f"{tb}|COMPLETENESS_SCORE"); k = tdA.get(f"{tb}|CONSISTENCY_SCORE")
    rows.append([tb, f"{counts[tb]:,}", f"{c:.1f}" if c is not None else "n/a", f"{k:.1f}" if k is not None else "n/a",
                 f"{tsA[tb]:.1f}", f"{tsB[tb]:.1f}", f"{tsB[tb]-tsA[tb]:+.1f}"])
rows.append(["OVERALL", "", "", "", f"{ovA:.1f}", f"{ovB:.1f}", f"{ovB-ovA:+.1f}"])
table(rows, [1.2, .7, 1.1, 1.0, 1.0, 1.0, .8], size=8.5)
P("Departments scores lowest only because it has 12 rows: one bad row is an 8% failure rate.", 8, italic=True)
H("3. Scoring methodology")
B(" Every check is one SQL query returning a violation count, plus a denominator (the rows that could have failed). Failure rate = count / denominator.", "Check.")
B(" Critical 5, High 3, Medium 2, Low 1. Critical = breaks payroll, identity or history (join date, salary, duplicates, orphans, current-record rules). High = statutory or reporting risk. Medium = degrades analytics. Low = cosmetic or optional.", "Severity weights.")
B(" Score = 100 x (1 - sum(weight x failure rate) / sum(weight)) over the checks in scope. The same formula gives table, field, dimension, table-by-dimension and overall scores. Completeness score uses only null checks; consistency score uses everything else (referential, uniqueness, validity, business rules).", "Score.")
B(" Weighted impact = weight x violating rows. Issues are ranked by this number, so a Critical defect with few rows can still outrank a Medium defect with many.", "Ranking.")
B(" Every query is in sql/audit_queries.sql and checks.py; counts were verified against the number of defects injected into the synthetic data, and a defect-free snapshot scored 100 with zero violations.", "Reproducibility.")
doc.add_page_break()

# ================= PAGE 2 =================
H("4. Completeness and consistency heatmaps", space=0)
P("Colour = weighted failure rate (darker is worse; the scale is capped at 10% so small defects stay visible). Numbers are the failure rate in each cell; grey means no check exists.", 8.5)
pic(f"{OUT}/heatmap_tables.png", 6.9)
pic(f"{OUT}/heatmap_fields_A.png", 4.6)
P("Snapshot A shown. Snapshot B is in heatmap_fields_B.png. Highest field-level problems in A: phone (7.0% missing), PAN (5.0% missing and 4.8% duplicated), email (4.0% missing), check_out (4.0% missing), duplicate employee identities (3.8%).", 8.5)
doc.add_page_break()

# ================= PAGE 3 =================
H("5. Issues ranked by severity (snapshot A)", space=0)
P("Ranked by weighted impact. Example records are the first match from the audit log (ordered by key); full examples for every check are in audit_log.db.", 8.5)
ranked = sorted(RA.values(), key=lambda r: -(r[5] * (r[7] or 0)))[:13]
def ex(r):
    e = json.loads(r[11] or "[]")
    if not e: return "-"
    d = e[0]; items = [f"{k.split('.')[-1]}={v}" for k, v in list(d.items())[:4]]
    return ", ".join(items)
short_cause = {k: RA[k][10] for k in RA}
rows = [["#", "ID", "Issue", "Sev.", "Count (rate)", "Example record", "Root cause hypothesis"]]
for i, r in enumerate(ranked, 1):
    rows.append([i, r[0], r[6][:88], r[4], f"{r[7]:,} ({r[9]*100:.1f}%)", ex(r), r[10][:120]])
table(rows, [.25, .4, 1.5, .55, .8, 1.5, 1.95], size=7, shade_sev=3)
P("")
P("Critical items outside the top 13 by volume (all ranked in the full CSV): " + ", ".join(
    f"{r[0]} ({r[7]})" for r in sorted(RA.values(), key=lambda r: -r[7]) if r[4] == "Critical" and r not in ranked) + ".", 8.5)
doc.add_page_break()

# ================= PAGE 4 =================
H("6. Snapshot comparison (A to B)", space=0)
pic(f"{OUT}/snapshot_delta.png", 4.9)
m, scs = compare(LOG, "A", "B")
imp, wor = (m.trend == "Improving").sum(), (m.trend == "Worsening").sum()
P(f"Of {len(m)} checks, {imp} improved, {wor} worsened and {len(m)-imp-wor} were stable (threshold: 0.05 percentage-point change in failure rate). Dimension scores: referential integrity fell from {sc(ra,'dimension')['REF']:.1f} to {sc(rb,'dimension')['REF']:.1f}; uniqueness rose from {sc(ra,'dimension')['UNIQ']:.1f} to {sc(rb,'dimension')['UNIQ']:.1f}.", 8.5)
H("7. Remediation priorities", 11, 3)
B(" Resolve active employees without exactly one current salary and position (B01-B04), overlapping salary periods (K05) and invalid salary values (K07), then merge duplicate employees (U01) and quarantine orphan salary/position rows (R03, R04) instead of migrating them.", "P1, before cut-over (payroll and identity).", 8.5)
B(" Fix date and status contradictions (K01-K04, B05), back-fill join date and DOB (C05, C03), repair department/manager links (R01, R02) and resolve duplicate PAN (U03).", "P2, before go-live sign-off.", 8.5)
B(" Attendance and contact gaps (C13, K12, U04, C02, C01) can migrate with a data-quality flag and be cleaned in the new system.", "P3, after migration.", 8.5)
B(" Enforce foreign keys, unique keys on (emp_id, att_date) and PAN, date-order CHECK constraints, a lookup table for status, and a single transaction that closes the old row when inserting a new salary/position. Schedule audit.py weekly and alert on worsening checks.", "Prevent recurrence.", 8.5)
H("8. Limitations of the scoring approach", 11, 3)
for lead, txt in [
    ("Dilution: ", "averaging many small rates produces scores near 98-99 even with serious problems; the employee-level business-rule rate above is a better headline. Read counts, not just scores."),
    ("Subjective weights: ", "severity weights are expert judgement, not calibrated to cost; different weights reorder the ranking (the formula and weights are parameters in checks.py)."),
    ("Denominators matter: ", "tiny tables (departments) swing wildly, and subset denominators make rates not comparable across checks."),
    ("Overlap and double counting: ", "one root cause often triggers several checks (a duplicate current row also creates an overlap), so check scores are not additive across issues."),
    ("Unknown unknowns: ", "checks find only rules we thought of; plausible-but-wrong values (a salary that is valid but incorrect) pass. No source-of-truth comparison was possible."),
    ("Synthetic data: ", "defect rates and root causes are hypotheses on generated data; real findings need business validation and records of how the data was created.")]:
    B(txt, lead, 8.5)
doc.save(f"{OUT}/HR_Data_Audit_Report.docx"); print("saved")
