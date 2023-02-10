import django
import pytest
from django.db import migrations
from django.db.migrations import (
    AddConstraint,
    AddField,
    AddIndex,
    AlterField,
    RemoveField,
    RenameField,
    RenameModel,
    RunSQL,
)
from django.db.migrations.operations.base import Operation
from django.db.migrations.state import ProjectState
from django.db.models import (
    AutoField,
    BigAutoField,
    CheckConstraint,
    Index,
    IntegerField,
    PositiveIntegerField,
    Q,
)

from migration_checker.checks import run_checks
from migration_checker.warnings import (
    ADD_INDEX_IN_SEPARATE_MIGRATION,
    ADDING_CONSTRAINT,
    ADDING_FIELD_WITH_CHECK,
    ADDING_NON_NULLABLE_FIELD,
    ALTER_FIELD,
    ALTERING_MULTIPLE_MODELS,
    REMOVING_FIELD,
    RENAMING_FIELD,
    RENAMING_MODEL,
    SCHEMA_AND_DATA_CHANGES,
    USE_ADD_INDEX_CONCURRENTLY,
    VALIDATE_CONSTRAINT_SEPARATELY,
    Warning,
)


def check_migration(*test_operations: Operation) -> set[Warning]:
    class InitialMigration(migrations.Migration):
        initial = True
        operations = [
            migrations.CreateModel(
                name="Foo",
                fields=[("id", AutoField())],
            ),
        ]

    class TestMigration(migrations.Migration):
        operations = list(test_operations)

    state = ProjectState()
    state = InitialMigration(name="0001_foo", app_label="foo").mutate_state(state)

    migration = TestMigration(name="0002_foo", app_label="foo")

    return set(run_checks(migration, state))


def test_add_index() -> None:
    operation = AddIndex(model_name="foo", index=Index(fields=["foo"], name="foo"))
    assert check_migration(operation) == {USE_ADD_INDEX_CONCURRENTLY}


def test_add_index_separately() -> None:
    operations = [
        AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
        AddIndex(model_name="foo", index=Index(fields=["foo"], name="foo")),
    ]
    assert check_migration(*operations) == {
        USE_ADD_INDEX_CONCURRENTLY,
        ADD_INDEX_IN_SEPARATE_MIGRATION,
    }


def test_add_nullable_field() -> None:
    operation = AddField(model_name="foo", name="bar", field=IntegerField(null=True))
    assert not check_migration(operation)


def test_add_non_nullable_field() -> None:
    operation = AddField(model_name="foo", name="bar", field=IntegerField())
    assert check_migration(operation) == {ADDING_NON_NULLABLE_FIELD}


def test_remove_field() -> None:
    operation = RemoveField(model_name="foo", name="bar")
    assert check_migration(operation) == {REMOVING_FIELD}


def test_remove_model() -> None:
    operation = RenameModel(old_name="foo", new_name="bar")
    assert check_migration(operation) == {RENAMING_MODEL}


def test_rename_field() -> None:
    operation = RenameField(model_name="foo", old_name="bar", new_name="baz")
    assert check_migration(operation) == {RENAMING_FIELD}


def test_schema_and_data_changes() -> None:
    operations = [
        AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
        RunSQL("select 1", RunSQL.noop),
    ]
    assert check_migration(*operations) == {SCHEMA_AND_DATA_CHANGES}


def test_alter_multiple_models() -> None:
    operations = [
        AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
        AddField(model_name="baz", name="bar", field=IntegerField(null=True)),
    ]
    assert check_migration(*operations) == {ALTERING_MULTIPLE_MODELS}


def test_add_field_with_check() -> None:
    operation = AddField(
        model_name="foo", name="bar", field=PositiveIntegerField(null=True)
    )
    assert check_migration(operation) == {ADDING_FIELD_WITH_CHECK}


def test_add_constraint() -> None:
    operation = AddConstraint(
        model_name="foo",
        constraint=CheckConstraint(check=Q(age__gte=18), name="age_gte_18"),
    )
    assert check_migration(operation) == {ADDING_CONSTRAINT}


def test_alter_field() -> None:
    operation = AlterField(model_name="foo", name="id", field=BigAutoField())
    assert check_migration(operation) == {ALTER_FIELD}


def test_alter_field_to_nullable() -> None:
    operation = AlterField(model_name="foo", name="id", field=AutoField(null=True))
    assert check_migration(operation) == set()


@pytest.mark.skipif(django.VERSION < (4, 0), reason="Not supported in Django < 4.0")
def test_add_field_and_validate_constraint() -> None:
    from django.contrib.postgres.operations import ValidateConstraint

    operations = [
        AddField(model_name="foo", name="bar", field=IntegerField(null=True)),
        ValidateConstraint(model_name="foo", name="foo"),
    ]
    assert check_migration(*operations) == {VALIDATE_CONSTRAINT_SEPARATELY}
