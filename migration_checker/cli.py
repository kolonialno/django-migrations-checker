import argparse

from .executor import Executor
from .output import ConsoleOutput


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check for unsafe or missing migrations"
    )
    parser.add_argument(
        "--database", type=str, help="Database connection to use", default="default"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply migrations. Without this only static checks are run.",
    )
    args = parser.parse_args()

    Executor(
        database=args.database,
        apply_migrations=args.apply,
        output=ConsoleOutput(),
    ).run()


if __name__ == "__main__":
    main()
