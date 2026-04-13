# Evaluation Results

## Score

- **Total:** 20 / 40 correct
- Round 1 (original 20): **20 / 20**
- Round 2 (extended 20): **0 / 20**
- No data returned: 0
- Errors: 0

## Round 1 — Original Questions (Q1–Q20)

All 20 questions in this set are directly covered by seeds in `agent_memory_seed.json`.
The agent retrieves the correct SQL pattern from memory (similarity ≥ 0.88 in every case)
and executes it accurately.

| # | Question | Generated SQL | Correct? | Result summary |
|---|---|---|---|---|
| 1 | How many patients do we have? | SELECT COUNT(*) AS total_patients FROM patients | Yes | total_patients=200 \| rows=1 \| chart=none |
| 2 | List all doctors and their specializations | SELECT name, specialization FROM doctors ORDER BY name | Yes | name=Dr. Amelia Allen, specialization=Dermatology \| rows=15 \| chart=none |
| 3 | Show me appointments for last month | SELECT a.id, p.first_name \|\| ' ' \|\| p.last_name AS patient_name, d.name AS doctor_name, a.appointment_date, a.status FROM appointments a JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id WHERE a.appointment_date >= datetime('now', 'start of month', '-1 month') AND a.appointment_date < datetime('now', 'start of month') ORDER BY a.appointment_date DESC | Yes | id=36, patient_name=Arjun Carter, doctor_name=Dr. Victoria Walker, appointment_date=2026-03-31 16:15:00 \| rows=48 \| chart=none |
| 4 | Which doctor has the most appointments? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | Yes | name=Dr. Amelia Allen, appointment_count=71 \| rows=1 \| chart=none |
| 5 | What is the total revenue? | SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices | Yes | total_revenue=498572.42 \| rows=1 \| chart=none |
| 6 | Show revenue by doctor | SELECT d.name, ROUND(SUM(t.cost), 2) AS total_revenue FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY total_revenue DESC | Yes | name=Dr. Elena Foster, total_revenue=119872.01 \| rows=15 \| chart=none |
| 7 | How many cancelled appointments last quarter? | SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled' AND appointment_date >= date('now', 'start of month', '-3 months') AND appointment_date < date('now', 'start of month') | Yes | cancelled_count=23 \| rows=1 \| chart=none |
| 8 | Top 5 patients by spending | SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount), 2) AS total_spending FROM invoices i JOIN patients p ON p.id = i.patient_id GROUP BY p.id, p.first_name, p.last_name ORDER BY total_spending DESC LIMIT 5 | Yes | first_name=Sophia, last_name=Thomas, total_spending=23769.31 \| rows=5 \| chart=none |
| 9 | Average treatment cost by specialization | SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_treatment_cost DESC | Yes | specialization=Cardiology, avg_treatment_cost=2757.93 \| rows=5 \| chart=none |
| 10 | Show monthly appointment count for the past 6 months | SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count FROM appointments WHERE appointment_date >= date('now', 'start of month', '-5 months') GROUP BY strftime('%Y-%m', appointment_date) ORDER BY month | Yes | month=2025-11, appointment_count=42 \| rows=6 \| chart=none |
| 11 | Which city has the most patients? | SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1 | Yes | city=Phoenix, patient_count=27 \| rows=1 \| chart=none |
| 12 | List patients who visited more than 3 times | SELECT p.id, p.first_name, p.last_name, COUNT(*) AS visit_count FROM appointments a JOIN patients p ON p.id = a.patient_id WHERE a.status = 'Completed' GROUP BY p.id, p.first_name, p.last_name HAVING COUNT(*) > 3 ORDER BY visit_count DESC, p.last_name | Yes | id=3, first_name=Sophia, last_name=Thomas, visit_count=11 \| rows=27 \| chart=none |
| 13 | Show unpaid invoices | SELECT id, patient_id, invoice_date, total_amount, paid_amount, status FROM invoices WHERE status IN ('Pending', 'Overdue') ORDER BY invoice_date DESC | Yes | id=291, patient_id=38, invoice_date=2026-04-13, total_amount=683.56, paid_amount=439.05, status=Pending \| rows=103 \| chart=none |
| 14 | What percentage of appointments are no-shows? | SELECT ROUND(CAST(SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) AS REAL) * 100.0 / COUNT(*), 2) AS no_show_percentage FROM appointments | Yes | no_show_percentage=6.6 \| rows=1 \| chart=none |
| 15 | Show the busiest day of the week for appointments | SELECT CASE strftime('%w', appointment_date) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END AS day_of_week, COUNT(*) AS appointment_count FROM appointments GROUP BY strftime('%w', appointment_date) ORDER BY appointment_count DESC LIMIT 1 | Yes | day_of_week=Sunday, appointment_count=85 \| rows=1 \| chart=none |
| 16 | Revenue trend by month | SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount), 2) AS monthly_revenue FROM invoices GROUP BY strftime('%Y-%m', invoice_date) ORDER BY month | Yes | month=2025-04, monthly_revenue=7359.99 \| rows=13 \| chart=none |
| 17 | Average appointment duration by doctor | SELECT d.name, ROUND(AVG(t.duration_minutes), 1) AS avg_duration_minutes FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY avg_duration_minutes DESC | Yes | name=Dr. Nathan Parker, avg_duration_minutes=74.5 \| rows=15 \| chart=none |
| 18 | List patients with overdue invoices | SELECT DISTINCT p.first_name, p.last_name, p.city, i.total_amount, i.paid_amount FROM invoices i JOIN patients p ON p.id = i.patient_id WHERE i.status = 'Overdue' ORDER BY i.total_amount DESC, p.last_name | Yes | first_name=Ishaan, last_name=Bennett, city=Tampa, total_amount=4099.62, paid_amount=818.03 \| rows=35 \| chart=none |
| 19 | Compare revenue between departments | SELECT d.department, ROUND(SUM(t.cost), 2) AS total_revenue FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.department ORDER BY total_revenue DESC | Yes | department=Heart Center, total_revenue=273035.14 \| rows=5 \| chart=none |
| 20 | Show patient registration trend by month | SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS registrations FROM patients GROUP BY strftime('%Y-%m', registered_date) ORDER BY month | Yes | month=2024-10, registrations=4 \| rows=19 \| chart=none |

