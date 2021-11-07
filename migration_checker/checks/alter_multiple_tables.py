from django.db.migrations import Migration
from django.db.migrations.operations.fields import FieldOperation
from django.db.migrations.operations.models import ModelOperation
from django.db.migrations.state import ProjectState


def check_alter_multiple_tables(
    *, migration: Migration, state: ProjectState
) -> list[str]:

    warnings = []

    altered_models = set()

    if migration.atomic and not migration.initial:
        for operation in migration.operations:
            if isinstance(operation, FieldOperation):
                altered_models.add(operation.model_name)
            elif isinstance(operation, ModelOperation):
                altered_models.add(operation.name)

    # TODO: Allow if models were created in the same migration
    if len(altered_models) > 1:
        warnings.append(
            "🚨 Altering multiple models\n"
            "Consider splitting this migration into separate migrations. "
            "This migration is making changes to multiple tables. That can be "
            "problematic because exclusive locks are required when altering "
            "a table. When multiple exclusive locks are required the chances "
            "of deadlocks increase."
        )

    return warnings
