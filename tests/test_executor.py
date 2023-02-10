from migration_checker.executor import Executor
from migration_checker.output import ConsoleOutput


def test_executor(setup_db: None) -> None:
    executor = Executor(
        database="default", apply_migrations=True, outputs=[ConsoleOutput()]
    )
    executor.run()
