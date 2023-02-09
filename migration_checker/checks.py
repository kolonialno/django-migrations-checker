from typing import Iterable, Protocol

from django.db.migrations import (
    AddField,
    AddIndex,
    Migration,
    RemoveField,
    RenameField,
    RenameModel,
    RunPython,
    RunSQL,
)
from django.db.migrations.operations.fields import FieldOperation
from django.db.migrations.operations.models import ModelOperation

from .warnings import (
    ADD_INDEX_IN_SEPARATE_MIGRATION,
    USE_ADD_INDEX_CONCURRENTLY,
    Warning,
)


class Check(Protocol):
    def __call__(self, *, migration: Migration) -> Iterable[Warning]:
        ...


def check_add_index(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, AddIndex) for operation in migration.operations):
        yield USE_ADD_INDEX_CONCURRENTLY

        # TODO: Allow if the table was created in the same migration
        if not migration.initial and len(migration.operations) > 1:
            yield ADD_INDEX_IN_SEPARATE_MIGRATION


def check_add_non_nullable_field(*, migration: Migration) -> Iterable[Warning]:
    if any(
        isinstance(operation, AddField) and not operation.field.null
        for operation in migration.operations
    ):
        # TODO: Allow if model was added in same migration
        yield Warning(
            title="Adding non-nullable field",
            description=(
                "This migration is adding a field that is not nullable. "
                "That will cause problems if the table is written to before "
                "the new code has been rolled out."
            ),
        )


def check_alter_multiple_tables(*, migration: Migration) -> Iterable[Warning]:
    altered_models = set()

    if migration.atomic and not migration.initial:
        for operation in migration.operations:
            if isinstance(operation, FieldOperation):
                altered_models.add(operation.model_name)
            elif isinstance(operation, ModelOperation):
                altered_models.add(operation.name)

    # TODO: Allow if models were created in the same migration
    if len(altered_models) > 1:
        yield Warning(
            level=Level.DANGER,
            title="Altering multiple models",
            description=(
                "Consider splitting this migration into separate migrations. "
                "This migration is making changes to multiple tables. That can be "
                "problematic because exclusive locks are required when altering "
                "a table. When multiple exclusive locks are required the chances "
                "of deadlocks increase."
            ),
        )


def check_atomic_run_python(*, migration: Migration) -> Iterable[Warning]:
    if migration.atomic and any(
        isinstance(operation, RunPython) for operation in migration.operations
    ):
        yield Warning(
            title="Atomic data migration",
            description=(
                "It looks like you are migrating data (assuming that since you "
                "have RunPython statements) Please note that this sort of data "
                "migration should not be run inside a transaction unless it is "
                "pretty fast. Have you considered using atomic=False on the "
                "Migration class?"
            ),
        )


def check_data_and_schema_changes(*, migration: Migration) -> Iterable[Warning]:
    data_migration, schema_migration = False, False
    for operation in migration.operations:
        if isinstance(operation, (RunPython, RunSQL)):
            data_migration = True
        else:
            schema_migration = True

    if data_migration and schema_migration:
        yield Warning(
            level=Level.NOTICE,
            title="Schema and data changes",
            description=(
                "It looks like you are doing both schema and data changes in the "
                "same migration. That should be avoided unless stricly required."
            ),
        )


def check_rename_model(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, RenameModel) for operation in migration.operations):
        yield Warning(
            level=Level.DANGER,
            title="Renaming a model is not safe",
            description=(
                "This migration is renaming a model. That is not safe if the model "
                "is in use. Please add a new model, copy data, and remove the old "
                "model instead."
            ),
        )


def check_rename_field(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, RenameField) for operation in migration.operations):
        yield Warning(
            level=Level.DANGER,
            title="Renaming a field is not safe",
            description=(
                "This migration is renaming a field. That is not safe if the table "
                "is in use. Please add a new field, copy data, and remove the old "
                "field instead."
            ),
        )


def check_remove_field(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, RemoveField) for operation in migration.operations):
        yield Warning(
            level=Level.NOTICE,
            title="Removing a field",
            description=(
                "This migration is removing a field. This is only safe if you "
                "have already removed all references to the field, including the "
                "field definition on the model."
            ),
        )


ALL_CHECKS: list[Check] = [
    check_add_index,
    check_add_non_nullable_field,
    check_alter_multiple_tables,
    check_atomic_run_python,
    check_data_and_schema_changes,
    check_remove_field,
    check_rename_field,
    check_rename_model,
]


def run_checks(migration: Migration) -> list[Warning]:
    return [warning for check in ALL_CHECKS for warning in check(migration=migration)]