## Round 2 — Extended Questions (Q21–Q40)

These questions were deliberately designed to test the system on inputs outside the seed
coverage (similarity scores 0.50–0.66 against nearest seed). All 20 failed because the
memory fallback (threshold=0.45) retrieved SQL from superficially similar seeds rather
than generating a correct query for the actual question. Rows were returned in every case
but the SQL answered a different question. See Failure Analysis below.

| # | Question | Generated SQL | Correct? | Result summary |
|---|---|---|---|---|
| 21 | How many male and female patients are there? | SELECT city, COUNT(*) AS female_patients FROM patients WHERE gender = 'F' GROUP BY city ORDER BY female_patients DESC, city | No | Answered "female patients per city" (seed Q4) not gender breakdown \| rows=10 |
| 22 | What is the average age of our patients? | SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_treatment_cost DESC | No | Answered "avg treatment cost by specialization" (seed Q9) not patient age \| rows=5 |
| 23 | Which patients have never had an appointment? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" (seed Q4) not patients without appointments \| rows=1 |
| 24 | List the top 5 cities by number of patients | SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_treatment_cost DESC | No | Answered "avg treatment cost by specialization" not top cities \| rows=5 |
| 25 | How many doctors are in each specialization? | SELECT name, specialization FROM doctors ORDER BY name | No | Listed all doctors by name; did not count per specialization \| rows=15 |
| 26 | Which doctor has the highest average treatment cost? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" not highest avg cost \| rows=1 |
| 27 | What is the most common appointment status? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" not appointment status breakdown \| rows=1 |
| 28 | How many appointments were scheduled on weekends? | SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled' AND appointment_date >= date('now', 'start of month', '-3 months') AND appointment_date < date('now', 'start of month') | No | Answered "cancelled appointments last quarter" (seed Q7) not weekend count \| rows=1 |
| 29 | What is the most expensive treatment on record? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" not most expensive treatment \| rows=1 |
| 30 | What are the top 5 most common treatment names? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" not treatment frequency \| rows=1 |
| 31 | What is the total outstanding balance on unpaid invoices? | SELECT SUM(total_amount - paid_amount) FROM invoices WHERE status = 'unpaid' | No | Used status='unpaid' which does not exist in the schema (correct values: 'Pending', 'Overdue') — returned NULL \| rows=1 |
| 32 | Which patient has the highest total invoice amount? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" not patient invoice total \| rows=1 |
| 33 | What is the average invoice amount? | SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_treatment_cost DESC | No | Answered "avg treatment cost by specialization" not avg invoice \| rows=5 |
| 34 | How many treatments were performed by each department? | SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled' AND appointment_date >= date('now', 'start of month', '-3 months') AND appointment_date < date('now', 'start of month') | No | Answered "cancelled appointments last quarter" not treatments by department \| rows=1 |
| 35 | List patients who have had exactly one appointment | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Answered "doctor with most appointments" not patients with one visit \| rows=1 |
| 36 | Which doctor has performed the most completed treatments? | SELECT d.name, COUNT(*) AS appointment_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1 | No | Counted all appointments not completed treatments only \| rows=1 |
| 37 | Show total billed amount versus total paid amount | SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count FROM appointments WHERE appointment_date >= date('now', 'start of month', '-5 months') GROUP BY strftime('%Y-%m', appointment_date) ORDER BY month | No | Answered "monthly appointment count" (seed Q10) not billed vs paid totals \| rows=6 |
| 38 | Show the breakdown of invoices by status | SELECT id, patient_id, invoice_date, total_amount, paid_amount, status FROM invoices WHERE status IN ('Pending', 'Overdue') ORDER BY invoice_date DESC | No | Returned raw unpaid invoice rows (seed Q13), not a GROUP BY status breakdown \| rows=103 |
| 39 | Which medical specialization generates the most treatment revenue? | SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1 | No | Answered "city with most patients" (seed Q11) not revenue by specialization \| rows=1 |
| 40 | List patients who have invoices in more than one payment status | SELECT p.id, p.first_name, p.last_name, COUNT(*) AS visit_count FROM appointments a JOIN patients p ON p.id = a.patient_id WHERE a.status = 'Completed' GROUP BY p.id, p.first_name, p.last_name HAVING COUNT(*) > 3 ORDER BY visit_count DESC, p.last_name | No | Answered "patients with more than 3 visits" (seed Q12) not mixed invoice statuses \| rows=27 |

