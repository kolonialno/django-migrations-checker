from django.db.migrations import Migration
from django.db.migrations.operations import RenameModel
from django.db.migrations.state import ProjectState


def check_rename_model(*, migration: Migration, state: ProjectState) -> list[str]:
    warnings = []

    if any(isinstance(operation, RenameModel) for operation in migration.operations):
        warnings.append(
            "🚨 Renaming a model is not safe\n"
            "This migration is renaming a model. That is not safe if the model "
            "is in use. Please add a new model, copy data, and remove the old "
            "model instead."
        )

    return warnings
