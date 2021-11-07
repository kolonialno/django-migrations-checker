from django.db.migrations import Migration
from django.db.migrations.operations import AddIndex
from django.db.migrations.state import ProjectState


def check_add_index(*, migration: Migration, state: ProjectState) -> list[str]:

    warnings = []

    if any(isinstance(operation, AddIndex) for operation in migration.operations):

        warnings.append(
            "⚠️ Consider using AddIndexConcurrently instead\n"
            "This migration adds an index to a table. That will take a share "
            "lock on the table, blocking any updates on the table until the "
            "index has been created. If the table is large it can take a long "
            "time to create the index. Please consider adding the index "
            "concurrently instead."
        )

        # TODO: Allow if the table was created in the same migration
        if not migration.initial and len(migration.operations) > 1:
            warnings.append(
                "⚠️ Add index in separate migration\n"
                "Adding a migration should be done alone in a migration to "
                "avoid keeping locks longer than strictly required."
            )

    return warnings
