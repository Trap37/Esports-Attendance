import sqlite3
from datetime import datetime

DB_FILE = "attendance.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ── Attendance functions ──────────────────────────────────────────────────────

def log_visit(scanner_code):
    """Insert a visit record and return the student name if found."""
    now = datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT full_name FROM students WHERE scanner_code = ?", (scanner_code,))
    row = cursor.fetchone()
    student_name = row["full_name"] if row else None

    cursor.execute(
        """
        INSERT INTO visits (scanner_code, check_in_time, day_of_week, week_number, month_str)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            scanner_code,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%A"),
            int(now.strftime("%W")),
            now.strftime("%Y-%m"),
        ),
    )
    conn.commit()
    conn.close()
    return student_name


def get_todays_attendance():
    """Return a list of student names who scanned in today."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.full_name, MIN(v.check_in_time) AS first_scan
        FROM visits v
        JOIN students s ON v.scanner_code = s.scanner_code
        WHERE v.check_in_time LIKE ?
        GROUP BY s.full_name
        ORDER BY first_scan
        """,
        (today + "%",),
    )
    names = [row["full_name"] for row in cursor.fetchall()]
    conn.close()
    return names


def register_student(scanner_code, school_id, full_name, major, grade_level):
    """Insert a new student into the database. Returns True on success."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO students (scanner_code, school_id, full_name, major, grade_level)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scanner_code, school_id, full_name, major, grade_level or None),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ── Gear checkout functions ───────────────────────────────────────────────────

def checkout_gear(scanner_code, keyboard, mouse, mousepad, headset):
    """
    Create a new gear checkout record.
    Returns checkout_id on success.
    Returns None if student not found.
    Raises ValueError if student already has an active checkout.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT full_name FROM students WHERE scanner_code = ?", (scanner_code,))
        if not cursor.fetchone():
            return None

        cursor.execute(
            "SELECT checkout_id FROM gear_checkouts WHERE scanner_code = ? AND is_returned = 0",
            (scanner_code,),
        )
        if cursor.fetchone():
            raise ValueError("Student already has an active checkout")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO gear_checkouts
                (scanner_code, keyboard, mouse, mousepad, headset, checkout_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                scanner_code,
                1 if keyboard else 0,
                1 if mouse else 0,
                1 if mousepad else 0,
                1 if headset else 0,
                now,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def return_gear(checkout_id, scanner_code):
    """
    Mark a checkout as returned after verifying the scanner_code matches.
    Returns True on success, False if not found or scanner_code mismatch.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT scanner_code FROM gear_checkouts WHERE checkout_id = ? AND is_returned = 0",
            (checkout_id,),
        )
        row = cursor.fetchone()
        if not row:
            return False
        if row["scanner_code"] != scanner_code:
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            UPDATE gear_checkouts
            SET is_returned = 1, returned_time = ?
            WHERE checkout_id = ?
            """,
            (now, checkout_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_active_checkouts():
    """Return all active (not yet returned) gear checkouts with student names."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT gc.checkout_id, gc.scanner_code, gc.keyboard, gc.mouse,
               gc.mousepad, gc.headset, gc.checkout_time,
               s.full_name
        FROM gear_checkouts gc
        LEFT JOIN students s ON gc.scanner_code = s.scanner_code
        WHERE gc.is_returned = 0
        ORDER BY gc.checkout_time
        """
    )
    rows = cursor.fetchall()
    conn.close()

    checkouts = []
    for row in rows:
        items = []
        if row["keyboard"]:
            items.append("Keyboard")
        if row["mouse"]:
            items.append("Mouse")
        if row["mousepad"]:
            items.append("Mousepad")
        if row["headset"]:
            items.append("Headset")
        checkouts.append(
            {
                "checkout_id": row["checkout_id"],
                "scanner_code": row["scanner_code"],
                "full_name": row["full_name"] or row["scanner_code"],
                "items": items,
                "checkout_time": row["checkout_time"],
            }
        )
    return checkouts


def get_attendance_in_range(start_date, end_date):
    """Return per-visit rows joined with student info for [start_date, end_date] (inclusive, YYYY-MM-DD)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT v.check_in_time,
               v.day_of_week,
               v.scanner_code,
               s.school_id,
               s.full_name,
               s.major,
               s.grade_level
        FROM visits v
        LEFT JOIN students s ON v.scanner_code = s.scanner_code
        WHERE date(v.check_in_time) BETWEEN ? AND ?
        ORDER BY v.check_in_time
        """,
        (start_date, end_date),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_gear_checkouts_in_range(start_date, end_date):
    """Return all gear checkouts whose checkout_time falls in [start_date, end_date]."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT gc.checkout_id,
               gc.scanner_code,
               s.full_name,
               gc.keyboard, gc.mouse, gc.mousepad, gc.headset,
               gc.checkout_time,
               gc.returned_time,
               gc.is_returned
        FROM gear_checkouts gc
        LEFT JOIN students s ON gc.scanner_code = s.scanner_code
        WHERE date(gc.checkout_time) BETWEEN ? AND ?
        ORDER BY gc.checkout_time
        """,
        (start_date, end_date),
    )
    rows = []
    for r in cursor.fetchall():
        items = []
        if r["keyboard"]: items.append("Keyboard")
        if r["mouse"]: items.append("Mouse")
        if r["mousepad"]: items.append("Mousepad")
        if r["headset"]: items.append("Headset")
        rows.append({
            "checkout_id": r["checkout_id"],
            "scanner_code": r["scanner_code"],
            "full_name": r["full_name"] or r["scanner_code"],
            "items": ", ".join(items),
            "checkout_time": r["checkout_time"],
            "returned_time": r["returned_time"] or "",
            "is_returned": "Yes" if r["is_returned"] else "No",
        })
    conn.close()
    return rows


def list_students(query=None):
    """Return all students; if query is given, filter by name, school_id, or scanner_code (case-insensitive)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if query:
        like = f"%{query}%"
        cursor.execute(
            """
            SELECT scanner_code, school_id, full_name, major, grade_level
            FROM students
            WHERE full_name LIKE ? OR school_id LIKE ? OR scanner_code LIKE ?
            ORDER BY full_name COLLATE NOCASE
            """,
            (like, like, like),
        )
    else:
        cursor.execute(
            """
            SELECT scanner_code, school_id, full_name, major, grade_level
            FROM students
            ORDER BY full_name COLLATE NOCASE
            """
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_student(scanner_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT scanner_code, school_id, full_name, major, grade_level FROM students WHERE scanner_code = ?",
        (scanner_code,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_student(scanner_code, school_id, full_name, major, grade_level):
    """Update an existing student. Returns True if the student exists (even if no values changed)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM students WHERE scanner_code = ?", (scanner_code,))
        if cursor.fetchone() is None:
            return False
        cursor.execute(
            """
            UPDATE students
            SET school_id = ?, full_name = ?, major = ?, grade_level = ?
            WHERE scanner_code = ?
            """,
            (school_id, full_name, major, grade_level or None, scanner_code),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_gear_stats():
    """Return counts of active checkouts broken down by gear type."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(*)        AS total,
            SUM(keyboard)   AS keyboards,
            SUM(mouse)      AS mice,
            SUM(mousepad + headset) AS other
        FROM gear_checkouts
        WHERE is_returned = 0
        """
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "total": row["total"] or 0,
        "keyboards": row["keyboards"] or 0,
        "mice": row["mice"] or 0,
        "other": row["other"] or 0,
    }
