# Test plan, coverage inventory, and known gaps

This repository has two separate execution paths: a Flask/SQLAlchemy web application and a legacy Tkinter scanner client using its own SQLite schema. The tests cover both paths, migration behavior, the API-to-frontend contract, export files, and isolated frontend JavaScript behavior.

## Run the suites

From the project root, with project dependencies and the development dependency group installed:

```bash
uv run --group dev pytest
node --test tests/frontend.test.mjs
```

The Python suite uses a temporary SQLite database and resets its schema for each test. The migration integration test runs Alembic against a separate temporary SQLite file. Tests for the legacy scanner create an isolated `attendance.db` in a temporary working directory. These tests do not read, mutate, or delete the project's `app.db` or a user's real legacy database.

`pytest` was added to the development dependency group. The original lock file could not be regenerated in the test environment because its package-index network access was unavailable; run `uv lock` once in an environment with package-index access before using a locked sync such as `uv sync --locked`. A normal `uv run --group dev pytest` can refresh an outdated lock automatically when network access is available.

## Last verified run

- Python: **153 passed, 11 xfailed, 0 failed**, with 35 WTForms deprecation warnings from the app's existing `SelectField` choice tuples.
- JavaScript: **6 passed, 0 failed**.
- Branch-instrumented Python coverage across the core runtime modules: **90% overall**; the Flask routes, configuration, database helpers, forms, and SQLAlchemy models were each at 100% in that run. The limits are described under measured coverage and omissions below.

The validation environment was Python 3.13.5. To run the uploaded project's code in that environment, I had to use SQLAlchemy 2.0.50 because the SQLAlchemy 2.1.5 package bundled in the uploaded Windows virtual environment failed to import under the available interpreter. Therefore these results validate the code path against SQLAlchemy 2.0.50, not the exact locked SQLAlchemy version. Re-run in the project's intended environment after refreshing dependencies to confirm against the locked version.

## Python suites

- **`test_config.py` — configuration and logging:** Eastern timezone selection, default SQLite URL and secret, environment overrides, and filtering the high-frequency pending-registration poll from logs.
- **`test_forms.py` — WTForms registration validation:** each required field, empty values, maximum lengths, valid/invalid grade-level options, labels, and field order.
- **`test_models.py` — SQLAlchemy models and schema:** student insertion/name normalization, unique Scan ID and primary CSU ID constraints, model representations, visit calendar properties, naïve-vs-aware timestamp conversion, Eastern daylight/standard-time end-of-day calculations, check-in/out state, gear-return state, table names, primary keys, uniqueness, foreign keys, and parent-student deletion cascades.
- **`test_database.py` — application data-access layer:** student registration and duplicate constraints; scan lookup and unknown-scan queuing; check-in/check-out toggling; outstanding gear preventing checkout; closing stale visits and gear at 5 PM Eastern, including closure-after-5-PM ordering; today's attendance filtering; creating visits and gear checkouts; avoiding duplicate visit records; rejecting a second active gear checkout; return ownership and already-returned handling; gear-item serialization; active checkout listings and aggregate stats; inclusive date ranges, Eastern calendar-date boundaries and sort order; student search/get/update; transaction recovery after duplicate registration; and rollback/re-raise behavior if a visit commit fails.
- **`test_api_attendance.py` — Flask app and attendance routes:** homepage, required/missing/non-JSON scan inputs, registered and unknown scans, check-in/out responses, pending-registration empty/oldest/clear behavior, today's attendance response/count, history date parsing and range order, history rows, Eastern-time day rollover for an open visit, plus whether a factory-created Flask app registers API routes.
- **`test_api_payloads.py` — JSON request shape validation:** verifies that scan, pending-registration clear, gear checkout, gear return, and student update endpoints return a structured client error rather than crashing when given a non-object JSON payload.
- **`test_api_students.py` — student API:** registration success, form-validation failures and duplicate Scan ID conflicts; listing order and search filters; lookup/404; required update fields, missing students, successful edits, and duplicate Scan ID edits.
- **`test_api_gear.py` — equipment API:** initial stats/list state; missing scan IDs, no items selected and unknown students; each individual gear item and combinations; automatic visit creation; duplicate active checkout rejection; list/stat updates; missing checkout/scan ID, wrong-student returns, successful returns and duplicate-return handling; and strict validation of gear flag types.
- **`test_reports.py` — Excel exports:** date/type validation, attendance-only/gear-only/combined workbook construction, sheet names, download filename/content type, column headers, attendance row values and gear row contents.
- **`test_frontend_contract.py` — HTML/JS/CSS/API wiring:** duplicate DOM IDs, all literal `getElementById` references, required tabs/modals, matching frontend API paths and Flask routes, static asset availability, CSS linking, UI subsystem initialization, student table column count, and duplicate history button handlers.
- **`test_migrations.py` — Alembic migrations:** unique revisions, existing parent revisions, one migration head, upgrade/downgrade functions in every migration, and an actual upgrade-to-head and downgrade-to-base run against a disposable database, including the renamed visit timestamp column.
- **`test_sentinel.py` — legacy scanner/database logic:** legacy tables/view creation and idempotency; registration success and duplicate scan-ID rejection; optional year; duplicate CSU ID behavior; registered and unknown scans being logged; today's attendance order and duplicate-name behavior; headless scan-handler behavior; registration-dialog required-field, success and conflict handling; refreshing today's attendance; refocusing the scanner entry; detecting existing toplevel windows; and opening the registration dialog.

