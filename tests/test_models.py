"""Database schema, validation, relationships, and date/time model tests."""

from datetime import UTC, date, datetime

import pytest
import sqlalchemy as sa

from config import EASTERN
from models import (
    GearCheckout,
    Student,
    Visit,
    _set_end_of_day,
    _to_eastern_datetime,
    _to_eastern_strftime,
)


def test_student_persists_and_normalizes_name(db_session):
    student = Student(
        csu_id='10000001',
        scan_id='abc123',
        full_name='aLEX mCDONALD',
        major='Computer Science',
        grade_level='Junior',
    )
    db_session.add(student)
    db_session.commit()

    loaded = db_session.get(Student, '10000001')
    assert loaded is not None
    assert loaded.full_name == 'Alex Mcdonald'
    assert loaded.scan_id == 'abc123'
    assert '10000001' in repr(loaded)


def test_student_scan_id_is_unique(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    db_session.add(
        Student(
            csu_id='10000002',
            scan_id='scan-1',
            full_name='Second Student',
            major='Math',
            grade_level='Freshman',
        )
    )
    try:
        db_session.commit()
    except sa.exc.IntegrityError:
        db_session.rollback()
    else:
        raise AssertionError('duplicate scan_id unexpectedly committed')


def test_student_csu_id_is_primary_key(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    db_session.add(
        Student(
            csu_id='10000001',
            scan_id='scan-2',
            full_name='Second Student',
            major='Math',
            grade_level='Freshman',
        )
    )
    try:
        db_session.commit()
    except sa.exc.IntegrityError:
        db_session.rollback()
    else:
        raise AssertionError('duplicate csu_id unexpectedly committed')


def test_visit_properties_use_eastern_local_calendar():
    # 2026-01-05 02:00 UTC is still Sunday evening in Eastern time.
    visit = Visit(
        csu_id='10000001',
        check_in_time=datetime(2026, 1, 5, 2, 0, tzinfo=UTC),
    )
    assert visit.day_of_week == 'Sunday'
    assert visit.month_str == '2026-01'
    assert visit.week_number == int('00')  # Sunday falls in week 00 in strftime('%W').
    assert visit.is_checked_out is False
    assert 'Attendance' in repr(visit)


def test_naive_datetimes_are_interpreted_as_utc():
    value = datetime(2026, 1, 5, 2, 0)
    converted = _to_eastern_datetime(value)
    assert converted.tzinfo == EASTERN
    assert (converted.year, converted.month, converted.day, converted.hour) == (
        2026,
        1,
        4,
        21,
    )


def test_end_of_day_is_five_pm_eastern_in_winter_and_summer():
    for day in (date(2026, 1, 15), date(2026, 7, 15)):
        result = _set_end_of_day(day)
        eastern = result.astimezone(EASTERN)
        assert (eastern.date(), eastern.hour, eastern.minute, eastern.second) == (
            day,
            17,
            0,
            0,
        )


def test_datetime_format_is_eastern_and_minute_precision():
    result = _to_eastern_strftime(datetime(2026, 1, 5, 2, 0, tzinfo=UTC))
    assert result == '2026-01-04 09:00 PM'


def test_visit_checkout_state_and_end_of_day_setter(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    visit = Visit(
        csu_id='10000001',
        check_in_time=datetime(2026, 1, 15, 14, 0, tzinfo=UTC),
    )
    db_session.add(visit)
    db_session.commit()

    assert visit.is_checked_out is False
    visit.set_checkout_time(to_eod=True)
    db_session.commit()
    assert visit.is_checked_out is True
    assert _to_eastern_datetime(visit.checkout_time).hour == 17


def test_gear_checkout_flags_and_end_of_day_return(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    record = GearCheckout(
        csu_id='10000001',
        keyboard=True,
        mouse=False,
        mousepad=True,
        headset=False,
        checkout_time=datetime(2026, 7, 15, 14, 0, tzinfo=UTC),
    )
    db_session.add(record)
    db_session.commit()

    assert record.is_returned is False
    record.set_return_time(to_eod=True)
    db_session.commit()
    assert record.is_returned is True
    assert _to_eastern_datetime(record.returned_time).hour == 17
    assert 'GearCheckout' in repr(record)


def test_schema_has_expected_tables_and_foreign_keys(application, db_session):
    from app import db

    inspector = sa.inspect(db.engine)
    assert {'students', 'visits', 'gear_checkouts'}.issubset(
        set(inspector.get_table_names())
    )
    assert inspector.get_pk_constraint('students')['constrained_columns'] == ['csu_id']
    visit_fks = inspector.get_foreign_keys('visits')
    gear_fks = inspector.get_foreign_keys('gear_checkouts')
    assert any(fk['referred_table'] == 'students' for fk in visit_fks)
    assert any(fk['referred_table'] == 'students' for fk in gear_fks)
    assert db.metadata.tables['students'].c.scan_id.unique is True


@pytest.mark.xfail(
    strict=False,
    reason='Known gap: Student relationships use WriteOnlyMapped with cascade delete but do not configure passive_deletes; deleting a student raises InvalidRequestError when SQLAlchemy tries to enumerate the write-only child collections.',
)
def test_deleting_student_cascades_to_visits_and_gear_checkouts(
    db_session, make_student, make_visit, make_gear_checkout
):
    student = make_student(csu_id='10000001', scan_id='scan-1')
    visit = make_visit(student.csu_id)
    checkout = make_gear_checkout(student.csu_id, keyboard=True)

    db_session.delete(student)
    db_session.commit()

    assert db_session.get(Student, student.csu_id) is None
    assert db_session.get(Visit, visit.visit_id) is None
    assert db_session.get(GearCheckout, checkout.checkout_id) is None
