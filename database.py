from collections import deque
from datetime import UTC, datetime, time, timedelta

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app import db
from config import EASTERN
from models import GearCheckout, Student, Visit, _convert_to_eastern


# LATER: Add type hints for all func args.
# TODO: Move a bunch of database queries from here to their respective models.
# TODO: Refactor this partly directly into app.py file.
# XXX: Need to complete student gear checkout if gear not returned and visit time defaulted to EOD.
# FEATURE: Add popup to let user know student checking in didn't checkout last time.
# BUG: Need to make sure all 3 visit checkout time edge cases are solved.
# ── Attendance functions ──────────────────────────────────────────────────────
def log_visit(scan_id: str, pending_scans: list[str]):
    """Insert a visit record and return the student name if found."""
    # TODO: Change this payload around to make more sense it's confusing.
    # Could probably convert to class.
    payload = {
        'student_name': None,
        'checkout': False,
        'gear_checkout': False,
        # 'status': 'student_not_found' | 'checked_in' | 'gear_return_required' | 'checked_out'
    }

    try:
        student = db.session.scalar(
            sa.select(Student).where(Student.scan_id == scan_id)
        )
        if student is None:
            pending_scans.append(scan_id)
            return payload
        payload['student_name'] = student.full_name

        visit = db.session.scalar(
            sa.select(Visit).where(
                Visit.csu_id == student.csu_id,
                Visit.checkout_time.is_(None),
            )
        )

        if visit is None:
            # Student is not currently checked in.
            db.session.add(Visit(csu_id=student.csu_id))
            payload['checkout'] = False
        elif visit.check_in_time.date() < datetime.now(UTC).date():
            # Close previous day's visit and start a new one.
            # BUG: If student checked in past 5pm check out time will be set before check in time.
            visit.set_checkout_time(to_eod=True)
            db.session.add(Visit(csu_id=student.csu_id))
            payload['checkout'] = False
        # BUG: Handle case where student comes twice in one day but.
        # doesn't check out on first visit.
        # Attendance record 1 will have check_in_time but check_out_time
        # will become second visit check_in_time.
        # There is a partial solution commented out on Attendance model `__table_args__`
        else:
            # Student is checking out; Check for outstanding gear returns.
            gear_checkout = db.session.scalar(
                sa.select(GearCheckout).where(
                    GearCheckout.csu_id == student.csu_id,
                    GearCheckout.returned_time.is_(None),
                )
            )

            if gear_checkout is not None:
                # Tell user to make sure student returns equipment.
                payload['gear_checkout'] = True
            else:
                visit.set_checkout_time()
                payload['checkout'] = True
                payload['gear_checkout'] = False

        # payload['checkout'] = visit.is_checked_out
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return payload


def get_todays_attendance() -> list:
    """Return a list of student names who scanned in today."""
    today = datetime.now(UTC)
    start_time = datetime.combine(today, time.min)
    end_time = start_time + timedelta(days=1)

    statement = (
        sa.select(
            Student.csu_id,
            Student.full_name,
            sa.func.min(Visit.check_in_time).label('first_scan'),
        )
        .join(Student, Visit.csu_id == Student.csu_id)
        .where(
            Visit.check_in_time >= start_time,
            Visit.check_in_time < end_time,
            Visit.checkout_time.is_(None),
        )
        .group_by(Student.csu_id, Student.full_name)
        .order_by('first_scan')
    )
    rows = db.session.execute(statement).all()
    return [row.full_name for row in rows]


def register_student(scan_id, csu_id, full_name, major, grade_level):
    """Insert a new student into the database. Returns True on success."""
    try:
        student = Student(
            csu_id=csu_id,
            scan_id=scan_id,
            full_name=full_name,
            major=major,
            grade_level=grade_level,
        )
        db.session.add(student)
        db.session.commit()
        return True
    except IntegrityError:
        return False