## Measured Python coverage

A branch-instrumented run covered **90% overall** across the core Python runtime modules listed below. `app.py`, `config.py`, `database.py`, `forms.py`, and `models.py` each measured 100% statement/branch coverage in that run. `sentinel.py` measured 66% because its two Tkinter window constructors and executable GUI launch create real OS windows, which cannot run headlessly; `setup_database.py` measured 92%, with only its script-entry-point call not executed by tests. The migration scripts are separately exercised by the real upgrade/downgrade integration test; their subprocess execution is not included in that in-process Python coverage percentage. Static JavaScript and HTML contract checks are not part of Python coverage.

## JavaScript suite

- **`tests/frontend.test.mjs` — isolated frontend functions:** HTML-sensitive character escaping and null/numeric values; opening/closing modal visibility; restoring scan-input focus after the last modal closes; not restoring focus while another modal remains open; and Escape-key dismissal.

## Known defects represented by expected-failure tests (`xfail`)

There are **21 expected-failure test outcomes** across the following defects. Each test asserts desired behavior and includes its own `xfail` reason; these are not silent omissions. The current application has not been modified to make these regression checks pass.

1. **Factory-created app has no API routes** (`test_application_factory_registers_api_routes`): `create_app()` initializes Flask/extensions but route decorators attach endpoints only to the module-global `app`.
2. **UTC-vs-Eastern day rollover** (`test_scan_starts_new_visit_when_open_visit_belongs_to_previous_eastern_day`): `log_visit()` compares UTC calendar dates, so a visit from late the previous Eastern day can be treated as a checkout on the current day.
3. **Non-boolean gear flags** (`test_gear_checkout_rejects_non_boolean_item_values`): `bool("false")` is `True`, so JSON strings and other truthy values can be interpreted as selected gear.
4. **Non-object JSON payloads on other mutation routes** (`test_json_mutation_routes_reject_non_object_payloads`, five parameter cases): `/api/scan`, `/api/students/clear`, `/api/gear/checkout`, `/api/gear/return/<id>`, and `/api/students/<scan_id>` call `.get(...)` without verifying that the parsed JSON is an object, so array payloads raise an exception instead of returning a JSON 400.
5. **Malformed JSON on registration** (`test_registration_route_rejects_non_json_and_non_object_payload`): malformed request content does not reliably follow the route's JSON error contract; the test receives a non-JSON response instead of the expected validation object.
6. **Array JSON on registration** (`test_registration_route_rejects_json_array_payload`): a non-empty JSON array reaches `.get(...)` and raises `AttributeError` instead of returning a JSON 400.
7. **Duplicate Scan ID on student edit** (`test_student_update_duplicate_scan_id_should_return_conflict`): the update path does not catch the database uniqueness error and return HTTP 409.
8. **Database session after duplicate registration** (`test_register_student_conflict_leaves_session_usable`): `register_student()` catches `IntegrityError` but does not roll back, leaving the session unusable until rollback.
9. **Stale visit/gear closed before its start time** (`test_stale_record_closure_never_sets_end_before_start`, two parameter cases): closing at 5 PM Eastern for a record started after 5 PM on the same date can put a checkout or return earlier than check-in or checkout.
10. **Cascade delete with write-only relationships** (`test_deleting_student_cascades_to_visits_and_gear_checkouts`): deleting a student raises SQLAlchemy `InvalidRequestError` because write-only child collections are not configured for passive deletion.
11. **Missing logo asset** (`test_logo_asset_is_present_and_served`): the template references `/static/CSUVikingLogo.avif`, but the asset is absent from the supplied project.
12. **Student table cell count** (`test_students_rendering_matches_six_column_table_contract`): `loadStudents()` emits eight cells for six headers, duplicating CSU ID and Scan ID.
13. **Duplicate history event binding** (`test_history_load_button_is_registered_once`): `setupHistoryTab()` registers the same `loadHistory()` handler twice.
14. **Gear report with data** (`test_gear_export_contains_checkout_row`): the query helper returns `return_time` while the exporter reads `returned_time`, so a non-empty gear export raises `KeyError`.
15. **Same-name legacy students** (`test_get_todays_attendance_does_not_collapse_distinct_students_with_same_name`): the legacy SQL query groups by `full_name`, collapsing different students who share a name.
16. **Duplicate CSU ID in legacy scanner database** (`test_register_student_rejects_duplicate_school_id`): the legacy `students` table does not apply a `UNIQUE` constraint to `school_id`, so different scan IDs can be registered with the same CSU ID.

