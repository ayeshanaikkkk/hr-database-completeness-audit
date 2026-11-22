-- HR database audit queries (auto-generated from checks.py).  Parameter :snap = snapshot date, e.g. '2026-11-01'
-- Each check: (1) violation count, (2) denominator, (3) five example records.

-- ===== C01 | employees.email | COMP | Medium | Email missing or blank
-- Root-cause hypothesis: Email not mandatory on the legacy onboarding form; blanks entered as '' by bulk import.
SELECT COUNT(*) FROM employees WHERE (email IS NULL OR TRIM(email)='');
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, email, status FROM employees WHERE (email IS NULL OR TRIM(email)='') ORDER BY 1 LIMIT 5;

-- ===== C02 | employees.phone | COMP | Low | Phone missing or blank
-- Root-cause hypothesis: Optional field in HR form; contact details held in a separate payroll tool.
SELECT COUNT(*) FROM employees WHERE (phone IS NULL OR TRIM(phone)='');
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, phone, status FROM employees WHERE (phone IS NULL OR TRIM(phone)='') ORDER BY 1 LIMIT 5;

-- ===== C03 | employees.dob | COMP | High | Date of birth missing
-- Root-cause hypothesis: Older records migrated from paper files; DOB never keyed in. Blocks age/statutory checks.
SELECT COUNT(*) FROM employees WHERE dob IS NULL;
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, dob, join_date FROM employees WHERE dob IS NULL ORDER BY 1 LIMIT 5;

-- ===== C04 | employees.pan_number | COMP | Medium | PAN (tax ID) missing or blank
-- Root-cause hypothesis: New joiners given grace period to submit PAN; never back-filled.
SELECT COUNT(*) FROM employees WHERE (pan_number IS NULL OR TRIM(pan_number)='');
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, pan_number, status FROM employees WHERE (pan_number IS NULL OR TRIM(pan_number)='') ORDER BY 1 LIMIT 5;

-- ===== C05 | employees.join_date | COMP | Critical | Join date missing
-- Root-cause hypothesis: Record created before offer acceptance workflow completed; join date is the anchor for tenure, payroll and leave.
SELECT COUNT(*) FROM employees WHERE join_date IS NULL;
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, join_date, status FROM employees WHERE join_date IS NULL ORDER BY 1 LIMIT 5;

-- ===== C06 | employees.dept_id | COMP | High | Department not assigned
-- Root-cause hypothesis: Transfers between departments temporarily nulled the field and were not completed.
SELECT COUNT(*) FROM employees WHERE dept_id IS NULL;
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, dept_id, status FROM employees WHERE dept_id IS NULL ORDER BY 1 LIMIT 5;

-- ===== C07 | employees.manager_id | COMP | Medium | Manager missing (excluding CEO emp_id=1)
-- Root-cause hypothesis: Manager left the firm and reporting line was cleared instead of reassigned.
SELECT COUNT(*) FROM employees WHERE manager_id IS NULL AND emp_id<>1;
SELECT COUNT(*) FROM employees WHERE emp_id<>1;
SELECT emp_id, first_name, last_name, manager_id, dept_id FROM employees WHERE manager_id IS NULL AND emp_id<>1 ORDER BY 1 LIMIT 5;

-- ===== C08 | employees.first_name | COMP | Low | First or last name blank
-- Root-cause hypothesis: Mononym handling in the source system; truncated imports.
SELECT COUNT(*) FROM employees WHERE (first_name IS NULL OR TRIM(first_name)='') OR (last_name IS NULL OR TRIM(last_name)='');
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, email FROM employees WHERE (first_name IS NULL OR TRIM(first_name)='') OR (last_name IS NULL OR TRIM(last_name)='') ORDER BY 1 LIMIT 5;

