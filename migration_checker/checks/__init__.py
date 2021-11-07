from typing import Protocol

from django.db.migrations import Migration
from django.db.migrations.state import ProjectState

from .add_index import check_add_index
from .add_non_nullable_field import check_add_non_nullable_field
from .alter_multiple_tables import check_alter_multiple_tables
from .atomic_run_python import check_atomic_run_python
from .data_and_schema_changes import check_data_and_schema_changes
from .remove_field import check_remove_field
from .rename_field import check_rename_field
from .rename_model import check_rename_model


class Check(Protocol):
    def __call__(self, *, migration: Migration, state: ProjectState) -> list[str]:
        ...


all_checks: list[Check] = [
    check_add_index,
    check_add_non_nullable_field,
    check_alter_multiple_tables,
    check_atomic_run_python,
    check_data_and_schema_changes,
    check_remove_field,
    check_rename_field,
    check_rename_model,
]
