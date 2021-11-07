"""
Helper to execute migrations and record results
"""

from typing import Union

import django
from django.db import connections, transaction
from django.db.migrations import Migration
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

from .checks import all_checks
from .output import ConsoleOutput, GithubCommentOutput


class QueryLogger:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def __call__(self, execute, sql, params, many, context):

        cursor = context["cursor"]
        rendered_sql = cursor.mogrify(sql, params).decode()
        self.queries.append(rendered_sql)

        return execute(sql, params, many, context)


def query_blocker(self, execute, sql, params, many, context):
    raise RuntimeError(
        'Queries are not allowed against the {context["database"]} database'
    )


class Executor:
    def __init__(
        self,
        *,
        database: str,
        apply_migrations: bool,
        output: Union[ConsoleOutput, GithubCommentOutput]
    ) -> None:
        self.database = database
        self.apply_migrations = apply_migrations
        self.output = output
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
            self.output.no_migrations_to_apply()
            return

        assert not any(backwards for _migration, backwards in plan)

        self.output.begin(num_migrations=len(plan))

        state = executor._create_project_state(  # type: ignore
            with_applied_migrations=True,
        )

        for i, (migration, _) in enumerate(plan):

            # Run checkers on the migration
            warnings = self._check_migration(migration, state)

            if self.apply_migrations:
                queries, locks = self._apply_migration(migration, state)
            else:
                queries, locks = [], []

            num_exclusive_locks = sum(
                1
                for _, lock_type in locks
                if lock_type in ("AccessExclusiveLock", "ExclusiveLock")
            )
            if num_exclusive_locks > 1:
                warnings.append(
                    "🚨 Multiple exclusive locks\n"
                    "This migration takes multiple exclusive locks. That can be "
                    "problematic if the tables are queried frequently.",
                )

            self.output.migration_result(
                migration=migration, queries=queries, locks=locks, warnings=warnings
            )

        self.output.done()

    def _check_migration(self, migration: Migration, state: ProjectState) -> list[str]:
        """
        Perform static checks on a migration.
        """

        return [
            message
            for check in all_checks
            for message in check(migration=migration, state=state)
        ]

    def _apply_migration(
        self, migration: Migration, state: ProjectState
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """
        Apply a single migration, while recording queries and checking locks
        held in the database afterwards.
        """

        # Apply the migration in the database and record queries and locks
        # TODO: Block queries against other databases
        query_logger = QueryLogger()
        with transaction.atomic(using=self.database):
            with self.connection.execute_wrapper(query_logger):  # type: ignore
                with self.connection.schema_editor(atomic=False) as schema_editor:
                    migration.apply(state, schema_editor)

            locks = self.get_locks()
            self.recorder.record_applied(migration.app_label, migration.name)

        return query_logger.queries, locks

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
            return cursor.fetchall()
