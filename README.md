<h1 align="center">
  🔍<br>
  Django migrations checker
</h1>

<p align="center">
  A GitHub Action for checking Django migrations
</p>

## About

This repository contains a [Github Action](https://github.com/features/actions)
that checks Django migrations against known issues when running with Postgres
in a high-load environment or using rolling deploys. It assumes that migrations
are run before new versions of your code starts rolling out.

The current checkers are based on our experience at [Oda](https://oda.com/) and
looks for paterns we know can be problematic.

## Usage

**NOTE:** This is currently unfinished, it will not post any comments yet

**NOTE:** This should never be used against a production database

The action requires you to install Python 3.9+ and your project's dependencies.
It has no additional requirements beyond the Python standard libary. When the
action runs it will apply and check all migrations that are unapplied.


### Example workflow

This is an example workflow that checks any migrations that are added in a
branch.


```yaml
name: Linting

# The main value of this check is to post a comment on the pull request, so
# only run on pull requests. You can also run on pushes and output to the
# console, but that is not very visible to developers.
on: [pull_request]

# Limit to one concurrent job and cancel previous runs if a new one is started.
# Because the action posts a comment on the pull request allowing concurrent
# workflows can cause duplicate comments.
concurrency:
  group: check-migrations-${{ github.head_ref }}
  cancel-in-progress: true

jobs:
  check-migrations:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:latest
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
        env:
          POSTGRES_DB: my_database
          POSTGRES_USER: my_user
          POSTGRES_PASSWORD: my_password

    steps:
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      # Check out the main branch and apply migrations
      - name: Check out main branch
        uses: actions/checkout@v2
        with:
          ref: main
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Apply migrations
        run: ./manage.py migrate

      # Check out the current branch and install dependencies
      - name: Check out current branch
        uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt

      # Check migrations. This will check any unapplied migrations. Because
      # we applied all migrations in the main branch this means that only new
      # migrations in this branch will be checked.
      - name: Check migrations
        uses: kolonialno/django-migrations-checker@main
        with:
          django-settings-module: my_project.settings
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Checks

### Add index

Checks if the migration contains an `AddIndex` operation and suggests using
`AddIndexConcurrently` instead. This is safer as it doesn't take a lock on the
table for the duration it takes to build the index.
