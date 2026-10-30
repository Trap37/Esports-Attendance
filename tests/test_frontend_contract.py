"""Static integration checks between the Jinja template, JavaScript, and Flask routes."""

from html.parser import HTMLParser
from pathlib import Path
import re

import pytest

from app import app


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
JS_FILE = ROOT / "static" / "app.js"
CSS_FILE = ROOT / "static" / "style.css"


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.table_headers: dict[str, int] = {}
        self.current_table: str | None = None
        self._in_th = False
        self._header_counts: dict[str, int] = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
            if tag == "table":
                self.current_table = attrs["id"]
                self._header_counts.setdefault(self.current_table, 0)
        if tag == "th" and self.current_table:
            self._in_th = True

    def handle_endtag(self, tag):
        if tag == "th":
            self._in_th = False
        elif tag == "table":
            if self.current_table:
                self.table_headers[self.current_table] = self._header_counts[self.current_table]
            self.current_table = None

    def handle_data(self, data):
        if self._in_th and self.current_table:
            self._header_counts[self.current_table] += 1


def read_frontend():
    html = TEMPLATE.read_text(encoding="utf-8")
    js = JS_FILE.read_text(encoding="utf-8")
    parser = IdParser()
    parser.feed(html)
    return html, js, parser


def test_template_has_no_duplicate_ids():
    _, _, parser = read_frontend()
    duplicates = {element_id for element_id in parser.ids if parser.ids.count(element_id) > 1}
    assert duplicates == set()


def test_every_literal_get_element_by_id_reference_exists_in_template():
    _, js, parser = read_frontend()
    references = set(re.findall(r"getElementById\([\"']([^\"']+)[\"']\)", js))
    missing = references - set(parser.ids)
    assert missing == set()


def test_template_includes_all_five_application_tabs_and_modals():
    html, _, parser = read_frontend()
    ids = set(parser.ids)
    for element_id in (
        "tab-attendance", "tab-gear", "tab-history", "tab-students", "tab-reports",
        "modal-register", "modal-checkout", "modal-return", "modal-edit",
    ):
        assert element_id in ids
    assert 'aria-modal="true"' in html


def test_frontend_api_paths_have_matching_flask_routes():
    _, js, _ = read_frontend()
    flask_routes = {rule.rule for rule in app.url_map.iter_rules()}
    known_calls = {
        "/api/scan": "/api/scan",
        "/api/attendance/today": "/api/attendance/today",
        "/api/students/register": "/api/students/register",
        "/api/students/pending": "/api/students/pending",
        "/api/students/clear": "/api/students/clear",
        "/api/gear/checkout": "/api/gear/checkout",
        "/api/gear/stats": "/api/gear/stats",
        "/api/gear/checkouts": "/api/gear/checkouts",
        "/api/attendance/history": "/api/attendance/history",
        "/api/students": "/api/students",
        "/reports/export": "/reports/export",
    }
    for js_path, flask_path in known_calls.items():
        assert js_path in js, f"Frontend no longer calls {js_path}"
        assert flask_path in flask_routes, f"No Flask route handles {flask_path}"
    assert "/api/gear/return/<int:checkout_id>" in flask_routes
    assert "/api/students/<scan_id>" in flask_routes


def test_main_static_assets_are_present_and_served(client):
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


@pytest.mark.xfail(strict=False, reason="Known gap: index.html references /static/CSUVikingLogo.avif, but that file is absent from the uploaded project archive.")
def test_logo_asset_is_present_and_served(client):
    assert client.get("/static/CSUVikingLogo.avif").status_code == 200


@pytest.mark.xfail(strict=False, reason="Known gap: loadStudents() emits eight table cells for a six-column table, including duplicate CSU ID and Scan ID cells.")
def test_students_rendering_matches_six_column_table_contract():
    _, js, parser = read_frontend()
    match = re.search(r"async function loadStudents\(\) \{(?P<body>.*?)\n\}", js, re.S)
    assert match is not None
    inserted_cells = len(re.findall(r"<td(?:\s|>)", match.group("body")))
    assert inserted_cells == parser.table_headers["students-table"]


def test_stylesheet_is_linked_from_template():
    html, _, _ = read_frontend()
    assert 'href="/static/style.css"' in html
    assert CSS_FILE.exists()


def test_javascript_initializes_each_ui_subsystem():
    _, js, _ = read_frontend()
    for setup in (
        "setupTabs()", "setupScanInput()", "setupRegisterModal()", "setupCheckoutModal()",
        "setupReturnModal()", "setupHistoryTab()", "setupStudentsTab()", "setupReportsTab()",
        "setupEditModal()", "setupModalCloseButtons()", "setupOverlayDismiss()",
    ):
        assert setup in js


@pytest.mark.xfail(strict=False, reason="Known gap: setupHistoryTab() registers loadHistory twice on the same click button.")
def test_history_load_button_is_registered_once():
    _, js, _ = read_frontend()
    history_setup = re.search(r"function setupHistoryTab\(\) \{(?P<body>.*?)\n\}", js, re.S)
    assert history_setup is not None
    assert history_setup.group("body").count("addEventListener(\"click\", loadHistory)") == 1
