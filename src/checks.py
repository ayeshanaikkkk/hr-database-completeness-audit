"""
Catalogue of data-quality checks (single source of truth).

Every check = a reproducible SQL query:
  count  : SELECT <unit> <frm>              -> number of violating records
  denom  : population the rate is measured against
  example: SELECT <cols> <frm> LIMIT 5      -> example records
Named parameter :snap = snapshot date (ISO) used where "today" matters.

Dimensions: COMP completeness | REF referential integrity | UNIQ uniqueness |
            CONS consistency / validity | RULE business rules
Severity weights (documented assumption): Critical 5, High 3, Medium 2, Low 1
"""

WEIGHTS = {"Critical": 5, "High": 3, "Medium": 2, "Low": 1}
DIMENSIONS = {"COMP": "Completeness", "REF": "Referential integrity", "UNIQ": "Uniqueness",
              "CONS": "Consistency / validity", "RULE": "Business rules"}

CHECKS = []


def chk(id, table, field, dim, sev, desc, frm, cols, denom, cause, unit="COUNT(*)"):
    CHECKS.append(dict(id=id, table=table, field=field, dim=dim, sev=sev, weight=WEIGHTS[sev], desc=desc,
                       count=f"SELECT {unit} {frm}", denom=denom,
                       example=f"SELECT {cols} {frm} ORDER BY 1 LIMIT 5", cause=cause))


EMP_BASE = "SELECT COUNT(*) FROM employees"
MISSING = lambda c: f"({c} IS NULL OR TRIM({c})='')"

# ------------------------------------------------------------------ COMPLETENESS
chk("C01", "employees", "email", "COMP", "Medium", "Email missing or blank",
    f"FROM employees WHERE {MISSING('email')}", "emp_id, first_name, last_name, email, status", EMP_BASE,
    "Email not mandatory on the legacy onboarding form; blanks entered as '' by bulk import.")
chk("C02", "employees", "phone", "COMP", "Low", "Phone missing or blank",
    f"FROM employees WHERE {MISSING('phone')}", "emp_id, first_name, last_name, phone, status", EMP_BASE,
    "Optional field in HR form; contact details held in a separate payroll tool.")
chk("C03", "employees", "dob", "COMP", "High", "Date of birth missing",
    "FROM employees WHERE dob IS NULL", "emp_id, first_name, last_name, dob, join_date", EMP_BASE,
    "Older records migrated from paper files; DOB never keyed in. Blocks age/statutory checks.")
chk("C04", "employees", "pan_number", "COMP", "Medium", "PAN (tax ID) missing or blank",
    f"FROM employees WHERE {MISSING('pan_number')}", "emp_id, first_name, last_name, pan_number, status", EMP_BASE,
    "New joiners given grace period to submit PAN; never back-filled.")
chk("C05", "employees", "join_date", "COMP", "Critical", "Join date missing",
    "FROM employees WHERE join_date IS NULL", "emp_id, first_name, last_name, join_date, status", EMP_BASE,
    "Record created before offer acceptance workflow completed; join date is the anchor for tenure, payroll and leave.")
chk("C06", "employees", "dept_id", "COMP", "High", "Department not assigned",
    "FROM employees WHERE dept_id IS NULL", "emp_id, first_name, last_name, dept_id, status", EMP_BASE,
    "Transfers between departments temporarily nulled the field and were not completed.")
chk("C07", "employees", "manager_id", "COMP", "Medium", "Manager missing (excluding CEO emp_id=1)",
    "FROM employees WHERE manager_id IS NULL AND emp_id<>1", "emp_id, first_name, last_name, manager_id, dept_id",
    "SELECT COUNT(*) FROM employees WHERE emp_id<>1",
    "Manager left the firm and reporting line was cleared instead of reassigned.")
chk("C08", "employees", "first_name", "COMP", "Low", "First or last name blank",
    f"FROM employees WHERE {MISSING('first_name')} OR {MISSING('last_name')}",
    "emp_id, first_name, last_name, email", EMP_BASE,
    "Mononym handling in the source system; truncated imports.")
