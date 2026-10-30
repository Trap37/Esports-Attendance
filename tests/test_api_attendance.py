"""HTTP contract tests for scan, pending-registration, and attendance history APIs."""

from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from flask.testing import FlaskClient

from app import db, pending_scans
from models import Visit


def test_home_page_renders_main_app_and_frontend(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'CSU Esports Attendance Tracker' in html
    assert 'id="tab-attendance"' in html
    assert 'id="tab-gear"' in html
    assert 'id="tab-history"' in html
    assert 'id="tab-students"' in html
    assert 'id="tab-reports"' in html
    assert '/static/app.js' in html
    assert '/static/style.css' in html


@pytest.mark.parametrize(
    'body',
    [
        {},
        {'scan_id': ''},
        {'scan_id': ' '},
        {'scan_id': None},
    ],
)
def test_scan_rejects_missing_or_blank_scan_id(client, body):
    response = client.post('/api/scan', json=body)
    assert response.status_code == 400
    assert response.get_json() == {'error': 'scan_id required'}


def test_scan_rejects_non_json_body(client):
    response = client.post(
        '/api/scan', data='this is not JSON', content_type='application/json'
    )
    assert response.status_code == 400
    assert response.get_json() == {'error': 'scan_id required'}


def test_unknown_scan_is_reported_and_queued_for_registration(client):
    response = client.post('/api/scan', json={'scan_id': 'unknown-123'})
    assert response.status_code == 200
    result = response.get_json()
    assert result['name'] is None
    assert result['registered'] is False
    assert result['checkout'] is False
    assert result['gear_checkout'] is False
    assert isinstance(result['time'], str)

    pending = client.get('/api/students/pending').get_json()
    assert pending == {'pending': True, 'scan_id': 'unknown-123'}


def test_scan_trims_scan_id_and_returns_registered_name(client, make_student):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='Jamie Student')
    response = client.post('/api/scan', json={'scan_id': ' scan-1 '})
    assert response.status_code == 200
    result = response.get_json()
    assert result['name'] == 'Jamie Student'
    assert result['registered'] is True
    assert result['checkout'] is False
    assert result['gear_checkout'] is False
    assert db.session.scalar(sa.select(sa.func.count()).select_from(Visit)) == 1


def test_scan_toggles_check_in_and_check_out_for_registered_student(
    client, make_student
):
    make_student(csu_id='10000001', scan_id='scan-1')

    first = client.post('/api/scan', json={'scan_id': 'scan-1'}).get_json()
    second = client.post('/api/scan', json={'scan_id': 'scan-1'}).get_json()
    third = client.post('/api/scan', json={'scan_id': 'scan-1'}).get_json()

    assert (first['checkout'], second['checkout'], third['checkout']) == (
        False,
        True,
        False,
    )
    visits = db.session.scalars(sa.select(Visit).order_by(Visit.visit_id)).all()
    assert len(visits) == 2
    assert visits[0].checkout_time is not None
    assert visits[1].checkout_time is None


def test_pending_registration_empty_state_and_clear_errors(client):
    assert client.get('/api/students/pending').get_json() == {'pending': False}

    for body in ({}, {'scan_id': '   '}, {'scan_id': None}):
        response = client.post('/api/students/clear', json=body)
        assert response.status_code == 400
        assert response.get_json() == {'error': 'scan_id required'}

    missing = client.post('/api/students/clear', json={'scan_id': 'missing'})
    assert missing.status_code == 404
    assert missing.get_json() == {'error': 'Pending scan not found'}


def test_pending_registration_can_be_cleared(client):
    client.post('/api/scan', json={'scan_id': 'unknown-123'})
    response = client.post('/api/students/clear', json={'scan_id': 'unknown-123'})
    assert response.status_code == 200
    assert response.get_json() == {'success': True}
    assert client.get('/api/students/pending').get_json() == {'pending': False}


def test_pending_registration_returns_oldest_scan_and_removes_one_duplicate(client):
    client.post('/api/scan', json={'scan_id': 'unknown-1'})
    client.post('/api/scan', json={'scan_id': 'unknown-2'})
    client.post('/api/scan', json={'scan_id': 'unknown-1'})
    assert client.get('/api/students/pending').get_json()['scan_id'] == 'unknown-1'

    client.post('/api/students/clear', json={'scan_id': 'unknown-1'})
    assert client.get('/api/students/pending').get_json()['scan_id'] == 'unknown-2'
    assert pending_scans == ['unknown-2', 'unknown-1']


