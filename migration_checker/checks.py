from typing import Iterable, Protocol

import django
from django.db import connection
from django.db.migrations import (
    AddConstraint,
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
from django.db.models import CheckConstraint

from .warnings import (
    ADD_INDEX_IN_SEPARATE_MIGRATION,
    ADDING_CONSTRAINT,
    ADDING_FIELD_WITH_CHECK,
    ADDING_NON_NULLABLE_FIELD,
    ALTERING_MULTIPLE_MODELS,
    ATOMIC_DATA_MIGRATION,
    REMOVING_FIELD,
    RENAMING_FIELD,
    RENAMING_MODEL,
    SCHEMA_AND_DATA_CHANGES,
    USE_ADD_INDEX_CONCURRENTLY,
    VALIDATE_CONSTRAINT_SEPARATELY,
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
        yield ADDING_NON_NULLABLE_FIELD


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
        yield ALTERING_MULTIPLE_MODELS


def check_atomic_run_python(*, migration: Migration) -> Iterable[Warning]:
    if migration.atomic and any(
        isinstance(operation, RunPython) for operation in migration.operations
    ):
        yield ATOMIC_DATA_MIGRATION


def check_data_and_schema_changes(*, migration: Migration) -> Iterable[Warning]:
    data_migration, schema_migration = False, False
    for operation in migration.operations:
        if isinstance(operation, (RunPython, RunSQL)):
            data_migration = True
        else:
            schema_migration = True

    if data_migration and schema_migration:
        yield SCHEMA_AND_DATA_CHANGES


def check_rename_model(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, RenameModel) for operation in migration.operations):
        yield RENAMING_MODEL


def check_rename_field(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, RenameField) for operation in migration.operations):
        yield RENAMING_FIELD


def check_remove_field(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, RemoveField) for operation in migration.operations):
        yield REMOVING_FIELD


def check_field_with_check_constraint(*, migration: Migration) -> Iterable[Warning]:
    if any(
        connection.data_type_check_constraints.get(operation.field.get_internal_type())
        is not None
        for operation in migration.operations
        if isinstance(operation, AddField)
    ):
        yield ADDING_FIELD_WITH_CHECK


def check_add_constraint(*, migration: Migration) -> Iterable[Warning]:
    if any(isinstance(operation, AddConstraint) for operation in migration.operations):
        yield ADDING_CONSTRAINT


def check_validate_constraint(*, migration: Migration) -> Iterable[Warning]:
    # This feature is only available in Django >= 4.0
    if django.VERSION < (4, 0):
        return

    from django.contrib.postgres.operations import ValidateConstraint

    has_validate_constraint = any(
        isinstance(operation, ValidateConstraint) for operation in migration.operations
    )
    has_other_operation = any(
        not isinstance(operation, ValidateConstraint)
        for operation in migration.operations
    )
    if has_validate_constraint and has_other_operation:
        yield VALIDATE_CONSTRAINT_SEPARATELY


ALL_CHECKS: list[Check] = [
    check_add_index,
    check_add_non_nullable_field,
    check_alter_multiple_tables,
    check_atomic_run_python,
    check_data_and_schema_changes,
    check_remove_field,
    check_rename_field,
    check_rename_model,
    check_field_with_check_constraint,
    check_add_constraint,
    check_validate_constraint,
]


def run_checks(migration: Migration) -> list[Warning]:
    return [warning for check in ALL_CHECKS for warning in check(migration=migration)]