-- ===== C09 | salaries.base_salary | COMP | High | Base salary missing
-- Root-cause hypothesis: Salary revisions logged by letter, amount keyed later by payroll and sometimes skipped.
SELECT COUNT(*) FROM salaries WHERE base_salary IS NULL;
SELECT COUNT(*) FROM salaries;
SELECT salary_id, emp_id, base_salary, effective_from, is_current FROM salaries WHERE base_salary IS NULL ORDER BY 1 LIMIT 5;

-- ===== C10 | salaries.effective_from | COMP | Low | Salary effective_from missing
-- Root-cause hypothesis: Free-text date field in the old payroll screen rejected invalid formats silently.
SELECT COUNT(*) FROM salaries WHERE effective_from IS NULL;
SELECT COUNT(*) FROM salaries;
SELECT salary_id, emp_id, base_salary, effective_from, effective_to FROM salaries WHERE effective_from IS NULL ORDER BY 1 LIMIT 5;

-- ===== C11 | positions.title | COMP | Low | Position title missing
-- Root-cause hypothesis: Title is derived from grade in reports so users skipped keying it.
SELECT COUNT(*) FROM positions WHERE title IS NULL;
SELECT COUNT(*) FROM positions;
SELECT position_id, emp_id, title, grade, start_date FROM positions WHERE title IS NULL ORDER BY 1 LIMIT 5;

-- ===== C12 | positions.start_date | COMP | Medium | Position start date missing
-- Root-cause hypothesis: Backdated promotions entered without effective date.
SELECT COUNT(*) FROM positions WHERE start_date IS NULL;
SELECT COUNT(*) FROM positions;
SELECT position_id, emp_id, title, start_date, end_date FROM positions WHERE start_date IS NULL ORDER BY 1 LIMIT 5;

-- ===== C13 | attendance.check_out | COMP | Medium | Present day with no check-out time
-- Root-cause hypothesis: Biometric device sync drops punch-out events when connectivity fails.
SELECT COUNT(*) FROM attendance WHERE status='Present' AND check_out IS NULL;
SELECT COUNT(*) FROM attendance WHERE status='Present';
SELECT att_id, emp_id, att_date, status, check_in, check_out FROM attendance WHERE status='Present' AND check_out IS NULL ORDER BY 1 LIMIT 5;

-- ===== C14 | leave.end_date | COMP | Medium | Leave end date missing
-- Root-cause hypothesis: Open-ended leave requests never closed after the employee returned.
SELECT COUNT(*) FROM leave WHERE end_date IS NULL;
SELECT COUNT(*) FROM leave;
SELECT leave_id, emp_id, leave_type, start_date, end_date, days FROM leave WHERE end_date IS NULL ORDER BY 1 LIMIT 5;

-- ===== C15 | leave.leave_type | COMP | Low | Leave type missing
-- Root-cause hypothesis: Mapped leave codes from the old system had no match and defaulted to NULL.
SELECT COUNT(*) FROM leave WHERE leave_type IS NULL;
SELECT COUNT(*) FROM leave;
SELECT leave_id, emp_id, leave_type, start_date, days FROM leave WHERE leave_type IS NULL ORDER BY 1 LIMIT 5;

-- ===== C16 | departments.head_emp_id | COMP | Low | Department head not assigned
-- Root-cause hypothesis: Department head resigned; reassignment pending.
SELECT COUNT(*) FROM departments WHERE head_emp_id IS NULL;
SELECT COUNT(*) FROM departments;
SELECT dept_id, dept_name, head_emp_id FROM departments WHERE head_emp_id IS NULL ORDER BY 1 LIMIT 5;

-- ===== R01 | employees.dept_id | REF | High | employees.dept_id not found in departments
-- Root-cause hypothesis: Departments merged/retired and rows deleted without re-pointing employees (no FK constraint).
SELECT COUNT(*) FROM employees WHERE dept_id IS NOT NULL AND dept_id NOT IN (SELECT dept_id FROM departments);
SELECT COUNT(*) FROM employees WHERE dept_id IS NOT NULL;
SELECT emp_id, first_name, last_name, dept_id FROM employees WHERE dept_id IS NOT NULL AND dept_id NOT IN (SELECT dept_id FROM departments) ORDER BY 1 LIMIT 5;

