\# HR Database Completeness Check



An independent data-quality audit of a relational HR database, prepared for a Pune firm planning to migrate to a new system.



\## The problem

Before migrating, the firm needs to know how complete and consistent its HR data really is. This project measures that with reproducible SQL checks and a scoring method.



\## The database

Synthetic data for 5,000 employees across six related tables: employees, departments, positions, salaries, attendance and leave. Realistic errors were injected on purpose, so the true number of defects is known.



\## What the project does

\- Runs 50 SQL checks: missing values, orphan keys, duplicate employees, overlapping salary and position histories, contradictory dates, and business-rule breaks

\- Gives each issue a severity weight and calculates scores per table, field and overall

\- Provides a reusable audit script that runs on any snapshot and writes results to an audit log

\- Compares two snapshots to show which issues are improving or worsening



\## Project structure

\- `src/` - data generator, check catalogue, audit procedure, comparison, charts and report builder



More files (SQL queries, data, results and report) will be added over the coming days.

