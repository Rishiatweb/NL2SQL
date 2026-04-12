from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta

from project_utils import DATABASE_PATH


RNG = random.Random(42)
TODAY = date.today()

FIRST_NAMES = [
    "Aarav",
    "Aisha",
    "Anaya",
    "Arjun",
    "Diya",
    "Ethan",
    "Fatima",
    "Grace",
    "Ishaan",
    "James",
    "Kavya",
    "Leah",
    "Liam",
    "Maya",
    "Noah",
    "Nora",
    "Oliver",
    "Priya",
    "Riya",
    "Saanvi",
    "Sophia",
    "Vihaan",
    "William",
    "Zara",
]

LAST_NAMES = [
    "Anderson",
    "Bennett",
    "Brown",
    "Carter",
    "Davis",
    "Fernandez",
    "Garcia",
    "Gupta",
    "Harris",
    "Iyer",
    "Johnson",
    "Khan",
    "Lee",
    "Martinez",
    "Mehta",
    "Miller",
    "Patel",
    "Reed",
    "Shah",
    "Singh",
    "Smith",
    "Taylor",
    "Thomas",
    "Wilson",
]

CITIES = [
    "Austin",
    "Boston",
    "Chicago",
    "Dallas",
    "Denver",
    "Houston",
    "Phoenix",
    "San Diego",
    "Seattle",
    "Tampa",
]

SPECIALIZATIONS = {
    "Dermatology": "Skin Care",
    "Cardiology": "Heart Center",
    "Orthopedics": "Bone & Joint",
    "General": "Primary Care",
    "Pediatrics": "Child Health",
}

DOCTOR_FIRST_NAMES = [
    "Amelia",
    "Benjamin",
    "Charlotte",
    "Daniel",
    "Elena",
    "Henry",
    "Isabella",
    "Lucas",
    "Mia",
    "Nathan",
    "Olivia",
    "Rohan",
    "Samuel",
    "Victoria",
    "Zoe",
]

DOCTOR_LAST_NAMES = [
    "Allen",
    "Brooks",
    "Collins",
    "Edwards",
    "Foster",
    "Hall",
    "King",
    "Lopez",
    "Morris",
    "Parker",
    "Ramirez",
    "Scott",
    "Turner",
    "Walker",
    "Young",
]

TREATMENTS_BY_SPECIALIZATION = {
    "Dermatology": ["Acne Therapy", "Skin Biopsy", "Laser Peel", "Mole Removal"],
    "Cardiology": ["ECG Review", "Stress Test", "Echo Follow-up", "Holter Analysis"],
    "Orthopedics": ["Joint Injection", "Fracture Review", "Physio Plan", "Brace Fitting"],
    "General": ["Wellness Check", "Vaccination", "Flu Treatment", "Lab Review"],
    "Pediatrics": ["Child Wellness", "Immunization", "Growth Review", "Allergy Care"],
}

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
APPOINTMENT_STATUS_WEIGHTS = [0.14, 0.61, 0.17, 0.08]

INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]
INVOICE_STATUS_WEIGHTS = [0.63, 0.22, 0.15]

NOTES = [
    "Follow-up recommended in two weeks.",
    "Patient requested early morning slot.",
    "Symptoms improved since last visit.",
    "Requires additional lab work.",
    "Insurance approval pending.",
    None,
    None,
    None,
]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=RNG.randint(0, max((end - start).days, 0)))


def random_datetime_within_last_year() -> datetime:
    appointment_day = random_date(TODAY - timedelta(days=365), TODAY)
    hour = RNG.choice([8, 9, 10, 11, 12, 14, 15, 16, 17])
    minute = RNG.choice([0, 15, 30, 45])
    return datetime.combine(appointment_day, datetime.min.time()).replace(
        hour=hour, minute=minute
    )


def maybe_email(first_name: str, last_name: str) -> str | None:
    if RNG.random() < 0.18:
        return None
    domain = RNG.choice(["gmail.com", "outlook.com", "yahoo.com", "healthmail.com"])
    return f"{first_name.lower()}.{last_name.lower()}{RNG.randint(1, 999)}@{domain}"


