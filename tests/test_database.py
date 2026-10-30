"""Integration tests for the SQLAlchemy data-access layer."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
import sqlalchemy as sa

import database
from config import EASTERN
from models import GearCheckout, Student, Visit, _to_eastern_datetime


def test_register_student_inserts_student(db_session):
    assert (
        database.register_student(
            'scan-1', '10000001', 'aLEX example', 'Math', 'Freshman'
        )
        is True
    )
    student = db_session.get(Student, '10000001')
    assert student is not None
    assert student.scan_id == 'scan-1'
    assert student.full_name == 'Alex Example'


def test_register_student_returns_false_for_duplicate_scan_id(db_session):
    assert (
        database.register_student(
            'scan-1', '10000001', 'First Student', 'Math', 'Freshman'
        )
        is True
    )
    assert (
        database.register_student(
            'scan-1', '10000002', 'Second Student', 'Math', 'Sophomore'
        )
        is False
    )
    # The helper currently leaves the session in SQLAlchemy's failed-transaction
    # state after IntegrityError; rollback here so this test can clean up safely.
    db_session.rollback()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Student)) == 1


def test_register_student_returns_false_for_duplicate_csu_id(db_session):
    database.register_student('scan-1', '10000001', 'First Student', 'Math', 'Freshman')
    assert (
        database.register_student(
            'scan-2', '10000001', 'Second Student', 'Math', 'Sophomore'
        )
        is False
    )
    db_session.rollback()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Student)) == 1


def test_log_visit_unknown_scan_queues_pending_registration(db_session):
    pending: list[str] = []
    result = database.log_visit('unknown-1', pending)
    assert result == {'student_name': None, 'checkout': False, 'gear_checkout': False}
    assert pending == ['unknown-1']
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Visit)) == 0


def test_log_visit_registered_student_checks_in_then_checks_out(
    db_session, make_student
):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='Jamie Example')
    pending: list[str] = []

    check_in = database.log_visit('scan-1', pending)
    visit = db_session.scalar(sa.select(Visit))
    assert check_in == {
        'student_name': 'Jamie Example',
        'checkout': False,
        'gear_checkout': False,
    }
    assert visit is not None and visit.checkout_time is None

    check_out = database.log_visit('scan-1', pending)
    db_session.refresh(visit)
    assert check_out == {
        'student_name': 'Jamie Example',
        'checkout': True,
        'gear_checkout': False,
    }
    assert visit.checkout_time is not None
    assert pending == []


def test_log_visit_will_not_check_out_while_gear_is_out(
    db_session, make_student, make_visit, make_gear_checkout
):
    make_student(csu_id='10000001', scan_id='scan-1')
    visit = make_visit('10000001')
    checkout = make_gear_checkout('10000001', headset=True)

    result = database.log_visit('scan-1', [])

    db_session.refresh(visit)
    db_session.refresh(checkout)
    assert result['checkout'] is True
    assert result['gear_checkout'] is True
    assert visit.checkout_time is None
    assert checkout.returned_time is None


def test_log_visit_closes_previous_day_visit_and_starts_another(
    db_session, make_student, make_visit
):
    make_student(csu_id='10000001', scan_id='scan-1')
    yesterday = datetime.now(UTC).date() - timedelta(days=1)
    previous_visit = make_visit(
        '10000001',
        check_in_time=datetime.combine(yesterday, time(14, 0), tzinfo=UTC),
    )

    result = database.log_visit('scan-1', [])

    db_session.refresh(previous_visit)
    visits = db_session.scalars(sa.select(Visit).order_by(Visit.visit_id)).all()
    assert result['checkout'] is False
    assert len(visits) == 2
    assert previous_visit.checkout_time is not None
    assert _to_eastern_datetime(previous_visit.checkout_time).hour == 17
    assert visits[-1].checkout_time is None


def test_get_todays_attendance_lists_only_open_visits_for_today(
    db_session, make_student, make_visit
):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='First Person')
    make_student(csu_id='10000002', scan_id='scan-2', full_name='Second Person')
    today = datetime.now(UTC).date()
    make_visit(
        '10000001', check_in_time=datetime.combine(today, time(9, 0), tzinfo=UTC)
    )
    make_visit(
        '10000002',
        check_in_time=datetime.combine(today, time(10, 0), tzinfo=UTC),
        checkout_time=datetime.combine(today, time(11, 0), tzinfo=UTC),
    )

    assert database.get_todays_attendance() == {'scan-1': 'First Person'}


def test_checkout_gear_creates_checkout_and_open_visit_when_needed(
    db_session, make_student
):
    make_student(csu_id='10000001', scan_id='scan-1')
    checkout_id = database.checkout_gear('scan-1', True, False, True, False, [])

    record = db_session.get(GearCheckout, checkout_id)
    visits = db_session.scalars(sa.select(Visit)).all()
    assert checkout_id is not None
    assert record is not None
    assert (record.keyboard, record.mouse, record.mousepad, record.headset) == (
        True,
        False,
        True,
        False,
    )
    assert len(visits) == 1 and visits[0].checkout_time is None


def test_checkout_gear_does_not_create_an_extra_visit_if_already_checked_in(
    db_session, make_student, make_visit
):
    make_student(csu_id='10000001', scan_id='scan-1')
    make_visit('10000001')
    database.checkout_gear('scan-1', False, True, False, True, [])
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Visit)) == 1


def test_checkout_gear_returns_none_for_unknown_student(db_session):
    assert database.checkout_gear('missing', True, False, False, False, []) is None


def test_checkout_gear_rejects_second_active_checkout(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    database.checkout_gear('scan-1', True, False, False, False, [])
    with pytest.raises(ValueError, match='already has an active checkout'):
        database.checkout_gear('scan-1', False, True, False, False, [])
    assert db_session.scalar(sa.select(sa.func.count()).select_from(GearCheckout)) == 1


def test_return_gear_checks_student_and_active_status(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    make_student(csu_id='10000002', scan_id='scan-2')
    checkout_id = database.checkout_gear('scan-1', True, False, False, False, [])

    assert database.return_gear(checkout_id, 'scan-2') is False
    assert database.return_gear(-1, 'scan-1') is False
    assert database.return_gear(checkout_id, 'scan-1') is True
    assert database.return_gear(checkout_id, 'scan-1') is False
    assert db_session.get(GearCheckout, checkout_id).returned_time is not None


def test_active_checkouts_lists_only_unreturned_items(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='Jamie Example')
    active_id = database.checkout_gear('scan-1', True, True, False, True, [])
    assert active_id is not None

    active = database.get_active_checkouts()
    assert len(active) == 1
    assert active[0]['checkout_id'] == active_id
    assert active[0]['scan_id'] == 'scan-1'
    assert active[0]['full_name'] == 'Jamie Example'
    assert active[0]['items'] == ['Keyboard', 'Mouse', 'Headset']
    assert isinstance(active[0]['checkout_time'], str)


def test_gear_items_returns_empty_list_when_no_items_selected(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    from models import GearCheckout

    record = GearCheckout(csu_id='10000001')
    assert database._gear_items(record) == []


def test_gear_stats_count_only_active_checkout_records(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    make_student(csu_id='10000002', scan_id='scan-2')
    first_id = database.checkout_gear('scan-1', True, True, True, False, [])
    database.checkout_gear('scan-2', False, True, False, True, [])
    database.return_gear(first_id, 'scan-1')

    assert database.get_gear_stats() == {
        'total': 1,
        'keyboards': 0,
        'mice': 1,
        'other': 1,
    }


def test_get_attendance_in_range_is_inclusive_of_eastern_calendar_dates(
    db_session, make_student, make_visit
):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='Jamie Example')
    # These are UTC instants. 04:30 UTC on Oct. 2 is 00:30 Eastern on Oct. 2
    # (EDT), so it belongs to the Oct. 2 local date rather than Oct. 1.
    make_visit('10000001', check_in_time=datetime(2026, 10, 2, 3, 30, tzinfo=UTC))
    make_visit('10000001', check_in_time=datetime(2026, 10, 2, 4, 30, tzinfo=UTC))

    rows = database.get_attendance_in_range(date(2026, 10, 1), date(2026, 10, 1))
    assert len(rows) == 1
    assert rows[0]['scan_id'] == 'scan-1'
    assert rows[0]['full_name'] == 'Jamie Example'
    assert rows[0]['day_of_week'] == 'Thursday'


def test_get_attendance_in_range_is_newest_first(db_session, make_student, make_visit):
    make_student(csu_id='10000001', scan_id='scan-1')
    make_visit('10000001', check_in_time=datetime(2026, 10, 1, 14, 0, tzinfo=UTC))
    make_visit('10000001', check_in_time=datetime(2026, 10, 1, 15, 0, tzinfo=UTC))
    rows = database.get_attendance_in_range(date(2026, 10, 1), date(2026, 10, 1))
    assert len(rows) == 2
    assert rows[0]['check_in_time'] > rows[1]['check_in_time']


def test_get_gear_checkouts_in_range_uses_checkout_time_bounds(
    db_session, make_student, make_gear_checkout
):
    make_student(csu_id='10000001', scan_id='scan-1')
    make_gear_checkout(
        '10000001',
        keyboard=True,
        checkout_time=datetime(2026, 10, 1, 15, 0, tzinfo=UTC),
    )
    make_gear_checkout(
        '10000001', mouse=True, checkout_time=datetime(2026, 10, 3, 15, 0, tzinfo=UTC)
    )
    rows = database.get_gear_checkouts_in_range(date(2026, 10, 1), date(2026, 10, 2))
    assert len(rows) == 1
    assert rows[0]['items'] == 'Keyboard'
    assert rows[0]['is_returned'] == 'No'
    assert rows[0]['return_time'] is None


def test_list_students_searches_name_csu_id_and_scan_id_case_insensitively(
    db_session, make_student
):
    make_student(csu_id='10000001', scan_id='Vik123', full_name='Alice Example')
    make_student(csu_id='10000002', scan_id='Stu456', full_name='Bob Example')

    assert [r['scan_id'] for r in database.list_students()] == ['Vik123', 'Stu456']
    assert [r['scan_id'] for r in database.list_students('ALICE')] == ['Vik123']
    assert [r['scan_id'] for r in database.list_students('000002')] == ['Stu456']
    assert [r['scan_id'] for r in database.list_students('vik')] == ['Vik123']
    assert database.list_students('not-found') == []


def test_get_student_returns_full_record_or_none(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    assert database.get_student('scan-1')['csu_id'] == '10000001'
    assert database.get_student('missing') is None


def test_update_student_changes_all_editable_fields(db_session, make_student):
    make_student(csu_id='10000001', scan_id='scan-1')
    assert (
        database.update_student('scan-1', 'new-scan', 'JANE DOE', 'Math', 'Senior')
        is True
    )
    updated = database.get_student('new-scan')
    assert updated == {
        'scan_id': 'new-scan',
        'csu_id': '10000001',
        'full_name': 'Jane Doe',
        'major': 'Math',
        'grade_level': 'Senior',
    }
    assert database.update_student('missing', 'x', 'X', 'Y', 'Freshman') is False


@pytest.mark.xfail(
    strict=False,
    reason='Known gap: register_student catches IntegrityError but does not roll back, leaving the SQLAlchemy session unusable after a duplicate insert.',
)
def test_register_student_conflict_leaves_session_usable(db_session):
    database.register_student('scan-1', '10000001', 'First Student', 'Math', 'Freshman')
    assert (
        database.register_student(
            'scan-1', '10000002', 'Second Student', 'Math', 'Sophomore'
        )
        is False
    )
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Student)) == 1


def test_close_previous_day_checkouts_sets_old_visit_and_gear_to_five_pm(
    db_session, make_student, make_visit, make_gear_checkout
):
    from datetime import timedelta

    student = make_student(csu_id='10000001', scan_id='scan-1')
    old_checkin = datetime.now(UTC) - timedelta(days=2)
    old_visit = make_visit(student.csu_id, check_in_time=old_checkin)
    old_gear = make_gear_checkout(
        student.csu_id,
        headset=True,
        checkout_time=old_checkin,
    )

    database.close_previous_day_checkouts(student.csu_id)
    db_session.refresh(old_visit)
    db_session.refresh(old_gear)

    expected_local_date = old_checkin.astimezone(EASTERN).date()
    visit_return = _to_eastern_datetime(old_visit.checkout_time)
    gear_return = _to_eastern_datetime(old_gear.returned_time)
    assert (visit_return.date(), visit_return.hour, visit_return.minute) == (
        expected_local_date,
        17,
        0,
    )
    assert (gear_return.date(), gear_return.hour, gear_return.minute) == (
        expected_local_date,
        17,
        0,
    )


def test_close_previous_day_checkouts_leaves_todays_records_open(
    db_session, make_student, make_visit, make_gear_checkout
):
    student = make_student(csu_id='10000001', scan_id='scan-1')
    today_checkin = datetime.now(UTC).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    visit = make_visit(student.csu_id, check_in_time=today_checkin)
    checkout = make_gear_checkout(
        student.csu_id,
        mouse=True,
        checkout_time=today_checkin,
    )

    database.close_previous_day_checkouts(student.csu_id)
    db_session.refresh(visit)
    db_session.refresh(checkout)

    assert visit.checkout_time is None
    assert checkout.returned_time is None


def test_log_visit_rolls_back_and_reraises_when_commit_fails(
    db_session, make_student, monkeypatch
):
    from unittest.mock import Mock

    make_student(csu_id='10000001', scan_id='scan-1')
    rollback = Mock(wraps=db_session.rollback)

    class FailingSession:
        def __getattr__(self, attribute):
            return getattr(db_session, attribute)

        def commit(self):
            raise RuntimeError('simulated commit failure')

        def rollback(self):
            rollback()

    monkeypatch.setattr(database.db, 'session', FailingSession())
    with pytest.raises(RuntimeError, match='simulated commit failure'):
        database.log_visit('scan-1', [])

    rollback.assert_called_once()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Visit)) == 0


@pytest.mark.parametrize('record_kind', ['visit', 'gear'])
@pytest.mark.xfail(
    strict=False,
    reason='Known gap: stale records checked in after 5 PM Eastern are forcibly closed at 5 PM on the same date, which can put checkout/return before check-in/checkout.',
)
def test_stale_record_closure_never_sets_end_before_start(
    db_session, make_student, make_visit, make_gear_checkout, record_kind
):
    student = make_student(csu_id='10000001', scan_id='scan-1')
    late_checkin = datetime(2026, 10, 27, 23, 0, tzinfo=UTC)  # 7 PM Eastern.

    if record_kind == 'visit':
        record = make_visit(student.csu_id, check_in_time=late_checkin)
        database.close_previous_day_checkouts(student.csu_id)
        db_session.refresh(record)
        assert record.checkout_time >= record.check_in_time
    else:
        record = make_gear_checkout(
            student.csu_id, headset=True, checkout_time=late_checkin
        )
        database.close_previous_day_checkouts(student.csu_id)
        db_session.refresh(record)
        assert record.returned_time >= record.checkout_time
