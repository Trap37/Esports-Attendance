import logging
from datetime import datetime
from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config, IgnorePendingRequests
from forms import StudentRegistrationForm

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    # app.logger.addFilter(IgnorePendingRequests())
    logging.getLogger('werkzeug').addFilter(IgnorePendingRequests())

    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        import models
    return app


app = create_app()

from database import (
    checkout_gear,
    get_active_checkouts,
    get_attendance_in_range,
    get_gear_checkouts_in_range,
    get_gear_stats,
    get_student,
    get_todays_attendance,
    list_students,
    log_visit,
    register_student,
    return_gear,
    update_student,
)

pending_scan: list[str] = []


# ── Main page ─────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── Attendance endpoints ──────────────────────────────────────────────────────
# FIXME: pending_scan should be a deque and accept more than one
@app.post('/api/scan')
def scan():
    data = request.get_json(silent=True) or {}
    scan_id = (data.get('scan_id') or '').strip()
    if not scan_id:
        return jsonify({'error': 'scan_id required'}), 400

    d = log_visit(scan_id, pending_scan)
    time_str = datetime.now().strftime('%H:%M:%S')
    return jsonify(
        {
            'name': d['student_name'],
            'time': time_str,
            'registered': d['student_name'] is not None,
            'checkout': d['checkout'],
            'gear_checkout': d['gear_checkout'],
        }
    )


@app.get('/api/students/pending')
def pending_registration():
    if not pending_scan:
        return jsonify({'pending': False})

    return jsonify(
        {
            'pending': True,
            'scan_id': pending_scan[0],
        }
    )


@app.post('/api/students/clear')
def clear_pending_registration():
    data = request.get_json(silent=True) or {}
    scan_id = (data.get('scan_id') or '').strip()
    if not scan_id:
        return jsonify({'error': 'scan_id required'}), 400

    try:
        pending_scan.remove(scan_id)
    except ValueError:
        return jsonify({'error': 'Pending scan not found'}), 404

    return jsonify({'success': True})


@app.get('/api/attendance/today')
def attendance_today():
    names = get_todays_attendance()
    return jsonify({'names': names, 'count': len(names)})


@app.post('/api/students/register')
def register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get('full_name') or '').strip()
    scan_id = (data.get('scan_id') or '').strip()
    csu_id = (data.get('csu_id') or '').strip()
    major = (data.get('major') or '').strip()
    grade_level = (data.get('grade_level') or '').strip()

    form = StudentRegistrationForm(
        meta={'csrf': False},
        data={
            'full_name': full_name,
            'scan_id': scan_id,
            'csu_id': csu_id,
            'major': major,
            'grade_level': grade_level,
        },
    )
    if form.validate():
        return jsonify(
            {'error': 'Invalid registration details', 'details': form.errors}
        ), 400

    success = register_student(
        scan_id=scan_id,
        csu_id=csu_id,
        full_name=full_name,
        major=major,
        grade_level=grade_level,
    )
    if success:
        return jsonify({'success': True}), 201
    return jsonify({'error': 'A student with that Scan ID already exists'}), 409


# ── Gear checkout endpoints ───────────────────────────────────────────────────
@app.get('/api/gear/stats')
def gear_stats():
    return jsonify(get_gear_stats())


@app.get('/api/gear/checkouts')
def gear_checkouts():
    return jsonify({'checkouts': get_active_checkouts()})


@app.post('/api/gear/checkout')
def gear_checkout():
    data = request.get_json(silent=True) or {}
    scan_id = (data.get('scan_id') or '').strip()
    keyboard = bool(data.get('keyboard'))
    mouse = bool(data.get('mouse'))
    mousepad = bool(data.get('mousepad'))
    headset = bool(data.get('headset'))

    if not scan_id:
        return jsonify({'error': 'scan_id required'}), 400
    if not any([keyboard, mouse, mousepad, headset]):
        return jsonify({'error': 'Select at least one gear item'}), 400

    try:
        checkout_id = checkout_gear(scan_id, keyboard, mouse, mousepad, headset)
    except ValueError as e:
        return jsonify({'error': str(e)}), 409

    if checkout_id is None:
        return jsonify({'error': 'Student not found — please register first'}), 404

    return jsonify({'checkout_id': checkout_id}), 201


