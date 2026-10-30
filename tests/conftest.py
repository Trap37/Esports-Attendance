"""Shared fixtures for the Esports Attendance Tracker test suite."""
# uv run --group dev pytest
# uv run --group dev pytest --cov=src

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SECRET_KEY = 'tests-only-secret'


@pytest.fixture(scope='session')
def application():
    """Load the real Flask app against a disposable SQLite file."""
    # from app import create_app

    # _app = create_app(TestConfig)
    # _app.config['WTF_CSRF_ENABLED'] = False
    # return _app

    from app import app as real_app

    real_app.config.from_object(TestConfig)
    real_app.config['WTF_CSRF_ENABLED'] = False

    return real_app


@pytest.fixture
def db_session(application):
    """Give each test a clean schema and a clean SQLAlchemy session."""
    from app import db, pending_scans

    with application.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        pending_scans.clear()
        yield db.session
        db.session.remove()
        pending_scans.clear()


@pytest.fixture
def client(application, db_session):
    """A Flask test client backed by the function-scoped clean database."""
    return application.test_client()


@pytest.fixture
def make_student(db_session) -> Callable[..., object]:
    """Create and persist a student with sensible defaults."""
    from models import Student

    def factory(
        *,
        csu_id: str = '1234567',
        scan_id: str = '12345',
        full_name: str = 'Alex Example',
        major: str = 'Computer Science',
        grade_level: str = 'Junior',
    ):
        student = Student(
            csu_id=csu_id,
            scan_id=scan_id,
            full_name=full_name,
            major=major,
            grade_level=grade_level,
        )
        db_session.add(student)
        db_session.commit()
        return student

    return factory


@pytest.fixture
def make_visit(db_session) -> Callable[..., object]:
    """Create a visit with a deterministic UTC timestamp."""
    from models import Visit

    def factory(
        csu_id: str,
        *,
        check_in_time: datetime | None = None,
        checkout_time: datetime | None = None,
    ):
        visit = Visit(
            csu_id=csu_id,
            check_in_time=check_in_time or datetime.now(UTC),
            checkout_time=checkout_time,
        )
        db_session.add(visit)
        db_session.commit()
        return visit

    return factory


@pytest.fixture
def make_gear_checkout(db_session) -> Callable[..., object]:
    """Create and persist a gear checkout."""
    from models import GearCheckout

    def factory(
        csu_id: str,
        *,
        keyboard: bool = False,
        mouse: bool = False,
        mousepad: bool = False,
        headset: bool = False,
        checkout_time: datetime | None = None,
        returned_time: datetime | None = None,
    ):
        record = GearCheckout(
            csu_id=csu_id,
            keyboard=keyboard,
            mouse=mouse,
            mousepad=mousepad,
            headset=headset,
            checkout_time=checkout_time or datetime.now(UTC),
            returned_time=returned_time,
        )
        db_session.add(record)
        db_session.commit()
        return record

    return factory
