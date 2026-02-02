import sqlite3
import os


def create_database():
    # 1. Connect to the database (or create it if it doesn't exist)
    # This creates a file named 'attendance.db' in the same folder as this script.
    db_file = "attendance.db"

    # Check if it already exists just to warn the user
    if os.path.exists(db_file):
        print(f"Warning: '{db_file}' already exists.")
    else:
        print(f"Creating new database: '{db_file}'...")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # TABLE 1: STUDENTS (The Roster)
    # This acts as the "Lookup Table." We only store names/majors here.
    # ---------------------------------------------------------
    print("Creating table: students...")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS students
                   (
                       scanner_code
                       TEXT
                       PRIMARY
                       KEY,
                       school_id
                       TEXT,
                       full_name
                       TEXT,
                       major
                       TEXT,
                       grade_level
                       TEXT,
                       email
                       TEXT
                   )
                   """)

    # ---------------------------------------------------------
    # TABLE 2: VISITS (The Log)
    # Every time someone scans, a row is added here.
    # ---------------------------------------------------------
    print("Creating table: visits...")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS visits
                   (
                       visit_id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT, -- The unique "Receipt Number"
                       scanner_code
                       TEXT,          -- Links back to the 'students' table
                       check_in_time
                       TEXT,          -- ISO Format: YYYY-MM-DD HH:MM:SS
                       day_of_week
                       TEXT,          -- e.g., "Monday", "Friday"
                       week_number
                       INTEGER,       -- Useful for "Weekly Reports" grouping
                       month_str
                       TEXT           -- Useful for "Monthly Reports" (e.g., "2025-10")
                   )
                   """)

    # ---------------------------------------------------------
    # OPTIONAL: Create a 'View' for easier reporting later
    # A View is a "Virtual Table" that joins the two tables together automatically.
    # When you query 'full_attendance_log', you get the name AND the time together.
    # ---------------------------------------------------------
    print("Creating view: full_attendance_log...")
    cursor.execute("""
                   CREATE VIEW IF NOT EXISTS full_attendance_log AS
                   SELECT visits.visit_id,
                          visits.check_in_time,
                          visits.day_of_week,
                          students.full_name,
                          students.major,
                          students.scanner_code
                   FROM visits
                            LEFT JOIN students ON visits.scanner_code = students.scanner_code
                   """)

    # Commit the changes (Save) and close
    conn.commit()
    conn.close()
    print("Success! Database 'attendance.db' is ready.")


if __name__ == "__main__":
    create_database()