# ── Gear checkout functions ───────────────────────────────────────────────────
# TICKET: Add an alert if student did not return gear last time.
# TICKET: Controllers can also be checked out.
# TICKET: Add some additional options box for checking out additional, unknown things.
def checkout_gear(scan_id, keyboard, mouse, mousepad, headset):  # -> Any | None:
    """
    Create a new gear checkout record.
    Returns checkout_id on success.
    Returns None if student not found.
    Raises ValueError if student already has an active checkout.
    """
    student = db.session.scalar(sa.select(Student).where(Student.scan_id == scan_id))
    if student is None:
        return None
    # Create attendance record if student forgot to scan in
    visit = Visit(csu_id=student.csu_id)
    db.session.add(visit)

    # gear_checkout = sa.select(GearCheckout.checkout_id).where(
    #     GearCheckout.csu_id == student.csu_id, GearCheckout.is_returned.is_(False)
    # )
    active = db.session.scalar(
        sa.select(GearCheckout.checkout_id).where(
            GearCheckout.csu_id == student.csu_id,
            GearCheckout.returned_time.is_(None),
        )
    )
    if active is not None:
        raise ValueError('Student already has an active checkout')

    checkout = GearCheckout(
        csu_id=student.csu_id,
        keyboard=keyboard,
        mouse=mouse,
        mousepad=mousepad,
        headset=headset,
    )
    db.session.add(checkout)
    db.session.commit()
    return checkout.checkout_id


def return_gear(checkout_id, scan_id):
    """
    Mark a checkout as returned after verifying the scan_id matches.
    Returns True on success, False if not found or scan_id mismatch.
    """
    checkout = db.session.scalar(
        sa.select(GearCheckout).where(
            GearCheckout.checkout_id == checkout_id,
            GearCheckout.returned_time.is_(None),
        )
    )
    if checkout is None or checkout.student.scan_id != scan_id:
        return False

    checkout.set_return_time()
    db.session.commit()
    return True


def _gear_items(gear_checkout_modal):
    return [
        name
        for attr, name in (
            ('keyboard', 'Keyboard'),
            ('mouse', 'Mouse'),
            ('mousepad', 'Mousepad'),
            ('headset', 'Headset'),
        )
        if getattr(gear_checkout_modal, attr)
    ]


def get_active_checkouts():
    """Return all active (not yet returned) gear checkouts with student names."""
    # statement = (
    #     sa.select(GearCheckout, Student.full_name, Student.scan_id)
    #     .outerjoin(Student, GearCheckout.csu_id == Student.csu_id)
    #     .where(GearCheckout.returned_time.is_(None))
    #     .order_by(GearCheckout.checkout_time)
    # )
    rows = db.session.scalars(
        sa.select(GearCheckout)
        .where(GearCheckout.returned_time.is_(None))
        .order_by(GearCheckout.checkout_time)
    ).all()
    return [
        {
            # BUG: Why would student not have a full name?
            'checkout_id': r.checkout_id,
            'scan_id': r.student.scan_id,
            'full_name': r.student.full_name,
            # if r.student.full_name
            # else r.student.scan_id,
            'items': _gear_items(r),
            'checkout_time': r.checkout_time,
        }
        for r in rows
    ]


def get_attendance_in_range(start_date, end_date):
    """Return per-visit rows joined with student info for [start_date, end_date] (inclusive, YYYY-MM-DD)."""
    # start, end = _date_bounds(start_date, end_date)
    start = datetime.combine(start_date, time.min, EASTERN).astimezone(UTC)
    end = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        EASTERN,
    ).astimezone(UTC)

    rows = db.session.execute(
        sa.select(Visit, Student)
        .select_from(Visit)
        .outerjoin(Student, Visit.csu_id == Student.csu_id)
        .where(Visit.check_in_time >= start, Visit.check_in_time < end)
        .order_by(Visit.check_in_time)
    ).all()
    return [
        {
            'check_in_time': _convert_to_eastern(v.check_in_time).strftime(
                '%Y-%m-%d %I:%M %p'
            ),
            'day_of_week': v.day_of_week,
            'scan_id': s.scan_id,
            'csu_id': s.csu_id,
            'full_name': s.full_name,
            'major': s.major,
            'grade_level': s.grade_level,
        }
        for v, s in rows
    ]