def maybe_phone(null_rate: float = 0.12) -> str | None:
    if RNG.random() < null_rate:
        return None
    return f"+1-({RNG.randint(200, 989)})-{RNG.randint(100, 999)}-{RNG.randint(1000, 9999)}"


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        DROP TABLE IF EXISTS treatments;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS patients;

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE NOT NULL,
            gender TEXT NOT NULL,
            city TEXT NOT NULL,
            registered_date DATE NOT NULL
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            department TEXT NOT NULL,
            phone TEXT
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date DATETIME NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            treatment_name TEXT NOT NULL,
            cost REAL NOT NULL,
            duration_minutes INTEGER NOT NULL,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            invoice_date DATE NOT NULL,
            total_amount REAL NOT NULL,
            paid_amount REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
        """
    )
    connection.commit()


def insert_doctors(connection: sqlite3.Connection) -> list[dict[str, str | int | None]]:
    doctors: list[dict[str, str | int | None]] = []
    specializations = [spec for spec in SPECIALIZATIONS for _ in range(3)]
    for index, specialization in enumerate(specializations):
        doctors.append(
            {
                "name": f"Dr. {DOCTOR_FIRST_NAMES[index]} {DOCTOR_LAST_NAMES[index]}",
                "specialization": specialization,
                "department": SPECIALIZATIONS[specialization],
                "phone": maybe_phone(null_rate=0.08),
            }
        )

    connection.executemany(
        """
        INSERT INTO doctors (name, specialization, department, phone)
        VALUES (:name, :specialization, :department, :phone)
        """,
        doctors,
    )
    connection.commit()

    return [
        {"id": row[0], "name": row[1], "specialization": row[2]}
        for row in connection.execute(
            "SELECT id, name, specialization FROM doctors ORDER BY id"
        )
    ]


def insert_patients(connection: sqlite3.Connection) -> list[int]:
    patients: list[dict[str, str | None]] = []
    start_registered = TODAY - timedelta(days=540)

    for _ in range(200):
        first_name = RNG.choice(FIRST_NAMES)
        last_name = RNG.choice(LAST_NAMES)
        patients.append(
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": maybe_email(first_name, last_name),
                "phone": maybe_phone(),
                "date_of_birth": random_date(date(1948, 1, 1), date(2018, 12, 31)).isoformat(),
                "gender": RNG.choice(["M", "F"]),
                "city": RNG.choice(CITIES),
                "registered_date": random_date(start_registered, TODAY).isoformat(),
            }
        )

    connection.executemany(
        """
        INSERT INTO patients (
            first_name, last_name, email, phone, date_of_birth, gender, city, registered_date
        ) VALUES (
            :first_name, :last_name, :email, :phone, :date_of_birth, :gender, :city, :registered_date
        )
        """,
        patients,
    )
    connection.commit()
    return [row[0] for row in connection.execute("SELECT id FROM patients ORDER BY id")]


def insert_appointments(
    connection: sqlite3.Connection,
    patient_ids: list[int],
    doctors: list[dict[str, str | int | None]],
) -> list[dict[str, int | str | None]]:
    patient_weights = [1 + (15 if index < 18 else 5 if index < 60 else 1) for index in range(len(patient_ids))]
    doctor_weights = [12, 10, 9, 8, 8, 7, 6, 5, 5, 4, 4, 3, 3, 2, 2]
    appointments: list[dict[str, int | str | None]] = []

    for _ in range(500):
        doctor = RNG.choices(doctors, weights=doctor_weights, k=1)[0]
        appointments.append(
            {
                "patient_id": RNG.choices(patient_ids, weights=patient_weights, k=1)[0],
                "doctor_id": int(doctor["id"]),
                "appointment_date": random_datetime_within_last_year().strftime("%Y-%m-%d %H:%M:%S"),
                "status": RNG.choices(
                    APPOINTMENT_STATUSES, weights=APPOINTMENT_STATUS_WEIGHTS, k=1
                )[0],
                "notes": RNG.choice(NOTES),
            }
        )

    connection.executemany(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes)
        VALUES (:patient_id, :doctor_id, :appointment_date, :status, :notes)
        """,
        appointments,
    )
    connection.commit()

    return [
        {
            "id": row[0],
            "patient_id": row[1],
            "doctor_id": row[2],
            "appointment_date": row[3],
            "status": row[4],
        }
        for row in connection.execute(
            """
            SELECT id, patient_id, doctor_id, appointment_date, status
            FROM appointments
            ORDER BY id
            """
        )
    ]


