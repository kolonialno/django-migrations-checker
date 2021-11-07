from django.db.migrations import Migration
from django.db.migrations.operations import RemoveField
from django.db.migrations.state import ProjectState


def check_remove_field(*, migration: Migration, state: ProjectState) -> list[str]:

    warnings = []

    if any(isinstance(operation, RemoveField) for operation in migration.operations):
        warnings.append(
            "💡 Removing a field\n"
            "This migration is removing a field. This is only safe if you "
            "have already removed all references to the field, including the "
            "field definition on the model."
        )

    return warnings