## What is not tested end-to-end, and exactly why

- **Actual rendered browser behavior, complete end-to-end frontend workflows, layout, responsiveness, accessibility tree, and cross-browser differences:** the project environment does not include a browser automation driver or browser session. Static HTML/API/CSS wiring checks and Node tests with a lightweight DOM stub cover deterministic behavior and selected reusable functions, but do not dispatch every `app.js` event through a real browser or prove visual/accessibility correctness.
- **Visual Tkinter layout and OS-native modal/focus behavior:** the environment has no desktop display server. Scanner event handling, validation, database operations, refresh logic, and focus decisions are tested with fake widgets; window geometry, actual drawing, keyboard focus as managed by Windows, and real event-loop interaction are not.
- **A physical USB/HID card scanner:** no scanner hardware is attached and there is no hardware fixture. Tests exercise the app's scan-handler with representative strings/newlines and the registered/unknown paths, but cannot verify device-specific key timing, firmware behavior, or physical connect/disconnect events.
- **Real two-machine or network operation:** no deployment topology or network service is included in this repository. The tests use Flask's in-process test client and local SQLite, so they do not validate Ethernet/Wi-Fi latency, firewall configuration, concurrent processes, or loss/recovery of a live network connection.
- **Microsoft Excel itself:** exported workbooks are read back with `openpyxl`, which checks workbook contents and metadata without needing Office. The suite does not launch Excel to test rendering or compatibility with a particular installed Office build.
- **Load, stress, and race-condition testing:** the codebase does not specify capacity or latency targets, and the current tests are functional regression tests rather than a performance harness. SQLite multi-process contention, many simultaneous scans, and concurrent duplicate checkouts are not simulated.
- **Security penetration testing and authenticated/role-based access:** the project currently contains no login, role, or permission system to exercise, and the app is described as a local attendance tool. The test client disables Flask-WTF CSRF for isolated form/API behavior; this is not a security guarantee for a deployed configuration. No external penetration scanner or security review is included.
- **The project's existing `app.db` / a real `attendance.db`:** these are deliberately not used, because tests should not mutate user or operational records. Disposable schemas and migration databases are used instead.
- **The `setup_database.py` command-line entry point itself:** tests call `create_database()` directly after changing to a temporary directory. They do not execute the module's `__main__` branch, because that branch would create or modify `attendance.db` in the process's working directory; its underlying schema-creation function is tested for schema correctness and idempotency instead.
- **Non-executable documentation and the architecture image:** README prose, the architecture PNG, and other descriptive files are not application runtime behavior, so no behavioral tests are applicable to them.

The tests intentionally do not modify the production application to make the known-defect tests pass. The expected failures describe the current behavior and the desired contract; fixing those failures requires code changes to the application.
