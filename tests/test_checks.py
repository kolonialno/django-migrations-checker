import pytest
from django.db import migrations
from django.db.migrations import AddField, AddIndex
from django.db.migrations.operations.base import Operation
from django.db.models import Index, IntegerField

from migration_checker.checks import run_checks
from migration_checker.warnings import (
    ADD_INDEX_IN_SEPARATE_MIGRATION,
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
            [AddIndex(model_name="foo", index=Index(fields=["foo"], name="foo"))],
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
            [AddField(model_name="foo", name="bar", field=IntegerField(null=True))],
            set(),
        ),
    ),
    ids=(
        "use-add-index-concurrently",
        "add-index-separately",
        "safe-add-nullable-field",
    ),
)
def test_checks(operations: list[Operation], warnings: set[Warning]) -> None:
    assert check_migration(operations) == warnings
