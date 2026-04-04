import csv
import io
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime, date as date_type
from database import (
    log_visit,
    get_todays_attendance,
    register_student,
    checkout_gear,
    return_gear,
    get_active_checkouts,
    get_gear_stats,
    get_report_summary,
    get_attendance_over_time,
    get_attendance_by_major,
    get_attendance_by_grade,
    get_peak_days,
    get_gear_usage_report,
    get_attendance_csv_rows,
    get_gear_csv_rows,
)

app = Flask(__name__)


# ── Main page ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Attendance endpoints ──────────────────────────────────────────────────────

@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.get_json(silent=True) or {}
    scanner_code = (data.get("scanner_code") or "").strip()
    if not scanner_code:
        return jsonify({"error": "scanner_code required"}), 400

    student_name = log_visit(scanner_code)
    time_str = datetime.now().strftime("%H:%M:%S")
    return jsonify(
        {
            "name": student_name,
            "time": time_str,
            "registered": student_name is not None,
        }
    )


@app.route("/api/attendance/today", methods=["GET"])
def attendance_today():
    names = get_todays_attendance()
    return jsonify({"names": names, "count": len(names)})


@app.route("/api/students/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    scanner_code = (data.get("scanner_code") or "").strip()
    school_id = (data.get("school_id") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    major = (data.get("major") or "").strip()
    grade_level = (data.get("grade_level") or "").strip()

    if not scanner_code or not school_id or not full_name or not major:
        return jsonify({"error": "scanner_code, school_id, full_name, and major are required"}), 400

    success = register_student(scanner_code, school_id, full_name, major, grade_level)
    if success:
        return jsonify({"success": True}), 201
    return jsonify({"error": "A student with that Scan ID already exists"}), 409


# ── Gear checkout endpoints ───────────────────────────────────────────────────

@app.route("/api/gear/stats", methods=["GET"])
def gear_stats():
    return jsonify(get_gear_stats())


@app.route("/api/gear/checkouts", methods=["GET"])
def gear_checkouts():
    return jsonify({"checkouts": get_active_checkouts()})


@app.route("/api/gear/checkout", methods=["POST"])
def gear_checkout():
    data = request.get_json(silent=True) or {}
    scanner_code = (data.get("scanner_code") or "").strip()
    keyboard = bool(data.get("keyboard"))
    mouse = bool(data.get("mouse"))
    mousepad = bool(data.get("mousepad"))
    headset = bool(data.get("headset"))

    if not scanner_code:
        return jsonify({"error": "scanner_code required"}), 400
    if not any([keyboard, mouse, mousepad, headset]):
        return jsonify({"error": "Select at least one gear item"}), 400

    try:
        checkout_id = checkout_gear(scanner_code, keyboard, mouse, mousepad, headset)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409

    if checkout_id is None:
        return jsonify({"error": "Student not found — please register first"}), 404

    return jsonify({"checkout_id": checkout_id}), 201


@app.route("/api/gear/return/<int:checkout_id>", methods=["POST"])
def gear_return(checkout_id):
    data = request.get_json(silent=True) or {}
    scanner_code = (data.get("scanner_code") or "").strip()
    if not scanner_code:
        return jsonify({"error": "scanner_code required"}), 400

    success = return_gear(checkout_id, scanner_code)
    if not success:
        # Distinguish between not-found and wrong ID
        from database import get_db_connection
        conn = get_db_connection()
        row = conn.execute(
            "SELECT scanner_code FROM gear_checkouts WHERE checkout_id = ? AND is_returned = 0",
            (checkout_id,),
        ).fetchone()
        conn.close()
        if row is None:
            return jsonify({"error": "Checkout record not found"}), 404
        return jsonify({"error": "Scan ID does not match the student who checked out this gear"}), 403

    return jsonify({"success": True})


# ── Reports endpoints ─────────────────────────────────────────────────────────

def _parse_date_range():
    """
    Extract and validate ?start=YYYY-MM-DD&end=YYYY-MM-DD query params.
    Defaults: start = first day of current month, end = today.
    Returns (start_str, end_str) or raises ValueError.
    """
    today = date_type.today()
    default_start = today.replace(day=1).strftime("%Y-%m-%d")
    default_end   = today.strftime("%Y-%m-%d")

    start_str = request.args.get("start", default_start)
    end_str   = request.args.get("end",   default_end)

    try:
        datetime.strptime(start_str, "%Y-%m-%d")
        datetime.strptime(end_str,   "%Y-%m-%d")
    except ValueError:
        raise ValueError("Dates must be in YYYY-MM-DD format")

    if start_str > end_str:
        raise ValueError("start date must not be after end date")

    return start_str, end_str


@app.route("/api/reports/summary", methods=["GET"])
def reports_summary():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(get_report_summary(start, end))


@app.route("/api/reports/attendance-over-time", methods=["GET"])
def reports_attendance_over_time():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(get_attendance_over_time(start, end))


@app.route("/api/reports/by-major", methods=["GET"])
def reports_by_major():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(get_attendance_by_major(start, end))


@app.route("/api/reports/by-grade", methods=["GET"])
def reports_by_grade():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(get_attendance_by_grade(start, end))


@app.route("/api/reports/peak-days", methods=["GET"])
def reports_peak_days():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(get_peak_days(start, end))


@app.route("/api/reports/gear-usage", methods=["GET"])
def reports_gear_usage():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(get_gear_usage_report(start, end))


@app.route("/api/reports/export/attendance", methods=["GET"])
def export_attendance_csv():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    rows = get_attendance_csv_rows(start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "visit_id", "check_in_time", "day_of_week", "week_number", "month_str",
        "scanner_code", "school_id", "full_name", "major", "grade_level", "email",
    ])
    for row in rows:
        writer.writerow([
            row.get("visit_id"), row.get("check_in_time"), row.get("day_of_week"),
            row.get("week_number"), row.get("month_str"), row.get("scanner_code"),
            row.get("school_id"), row.get("full_name"), row.get("major"),
            row.get("grade_level"), row.get("email"),
        ])

    filename = f"attendance_{start}_to_{end}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/api/reports/export/gear", methods=["GET"])
def export_gear_csv():
    try:
        start, end = _parse_date_range()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    rows = get_gear_csv_rows(start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "checkout_id", "checkout_time", "returned_time", "is_returned",
        "keyboard", "mouse", "mousepad", "headset",
        "scanner_code", "school_id", "full_name", "major", "grade_level", "email",
    ])
    for row in rows:
        writer.writerow([
            row.get("checkout_id"), row.get("checkout_time"), row.get("returned_time"),
            row.get("is_returned"), row.get("keyboard"), row.get("mouse"),
            row.get("mousepad"), row.get("headset"), row.get("scanner_code"),
            row.get("school_id"), row.get("full_name"), row.get("major"),
            row.get("grade_level"), row.get("email"),
        ])

    filename = f"gear_checkouts_{start}_to_{end}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