-- ===== R02 | employees.manager_id | REF | Medium | employees.manager_id not found in employees
-- Root-cause hypothesis: Manager's record purged after exit while subordinates still point to the old id.
SELECT COUNT(*) FROM employees WHERE manager_id IS NOT NULL AND manager_id NOT IN (SELECT emp_id FROM employees);
SELECT COUNT(*) FROM employees WHERE manager_id IS NOT NULL;
SELECT emp_id, first_name, last_name, manager_id FROM employees WHERE manager_id IS NOT NULL AND manager_id NOT IN (SELECT emp_id FROM employees) ORDER BY 1 LIMIT 5;

-- ===== R03 | positions.emp_id | REF | Critical | positions.emp_id has no employee (orphan)
-- Root-cause hypothesis: Employee rows deleted (e.g. duplicate clean-up) without cascading to child tables.
SELECT COUNT(*) FROM positions WHERE emp_id NOT IN (SELECT emp_id FROM employees);
SELECT COUNT(*) FROM positions;
SELECT position_id, emp_id, title, start_date FROM positions WHERE emp_id NOT IN (SELECT emp_id FROM employees) ORDER BY 1 LIMIT 5;

-- ===== R04 | salaries.emp_id | REF | Critical | salaries.emp_id has no employee (orphan)
-- Root-cause hypothesis: Same as R03; orphan salary rows are a payroll-liability and privacy risk if migrated.
SELECT COUNT(*) FROM salaries WHERE emp_id NOT IN (SELECT emp_id FROM employees);
SELECT COUNT(*) FROM salaries;
SELECT salary_id, emp_id, base_salary, effective_from FROM salaries WHERE emp_id NOT IN (SELECT emp_id FROM employees) ORDER BY 1 LIMIT 5;

-- ===== R05 | attendance.emp_id | REF | High | attendance.emp_id has no employee (orphan)
-- Root-cause hypothesis: Biometric device IDs not mapped to HR ids (contractors / visitors / deleted staff).
SELECT COUNT(*) FROM attendance WHERE emp_id NOT IN (SELECT emp_id FROM employees);
SELECT COUNT(*) FROM attendance;
SELECT att_id, emp_id, att_date, status FROM attendance WHERE emp_id NOT IN (SELECT emp_id FROM employees) ORDER BY 1 LIMIT 5;

-- ===== R06 | leave.emp_id | REF | High | leave.emp_id has no employee (orphan)
-- Root-cause hypothesis: Leave records survived after employee purge.
SELECT COUNT(*) FROM leave WHERE emp_id NOT IN (SELECT emp_id FROM employees);
SELECT COUNT(*) FROM leave;
SELECT leave_id, emp_id, leave_type, start_date FROM leave WHERE emp_id NOT IN (SELECT emp_id FROM employees) ORDER BY 1 LIMIT 5;

-- ===== R07 | positions.dept_id | REF | Medium | positions.dept_id not found in departments
-- Root-cause hypothesis: Historic department codes retired during a re-organisation.
SELECT COUNT(*) FROM positions WHERE dept_id IS NOT NULL AND dept_id NOT IN (SELECT dept_id FROM departments);
SELECT COUNT(*) FROM positions WHERE dept_id IS NOT NULL;
SELECT position_id, emp_id, dept_id, title FROM positions WHERE dept_id IS NOT NULL AND dept_id NOT IN (SELECT dept_id FROM departments) ORDER BY 1 LIMIT 5;

