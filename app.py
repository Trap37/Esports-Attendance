from flask import Flask, render_template, request, jsonify
from datetime import datetime
from database import (
    log_visit,
    get_todays_attendance,
    register_student,
    checkout_gear,
    return_gear,
    get_active_checkouts,
    get_gear_stats,
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=7020)
