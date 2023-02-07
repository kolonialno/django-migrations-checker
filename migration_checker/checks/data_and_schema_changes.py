from django.db.migrations import Migration
from django.db.migrations.operations import RunPython, RunSQL
from django.db.migrations.state import ProjectState


def check_data_and_schema_changes(
    *, migration: Migration, state: ProjectState, sql: str
) -> list[str]:
    warnings = []

    data_migration, schema_migration = False, False
    for operation in migration.operations:
        if isinstance(operation, (RunPython, RunSQL)):
            data_migration = True
        else:
            schema_migration = True

    if data_migration and schema_migration:
        warnings.append(
            "⚠️ Schema and data changes\n"
            "It looks like you are doing both schema and data changes in the "
            "same migration. That should be avoided unless stricly required."
        )

    return warnings
