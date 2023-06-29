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

### Adding a non-nullable field

Adding a non-nullable field is not entirely straight forward. This is the case
even if you set a default value, because Django does not use default values at
the database level. This means that the previous version running when you roll
out the field will not provide a value when writing to the table. Because of
this you should add always add new fields as nullable first. You should also
make sure any code that writes to the table is updated to also provide a value
for the new field (either through defaults or by explicity updating code that
writes to the models). Once that has been rolled out you can make a second
deploy, which first backfills old rows and then makes the field non-nullable.

#### First deploy

```python
class Migration(migrations.Migration):
    ...
    operations = [
        migrations.AddField(
            model_name="order",
            name="number",
            field=models.PositiveBigIntegerField(null=True),
        ),
    ]
```

#### Second deploy

First backfill data in one migration:

```python
class Migration(migrations.Migration):
    ...
    operations = [
        migrations.RunSQL(
            "update tests_order set number=1 where number is null",
            migrations.RunSQL.noop,
        ),
    ]
```

Then make the field non-nullable

```python
class Migration(migrations.Migration):
    ...
    operations = [
        migrations.AlterField(
            model_name="order",
            name="number",
            field=models.PositiveBigIntegerField(),
        ),
    ]
```


### Changing field type

Changing the type of a field is generally not safe to do because it causes a
full table rewrite, during which the table will be fully locked. Additionally
old code still running after the migration has been applied might write
unsupported values to the column.

Rather than changing the type of a column you should add a new column and
manually migrate data from the old column to the new one.


### Adding indexes

Checks if the migration contains an `AddIndex` operation and suggests using
`AddIndexConcurrently` instead. This is safer as it doesn't take a lock on the
table for the duration it takes to build the index.