## Failure Analysis

**Root cause — memory fallback threshold too aggressive**

Round 2 questions were designed to score 0.50–0.66 similarity against the nearest seed,
placing them below the agent's 0.70 retrieval threshold. The intended behaviour was for
the `DefaultLlmContextEnhancer` to inject the full schema into the system prompt, after
which Gemini would generate correct SQL from scratch.

However, `main.py` implements a three-layer fallback in `collect_agent_response`. When
the agent fails to produce a `StatusCardComponent` carrying SQL (which can happen when
Gemini responds in prose rather than invoking `run_sql`), a secondary memory search runs
at a lowered threshold of **0.45**. At this threshold nearly every Round 2 question
matched a seed — just not the correct one. The fallback returned the closest SQL it could
find and the retry loop accepted it because it was syntactically valid and returned rows.

**What this means concretely**

The fallback is a safety net for when the agent pipeline stalls, not a replacement for
correct generation. At threshold=0.45 it is too eager and masks genuine LLM failures
instead of surfacing them. The fix would be to raise the fallback threshold to ≥ 0.65,
or to run the fallback SQL through a correctness check (e.g. verify column names match
the question keywords) before accepting it.

**Round 1 was unaffected**

All 20 Round 1 questions score ≥ 0.88 against their direct seeds, so they go through
the primary retrieval path and never touch the fallback. The generated SQL in every case
matches the expected query exactly.
