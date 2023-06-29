from unittest.mock import Mock

import pytest
from django.contrib.postgres.operations import (
    AddIndexConcurrently,
    RemoveIndexConcurrently,
)
from django.db.migrations import AddIndex, RunSQL, SeparateDatabaseAndState
from django.db.migrations.operations.base import Operation

from migration_checker.executor import Executor
from migration_checker.output import ConsoleOutput


def test_executor(setup_db: None) -> None:
    executor = Executor(
        database="default", apply_migrations=True, outputs=[ConsoleOutput()]
    )
    executor.run()


@pytest.mark.parametrize(
    "operation,must_be_non_atomic",
    [
        (AddIndex("test", index=Mock()), False),
        (AddIndexConcurrently("test", index=Mock()), True),
        (RemoveIndexConcurrently("foo", "test"), True),
        (RunSQL("CREATE INDEX foobar"), False),
        (RunSQL("CREATE INDEX foobar CONCURRENTLY", RunSQL.noop), True),
        (RunSQL("DROP INDEX foobar CONCURRENTLY", RunSQL.noop), True),
        (RunSQL([("CREATE INDEX foobar", None)]), False),
        (RunSQL([("CREATE INDEX foobar CONCURRENTLY", None)]), True),
        (
            SeparateDatabaseAndState(
                database_operations=[RunSQL("CREATE INDEX foobar")]
            ),
            False,
        ),
        (
            SeparateDatabaseAndState(
                database_operations=[RunSQL("CREATE INDEX foobar CONCURRENTLY")]
            ),
            True,
        ),
        (
            SeparateDatabaseAndState(
                database_operations=[AddIndex("test", index=Mock())]
            ),
            False,
        ),
        (
            SeparateDatabaseAndState(
                database_operations=[AddIndexConcurrently("test", index=Mock())]
            ),
            True,
        ),
    ],
)
def test_run_sql_must_be_non_atomic(
    operation: Operation, must_be_non_atomic: bool
) -> None:
    executor = Executor(
        database="default", apply_migrations=True, outputs=[ConsoleOutput()]
    )

    assert executor._must_be_non_atomic([operation]) is must_be_non_atomic
