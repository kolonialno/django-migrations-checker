import pytest
from django.db import migrations
from django.db.migrations import (
    AddField,
    AddIndex,
    RemoveField,
    RenameField,
    RenameModel,
    RunSQL,
)
from django.db.migrations.operations.base import Operation
from django.db.models import Index, IntegerField, PositiveIntegerField

from migration_checker.checks import run_checks
from migration_checker.warnings import (
    ADD_INDEX_IN_SEPARATE_MIGRATION,
    ADDING_FIELD_WITH_CHECK,
    ADDING_NON_NULLABLE_FIELD,
    ALTERING_MULTIPLE_MODELS,
    REMOVING_FIELD,
    RENAMING_FIELD,
    RENAMING_MODEL,
    SCHEMA_AND_DATA_CHANGES,
    USE_ADD_INDEX_CONCURRENTLY,
    Warning,
)


def check_migration(_operations: list[Operation]) -> set[Warning]:
    class Migration(migrations.Migration):
        operations = _operations

    return set(run_checks(migration=Migration(name="0001_foo", app_label="foo")))


@pytest.mark.parametrize(
    ("operations", "warnings"),
    (
        (
            [
                AddIndex(model_name="foo", index=Index(fields=["foo"], name="foo")),
            ],
            {USE_ADD_INDEX_CONCURRENTLY},
        ),
        (
            [
                AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
                AddIndex(model_name="foo", index=Index(fields=["foo"], name="foo")),
            ],
            {USE_ADD_INDEX_CONCURRENTLY, ADD_INDEX_IN_SEPARATE_MIGRATION},
        ),
        (
            [
                AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
            ],
            set(),
        ),
        (
            [
                AddField(model_name="foo", name="bar", field=IntegerField()),
            ],
            {ADDING_NON_NULLABLE_FIELD},
        ),
        (
            [
                RemoveField(model_name="foo", name="bar"),
            ],
            {REMOVING_FIELD},
        ),
        (
            [
                RenameModel(old_name="foo", new_name="bar"),
            ],
            {RENAMING_MODEL},
        ),
        (
            [
                RenameField(model_name="foo", old_name="bar", new_name="baz"),
            ],
            {RENAMING_FIELD},
        ),
        (
            [
                AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
                RunSQL("select 1", RunSQL.noop),
            ],
            {SCHEMA_AND_DATA_CHANGES},
        ),
        (
            [
                AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
                AddField(model_name="baz", name="bar", field=IntegerField(null=True)),
            ],
            {ALTERING_MULTIPLE_MODELS},
        ),
        (
            [
                AddField(
                    model_name="foo", name="bar", field=PositiveIntegerField(null=True)
                ),
            ],
            {ADDING_FIELD_WITH_CHECK},
        ),
    ),
    ids=(
        "use-add-index-concurrently",
        "add-index-separately",
        "safe-add-nullable-field",
        "adding-non-nullable-field",
        "removing-field",
        "renaming-model",
        "renaming-field",
        "schema-and-data-changes",
        "altering-multiple-models",
        "adding-field-with-check",
    ),
)
def test_checks(operations: list[Operation], warnings: set[Warning]) -> None:
    assert check_migration(operations) == warnings
