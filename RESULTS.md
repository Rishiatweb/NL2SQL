# Evaluation Results

## Score

- **Total:** 20 / 20 correct
- Passed (rows returned): 20
- No data returned: 0
- Errors: 0

## Questions

| # | Question | Generated SQL | Correct? | Result summary |
|---|---|---|---|---|
| 1 | How many patients do we have? | SELECT COUNT(*) AS total_patients FROM patients | Yes | total_patients=200 \| rows=1 \| chart=none |
| 2 | List all doctors and their specializations | SELECT name, specialization, department FROM doctors ORDER BY name | Yes | name=Dr. Amelia Allen, specialization=Dermatology, department=Skin Care \| rows=15 \| chart=none |
| 3 | Show me appointments for last month | SELECT a.id, p.first_name \|\| ' ' \|\| p.last_name AS patient_name, d.name AS doctor_name, a.appointment_date, a.status FROM appointments a JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id WHERE a.appointment_date >= datetime('now', 'start of month', '-1 month') AND a.appointment_date < datetime('now', 'start of month') ORDER BY a.appointment_date DESC | Yes | id=36, patient_name=Arjun Carter, doctor_name=Dr. Victoria Walker, appointment_date=2026-03-31 16:15:00, status=Complete… \| rows=48 \| chart=none |
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

## Failure Analysis

- No failures detected.