chk("C09", "salaries", "base_salary", "COMP", "High", "Base salary missing",
    "FROM salaries WHERE base_salary IS NULL", "salary_id, emp_id, base_salary, effective_from, is_current",
    "SELECT COUNT(*) FROM salaries", "Salary revisions logged by letter, amount keyed later by payroll and sometimes skipped.")
chk("C10", "salaries", "effective_from", "COMP", "Low", "Salary effective_from missing",
    "FROM salaries WHERE effective_from IS NULL", "salary_id, emp_id, base_salary, effective_from, effective_to",
    "SELECT COUNT(*) FROM salaries", "Free-text date field in the old payroll screen rejected invalid formats silently.")
chk("C11", "positions", "title", "COMP", "Low", "Position title missing",
    "FROM positions WHERE title IS NULL", "position_id, emp_id, title, grade, start_date",
    "SELECT COUNT(*) FROM positions", "Title is derived from grade in reports so users skipped keying it.")
chk("C12", "positions", "start_date", "COMP", "Medium", "Position start date missing",
    "FROM positions WHERE start_date IS NULL", "position_id, emp_id, title, start_date, end_date",
    "SELECT COUNT(*) FROM positions", "Backdated promotions entered without effective date.")
chk("C13", "attendance", "check_out", "COMP", "Medium", "Present day with no check-out time",
    "FROM attendance WHERE status='Present' AND check_out IS NULL",
    "att_id, emp_id, att_date, status, check_in, check_out",
    "SELECT COUNT(*) FROM attendance WHERE status='Present'",
    "Biometric device sync drops punch-out events when connectivity fails.")
chk("C14", "leave", "end_date", "COMP", "Medium", "Leave end date missing",
    "FROM leave WHERE end_date IS NULL", "leave_id, emp_id, leave_type, start_date, end_date, days",
    "SELECT COUNT(*) FROM leave", "Open-ended leave requests never closed after the employee returned.")
chk("C15", "leave", "leave_type", "COMP", "Low", "Leave type missing",
    "FROM leave WHERE leave_type IS NULL", "leave_id, emp_id, leave_type, start_date, days",
    "SELECT COUNT(*) FROM leave", "Mapped leave codes from the old system had no match and defaulted to NULL.")
chk("C16", "departments", "head_emp_id", "COMP", "Low", "Department head not assigned",
    "FROM departments WHERE head_emp_id IS NULL", "dept_id, dept_name, head_emp_id",
    "SELECT COUNT(*) FROM departments", "Department head resigned; reassignment pending.")

# ------------------------------------------------------------------ REFERENTIAL INTEGRITY
chk("R01", "employees", "dept_id", "REF", "High", "employees.dept_id not found in departments",
    "FROM employees WHERE dept_id IS NOT NULL AND dept_id NOT IN (SELECT dept_id FROM departments)",
    "emp_id, first_name, last_name, dept_id", "SELECT COUNT(*) FROM employees WHERE dept_id IS NOT NULL",
    "Departments merged/retired and rows deleted without re-pointing employees (no FK constraint).")
chk("R02", "employees", "manager_id", "REF", "Medium", "employees.manager_id not found in employees",
    "FROM employees WHERE manager_id IS NOT NULL AND manager_id NOT IN (SELECT emp_id FROM employees)",
    "emp_id, first_name, last_name, manager_id", "SELECT COUNT(*) FROM employees WHERE manager_id IS NOT NULL",
    "Manager's record purged after exit while subordinates still point to the old id.")
chk("R03", "positions", "emp_id", "REF", "Critical", "positions.emp_id has no employee (orphan)",
    "FROM positions WHERE emp_id NOT IN (SELECT emp_id FROM employees)",
    "position_id, emp_id, title, start_date", "SELECT COUNT(*) FROM positions",
    "Employee rows deleted (e.g. duplicate clean-up) without cascading to child tables.")