-- ===== R08 | departments.head_emp_id | REF | Low | departments.head_emp_id not found in employees
-- Root-cause hypothesis: Head's employee record removed; department row never updated.
SELECT COUNT(*) FROM departments WHERE head_emp_id IS NOT NULL AND head_emp_id NOT IN (SELECT emp_id FROM employees);
SELECT COUNT(*) FROM departments WHERE head_emp_id IS NOT NULL;
SELECT dept_id, dept_name, head_emp_id FROM departments WHERE head_emp_id IS NOT NULL AND head_emp_id NOT IN (SELECT emp_id FROM employees) ORDER BY 1 LIMIT 5;

-- ===== U01 | employees.first_name | UNIQ | Critical | Duplicate employees (same first name + last name + DOB, case-insensitive); counts all records in a duplicate group
-- Root-cause hypothesis: Rehires and re-keyed joiners were created as new employees instead of re-activating the old record.
SELECT COUNT(*) FROM employees e JOIN (SELECT LOWER(TRIM(first_name)) fn, LOWER(TRIM(last_name)) ln, dob FROM employees WHERE dob IS NOT NULL GROUP BY 1,2,3 HAVING COUNT(*)>1) g ON LOWER(TRIM(e.first_name))=g.fn AND LOWER(TRIM(e.last_name))=g.ln AND e.dob=g.dob;
SELECT COUNT(*) FROM employees;
SELECT e.emp_id, e.first_name, e.last_name, e.dob, e.pan_number, e.join_date FROM employees e JOIN (SELECT LOWER(TRIM(first_name)) fn, LOWER(TRIM(last_name)) ln, dob FROM employees WHERE dob IS NOT NULL GROUP BY 1,2,3 HAVING COUNT(*)>1) g ON LOWER(TRIM(e.first_name))=g.fn AND LOWER(TRIM(e.last_name))=g.ln AND e.dob=g.dob ORDER BY 1 LIMIT 5;

-- ===== U02 | employees.email | UNIQ | Medium | Duplicate email addresses (case-insensitive)
-- Root-cause hypothesis: Copy-paste during manual entry; shared mailboxes used as personal email.
SELECT COUNT(*) FROM employees e JOIN (SELECT LOWER(TRIM(email)) em FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'' GROUP BY 1 HAVING COUNT(*)>1) g ON LOWER(TRIM(e.email))=g.em;
SELECT COUNT(*) FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'';
SELECT e.emp_id, e.first_name, e.last_name, e.email FROM employees e JOIN (SELECT LOWER(TRIM(email)) em FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'' GROUP BY 1 HAVING COUNT(*)>1) g ON LOWER(TRIM(e.email))=g.em ORDER BY 1 LIMIT 5;

-- ===== U03 | employees.pan_number | UNIQ | High | Duplicate PAN (tax ID) on different employees
-- Root-cause hypothesis: Typing errors or genuine duplicate people; tax-filing risk (Form 16 mismatch).
SELECT COUNT(*) FROM employees e JOIN (SELECT UPPER(TRIM(pan_number)) p FROM employees WHERE pan_number IS NOT NULL AND TRIM(pan_number)<>'' GROUP BY 1 HAVING COUNT(*)>1) g ON UPPER(TRIM(e.pan_number))=g.p;
SELECT COUNT(*) FROM employees WHERE pan_number IS NOT NULL AND TRIM(pan_number)<>'';
SELECT e.emp_id, e.first_name, e.last_name, e.pan_number FROM employees e JOIN (SELECT UPPER(TRIM(pan_number)) p FROM employees WHERE pan_number IS NOT NULL AND TRIM(pan_number)<>'' GROUP BY 1 HAVING COUNT(*)>1) g ON UPPER(TRIM(e.pan_number))=g.p ORDER BY 1 LIMIT 5;

