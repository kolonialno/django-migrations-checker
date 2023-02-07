from django.db.migrations import Migration
from django.db.migrations.operations import AddField
from django.db.migrations.state import ProjectState


def check_add_non_nullable_field(
    *, migration: Migration, state: ProjectState
) -> list[str]:
    warnings = []

    if any(
        isinstance(operation, AddField) and not operation.field.null
        for operation in migration.operations
    ):
        # TODO: Allow if model was added in same migration
        warnings.append(
            "⚠️ Adding non-nullable field\n"
            "This migration is adding a field that is not nullable. "
            "That will cause problems if the table is written to before "
            "the new code has been rolled out."
        )

    return warnings
