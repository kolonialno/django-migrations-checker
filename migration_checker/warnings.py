from dataclasses import dataclass
from enum import Enum

from typing_extensions import Self


class Level(str, Enum):
    DANGER = "danger", "🚨"
    WARNING = "warning", "⚠️"
    NOTICE = "notice", "💡"

    def __new__(cls, value: str, _: str) -> Self:
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, emoji: str):
        self.emoji = emoji


@dataclass(kw_only=True, eq=True, frozen=True)
class Warning:
    level: Level = Level.WARNING
    title: str
    description: str

    def __str__(self) -> str:
        return f"{self.level.emoji} {self.title}"

    def __repr__(self) -> str:
        return f"<Warning: {self}>"


MULTIPLE_EXCLUSIVE_LOCKS = Warning(
    level=Level.DANGER,
    title="Multiple exclusive locks",
    description=(
        "This migration takes multiple exclusive locks."
        "That can be problematic if the tables are "
        "queried frequently."
    ),
)


USE_ADD_INDEX_CONCURRENTLY = Warning(
    title="Consider using AddIndexConcurrently instead",
    description=(
        "This migration adds an index to a table. That will take a share "
        "lock on the table, blocking any updates on the table until the "
        "index has been created. If the table is large it can take a long "
        "time to create the index. Please consider adding the index "
        "concurrently instead."
    ),
)

ADD_INDEX_IN_SEPARATE_MIGRATION = Warning(
    title="Add index in separate migration",
    description=(
        "Adding a migration should be done alone in a migration to "
        "avoid keeping locks longer than strictly required."
    ),
)

ADDING_NON_NULLABLE_FIELD = Warning(
    title="Adding non-nullable field",
    description=(
        "This migration is adding a field that is not nullable. "
        "That will cause problems if the table is written to before "
        "the new code has been rolled out."
    ),
)
ALTERING_MULTIPLE_MODELS = Warning(
    level=Level.DANGER,
    title="Altering multiple models",
    description=(
        "Consider splitting this migration into separate migrations. "
        "This migration is making changes to multiple tables. That can be "
        "problematic because exclusive locks are required when altering "
        "a table. When multiple exclusive locks are required the chances "
        "of deadlocks increase."
    ),
)

ATOMIC_DATA_MIGRATION = Warning(
    title="Atomic data migration",
    description=(
        "It looks like you are migrating data (assuming that since you "
        "have RunPython statements) Please note that this sort of data "
        "migration should not be run inside a transaction unless it is "
        "pretty fast. Have you considered using atomic=False on the "
        "Migration class?"
    ),
)

SCHEMA_AND_DATA_CHANGES = Warning(
    level=Level.NOTICE,
    title="Schema and data changes",
    description=(
        "It looks like you are doing both schema and data changes in the "
        "same migration. That should be avoided unless stricly required."
    ),
)

RENAMING_MODEL = Warning(
    level=Level.DANGER,
    title="Renaming a model is not safe",
    description=(
        "This migration is renaming a model. That is not safe if the model "
        "is in use. Please add a new model, copy data, and remove the old "
        "model instead."
    ),
)
RENAMING_FIELD = Warning(
    level=Level.DANGER,
    title="Renaming a field is not safe",
    description=(
        "This migration is renaming a field. That is not safe if the table "
        "is in use. Please add a new field, copy data, and remove the old "
        "field instead."
    ),
)

REMOVING_FIELD = Warning(
    level=Level.NOTICE,
    title="Removing a field",
    description=(
        "This migration is removing a field. This is only safe if you "
        "have already removed all references to the field, including the "
        "field definition on the model."
    ),
)