-- ===== U04 | attendance.att_date | UNIQ | Medium | Duplicate attendance rows (same employee + date); counts all rows in a group
-- Root-cause hypothesis: Biometric re-sync inserts the same punch twice; no unique key on (emp_id, att_date).
SELECT COUNT(*) FROM attendance a JOIN (SELECT emp_id, att_date FROM attendance GROUP BY 1,2 HAVING COUNT(*)>1) g ON a.emp_id=g.emp_id AND a.att_date=g.att_date;
SELECT COUNT(*) FROM attendance;
SELECT a.att_id, a.emp_id, a.att_date, a.status FROM attendance a JOIN (SELECT emp_id, att_date FROM attendance GROUP BY 1,2 HAVING COUNT(*)>1) g ON a.emp_id=g.emp_id AND a.att_date=g.att_date ORDER BY 1 LIMIT 5;

-- ===== K01 | employees.termination_date | CONS | Critical | Termination date earlier than join date
-- Root-cause hypothesis: Day/month swap or wrong year typed at exit; no date-order validation in the UI.
SELECT COUNT(*) FROM employees WHERE termination_date IS NOT NULL AND join_date IS NOT NULL AND termination_date<join_date;
SELECT COUNT(*) FROM employees WHERE termination_date IS NOT NULL AND join_date IS NOT NULL;
SELECT emp_id, first_name, last_name, join_date, termination_date, status FROM employees WHERE termination_date IS NOT NULL AND join_date IS NOT NULL AND termination_date<join_date ORDER BY 1 LIMIT 5;

-- ===== K02 | employees.status | CONS | High | Status 'Active' but has a termination date
-- Root-cause hypothesis: Rehire or reversed exit: date retained but status flipped back.
SELECT COUNT(*) FROM employees WHERE status='Active' AND termination_date IS NOT NULL;
SELECT COUNT(*) FROM employees WHERE status='Active';
SELECT emp_id, first_name, last_name, status, termination_date FROM employees WHERE status='Active' AND termination_date IS NOT NULL ORDER BY 1 LIMIT 5;

-- ===== K03 | employees.status | CONS | High | Status 'Terminated' but termination date missing
-- Root-cause hypothesis: Status updated by manager; date left for HR to fill during full-and-final settlement.
SELECT COUNT(*) FROM employees WHERE status='Terminated' AND termination_date IS NULL;
SELECT COUNT(*) FROM employees WHERE status='Terminated';
SELECT emp_id, first_name, last_name, status, join_date FROM employees WHERE status='Terminated' AND termination_date IS NULL ORDER BY 1 LIMIT 5;

-- ===== K04 | employees.dob | CONS | High | Employee under 18 at joining or DOB in the future
-- Root-cause hypothesis: Wrong century / year keyed; possible statutory (child labour) flag if genuine.
SELECT COUNT(*) FROM employees WHERE dob IS NOT NULL AND join_date IS NOT NULL AND (dob>date(join_date,'-18 years') OR dob>:snap);
SELECT COUNT(*) FROM employees WHERE dob IS NOT NULL AND join_date IS NOT NULL;
SELECT emp_id, first_name, last_name, dob, join_date FROM employees WHERE dob IS NOT NULL AND join_date IS NOT NULL AND (dob>date(join_date,'-18 years') OR dob>:snap) ORDER BY 1 LIMIT 5;

-- ===== K05 | salaries.effective_to | CONS | Critical | Overlapping salary periods for the same employee (employees affected)
-- Root-cause hypothesis: Revision added without closing the previous row; concurrent edits by payroll and HR. Causes double-pay in history reports.
SELECT COUNT(DISTINCT a.emp_id) FROM salaries a JOIN salaries b ON a.emp_id=b.emp_id AND a.salary_id<b.salary_id AND a.effective_from<=COALESCE(b.effective_to,'9999-12-31') AND b.effective_from<=COALESCE(a.effective_to,'9999-12-31');
SELECT COUNT(DISTINCT emp_id) FROM salaries;
SELECT a.emp_id, a.salary_id AS sal_a, b.salary_id AS sal_b, a.effective_from AS a_from, a.effective_to AS a_to, b.effective_from AS b_from, b.effective_to AS b_to FROM salaries a JOIN salaries b ON a.emp_id=b.emp_id AND a.salary_id<b.salary_id AND a.effective_from<=COALESCE(b.effective_to,'9999-12-31') AND b.effective_from<=COALESCE(a.effective_to,'9999-12-31') ORDER BY 1 LIMIT 5;

