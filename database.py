from datetime import datetime, time, timedelta

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app import db
from models import GearCheckout, Student, Visit


# TODO: Add type hints for all func args
# TODO: Move a bunch of database queries from here to their respective models
# ── Attendance functions ──────────────────────────────────────────────────────
def log_visit(scan_id):
    """Insert a visit record and return the student name if found."""
    student = db.session.scalar(sa.select(Student).where(Student.scan_id == scan_id))

    visit = Visit(csu_id=student.csu_id)
    db.session.add(visit)
    db.session.commit()

    # TODO: flash('Student registered successfully!', 'success')
    return student.full_name if student else None


def get_todays_attendance() -> list:
    """Return a list of student names who scanned in today."""
    today = datetime.now()
    start_time = datetime.combine(today, time.min)
    end_time = start_time + timedelta(days=1)

    # XXX: I have no idea what this does
    statement = (
        sa.select(
            Student.csu_id,  # FIXME: Apparently for making sure same name people cause no issues
            Student.full_name,
            sa.func.min(Visit.check_in_time).label('first_scan'),
        )
        .join(Student, Visit.csu_id == Student.csu_id)
        .where(
            Visit.check_in_time >= start_time,
            Visit.check_in_time < end_time,
        )
        .group_by(Student.full_name)
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
# IDEA: Can add alert if student did not return gear last time
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

    # gear_checkout = sa.select(GearCheckout.checkout_id).where(
    #     GearCheckout.csu_id == student.csu_id, GearCheckout.is_returned.is_(False)
    # )
    active = db.session.scalar(
        sa.select(GearCheckout.checkout_id).where(
            GearCheckout.csu_id == student.csu_id,
            GearCheckout.returned_time.is_(None),
        )
    )
    # XXX: This should just add to student's current checkout unless items are duplicates
    # Such as having checked out headphones and trying to checkout a second
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
    # TODO: Why can full_name be the name or scan_id
    # TODO: Make sure that it's ok I changed from scan_id to csu_id for missing name
    return [
        {
            'checkout_id': r.checkout_id,
            'scan_id': r.student.scan_id,
            'full_name': r.student.full_name if r.student.full_name else r.csu_id,
            'items': _gear_items(r),
            'checkout_time': r.checkout_time,
        }
        for r in rows
    ]


def get_attendance_in_range(start_date, end_date):
    """Return per-visit rows joined with student info for [start_date, end_date] (inclusive, YYYY-MM-DD)."""
    # start, end = _date_bounds(start_date, end_date)
    statement = (
        sa.select(
            Visit.check_in_time,
            Visit.day_of_week,
            Student.csu_id,
            Student.scan_id,
            Student.full_name,
            Student.major,
            Student.grade_level,
        )
        # .select_from(Visit)
        .outerjoin(Student, Visit.csu_id == Student.csu_id)
        # .where(Visit.check_in_time >= start, Visit.check_in_time < end)
        .where(Visit.check_in_time >= start_date, Visit.check_in_time < end_date)
        .order_by(Visit.check_in_time)
    )

    return [dict(row) for row in db.session.execute(statement).mappings().all()]


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


def update_student(scan_id, csu_id, full_name, major, grade_level):
    """Update an existing student. Returns True if the student exists (even if no values changed)."""
    student = db.session.scalar(sa.select(Student).where(Student.scan_id == scan_id))
    if student is None:
        return False

    student.csu_id = csu_id
    student.full_name = full_name
    student.major = major
    student.grade_level = grade_level
    db.session.commit()
    return True


def get_gear_stats():
    """Return counts of active checkouts broken down by gear type."""
    # TODO:: Mousepad and headset can just be separate why combined?
    # statement = sa.select(
    #     sa.func.count(GearCheckout.checkout_id),
    #     sa.func.coalesce(sa.func.sum(GearCheckout.keyboard), 0),
    #     sa.func.coalesce(sa.func.sum(GearCheckout.mouse), 0),
    #     sa.func.coalesce(sa.func.sum(GearCheckout.mousepad + GearCheckout.headset), 0),
    # ).where(GearCheckout.returned_time.is_(None))
    # total, keyboards, mice, other = db.session.execute(statement).one()
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
        'keyboards': sum(bool(r.keyboard) for r in records),
        'mice': sum(bool((r.mouse) for r in records)),
        'other': sum(bool(r.mousepad) + bool(r.headset) for r in records),
    }
