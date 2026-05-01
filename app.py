from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
from database import (
    log_visit,
    get_todays_attendance,
    register_student,
    checkout_gear,
    return_gear,
    get_active_checkouts,
    get_gear_stats,
    get_attendance_in_range,
    get_gear_checkouts_in_range,
    list_students,
    get_student,
    update_student,
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


# ── Attendance history ────────────────────────────────────────────────────────

def _parse_date_range():
    start = (request.args.get("start") or "").strip()
    end = (request.args.get("end") or "").strip()
    try:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return None, None, ("start and end must be YYYY-MM-DD", 400)
    if s > e:
        return None, None, ("start must be on or before end", 400)
    return start, end, None


@app.route("/api/attendance/history", methods=["GET"])
def attendance_history():
    start, end, err = _parse_date_range()
    if err:
        return jsonify({"error": err[0]}), err[1]
    rows = get_attendance_in_range(start, end)
    return jsonify({"start": start, "end": end, "count": len(rows), "rows": rows})


# ── Students list & edit ──────────────────────────────────────────────────────

@app.route("/api/students", methods=["GET"])
def students_list():
    q = (request.args.get("q") or "").strip() or None
    return jsonify({"students": list_students(q)})


@app.route("/api/students/<scanner_code>", methods=["GET"])
def students_get(scanner_code):
    student = get_student(scanner_code)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student)


@app.route("/api/students/<scanner_code>", methods=["PUT"])
def students_update(scanner_code):
    data = request.get_json(silent=True) or {}
    school_id = (data.get("school_id") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    major = (data.get("major") or "").strip()
    grade_level = (data.get("grade_level") or "").strip()

    if not school_id or not full_name or not major:
        return jsonify({"error": "school_id, full_name, and major are required"}), 400

    if not update_student(scanner_code, school_id, full_name, major, grade_level):
        return jsonify({"error": "Student not found"}), 404
    return jsonify({"success": True})


# ── Reports / Excel export ────────────────────────────────────────────────────

@app.route("/reports/export", methods=["GET"])
def reports_export():
    start, end, err = _parse_date_range()
    if err:
        return jsonify({"error": err[0]}), err[1]

    export_type = (request.args.get("type") or "both").strip().lower()
    if export_type not in {"attendance", "gear", "both"}:
        return jsonify({"error": "type must be attendance, gear, or both"}), 400

    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)

    if export_type in {"attendance", "both"}:
        ws = wb.create_sheet("Attendance")
        ws.append(["Check-in time", "Day", "Scanner code", "School ID", "Name", "Major", "Year"])
        for r in get_attendance_in_range(start, end):
            ws.append([
                r["check_in_time"],
                r["day_of_week"],
                r["scanner_code"],
                r["school_id"] or "",
                r["full_name"] or "",
                r["major"] or "",
                r["grade_level"] or "",
            ])

    if export_type in {"gear", "both"}:
        ws = wb.create_sheet("GearCheckouts")
        ws.append(["Checkout ID", "Student", "Scanner code", "Items", "Checkout time", "Returned time", "Returned"])
        for r in get_gear_checkouts_in_range(start, end):
            ws.append([
                r["checkout_id"],
                r["full_name"],
                r["scanner_code"],
                r["items"],
                r["checkout_time"],
                r["returned_time"],
                r["is_returned"],
            ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"attendance_{start}_{end}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=7020)
