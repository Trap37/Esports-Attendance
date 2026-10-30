"""Structural checks for the Alembic migration graph."""

from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations" / "versions"


def migration_metadata(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {"revision", "down_revision"}:
                values[node.targets[0].id] = ast.literal_eval(node.value)
    return values


def test_migration_revision_ids_are_unique_and_parents_exist():
    revisions = {
        metadata["revision"]: metadata["down_revision"]
        for path in MIGRATIONS.glob("*.py")
        if (metadata := migration_metadata(path)).get("revision") is not None
    }
    assert revisions
    assert len(revisions) == len(set(revisions))
    for revision, parent in revisions.items():
        if parent is not None:
            assert parent in revisions, f"{revision} refers to missing parent {parent}"


def test_migration_graph_has_exactly_one_head():
    revisions = {
        metadata["revision"]: metadata["down_revision"]
        for path in MIGRATIONS.glob("*.py")
        if (metadata := migration_metadata(path)).get("revision") is not None
    }
    parents = {parent for parent in revisions.values() if parent is not None}
    heads = set(revisions) - parents
    assert len(heads) == 1


def test_migration_scripts_have_upgrade_and_downgrade_functions():
    paths = list(MIGRATIONS.glob("*.py"))
    assert paths, "No migration scripts found"
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        assert "upgrade" in functions, f"{path.name} has no upgrade()"
        assert "downgrade" in functions, f"{path.name} has no downgrade()"


def test_migrations_upgrade_to_head_and_downgrade_to_base(tmp_path):
    """Exercise the real Alembic scripts against a disposable SQLite file."""
    import os
    import sqlite3
    import subprocess
    import sys

    database_file = tmp_path / "migration-check.sqlite"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_file}"
    environment["SECRET_KEY"] = "migration-tests-only"

    upgrade = subprocess.run(
        [sys.executable, "-m", "flask", "--app", "app", "db", "upgrade"],
        cwd=ROOT,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Running upgrade" in upgrade.stderr or "Running upgrade" in upgrade.stdout

    with sqlite3.connect(database_file) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert revision == next(
            metadata["revision"]
            for path in MIGRATIONS.glob("*.py")
            if (metadata := migration_metadata(path)).get("revision")
            and not any(
                other_metadata.get("down_revision") == metadata["revision"]
                for other_path in MIGRATIONS.glob("*.py")
                if (other_metadata := migration_metadata(other_path))
            )
        )
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"students", "visits", "gear_checkouts"}.issubset(tables)
        visit_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(visits)")
        }
        assert "checkout_time" in visit_columns
        assert "check_out_time" not in visit_columns

    subprocess.run(
        [sys.executable, "-m", "flask", "--app", "app", "db", "downgrade", "base"],
        cwd=ROOT,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )
    with sqlite3.connect(database_file) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert not {"students", "visits", "gear_checkouts"} & tables
