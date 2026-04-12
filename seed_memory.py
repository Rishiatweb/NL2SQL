from __future__ import annotations

from project_utils import (
    DATABASE_PATH,
    SeedExample,
    configure_logging,
    execute_select_sql,
    save_seed_pairs,
    validate_select_sql,
)


SEED_EXAMPLES = [
    SeedExample(
        question="How many patients do we have?",
        sql="SELECT COUNT(*) AS total_patients FROM patients",
        category="patients",
    ),
    SeedExample(
        question="List all doctors and their specializations.",
        sql="SELECT name, specialization, department FROM doctors ORDER BY name",
        category="doctors",
    ),
    SeedExample(
        question="Which city has the most patients?",
        sql=(
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1"
        ),
        category="patients",
    ),
    SeedExample(
        question="How many female patients are registered in each city?",
        sql=(
            "SELECT city, COUNT(*) AS female_patients "
            "FROM patients WHERE gender = 'F' "
            "GROUP BY city ORDER BY female_patients DESC, city"
        ),
        category="patients",
    ),
    SeedExample(
        question="Which doctor has the most appointments?",
        sql=(
            "SELECT d.name, COUNT(*) AS appointment_count "
            "FROM appointments a "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY appointment_count DESC LIMIT 1"
        ),
        category="doctors",
    ),
    SeedExample(
        question="Show appointment counts by status for the last 90 days.",
        sql=(
            "SELECT status, COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE appointment_date >= datetime('now', '-90 days') "
            "GROUP BY status ORDER BY appointment_count DESC"
        ),
        category="appointments",
    ),
    SeedExample(
        question="Show me appointments for last month.",
        sql=(
            "SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name, "
            "d.name AS doctor_name, a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE a.appointment_date >= datetime('now', 'start of month', '-1 month') "
            "AND a.appointment_date < datetime('now', 'start of month') "
            "ORDER BY a.appointment_date DESC"
        ),
        category="appointments",
    ),
    SeedExample(
        question="Show monthly appointment count for the past 6 months.",
        sql=(
            "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE appointment_date >= date('now', 'start of month', '-5 months') "
            "GROUP BY strftime('%Y-%m', appointment_date) "
            "ORDER BY month"
        ),
        category="appointments",
    ),
    SeedExample(
        question="List patients who visited more than 3 times.",
        sql=(
            "SELECT p.id, p.first_name, p.last_name, COUNT(*) AS visit_count "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "WHERE a.status = 'Completed' "
            "GROUP BY p.id, p.first_name, p.last_name "
            "HAVING COUNT(*) > 3 "
            "ORDER BY visit_count DESC, p.last_name"
        ),
        category="patients",
    ),
    SeedExample(
        question="What is the total revenue?",
        sql="SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices",
        category="revenue",
    ),
    SeedExample(
        question="Show revenue by doctor.",
        sql=(
            "SELECT d.name, ROUND(SUM(t.cost), 2) AS total_revenue "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY total_revenue DESC"
        ),
        category="revenue",
    ),
    SeedExample(
        question="Show unpaid invoices.",
        sql=(
            "SELECT id, patient_id, invoice_date, total_amount, paid_amount, status "
            "FROM invoices WHERE status IN ('Pending', 'Overdue') "
            "ORDER BY invoice_date DESC"
        ),
        category="revenue",
    ),
    SeedExample(
        question="List patients with overdue invoices.",
        sql=(
            "SELECT DISTINCT p.first_name, p.last_name, p.city, i.total_amount, i.paid_amount "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status = 'Overdue' "
            "ORDER BY i.total_amount DESC, p.last_name"
        ),
        category="revenue",
    ),
    SeedExample(
        question="What is the average treatment cost by specialization?",
        sql=(
            "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_treatment_cost "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.specialization "
            "ORDER BY avg_treatment_cost DESC"
        ),
        category="revenue",
    ),
    SeedExample(
        question="Show patient registration trend by month.",
        sql=(
            "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS registrations "
            "FROM patients "
            "GROUP BY strftime('%Y-%m', registered_date) "
            "ORDER BY month"
        ),
        category="time",
    ),
    SeedExample(
        question="How many cancelled appointments were there last quarter?",
        sql=(
            "SELECT COUNT(*) AS cancelled_count "
            "FROM appointments "
            "WHERE status = 'Cancelled' "
            "AND appointment_date >= date('now', 'start of month', '-3 months') "
            "AND appointment_date < date('now', 'start of month')"
        ),
        category="appointments",
    ),
    SeedExample(
        question="Top 5 patients by total spending.",
        sql=(
            "SELECT p.first_name, p.last_name, "
            "ROUND(SUM(i.total_amount), 2) AS total_spending "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "ORDER BY total_spending DESC LIMIT 5"
        ),
        category="revenue",
    ),
    SeedExample(
        question="What percentage of appointments are no-shows?",
        sql=(
            "SELECT ROUND("
            "CAST(SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) AS REAL) "
            "* 100.0 / COUNT(*), 2) AS no_show_percentage "
            "FROM appointments"
        ),
        category="appointments",
    ),
    SeedExample(
        question="Show the busiest day of the week for appointments.",
        sql=(
            "SELECT CASE strftime('%w', appointment_date) "
            "WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' "
            "WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' "
            "WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' "
            "WHEN '6' THEN 'Saturday' END AS day_of_week, "
            "COUNT(*) AS appointment_count "
            "FROM appointments "
            "GROUP BY strftime('%w', appointment_date) "
            "ORDER BY appointment_count DESC LIMIT 1"
        ),
        category="appointments",
    ),
    SeedExample(
        question="Revenue trend by month.",
        sql=(
            "SELECT strftime('%Y-%m', invoice_date) AS month, "
            "ROUND(SUM(total_amount), 2) AS monthly_revenue "
            "FROM invoices "
            "GROUP BY strftime('%Y-%m', invoice_date) "
            "ORDER BY month"
        ),
        category="revenue",
    ),
    SeedExample(
        question="Average appointment duration by doctor.",
        sql=(
            "SELECT d.name, "
            "ROUND(AVG(t.duration_minutes), 1) AS avg_duration_minutes "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY avg_duration_minutes DESC"
        ),
        category="doctors",
    ),
    SeedExample(
        question="Compare revenue between departments.",
        sql=(
            "SELECT d.department, "
            "ROUND(SUM(t.cost), 2) AS total_revenue "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.department "
            "ORDER BY total_revenue DESC"
        ),
        category="revenue",
    ),
]


def main() -> None:
    configure_logging()

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "clinic.db was not found. Run `python setup_database.py` before seeding memory."
        )

    validated_examples: list[SeedExample] = []
    for example in SEED_EXAMPLES:
        validate_select_sql(example.sql)
        execute_select_sql(example.sql)
        validated_examples.append(example)

    save_seed_pairs(validated_examples)
    print(f"Validated and persisted {len(validated_examples)} seed examples.")


if __name__ == "__main__":
    main()
