all : black mypy isort flake8 pytest

.PHONY: black
black:
	black --check migration_checker tests

.PHONY: mypy
mypy:
	mypy

.PHONY: isort
isort:
	isort --check-only migration_checker tests

.PHONY: flake8
flake8:
	flake8 migration_checker tests

.PHONY: pytest
pytest:
	pytest