chk("R04", "salaries", "emp_id", "REF", "Critical", "salaries.emp_id has no employee (orphan)",
    "FROM salaries WHERE emp_id NOT IN (SELECT emp_id FROM employees)",
    "salary_id, emp_id, base_salary, effective_from", "SELECT COUNT(*) FROM salaries",
    "Same as R03; orphan salary rows are a payroll-liability and privacy risk if migrated.")
chk("R05", "attendance", "emp_id", "REF", "High", "attendance.emp_id has no employee (orphan)",
    "FROM attendance WHERE emp_id NOT IN (SELECT emp_id FROM employees)",
    "att_id, emp_id, att_date, status", "SELECT COUNT(*) FROM attendance",
    "Biometric device IDs not mapped to HR ids (contractors / visitors / deleted staff).")
chk("R06", "leave", "emp_id", "REF", "High", "leave.emp_id has no employee (orphan)",
    "FROM leave WHERE emp_id NOT IN (SELECT emp_id FROM employees)",
    "leave_id, emp_id, leave_type, start_date", "SELECT COUNT(*) FROM leave",
    "Leave records survived after employee purge.")
chk("R07", "positions", "dept_id", "REF", "Medium", "positions.dept_id not found in departments",
    "FROM positions WHERE dept_id IS NOT NULL AND dept_id NOT IN (SELECT dept_id FROM departments)",
    "position_id, emp_id, dept_id, title", "SELECT COUNT(*) FROM positions WHERE dept_id IS NOT NULL",
    "Historic department codes retired during a re-organisation.")
chk("R08", "departments", "head_emp_id", "REF", "Low", "departments.head_emp_id not found in employees",
    "FROM departments WHERE head_emp_id IS NOT NULL AND head_emp_id NOT IN (SELECT emp_id FROM employees)",
    "dept_id, dept_name, head_emp_id", "SELECT COUNT(*) FROM departments WHERE head_emp_id IS NOT NULL",
    "Head's employee record removed; department row never updated.")

# ------------------------------------------------------------------ UNIQUENESS
chk("U01", "employees", "first_name", "UNIQ", "Critical",
    "Duplicate employees (same first name + last name + DOB, case-insensitive); counts all records in a duplicate group",
    """FROM employees e JOIN (SELECT LOWER(TRIM(first_name)) fn, LOWER(TRIM(last_name)) ln, dob FROM employees
        WHERE dob IS NOT NULL GROUP BY 1,2,3 HAVING COUNT(*)>1) g
        ON LOWER(TRIM(e.first_name))=g.fn AND LOWER(TRIM(e.last_name))=g.ln AND e.dob=g.dob""",
    "e.emp_id, e.first_name, e.last_name, e.dob, e.pan_number, e.join_date", EMP_BASE,
    "Rehires and re-keyed joiners were created as new employees instead of re-activating the old record.")
chk("U02", "employees", "email", "UNIQ", "Medium", "Duplicate email addresses (case-insensitive)",
    """FROM employees e JOIN (SELECT LOWER(TRIM(email)) em FROM employees WHERE email IS NOT NULL AND TRIM(email)<>''
        GROUP BY 1 HAVING COUNT(*)>1) g ON LOWER(TRIM(e.email))=g.em""",
    "e.emp_id, e.first_name, e.last_name, e.email",
    "SELECT COUNT(*) FROM employees WHERE email IS NOT NULL AND TRIM(email)<>''",
    "Copy-paste during manual entry; shared mailboxes used as personal email.")
chk("U03", "employees", "pan_number", "UNIQ", "High", "Duplicate PAN (tax ID) on different employees",
    """FROM employees e JOIN (SELECT UPPER(TRIM(pan_number)) p FROM employees WHERE pan_number IS NOT NULL AND TRIM(pan_number)<>''
        GROUP BY 1 HAVING COUNT(*)>1) g ON UPPER(TRIM(e.pan_number))=g.p""",
    "e.emp_id, e.first_name, e.last_name, e.pan_number",
    "SELECT COUNT(*) FROM employees WHERE pan_number IS NOT NULL AND TRIM(pan_number)<>''",
    "Typing errors or genuine duplicate people; tax-filing risk (Form 16 mismatch).")
