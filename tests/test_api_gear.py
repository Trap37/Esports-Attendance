"""HTTP contract tests for checkout, return, active gear, and gear statistics."""

from datetime import UTC, datetime

import pytest
import sqlalchemy as sa

from app import db
from models import GearCheckout, Visit


GEAR_TYPES = ("keyboard", "mouse", "mousepad", "headset")


def test_gear_stats_and_active_checkout_list_start_empty(client):
    assert client.get("/api/gear/stats").get_json() == {
        "total": 0,
        "keyboards": 0,
        "mice": 0,
        "other": 0,
    }
    assert client.get("/api/gear/checkouts").get_json() == {"checkouts": []}


def test_gear_checkout_rejects_missing_scan_id(client):
    for payload in ({}, {"scan_id": ""}, {"scan_id": "  "}):
        response = client.post("/api/gear/checkout", json=payload)
        assert response.status_code == 400
        assert response.get_json() == {"error": "scan_id required"}


def test_gear_checkout_requires_at_least_one_item(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    response = client.post("/api/gear/checkout", json={"scan_id": "scan-1"})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Select at least one gear item"}


def test_gear_checkout_rejects_unknown_student(client):
    response = client.post(
        "/api/gear/checkout",
        json={"scan_id": "missing", "keyboard": True},
    )
    assert response.status_code == 404
    assert response.get_json() == {"error": "Student not found — please register first"}


@pytest.mark.parametrize("item", GEAR_TYPES)
def test_each_gear_type_can_be_checked_out(client, make_student, item):
    make_student(csu_id="10000001", scan_id="scan-1")
    response = client.post("/api/gear/checkout", json={"scan_id": "scan-1", item: True})
    assert response.status_code == 201
    checkout_id = response.get_json()["checkout_id"]
    record = db.session.get(GearCheckout, checkout_id)
    assert record is not None
    assert [name for name in GEAR_TYPES if getattr(record, name)] == [item]


def test_gear_checkout_can_select_multiple_items_and_creates_open_visit(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    response = client.post(
        "/api/gear/checkout",
        json={"scan_id": "scan-1", "keyboard": True, "mouse": True, "headset": True},
    )
    assert response.status_code == 201
    checkout = db.session.get(GearCheckout, response.get_json()["checkout_id"])
    assert (checkout.keyboard, checkout.mouse, checkout.mousepad, checkout.headset) == (True, True, False, True)
    assert db.session.scalar(sa.select(sa.func.count()).select_from(Visit)) == 1


def test_gear_checkout_rejects_second_active_checkout(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    first = client.post("/api/gear/checkout", json={"scan_id": "scan-1", "keyboard": True})
    second = client.post("/api/gear/checkout", json={"scan_id": "scan-1", "mouse": True})
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json() == {"error": "Student already has an active checkout"}


def test_active_checkout_list_and_stats_reflect_records(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1", full_name="Jamie Example")
    make_student(csu_id="10000002", scan_id="scan-2", full_name="Taylor Example")
    first = client.post(
        "/api/gear/checkout",
        json={"scan_id": "scan-1", "keyboard": True, "mouse": True, "mousepad": True},
    )
    client.post("/api/gear/checkout", json={"scan_id": "scan-2", "headset": True})

    checkouts = client.get("/api/gear/checkouts").get_json()["checkouts"]
    assert len(checkouts) == 2
    assert checkouts[0]["full_name"] == "Jamie Example"
    assert checkouts[0]["items"] == ["Keyboard", "Mouse", "Mousepad"]
    assert client.get("/api/gear/stats").get_json() == {
        "total": 2,
        "keyboards": 1,
        "mice": 1,
        "other": 2,
    }

    returned = client.post(
        f"/api/gear/return/{first.get_json()['checkout_id']}",
        json={"scan_id": "scan-1"},
    )
    assert returned.status_code == 200
    assert client.get("/api/gear/stats").get_json() == {
        "total": 1,
        "keyboards": 0,
        "mice": 0,
        "other": 1,
    }


def test_gear_return_requires_scan_id(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    checkout_id = client.post(
        "/api/gear/checkout", json={"scan_id": "scan-1", "keyboard": True}
    ).get_json()["checkout_id"]
    for payload in ({}, {"scan_id": ""}, {"scan_id": "  "}):
        response = client.post(f"/api/gear/return/{checkout_id}", json=payload)
        assert response.status_code == 400
        assert response.get_json() == {"error": "scan_id required"}


def test_gear_return_for_unknown_checkout_returns_404(client):
    response = client.post("/api/gear/return/999", json={"scan_id": "scan-1"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Checkout record not found"}


def test_gear_return_rejects_wrong_student_scan_id(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    make_student(csu_id="10000002", scan_id="scan-2")
    checkout_id = client.post(
        "/api/gear/checkout", json={"scan_id": "scan-1", "keyboard": True}
    ).get_json()["checkout_id"]
    response = client.post(f"/api/gear/return/{checkout_id}", json={"scan_id": "scan-2"})
    assert response.status_code == 403
    assert response.get_json() == {
        "error": "Scan ID does not match the student who checked out this gear"
    }


def test_gear_return_cannot_return_same_checkout_twice(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    checkout_id = client.post(
        "/api/gear/checkout", json={"scan_id": "scan-1", "keyboard": True}
    ).get_json()["checkout_id"]
    assert client.post(f"/api/gear/return/{checkout_id}", json={"scan_id": "scan-1"}).status_code == 200
    second = client.post(f"/api/gear/return/{checkout_id}", json={"scan_id": "scan-1"})
    assert second.status_code == 404
    assert second.get_json() == {"error": "Checkout record not found"}


@pytest.mark.xfail(strict=False, reason="Known gap: JSON strings such as 'false' are truthy in Python and are accepted as checked gear items.")
def test_gear_checkout_rejects_non_boolean_item_values(client, make_student):
    make_student(csu_id="10000001", scan_id="scan-1")
    response = client.post("/api/gear/checkout", json={"scan_id": "scan-1", "keyboard": "false"})
    assert response.status_code == 400