@app.post('/api/gear/return/<int:checkout_id>')
def gear_return(checkout_id: int):
    data = request.get_json(silent=True) or {}
    scan_id = (data.get('scan_id') or '').strip()
    if not scan_id:
        return jsonify({'error': 'scan_id required'}), 400

    success = return_gear(checkout_id, scan_id)
    if not success:
        # Distinguish between not-found and wrong ID
        from models import GearCheckout

        row = db.session.get(GearCheckout, checkout_id)
        if row is None or row.is_returned:
            return jsonify({'error': 'Checkout record not found'}), 404
        return jsonify(
            {'error': 'Scan ID does not match the student who checked out this gear'}
        ), 403

    return jsonify({'success': True})


# ── Attendance history ────────────────────────────────────────────────────────
def _parse_date_range():
    start = (request.args.get('start') or '').strip()
    end = (request.args.get('end') or '').strip()
    try:
        s = datetime.strptime(start, '%Y-%m-%d').date()
        e = datetime.strptime(end, '%Y-%m-%d').date()
    except ValueError:
        return None, None, ('start and end must be YYYY-MM-DD', 400)
    if s > e:
        return None, None, ('start must be on or before end', 400)
    return start, end, None


# TODO: The dates are in GMT should be in EST
@app.get('/api/attendance/history')
def attendance_history():
    start, end, err = _parse_date_range()
    if err:
        return jsonify({'error': err[0]}), err[1]
    rows = get_attendance_in_range(start, end)
    return jsonify({'start': start, 'end': end, 'count': len(rows), 'rows': rows})


# ── Students list & edit ──────────────────────────────────────────────────────
@app.get('/api/students')
def students_list():
    q = (request.args.get('q') or '').strip() or None
    return jsonify({'students': list_students(q)})


@app.get('/api/students/<scan_id>')
def students_get(scan_id: str):
    student = get_student(scan_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    return jsonify(student)


@app.put('/api/students/<scanner_code>')
def students_update(scanner_code):
    data = request.get_json(silent=True) or {}
    scan_id = (data.get('scan_id') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    major = (data.get('major') or '').strip()
    grade_level = (data.get('grade_level') or '').strip()

    if not scan_id or not full_name or not major or not grade_level:
        return jsonify({'error': 'scan_id, full_name, and major are required'}), 400

    if not update_student(scanner_code, scan_id, full_name, major, grade_level):
        return jsonify({'error': 'Student not found'}), 404
    return jsonify({'success': True})


# ── Reports / Excel export ────────────────────────────────────────────────────
@app.get('/reports/export')
def reports_export():
    start, end, err = _parse_date_range()
    if err:
        return jsonify({'error': err[0]}), err[1]

    export_type = (request.args.get('type') or 'both').strip().lower()
    if export_type not in {'attendance', 'gear', 'both'}:
        return jsonify({'error': 'type must be attendance, gear, or both'}), 400

    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)

    if export_type in {'attendance', 'both'}:
        ws = wb.create_sheet('Attendance')
        ws.append(
            [
                'Check-in time',
                'Day',
                'Scan ID',
                'School ID',
                'Name',
                'Major',
                'Year',
            ]
        )
        for r in get_attendance_in_range(start, end):
            ws.append(
                [
                    r['check_in_time'],
                    r['day_of_week'],
                    r['scan_id'],
                    r['csu_id'] or '',
                    r['full_name'] or '',
                    r['major'] or '',
                    r['grade_level'] or '',
                ]
            )

    if export_type in {'gear', 'both'}:
        ws = wb.create_sheet('GearCheckouts')
        ws.append(
            [
                'Checkout ID',
                'Student',
                'scan_id',
                'Items',
                'Checkout time',
                'Returned time',
                'Returned',
            ]
        )
        for r in get_gear_checkouts_in_range(start, end):
            ws.append(
                [
                    r['checkout_id'],
                    r['full_name'],
                    r['scan_id'],
                    r['items'],
                    r['checkout_time'],
                    r['returned_time'],
                    r['is_returned'],
                ]
            )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f'attendance_{start}_{end}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
