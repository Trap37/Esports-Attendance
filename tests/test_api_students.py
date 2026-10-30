"""HTTP tests for registration, pending scans, student search, and editing."""

import pytest
import sqlalchemy as sa

from app import db
from models import Student


VALID_STUDENT = {
    "full_name": "jAMIE eXAMPLE",
    "csu_id": "10000001",
    "scan_id": "scan-1",
    "major": "Computer Science",
    "grade_level": "Junior",
}


def test_register_student_success_returns_created_and_persists(client):
    response = client.post("/api/students/register", json=VALID_STUDENT)
    assert response.status_code == 201
    assert response.get_json() == {"success": True}

    student = db.session.get(Student, "10000001")
    assert student is not None
    assert student.full_name == "Jamie Example"
    assert student.scan_id == "scan-1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("full_name", ""),
        ("csu_id", ""),
        ("scan_id", ""),
        ("major", ""),
        ("grade_level", ""),
        ("grade_level", "Not A Year"),
        ("full_name", "x" * 129),
        ("csu_id", "1" * 9),
        ("scan_id", "1" * 9),
        ("major", "x" * 65),
    ],
)
def test_registration_route_rejects_invalid_field_values(client, field, value):
    response = client.post("/api/students/register", json={**VALID_STUDENT, field: value})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Invalid registration details"
    assert field in data["details"]


@pytest.mark.xfail(strict=False, reason="Known gap: malformed JSON is rejected by Flask/Werkzeug as an HTML 400 response instead of the route’s JSON error contract.")
def test_registration_route_rejects_non_json_and_non_object_payload(client):
    response = client.post("/api/students/register", data="bad", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid registration details"


@pytest.mark.xfail(strict=False, reason="Known gap: a non-empty JSON array reaches data.get(...) and raises AttributeError instead of a JSON 400.")
def test_registration_route_rejects_json_array_payload(client):
    response = client.post("/api/students/register", json=["not", "an", "object"])
    assert response.status_code == 400


def test_registration_route_returns_conflict_for_duplicate_scan_id(client):
    assert client.post("/api/students/register", json=VALID_STUDENT).status_code == 201
    duplicate = {**VALID_STUDENT, "csu_id": "10000002", "full_name": "Another Student"}
    response = client.post("/api/students/register", json=duplicate)
    assert response.status_code == 409
    assert response.get_json() == {"error": "A student with that Scan ID already exists"}


def test_students_list_returns_all_students_sorted_by_name(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1", full_name="Zoe Example")
    make_student(csu_id="10000002", scan_id="scan-2", full_name="Alex Example")
    response = client.get("/api/students")
    assert response.status_code == 200
    data = response.get_json()["students"]
    assert [student["full_name"] for student in data] == ["Alex Example", "Zoe Example"]


def test_students_list_filters_by_name_csu_id_and_scan_id(client, make_student):
    make_student(csu_id="10000001", scan_id="Viking1", full_name="Alice Example")
    make_student(csu_id="10000002", scan_id="Another2", full_name="Bob Example")
    assert len(client.get("/api/students?q=alice").get_json()["students"]) == 1
    assert client.get("/api/students?q=000002").get_json()["students"][0]["scan_id"] == "Another2"
    assert client.get("/api/students?q=viking").get_json()["students"][0]["full_name"] == "Alice Example"
    assert client.get("/api/students?q=nobody").get_json()["students"] == []


def test_get_student_returns_record_or_404(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    response = client.get("/api/students/scan-1")
    assert response.status_code == 200
    assert response.get_json()["csu_id"] == "10000001"
    missing = client.get("/api/students/no-such-student")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Student not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"scan_id": "", "full_name": "Name", "major": "Major", "grade_level": "Junior"},
        {"scan_id": "id", "full_name": "", "major": "Major", "grade_level": "Junior"},
        {"scan_id": "id", "full_name": "Name", "major": "", "grade_level": "Junior"},
        {"scan_id": "id", "full_name": "Name", "major": "Major", "grade_level": ""},
    ],
)
def test_student_update_rejects_missing_required_fields(client, make_student, payload):
    make_student(csu_id="10000001", scan_id="scan-1")
    response = client.put("/api/students/scan-1", json=payload)
    assert response.status_code == 400
    assert "required" in response.get_json()["error"]


def test_student_update_returns_404_for_unknown_student(client):
    response = client.put(
        "/api/students/missing",
        json={"scan_id": "new", "full_name": "Name", "major": "Major", "grade_level": "Senior"},
    )
    assert response.status_code == 404
    assert response.get_json() == {"error": "Student not found"}


def test_student_update_updates_editable_values_but_preserves_csu_id(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1", full_name="Old Name")
    response = client.put(
        "/api/students/scan-1",
        json={"scan_id": "scan-new", "full_name": "NEW NAME", "major": "Math", "grade_level": "Senior"},
    )
    assert response.status_code == 200
    assert response.get_json() == {"success": True}
    student = client.get("/api/students/scan-new").get_json()
    assert student == {
        "scan_id": "scan-new",
        "csu_id": "10000001",
        "full_name": "New Name",
        "major": "Math",
        "grade_level": "Senior",
    }


@pytest.mark.xfail(strict=False, reason="Known gap: update_student does not catch duplicate scan_id IntegrityError or return a conflict response.")
def test_student_update_duplicate_scan_id_should_return_conflict(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    make_student(csu_id="10000002", scan_id="scan-2")
    response = client.put(
        "/api/students/scan-1",
        json={"scan_id": "scan-2", "full_name": "Changed Name", "major": "Math", "grade_level": "Senior"},
    )
    assert response.status_code == 409
