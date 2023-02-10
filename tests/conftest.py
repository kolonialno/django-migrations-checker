from typing import Iterable

import django
import pytest
from django.conf import settings
from django.db import connection


@pytest.fixture
def setup_django() -> None:
    django.setup()


@pytest.fixture
def setup_db(setup_django: None) -> Iterable[None]:
    old_database_name = connection.settings_dict["NAME"]
    test_database_name = connection.creation._create_test_db(  # type: ignore
        autoclobber=True, verbosity=2
    )

    try:
        connection.close()
        settings.DATABASES[connection.alias]["NAME"] = test_database_name
        connection.settings_dict["NAME"] = test_database_name
        yield
    finally:
        connection.creation.destroy_test_db(
            old_database_name, verbosity=2, keepdb=False
        )