chk("U04", "attendance", "att_date", "UNIQ", "Medium", "Duplicate attendance rows (same employee + date); counts all rows in a group",
    """FROM attendance a JOIN (SELECT emp_id, att_date FROM attendance GROUP BY 1,2 HAVING COUNT(*)>1) g
        ON a.emp_id=g.emp_id AND a.att_date=g.att_date""",
    "a.att_id, a.emp_id, a.att_date, a.status", "SELECT COUNT(*) FROM attendance",
    "Biometric re-sync inserts the same punch twice; no unique key on (emp_id, att_date).")

# ------------------------------------------------------------------ CONSISTENCY / VALIDITY
chk("K01", "employees", "termination_date", "CONS", "Critical", "Termination date earlier than join date",
    "FROM employees WHERE termination_date IS NOT NULL AND join_date IS NOT NULL AND termination_date<join_date",
    "emp_id, first_name, last_name, join_date, termination_date, status",
    "SELECT COUNT(*) FROM employees WHERE termination_date IS NOT NULL AND join_date IS NOT NULL",
    "Day/month swap or wrong year typed at exit; no date-order validation in the UI.")
chk("K02", "employees", "status", "CONS", "High", "Status 'Active' but has a termination date",
    "FROM employees WHERE status='Active' AND termination_date IS NOT NULL",
    "emp_id, first_name, last_name, status, termination_date",
    "SELECT COUNT(*) FROM employees WHERE status='Active'",
    "Rehire or reversed exit: date retained but status flipped back.")
chk("K03", "employees", "status", "CONS", "High", "Status 'Terminated' but termination date missing",
    "FROM employees WHERE status='Terminated' AND termination_date IS NULL",
    "emp_id, first_name, last_name, status, join_date",
    "SELECT COUNT(*) FROM employees WHERE status='Terminated'",
    "Status updated by manager; date left for HR to fill during full-and-final settlement.")
chk("K04", "employees", "dob", "CONS", "High", "Employee under 18 at joining or DOB in the future",
    "FROM employees WHERE dob IS NOT NULL AND join_date IS NOT NULL AND (dob>date(join_date,'-18 years') OR dob>:snap)",
    "emp_id, first_name, last_name, dob, join_date",
    "SELECT COUNT(*) FROM employees WHERE dob IS NOT NULL AND join_date IS NOT NULL",
    "Wrong century / year keyed; possible statutory (child labour) flag if genuine.")
chk("K05", "salaries", "effective_to", "CONS", "Critical", "Overlapping salary periods for the same employee (employees affected)",
    """FROM salaries a JOIN salaries b ON a.emp_id=b.emp_id AND a.salary_id<b.salary_id
        AND a.effective_from<=COALESCE(b.effective_to,'9999-12-31') AND b.effective_from<=COALESCE(a.effective_to,'9999-12-31')""",
    "a.emp_id, a.salary_id AS sal_a, b.salary_id AS sal_b, a.effective_from AS a_from, a.effective_to AS a_to, b.effective_from AS b_from, b.effective_to AS b_to",
    "SELECT COUNT(DISTINCT emp_id) FROM salaries",
    "Revision added without closing the previous row; concurrent edits by payroll and HR. Causes double-pay in history reports.",
    unit="COUNT(DISTINCT a.emp_id)")
chk("K06", "positions", "end_date", "CONS", "High", "Overlapping position periods for the same employee (employees affected)",
    """FROM positions a JOIN positions b ON a.emp_id=b.emp_id AND a.position_id<b.position_id
        AND a.start_date<=COALESCE(b.end_date,'9999-12-31') AND b.start_date<=COALESCE(a.end_date,'9999-12-31')""",
    "a.emp_id, a.position_id AS pos_a, b.position_id AS pos_b, a.start_date AS a_start, a.end_date AS a_end, b.start_date AS b_start, b.end_date AS b_end",
    "SELECT COUNT(DISTINCT emp_id) FROM positions",
    "Promotion/transfer recorded as a new row without end-dating the old one; also arises from concurrent 'acting' roles.",
    unit="COUNT(DISTINCT a.emp_id)")
