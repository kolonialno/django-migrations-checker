from django.db.migrations import Migration
from django.db.migrations.operations import RenameField
from django.db.migrations.state import ProjectState


def check_rename_field(*, migration: Migration, state: ProjectState) -> list[str]:

    warnings = []

    if any(isinstance(operation, RenameField) for operation in migration.operations):
        warnings.append(
            "🚨 Renaming a field is not safe\n"
            "This migration is renaming a field. That is not safe if the table "
            "is in use. Please add a new field, copy data, and remove the old "
            "field instead."
        )

    return warnings
