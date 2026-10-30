"""Robustness tests for JSON payload shape validation across mutation routes."""

import pytest


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/scan"),
        ("post", "/api/students/clear"),
        ("post", "/api/gear/checkout"),
        ("post", "/api/gear/return/1"),
        ("put", "/api/students/scan-1"),
    ],
    ids=["scan", "clear-pending", "gear-checkout", "gear-return", "student-update"],
)
@pytest.mark.xfail(
    strict=False,
    reason="Known gap: this endpoint calls .get(...) on a parsed JSON list instead of validating that the payload is an object, raising AttributeError instead of returning a JSON 400.",
)
def test_json_mutation_routes_reject_non_object_payloads(client, method, path):
    response = getattr(client, method)(path, json=["not", "an", "object"])
    assert response.status_code == 400
    assert response.is_json
    assert "error" in response.get_json()
