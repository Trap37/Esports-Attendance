"""Tests for the separate legacy SQLite/Tkinter scanner client."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import sentinel
import setup_database


@pytest.fixture
def legacy_database(tmp_path, monkeypatch):
    """Create the legacy attendance.db schema in a temporary working directory."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sentinel, "DB_FILE", "attendance.db")
    setup_database.create_database()
    yield tmp_path / "attendance.db"


def test_legacy_setup_creates_expected_tables_and_view(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    setup_database.create_database()
    with sqlite3.connect("attendance.db") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
    assert {"students", "visits", "gear_checkouts", "full_attendance_log"}.issubset(tables)


def test_legacy_setup_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    setup_database.create_database()
    setup_database.create_database()
    with sqlite3.connect("attendance.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0


def test_register_student_success_and_duplicate_scan_id(legacy_database):
    assert sentinel.register_student("scan-1", "10000001", "Alex Example", "Math", "Junior") is True
    assert sentinel.register_student("scan-1", "10000002", "Second Person", "Math", "Senior") is False
    with sqlite3.connect(legacy_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1


def test_register_student_allows_optional_year(legacy_database):
    assert sentinel.register_student("scan-1", "10000001", "Alex Example", "Math", "") is True
    with sqlite3.connect(legacy_database) as connection:
        assert connection.execute("SELECT grade_level FROM students").fetchone()[0] is None


def test_log_visit_returns_name_and_logs_registered_scan(legacy_database):
    sentinel.register_student("scan-1", "10000001", "Alex Example", "Math", "Junior")
    assert sentinel.log_visit("scan-1") == "Alex Example"
    with sqlite3.connect(legacy_database) as connection:
        row = connection.execute(
            "SELECT scanner_code, check_in_time, day_of_week, week_number, month_str FROM visits"
        ).fetchone()
    assert row[0] == "scan-1"
    assert len(row[1]) == 19
    assert row[2] in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    assert isinstance(row[3], int)
    assert len(row[4]) == 7


def test_log_visit_still_records_unknown_scans(legacy_database):
    assert sentinel.log_visit("unknown-1") is None
    with sqlite3.connect(legacy_database) as connection:
        row = connection.execute("SELECT scanner_code FROM visits").fetchone()
    assert row == ("unknown-1",)


def test_get_todays_attendance_returns_registered_names_in_first_scan_order(legacy_database):
    sentinel.register_student("scan-1", "10000001", "Alex Example", "Math", "Junior")
    sentinel.register_student("scan-2", "10000002", "Jamie Example", "Math", "Senior")
    sentinel.log_visit("scan-1")
    sentinel.log_visit("scan-2")
    sentinel.log_visit("scan-1")
    assert sentinel.get_todays_attendance() == ["Alex Example", "Jamie Example"]


@pytest.mark.xfail(strict=False, reason="Known gap: get_todays_attendance groups by full_name, so two distinct students with identical names collapse into one row.")
def test_get_todays_attendance_does_not_collapse_distinct_students_with_same_name(legacy_database):
    sentinel.register_student("scan-1", "10000001", "Alex Example", "Math", "Junior")
    sentinel.register_student("scan-2", "10000002", "Alex Example", "Computer Science", "Senior")
    sentinel.log_visit("scan-1")
    sentinel.log_visit("scan-2")
    assert sentinel.get_todays_attendance() == ["Alex Example", "Alex Example"]


class FakeEntry:
    def __init__(self, value=""):
        self.value = value
        self.focused = False

    def get(self):
        return self.value

    def delete(self, start, end):
        self.value = ""

    def focus_set(self):
        self.focused = True


class FakeText:
    def __init__(self):
        self.state = "disabled"
        self.messages = []
        self.scrolled = False

    def configure(self, **kwargs):
        self.state = kwargs.get("state", self.state)

    def insert(self, index, message):
        self.messages.append(message)

    def see(self, index):
        self.scrolled = True


def fake_sentinel_app(scan_value):
    instance = SimpleNamespace(
        scan_entry=FakeEntry(scan_value),
        log_text=FakeText(),
        refresh_calls=0,
    )
    instance._refresh_attendance = lambda: setattr(instance, "refresh_calls", instance.refresh_calls + 1)
    return instance


def test_tk_scan_handler_ignores_empty_input(monkeypatch):
    instance = fake_sentinel_app("   ")
    log_visit = Mock()
    monkeypatch.setattr(sentinel, "log_visit", log_visit)
    sentinel.SentinelApp.on_scan(instance)
    assert instance.scan_entry.value == ""
    log_visit.assert_not_called()
    assert instance.log_text.messages == []
    assert instance.refresh_calls == 0


@pytest.mark.parametrize(
    ("student_name", "expected_text"),
    [
        ("Alex Example", "Welcome Alex Example!"),
        (None, "Unknown scan (not registered)"),
    ],
)
def test_tk_scan_handler_logs_scan_and_refreshes_attendance(monkeypatch, student_name, expected_text):
    instance = fake_sentinel_app("scan-1\n")
    monkeypatch.setattr(sentinel, "log_visit", Mock(return_value=student_name))
    sentinel.SentinelApp.on_scan(instance)
    assert instance.scan_entry.value == ""
    assert expected_text in instance.log_text.messages[0]
    assert instance.log_text.state == "disabled"
    assert instance.log_text.scrolled is True
    assert instance.refresh_calls == 1


def fake_registration_window(*, name="Alex Example", csu_id="10000001", scan_id="scan-1", major="Math", year="Junior"):
    return SimpleNamespace(
        name_entry=FakeEntry(name),
        csu_id_entry=FakeEntry(csu_id),
        scan_id_entry=FakeEntry(scan_id),
        major_entry=FakeEntry(major),
        year_combo=FakeEntry(year),
        destroyed=False,
        destroy=lambda: None,
    )


@pytest.mark.parametrize(
    ("field", "expected_message"),
    [
        ("name", "Name is required."),
        ("csu_id", "CSU ID is required."),
        ("scan_id", "Scan ID is required."),
        ("major", "Major is required."),
    ],
)
def test_registration_dialog_warns_and_focuses_missing_required_field(monkeypatch, field, expected_message):
    values = {"name": "Alex Example", "csu_id": "10000001", "scan_id": "scan-1", "major": "Math"}
    values[field] = "   "
    instance = fake_registration_window(**values)
    warning = Mock()
    monkeypatch.setattr(sentinel.messagebox, "showwarning", warning)
    register = Mock()
    monkeypatch.setattr(sentinel, "register_student", register)

    sentinel.RegistrationWindow.on_register(instance)

    warning.assert_called_once()
    assert warning.call_args.args[1] == expected_message
    assert getattr(instance, {"name": "name_entry", "csu_id": "csu_id_entry", "scan_id": "scan_id_entry", "major": "major_entry"}[field]).focused
    register.assert_not_called()


def test_registration_dialog_success_shows_confirmation_and_closes(monkeypatch):
    instance = fake_registration_window()
    instance.destroy = Mock()
    register = Mock(return_value=True)
    showinfo = Mock()
    monkeypatch.setattr(sentinel, "register_student", register)
    monkeypatch.setattr(sentinel.messagebox, "showinfo", showinfo)

    sentinel.RegistrationWindow.on_register(instance)

    register.assert_called_once_with("scan-1", "10000001", "Alex Example", "Math", "Junior")
    showinfo.assert_called_once()
    instance.destroy.assert_called_once()


def test_registration_dialog_duplicate_keeps_window_open_and_focuses_scan_id(monkeypatch):
    instance = fake_registration_window()
    instance.destroy = Mock()
    register = Mock(return_value=False)
    showerror = Mock()
    monkeypatch.setattr(sentinel, "register_student", register)
    monkeypatch.setattr(sentinel.messagebox, "showerror", showerror)

    sentinel.RegistrationWindow.on_register(instance)

    showerror.assert_called_once()
    instance.destroy.assert_not_called()
    assert instance.scan_id_entry.focused is True


def test_refresh_attendance_updates_header_and_list(monkeypatch):
    listbox = SimpleNamespace(items=[], deleted=None)
    listbox.delete = lambda start, end: (setattr(listbox, "deleted", (start, end)), listbox.items.clear())
    listbox.insert = lambda index, name: listbox.items.append(name)
    header = SimpleNamespace(text=None, configure=lambda **kwargs: setattr(header, "text", kwargs["text"]))
    instance = SimpleNamespace(attendance_header=header, attendance_list=listbox)
    monkeypatch.setattr(sentinel, "get_todays_attendance", lambda: ["Alex Example", "Jamie Example"])

    sentinel.SentinelApp._refresh_attendance(instance)

    assert header.text == "Today's Attendance (2)"
    assert listbox.deleted == (0, "end")
    assert listbox.items == ["Alex Example", "Jamie Example"]


def test_refocus_scan_entry_only_when_no_toplevel_is_open():
    scan_entry = FakeEntry()
    instance = SimpleNamespace(scan_entry=scan_entry, _has_toplevel=lambda: False)
    sentinel.SentinelApp._refocus_scan_entry(instance, event=None)
    assert scan_entry.focused is True

    scan_entry.focused = False
    instance._has_toplevel = lambda: True
    sentinel.SentinelApp._refocus_scan_entry(instance, event=None)
    assert scan_entry.focused is False


def test_has_toplevel_detects_only_existing_toplevel_widgets(monkeypatch):
    class FakeToplevel:
        def __init__(self, exists=True):
            self.exists = exists

        def winfo_exists(self):
            return self.exists

    monkeypatch.setattr(sentinel.tk, "Toplevel", FakeToplevel)
    instance = SimpleNamespace(winfo_children=lambda: [object(), FakeToplevel(exists=True)])
    assert sentinel.SentinelApp._has_toplevel(instance) is True

    instance.winfo_children = lambda: [object(), FakeToplevel(exists=False)]
    assert sentinel.SentinelApp._has_toplevel(instance) is False


def test_open_registration_constructs_registration_window(monkeypatch):
    calls = []
    monkeypatch.setattr(sentinel, "RegistrationWindow", lambda parent: calls.append(parent))
    instance = object()
    sentinel.SentinelApp.open_registration(instance)
    assert calls == [instance]


@pytest.mark.xfail(
    strict=False,
    reason="Known gap: the legacy SQLite students table does not put a UNIQUE constraint on school_id, so the same CSU ID can be registered twice with different scanner codes.",
)
def test_register_student_rejects_duplicate_school_id(legacy_database):
    assert sentinel.register_student("scan-1", "10000001", "Alex Example", "Math", "Junior") is True
    assert sentinel.register_student("scan-2", "10000001", "Second Person", "Math", "Senior") is False
    with sqlite3.connect(legacy_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1