def get_gear_checkouts_in_range(start_date: datetime, end_date: datetime):
    """Return all gear checkouts whose checkout_time falls in [start_date, end_date]."""
    # start, end = _date_bounds(start_date, end_date)
    # statement = (
    #     sa.select(GearCheckout, Student.full_name, Student.scan_id)
    #     .outerjoin(Student, GearCheckout.csu_id == Student.csu_id)
    #     .where(GearCheckout.checkout_time >= start, GearCheckout.checkout_time < end)
    #     .order_by(GearCheckout.checkout_time)
    # )
    rows = db.session.scalars(
        sa.select(GearCheckout)
        # .where(GearCheckout.checkout_time >= start, GearCheckout.checkout_time < end)
        .where(
            GearCheckout.checkout_time >= start_date,
            GearCheckout.checkout_time < end_date,
        )
        .order_by(GearCheckout.checkout_time)
    ).all()
    return [
        {
            'checkout_id': r.checkout_id,
            'scan_id': r.student.scan_id,
            'full_name': r.student.full_name if r.student.full_name else r.csu_id,
            'items': ', '.join(_gear_items(r)),
            'checkout_time': r.checkout_time,
            'return_time': r.returned_time,
            'is_returned': 'Yes' if r.is_returned else 'No',
        }
        for r in rows
    ]


def list_students(query=None):
    """Return all students; if query is given, filter by name, school_id, or scan_id (case-insensitive)."""
    statement = sa.select(
        Student.scan_id,
        Student.csu_id,
        Student.full_name,
        Student.major,
        Student.grade_level,
    )
    if query:
        pattern = f'%{query}%'
        statement = statement.where(
            sa.or_(
                Student.full_name.ilike(pattern),
                Student.csu_id.ilike(pattern),
                Student.scan_id.ilike(pattern),
            )
        )
    statement = statement.order_by(sa.func.lower(Student.full_name))
    return [dict(row) for row in db.session.execute(statement).mappings().all()]


def get_student(scan_id):
    statement = sa.select(
        Student.scan_id,
        Student.csu_id,
        Student.full_name,
        Student.major,
        Student.grade_level,
    ).where(Student.scan_id == scan_id)
    row = db.session.execute(statement).mappings().first()
    return dict(row) if row else None


def update_student(scanner_code, scan_id, full_name, major, grade_level):
    """Update an existing student. Returns True if the student exists (even if no values changed)."""
    student = db.session.scalar(
        sa.select(Student).where(Student.scan_id == scanner_code)
    )
    if student is None:
        return False

    student.scan_id = scan_id
    student.full_name = full_name
    student.major = major
    student.grade_level = grade_level
    db.session.commit()
    return True


def get_gear_stats():
    """Return counts of active checkouts broken down by gear type."""
    # FIXME:: Mousepad and headset can just be separate why combined?
    # statement = sa.select(
    #     sa.func.count(GearCheckout.checkout_id),
    #     sa.func.coalesce(sa.func.sum(GearCheckout.keyboard), 0),
    #     sa.func.coalesce(sa.func.sum(GearCheckout.mouse), 0),
    #     sa.func.coalesce(sa.func.sum(GearCheckout.mousepad + GearCheckout.headset), 0),
    # ).where(GearCheckout.returned_time.is_(None))
    # total, keyboards, mice, other = db.session.execute(statement).one()
    # # XXX: These are returning bools instead of numbers
    # return {
    #     'total': total or 0,
    #     'keyboards': keyboards or 0,
    #     'mice': mice or 0,
    #     'other': other or 0,
    # }
    records = db.session.scalars(
        sa.select(GearCheckout).where(GearCheckout.returned_time.is_(None))
    ).all()
    return {
        'total': len(records),
        'keyboards': sum(r.keyboard for r in records),
        'mice': sum(r.mouse for r in records),
        'other': sum(bool(r.mousepad) + bool(r.headset) for r in records),
    }
