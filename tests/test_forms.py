"""Validation and boundary tests for the WTForms registration form."""

import pytest

from forms import StudentRegistrationForm
import pytest


@pytest.fixture(autouse=True)
def app_context(application):
    """WTForms Flask integration reads current_app even when CSRF is disabled."""
    with application.app_context():
        yield


VALID = {
    "full_name": "Alex Example",
    "csu_id": "12345678",
    "scan_id": "12345",
    "major": "Computer Science",
    "grade_level": "Junior",
}


def build_form(**overrides):
    values = {**VALID, **overrides}
    return StudentRegistrationForm(meta={"csrf": False}, data=values)


def test_valid_registration_form_passes():
    assert build_form().validate() is True


@pytest.mark.parametrize("field", ["full_name", "csu_id", "scan_id", "major", "grade_level"])
def test_each_required_field_rejects_empty_value(field):
    form = build_form(**{field: ""})
    assert form.validate() is False
    assert field in form.errors


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("full_name", "A" * 129),
        ("csu_id", "1" * 9),
        ("scan_id", "1" * 9),
        ("major", "M" * 65),
    ],
)
def test_string_fields_enforce_maximum_lengths(field, value):
    form = build_form(**{field: value})
    assert form.validate() is False
    assert field in form.errors


@pytest.mark.parametrize("grade", ["", "Freshperson", "graduate", "PhD", "Senior "])
def test_grade_level_must_match_an_explicit_choice(grade):
    form = build_form(grade_level=grade)
    assert form.validate() is False
    assert "grade_level" in form.errors


@pytest.mark.parametrize("grade", ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"])
def test_each_supported_grade_level_is_valid(grade):
    assert build_form(grade_level=grade).validate() is True


def test_form_fields_use_expected_labels_and_order():
    form = build_form()
    assert list(form._fields) == ["full_name", "csu_id", "scan_id", "major", "grade_level", "submit"]
    assert form.full_name.label.text == "Full Name"
    assert form.csu_id.label.text == "CSU ID"
    assert form.scan_id.label.text == "Scan ID"
    assert form.major.label.text == "Major"
    assert form.grade_level.label.text == "Year"
