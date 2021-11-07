from django.db.migrations import Migration
from django.db.migrations.operations import RunPython
from django.db.migrations.state import ProjectState


def check_atomic_run_python(*, migration: Migration, state: ProjectState) -> list[str]:

    warnings = []

    if migration.atomic and any(
        isinstance(operation, RunPython) for operation in migration.operations
    ):
        warnings.append(
            "⚠️ Atomic data migration\n"
            "It looks like you are migrating data (assuming that since you "
            "have RunPython statements) Please note that this sort of data "
            "migration should not be run inside a transaction unless it is "
            "pretty fast. Have you considered using atomic=False on the "
            "Migration class?"
        )

    return warnings