def insert_treatments(
    connection: sqlite3.Connection,
    appointments: list[dict[str, int | str | None]],
    doctor_lookup: dict[int, str],
) -> list[dict[str, int | float]]:
    completed = [appointment for appointment in appointments if appointment["status"] == "Completed"]
    selected = [RNG.choice(completed) for _ in range(350)]
    treatments: list[dict[str, int | float | str]] = []

    for appointment in selected:
        specialization = doctor_lookup[int(appointment["doctor_id"])]
        treatment_name = RNG.choice(TREATMENTS_BY_SPECIALIZATION[specialization])
        min_cost, max_cost = {
            "Dermatology": (120, 1800),
            "Cardiology": (250, 5000),
            "Orthopedics": (180, 3200),
            "General": (50, 800),
            "Pediatrics": (60, 950),
        }[specialization]
        treatments.append(
            {
                "appointment_id": int(appointment["id"]),
                "treatment_name": treatment_name,
                "cost": round(RNG.uniform(min_cost, max_cost), 2),
                "duration_minutes": RNG.randint(15, 120),
            }
        )

    connection.executemany(
        """
        INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)
        VALUES (:appointment_id, :treatment_name, :cost, :duration_minutes)
        """,
        treatments,
    )
    connection.commit()
    return treatments


def insert_invoices(
    connection: sqlite3.Connection,
    appointments: list[dict[str, int | str | None]],
    treatments: list[dict[str, int | float]],
) -> None:
    treatment_by_appointment = {int(item["appointment_id"]): item for item in treatments}
    candidates = [appointment for appointment in appointments if int(appointment["id"]) in treatment_by_appointment]
    selected = [RNG.choice(candidates) for _ in range(300)]
    visit_counts: defaultdict[int, int] = defaultdict(int)
    invoices: list[dict[str, float | int | str]] = []

    for appointment in selected:
        patient_id = int(appointment["patient_id"])
        visit_counts[patient_id] += 1
        treatment_cost = float(treatment_by_appointment[int(appointment["id"])]["cost"])
        total_amount = max(
            50.0,
            min(
                5000.0,
                round(
                    treatment_cost
                    * (1 + (0.15 if visit_counts[patient_id] > 3 else 0) + RNG.uniform(-0.05, 0.35)),
                    2,
                ),
            ),
        )
        status = RNG.choices(INVOICE_STATUSES, weights=INVOICE_STATUS_WEIGHTS, k=1)[0]
        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(total_amount * RNG.uniform(0.1, 0.75), 2)
        else:
            paid_amount = round(total_amount * RNG.uniform(0.0, 0.2), 2)

        appointment_day = datetime.strptime(
            str(appointment["appointment_date"]), "%Y-%m-%d %H:%M:%S"
        ).date()
        invoices.append(
            {
                "patient_id": patient_id,
                "invoice_date": (appointment_day + timedelta(days=RNG.randint(0, 14))).isoformat(),
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "status": status,
            }
        )

    connection.executemany(
        """
        INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)
        VALUES (:patient_id, :invoice_date, :total_amount, :paid_amount, :status)
        """,
        invoices,
    )
    connection.commit()


def main() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        create_schema(connection)
        doctors = insert_doctors(connection)
        patient_ids = insert_patients(connection)
        appointments = insert_appointments(connection, patient_ids, doctors)
        doctor_lookup = {int(doctor["id"]): str(doctor["specialization"]) for doctor in doctors}
        treatments = insert_treatments(connection, appointments, doctor_lookup)
        insert_invoices(connection, appointments, treatments)

        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ["patients", "doctors", "appointments", "treatments", "invoices"]
        }
        print(
            "Created "
            f"{counts['patients']} patients, "
            f"{counts['doctors']} doctors, "
            f"{counts['appointments']} appointments, "
            f"{counts['treatments']} treatments, "
            f"{counts['invoices']} invoices."
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