-- ===== K06 | positions.end_date | CONS | High | Overlapping position periods for the same employee (employees affected)
-- Root-cause hypothesis: Promotion/transfer recorded as a new row without end-dating the old one; also arises from concurrent 'acting' roles.
SELECT COUNT(DISTINCT a.emp_id) FROM positions a JOIN positions b ON a.emp_id=b.emp_id AND a.position_id<b.position_id AND a.start_date<=COALESCE(b.end_date,'9999-12-31') AND b.start_date<=COALESCE(a.end_date,'9999-12-31');
SELECT COUNT(DISTINCT emp_id) FROM positions;
SELECT a.emp_id, a.position_id AS pos_a, b.position_id AS pos_b, a.start_date AS a_start, a.end_date AS a_end, b.start_date AS b_start, b.end_date AS b_end FROM positions a JOIN positions b ON a.emp_id=b.emp_id AND a.position_id<b.position_id AND a.start_date<=COALESCE(b.end_date,'9999-12-31') AND b.start_date<=COALESCE(a.end_date,'9999-12-31') ORDER BY 1 LIMIT 5;

-- ===== K07 | salaries.base_salary | CONS | Critical | Salary <= 0 or implausibly high (> INR 5 crore)
-- Root-cause hypothesis: Unit/decimal errors (monthly vs annual, extra zeros) and placeholder zeros for unpaid roles.
SELECT COUNT(*) FROM salaries WHERE base_salary IS NOT NULL AND (base_salary<=0 OR base_salary>50000000);
SELECT COUNT(*) FROM salaries WHERE base_salary IS NOT NULL;
SELECT salary_id, emp_id, base_salary, effective_from FROM salaries WHERE base_salary IS NOT NULL AND (base_salary<=0 OR base_salary>50000000) ORDER BY 1 LIMIT 5;

-- ===== K08 | salaries.effective_to | CONS | Medium | Salary effective_to earlier than effective_from
-- Root-cause hypothesis: Dates typed in wrong order; no CHECK (effective_to >= effective_from).
SELECT COUNT(*) FROM salaries WHERE effective_to IS NOT NULL AND effective_from IS NOT NULL AND effective_to<effective_from;
SELECT COUNT(*) FROM salaries WHERE effective_to IS NOT NULL AND effective_from IS NOT NULL;
SELECT salary_id, emp_id, effective_from, effective_to FROM salaries WHERE effective_to IS NOT NULL AND effective_from IS NOT NULL AND effective_to<effective_from ORDER BY 1 LIMIT 5;

-- ===== K09 | leave.end_date | CONS | Medium | Leave end date before start date
-- Root-cause hypothesis: Date-picker swap; request approved without validation.
SELECT COUNT(*) FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND end_date<start_date;
SELECT COUNT(*) FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL;
SELECT leave_id, emp_id, start_date, end_date, days FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND end_date<start_date ORDER BY 1 LIMIT 5;

-- ===== K10 | leave.days | CONS | Medium | Leave 'days' does not equal end - start + 1
-- Root-cause hypothesis: Days manually overridden (half-days, weekends excluded) while stored in the same column as calendar days.
SELECT COUNT(*) FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND end_date>=start_date AND days IS NOT NULL AND days<>CAST(julianday(end_date)-julianday(start_date)+1 AS INTEGER);
SELECT COUNT(*) FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND days IS NOT NULL;
SELECT leave_id, emp_id, start_date, end_date, days FROM leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND end_date>=start_date AND days IS NOT NULL AND days<>CAST(julianday(end_date)-julianday(start_date)+1 AS INTEGER) ORDER BY 1 LIMIT 5;