chk("K07", "salaries", "base_salary", "CONS", "Critical", "Salary <= 0 or implausibly high (> INR 5 crore)",
    "FROM salaries WHERE base_salary IS NOT NULL AND (base_salary<=0 OR base_salary>50000000)",
    "salary_id, emp_id, base_salary, effective_from", "SELECT COUNT(*) FROM salaries WHERE base_salary IS NOT NULL",
    "Unit/decimal errors (monthly vs annual, extra zeros) and placeholder zeros for unpaid roles.")
chk("K08", "salaries", "effective_to", "CONS", "Medium", "Salary effective_to earlier than effective_from",
    "FROM salaries WHERE effective_to IS NOT NULL AND effective_from IS NOT NULL AND effective_to<effective_from",
    "salary_id, emp_id, effective_from, effective_to",
    "SELECT COUNT(*) FROM salaries WHERE effective_to IS NOT NULL AND effective_from IS NOT NULL",
    "Dates typed in wrong order; no CHECK (effective_to >= effective_from).")
chk("K09", "leave", "end_date", "CONS", "Medium", "Leave end date before start date",
    "FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND end_date<start_date",
    "leave_id, emp_id, start_date, end_date, days",
    "SELECT COUNT(*) FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL",
    "Date-picker swap; request approved without validation.")
chk("K10", "leave", "days", "CONS", "Medium", "Leave 'days' does not equal end - start + 1",
    """FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND end_date>=start_date AND days IS NOT NULL
        AND days<>CAST(julianday(end_date)-julianday(start_date)+1 AS INTEGER)""",
    "leave_id, emp_id, start_date, end_date, days",
    "SELECT COUNT(*) FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND days IS NOT NULL",
    "Days manually overridden (half-days, weekends excluded) while stored in the same column as calendar days.")
chk("K11", "attendance", "check_out", "CONS", "Medium", "Check-out time not after check-in time",
    "FROM attendance WHERE check_in IS NOT NULL AND check_out IS NOT NULL AND check_out<=check_in",
    "att_id, emp_id, att_date, check_in, check_out",
    "SELECT COUNT(*) FROM attendance WHERE check_in IS NOT NULL AND check_out IS NOT NULL",
    "Night shifts crossing midnight stored without date component; device clock drift.")
chk("K12", "attendance", "att_date", "CONS", "Medium", "Attendance dated before join date or after termination date",
    """FROM attendance a JOIN employees e ON e.emp_id=a.emp_id
        WHERE (e.join_date IS NOT NULL AND a.att_date<e.join_date)
           OR (e.termination_date IS NOT NULL AND a.att_date>e.termination_date)""",
    "a.att_id, a.emp_id, a.att_date, e.join_date, e.termination_date", "SELECT COUNT(*) FROM attendance",
    "Join/termination dates corrected after the fact but attendance was not re-validated; or pre-joining training logs.")
chk("K13", "salaries", "effective_from", "CONS", "High", "Salary effective before employee's join date",
    "FROM salaries s JOIN employees e ON e.emp_id=s.emp_id WHERE s.effective_from IS NOT NULL AND e.join_date IS NOT NULL AND s.effective_from<e.join_date",
    "s.salary_id, s.emp_id, s.effective_from, e.join_date", "SELECT COUNT(*) FROM salaries",
    "Offer-letter date used instead of actual joining date.")
chk("K14", "employees", "email", "CONS", "Low", "Email format invalid (no @ / domain)",
    "FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'' AND email NOT LIKE '%_@_%._%'",
    "emp_id, first_name, last_name, email",
    "SELECT COUNT(*) FROM employees WHERE email IS NOT NULL AND TRIM(email)<>''",
    "Free-text field with no format validation; '@' lost in CSV export/import.")
chk("K15", "employees", "status", "CONS", "Medium", "Status outside allowed values (Active / Terminated / On Leave)",
    "FROM employees WHERE status IS NULL OR status NOT IN ('Active','Terminated','On Leave')",
    "emp_id, first_name, last_name, status", EMP_BASE,
    "Free-text status instead of a lookup table; typos and trailing spaces.")