def test_attendance_today_returns_open_visits_and_count(
    client: FlaskClient, make_student
):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='Alex One')
    make_student(csu_id='10000002', scan_id='scan-2', full_name='Alex Two')
    client.post('/api/scan', json={'scan_id': 'scan-1'})
    client.post('/api/scan', json={'scan_id': 'scan-2'})
    client.post('/api/scan', json={'scan_id': 'scan-2'})  # check out Alex Two

    response = client.get('/api/attendance/today')
    assert response.status_code == 200
    assert response.get_json() == {'students': {'scan-1': 'Alex One'}, 'count': 1}


@pytest.mark.parametrize(
    'query',
    [
        '',
        '?start=2026-02-30&end=2026-03-01',
        '?start=10/01/2026&end=2026-10-02',
        '?start=2026-1-1&end=2026-01-02',
        '?start=20261001&end=20261002',
    ],
)
def test_attendance_history_rejects_missing_or_malformed_dates(client, query):
    response = client.get('/api/attendance/history' + query)
    assert response.status_code == 400
    assert response.get_json()['error'] == 'start and end must be YYYY-MM-DD'


def test_attendance_history_rejects_reversed_date_range(client):
    response = client.get('/api/attendance/history?start=2026-10-03&end=2026-10-02')
    assert response.status_code == 400
    assert response.get_json() == {'error': 'start must be on or before end'}


def test_attendance_history_returns_rows_and_count(client, make_student, make_visit):
    make_student(csu_id='10000001', scan_id='scan-1', full_name='Alex One')
    make_visit('10000001', check_in_time=datetime(2026, 10, 1, 15, 0, tzinfo=UTC))
    make_visit('10000001', check_in_time=datetime(2026, 10, 2, 15, 0, tzinfo=UTC))

    response = client.get('/api/attendance/history?start=2026-10-01&end=2026-10-01')
    assert response.status_code == 200
    data = response.get_json()
    assert (data['start'], data['end'], data['count']) == (
        '2026-10-01',
        '2026-10-01',
        1,
    )
    assert len(data['rows']) == 1
    assert data['rows'][0]['scan_id'] == 'scan-1'
    assert data['rows'][0]['full_name'] == 'Alex One'


@pytest.mark.xfail(
    strict=False,
    reason='Known gap: create_app() builds a Flask app but route decorators are attached only to the module-global app, so factory-created apps lack the API routes.',
)
def test_application_factory_registers_api_routes(tmp_path):
    from app import create_app

    class FactoryTestConfig:
        TESTING = True
        SECRET_KEY = 'factory-test-only'
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{tmp_path / "factory.sqlite"}'

    factory_app = create_app(FactoryTestConfig)
    route_paths = {rule.rule for rule in factory_app.url_map.iter_rules()}
    assert '/api/scan' in route_paths
    assert '/api/gear/checkout' in route_paths
    assert '/api/students/register' in route_paths


@pytest.mark.xfail(
    strict=False,
    reason="Known gap: log_visit compares UTC dates instead of Eastern calendar dates, so a visit that began late yesterday in Eastern time can be treated as today's checkout.",
)
def test_scan_starts_new_visit_when_open_visit_belongs_to_previous_eastern_day(
    client, make_student, make_visit, monkeypatch
):
    from datetime import datetime as DateTime

    import database

    class FrozenDateTime(DateTime):
        @classmethod
        def now(cls, tz=None):
            if tz == UTC:
                return DateTime(2026, 10, 29, 10, 0, tzinfo=UTC)
            return DateTime.now(tz)

    make_student(csu_id='10000001', scan_id='scan-1')
    # 02:00 UTC on Oct 29 is 22:00 Eastern on Oct 28.
    make_visit('10000001', check_in_time=DateTime(2026, 10, 29, 2, 0, tzinfo=UTC))
    monkeypatch.setattr(database, 'datetime', FrozenDateTime)

    response = client.post('/api/scan', json={'scan_id': 'scan-1'})

    assert response.status_code == 200
    assert response.get_json()['checkout'] is False
    visits = db.session.scalars(sa.select(Visit).order_by(Visit.visit_id)).all()
    assert len(visits) == 2
    assert visits[0].checkout_time is not None
    assert visits[1].checkout_time is None
