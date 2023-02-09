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