# ------------------------------------------------------------------ BUSINESS RULES
def cnt_join(tbl, cond):
    return (f"FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM {tbl} WHERE is_current=1 GROUP BY emp_id) c "
            f"ON c.emp_id=e.emp_id WHERE e.status='Active' AND {cond}")


ACT = "SELECT COUNT(*) FROM employees WHERE status='Active'"
chk("B01", "positions", "is_current", "RULE", "Critical", "Active employee with NO current position",
    cnt_join("positions", "COALESCE(c.n,0)=0"), "e.emp_id, e.first_name, e.last_name, e.status, COALESCE(c.n,0) AS current_positions", ACT,
    "Position closed on promotion/transfer but new row never inserted, or is_current flag reset in bulk.")
chk("B02", "positions", "is_current", "RULE", "Critical", "Active employee with MORE THAN ONE current position",
    cnt_join("positions", "c.n>1"), "e.emp_id, e.first_name, e.last_name, e.status, c.n AS current_positions", ACT,
    "New position added with is_current=1 but old flag never cleared; also 'acting' roles recorded as concurrent rows.")
chk("B03", "salaries", "is_current", "RULE", "Critical", "Active employee with NO current salary record",
    cnt_join("salaries", "COALESCE(c.n,0)=0"), "e.emp_id, e.first_name, e.last_name, e.status, COALESCE(c.n,0) AS current_salaries", ACT,
    "Revision closed but successor not created (payroll running off a spreadsheet).")
chk("B04", "salaries", "is_current", "RULE", "Critical", "Active employee with MORE THAN ONE current salary record",
    cnt_join("salaries", "c.n>1"), "e.emp_id, e.first_name, e.last_name, e.status, c.n AS current_salaries", ACT,
    "Correction inserted as new row instead of updating the old; flag never cleared. Risk of double payroll.")
chk("B05", "employees", "status", "RULE", "High", "Terminated employee still holding a current position or salary",
    """FROM employees e WHERE e.status='Terminated' AND (e.emp_id IN (SELECT emp_id FROM positions WHERE is_current=1)
        OR e.emp_id IN (SELECT emp_id FROM salaries WHERE is_current=1))""",
    "e.emp_id, e.first_name, e.last_name, e.status, e.termination_date",
    "SELECT COUNT(*) FROM employees WHERE status='Terminated'",
    "Exit process updates status but does not end-date child tables; risk of ghost-employee payroll.")
chk("B06", "positions", "end_date", "RULE", "Medium", "Current position (is_current=1) that has an end date",
    "FROM positions WHERE is_current=1 AND end_date IS NOT NULL", "position_id, emp_id, title, end_date, is_current",
    "SELECT COUNT(*) FROM positions WHERE is_current=1",
    "Flag and end_date maintained by different processes and drift apart.")
chk("B07", "salaries", "effective_to", "RULE", "Medium", "Current salary (is_current=1) that has an end date",
    "FROM salaries WHERE is_current=1 AND effective_to IS NOT NULL", "salary_id, emp_id, base_salary, effective_to, is_current",
    "SELECT COUNT(*) FROM salaries WHERE is_current=1",
    "Same as B06.")


def to_sql_script():
    out = ["-- HR database audit queries (auto-generated from checks.py).  Parameter :snap = snapshot date, e.g. '2026-11-01'",
           "-- Each check: (1) violation count, (2) denominator, (3) five example records.\n"]
    for c in CHECKS:
        out.append(f"-- ===== {c['id']} | {c['table']}.{c['field']} | {c['dim']} | {c['sev']} | {c['desc']}")
        out.append(f"-- Root-cause hypothesis: {c['cause']}")
        out.append(" ".join(c["count"].split()) + ";")
        out.append(" ".join(c["denom"].split()) + ";")
        out.append(" ".join(c["example"].split()) + ";\n")
    return "\n".join(out)