-- ===== K11 | attendance.check_out | CONS | Medium | Check-out time not after check-in time
-- Root-cause hypothesis: Night shifts crossing midnight stored without date component; device clock drift.
SELECT COUNT(*) FROM attendance WHERE check_in IS NOT NULL AND check_out IS NOT NULL AND check_out<=check_in;
SELECT COUNT(*) FROM attendance WHERE check_in IS NOT NULL AND check_out IS NOT NULL;
SELECT att_id, emp_id, att_date, check_in, check_out FROM attendance WHERE check_in IS NOT NULL AND check_out IS NOT NULL AND check_out<=check_in ORDER BY 1 LIMIT 5;

-- ===== K12 | attendance.att_date | CONS | Medium | Attendance dated before join date or after termination date
-- Root-cause hypothesis: Join/termination dates corrected after the fact but attendance was not re-validated; or pre-joining training logs.
SELECT COUNT(*) FROM attendance a JOIN employees e ON e.emp_id=a.emp_id WHERE (e.join_date IS NOT NULL AND a.att_date<e.join_date) OR (e.termination_date IS NOT NULL AND a.att_date>e.termination_date);
SELECT COUNT(*) FROM attendance;
SELECT a.att_id, a.emp_id, a.att_date, e.join_date, e.termination_date FROM attendance a JOIN employees e ON e.emp_id=a.emp_id WHERE (e.join_date IS NOT NULL AND a.att_date<e.join_date) OR (e.termination_date IS NOT NULL AND a.att_date>e.termination_date) ORDER BY 1 LIMIT 5;

-- ===== K13 | salaries.effective_from | CONS | High | Salary effective before employee's join date
-- Root-cause hypothesis: Offer-letter date used instead of actual joining date.
SELECT COUNT(*) FROM salaries s JOIN employees e ON e.emp_id=s.emp_id WHERE s.effective_from IS NOT NULL AND e.join_date IS NOT NULL AND s.effective_from<e.join_date;
SELECT COUNT(*) FROM salaries;
SELECT s.salary_id, s.emp_id, s.effective_from, e.join_date FROM salaries s JOIN employees e ON e.emp_id=s.emp_id WHERE s.effective_from IS NOT NULL AND e.join_date IS NOT NULL AND s.effective_from<e.join_date ORDER BY 1 LIMIT 5;

-- ===== K14 | employees.email | CONS | Low | Email format invalid (no @ / domain)
-- Root-cause hypothesis: Free-text field with no format validation; '@' lost in CSV export/import.
SELECT COUNT(*) FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'' AND email NOT LIKE '%_@_%._%';
SELECT COUNT(*) FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'';
SELECT emp_id, first_name, last_name, email FROM employees WHERE email IS NOT NULL AND TRIM(email)<>'' AND email NOT LIKE '%_@_%._%' ORDER BY 1 LIMIT 5;

-- ===== K15 | employees.status | CONS | Medium | Status outside allowed values (Active / Terminated / On Leave)
-- Root-cause hypothesis: Free-text status instead of a lookup table; typos and trailing spaces.
SELECT COUNT(*) FROM employees WHERE status IS NULL OR status NOT IN ('Active','Terminated','On Leave');
SELECT COUNT(*) FROM employees;
SELECT emp_id, first_name, last_name, status FROM employees WHERE status IS NULL OR status NOT IN ('Active','Terminated','On Leave') ORDER BY 1 LIMIT 5;

-- ===== B01 | positions.is_current | RULE | Critical | Active employee with NO current position
-- Root-cause hypothesis: Position closed on promotion/transfer but new row never inserted, or is_current flag reset in bulk.
SELECT COUNT(*) FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM positions WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND COALESCE(c.n,0)=0;
SELECT COUNT(*) FROM employees WHERE status='Active';
SELECT e.emp_id, e.first_name, e.last_name, e.status, COALESCE(c.n,0) AS current_positions FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM positions WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND COALESCE(c.n,0)=0 ORDER BY 1 LIMIT 5;

