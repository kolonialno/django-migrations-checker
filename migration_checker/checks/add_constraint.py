from django.db.migrations import Migration
from django.db.migrations.state import ProjectState


def check_add_constraint(
    *, migration: Migration, state: ProjectState, sql: str
) -> list[str]:
    """
    Warn if a constraint is being added without specifying NOT VALID
    """

    sql = sql.lower()
    if "alter table" in sql and "add constraint" in sql and "not valid" not in sql:
        return [
            "⚠️ Adding constraint with immediate validation\n"
            "This migration adds a constraint to an existing table without "
            "specifying NOT VALID. This will cause an exclusive lock to be "
            "held until the constraint has been checked on all rows. If the "
            "table is large this can be problematic."
        ]

    # TODO: Check for unique or other types that create indexes

    return []
