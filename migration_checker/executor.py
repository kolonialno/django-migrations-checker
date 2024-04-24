"""
Helper to execute migrations and record results
"""

from typing import Any, Callable, Sequence, Union, cast

import django
import sqlparse  # type: ignore[import]
from django.contrib.postgres.operations import NotInTransactionMixin
from django.db import connections, transaction
from django.db.migrations import Migration, RunSQL, SeparateDatabaseAndState
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.operations.base import Operation
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

from migration_checker.warnings import MULTIPLE_EXCLUSIVE_LOCKS

from .checks import run_checks
from .output import ConsoleOutput, GithubCommentOutput


class QueryLogger:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def __call__(
        self,
        execute: Callable[[str, list[Any], bool, dict[str, Any]], Any],
        sql: str,
        params: list[Any],
        many: bool,
        context: dict[str, Any],
    ) -> Any:
        cursor = context["cursor"]
        mogrify_result = cursor.mogrify(sql, params)
        rendered_sql: str = (
            mogrify_result
            if isinstance(mogrify_result, str)
            else mogrify_result.decode()
        )
        self.queries.append(rendered_sql)

        return execute(sql, params, many, context)


class Executor:
    def __init__(
        self,
        *,
        database: str,
        apply_migrations: bool,
        outputs: list[Union[ConsoleOutput, GithubCommentOutput]],
    ) -> None:
        self.database = database
        self.apply_migrations = apply_migrations
        self.outputs = outputs
        self.connection = connections[self.database]
        self.recorder = MigrationRecorder(self.connection)

    def run(self) -> None:
        # First we need to set up Django
        django.setup()

        connection = connections[self.database]

        # Hook for backends needing any database preparation
        connection.prepare_database()

        executor = MigrationExecutor(connection)

        # Raise an error if any migrations are applied before their dependencies.
        executor.loader.check_consistent_history(connection)

        targets: set[tuple[str, str]] = executor.loader.graph.leaf_nodes()
        plan: list[tuple[Migration, bool]] = executor.migration_plan(targets)

        if not plan:
            for output in self.outputs:
                output.no_migrations_to_apply()
            return

        assert not any(backwards for _migration, backwards in plan)

        for output in self.outputs:
            output.begin(num_migrations=len(plan))

        state = executor._create_project_state(  # type: ignore[attr-defined]
            with_applied_migrations=True,
        )

        for migration, _ in plan:
            # Run checkers on the migration
            warnings = run_checks(migration, state)

            if self.apply_migrations:
                queries, locks = self._apply_migration(migration, state)
            else:
                queries, locks = [], None

            num_exclusive_locks = sum(
                1
                for _, lock_type in locks or ()
                if lock_type in ("AccessExclusiveLock", "ExclusiveLock")
            )
            if num_exclusive_locks > 1:
                warnings.append(MULTIPLE_EXCLUSIVE_LOCKS)

            for output in self.outputs:
                output.migration_result(
                    migration=migration, queries=queries, locks=locks, warnings=warnings
                )

        for output in self.outputs:
            output.done()

    def _apply_migration(
        self, migration: Migration, state: ProjectState
    ) -> tuple[list[str], list[tuple[str, str]] | None]:
        """
        Apply a single migration, while recording queries and checking locks
        held in the database afterwards.
        """

        # Some operations, like AddIndexConcurrently, cannot be run in a
        # transaction, so for those special cases we skip recording locks
        # because we ahave no way of doing that.
        if self._must_be_non_atomic(migration.operations):
            return self._apply_non_atomic_migration(migration, state), None

        # Apply the migration in the database and record queries and locks
        query_logger = QueryLogger()
        with transaction.atomic(using=self.database):
            with self.connection.execute_wrapper(query_logger):
                with self.connection.schema_editor(atomic=False) as schema_editor:
                    migration.apply(state, schema_editor)

            locks = self.get_locks()
            self.recorder.record_applied(migration.app_label, migration.name)

        return query_logger.queries, locks

    def _must_be_non_atomic_query(self, query: str) -> bool:
        """
        Try to detect if a raw query must be non-atomic.
        """

        patterns = [
            [
                (sqlparse.tokens.DDL, "CREATE"),
                (sqlparse.tokens.Keyword, "INDEX"),
                (sqlparse.tokens.Keyword, "CONCURRENTLY"),
            ],
            [
                (sqlparse.tokens.DDL, "DROP"),
                (sqlparse.tokens.Keyword, "INDEX"),
                (sqlparse.tokens.Keyword, "CONCURRENTLY"),
            ],
        ]

        for statement in sqlparse.parse(query):
            for pattern in patterns:
                if all(
                    any(token.match(ttype, value) for token in statement.tokens)
                    for ttype, value in pattern
                ):
                    return True
        return False

    def _must_be_non_atomic(self, operations: Sequence[Operation]) -> bool:
        """
        Check if any of the operations must be run outside of a transaction.
        This is the case for some operations, like AddIndexConcurrently. This
        will recursivey check SeparateDatabaseAndState migrations.
        """

        for operation in operations:
            if isinstance(operation, NotInTransactionMixin):
                return True
            if isinstance(operation, SeparateDatabaseAndState):
                return self._must_be_non_atomic(operation.database_operations)
            if isinstance(operation, RunSQL):
                if isinstance(operation.sql, str):
                    return self._must_be_non_atomic_query(operation.sql)
                else:
                    return any(
                        self._must_be_non_atomic_query(statement)
                        if isinstance(statement, str)
                        else self._must_be_non_atomic_query(statement[0])
                        for statement in operation.sql
                    )

        return False

    def _apply_non_atomic_migration(
        self, migration: Migration, state: ProjectState
    ) -> list[str]:
        """
        Apply a migration outside of a migration. This is needed for some
        operations that cannot be executed inside a transaction, like
        AddIndexConcurrently.
        """

        # Apply the migration in the database and record queries and locks
        query_logger = QueryLogger()
        with self.connection.execute_wrapper(query_logger):
            with self.connection.schema_editor(atomic=False) as schema_editor:
                migration.apply(state, schema_editor)

            self.recorder.record_applied(migration.app_label, migration.name)

        return query_logger.queries

    def get_locks(self) -> list[tuple[str, str]]:
        """
        Get database locks held by the current transaction.
        """

        # Check which locks are held by the transaction.
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.relname,
                    l.mode
                FROM pg_locks l
                LEFT JOIN pg_stat_all_tables t
                ON l.relation = t.relid

                WHERE t.relname IS NOT null
                AND t.relname NOT LIKE 'pg_%'
                AND l.pid = pg_backend_pid()

                ORDER BY l.mode, l.relation ASC;
                """
            )
            return cast(list[tuple[str, str]], cursor.fetchall())