-- ===== B02 | positions.is_current | RULE | Critical | Active employee with MORE THAN ONE current position
-- Root-cause hypothesis: New position added with is_current=1 but old flag never cleared; also 'acting' roles recorded as concurrent rows.
SELECT COUNT(*) FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM positions WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND c.n>1;
SELECT COUNT(*) FROM employees WHERE status='Active';
SELECT e.emp_id, e.first_name, e.last_name, e.status, c.n AS current_positions FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM positions WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND c.n>1 ORDER BY 1 LIMIT 5;

-- ===== B03 | salaries.is_current | RULE | Critical | Active employee with NO current salary record
-- Root-cause hypothesis: Revision closed but successor not created (payroll running off a spreadsheet).
SELECT COUNT(*) FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM salaries WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND COALESCE(c.n,0)=0;
SELECT COUNT(*) FROM employees WHERE status='Active';
SELECT e.emp_id, e.first_name, e.last_name, e.status, COALESCE(c.n,0) AS current_salaries FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM salaries WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND COALESCE(c.n,0)=0 ORDER BY 1 LIMIT 5;

-- ===== B04 | salaries.is_current | RULE | Critical | Active employee with MORE THAN ONE current salary record
-- Root-cause hypothesis: Correction inserted as new row instead of updating the old; flag never cleared. Risk of double payroll.
SELECT COUNT(*) FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM salaries WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND c.n>1;
SELECT COUNT(*) FROM employees WHERE status='Active';
SELECT e.emp_id, e.first_name, e.last_name, e.status, c.n AS current_salaries FROM employees e LEFT JOIN (SELECT emp_id, COUNT(*) n FROM salaries WHERE is_current=1 GROUP BY emp_id) c ON c.emp_id=e.emp_id WHERE e.status='Active' AND c.n>1 ORDER BY 1 LIMIT 5;

-- ===== B05 | employees.status | RULE | High | Terminated employee still holding a current position or salary
-- Root-cause hypothesis: Exit process updates status but does not end-date child tables; risk of ghost-employee payroll.
SELECT COUNT(*) FROM employees e WHERE e.status='Terminated' AND (e.emp_id IN (SELECT emp_id FROM positions WHERE is_current=1) OR e.emp_id IN (SELECT emp_id FROM salaries WHERE is_current=1));
SELECT COUNT(*) FROM employees WHERE status='Terminated';
SELECT e.emp_id, e.first_name, e.last_name, e.status, e.termination_date FROM employees e WHERE e.status='Terminated' AND (e.emp_id IN (SELECT emp_id FROM positions WHERE is_current=1) OR e.emp_id IN (SELECT emp_id FROM salaries WHERE is_current=1)) ORDER BY 1 LIMIT 5;

-- ===== B06 | positions.end_date | RULE | Medium | Current position (is_current=1) that has an end date
-- Root-cause hypothesis: Flag and end_date maintained by different processes and drift apart.
SELECT COUNT(*) FROM positions WHERE is_current=1 AND end_date IS NOT NULL;
SELECT COUNT(*) FROM positions WHERE is_current=1;
SELECT position_id, emp_id, title, end_date, is_current FROM positions WHERE is_current=1 AND end_date IS NOT NULL ORDER BY 1 LIMIT 5;

-- ===== B07 | salaries.effective_to | RULE | Medium | Current salary (is_current=1) that has an end date
-- Root-cause hypothesis: Same as B06.
SELECT COUNT(*) FROM salaries WHERE is_current=1 AND effective_to IS NOT NULL;
SELECT COUNT(*) FROM salaries WHERE is_current=1;
SELECT salary_id, emp_id, base_salary, effective_to, is_current FROM salaries WHERE is_current=1 AND effective_to IS NOT NULL ORDER BY 1 LIMIT 5;
