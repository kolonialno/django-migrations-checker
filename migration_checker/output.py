"""
Helpers to build the Github comment output
"""

import functools
import inspect
import io
import textwrap

from django.db.migrations import Migration

from .checks import Warning
from .github import GithubClient


class ConsoleOutput:
    def no_migrations_to_apply(self) -> None:
        print("No migrations to apply")

    def begin(self, num_migrations: int) -> None:
        print(f"🔍 Applying and checking {num_migrations} migrations")

    def migration_result(
        self,
        migration: Migration,
        queries: list[str],
        locks: list[tuple[str, str]],
        warnings: list[Warning],
    ) -> None:
        print(cyan(f"\n{migration.app_label}.{migration.name}"))
        for operation in migration.operations:
            print(f"    {operation.describe()}")

        for warning in warnings:
            print(f"\n    {warning.level.emoji} {bold(warning.title)}")
            print(
                textwrap.fill(
                    warning.description,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
            )

        if locks:
            print()
        for table_name, lock_type in locks:
            print(f"    🔒 {red(lock_type)} on {bold(table_name)}")

    def done(self) -> None:
        pass


def _color(value: str, *, color_code: str) -> str:
    return f"\033[{color_code}m{value}\033[0m"


green = functools.partial(_color, color_code="32")
magenta = functools.partial(_color, color_code="35")
cyan = functools.partial(_color, color_code="36")
gray = functools.partial(_color, color_code="37")
red = functools.partial(_color, color_code="91")
yellow = functools.partial(_color, color_code="93")
bold = functools.partial(_color, color_code="1")


class GithubCommentOutput:
    def __init__(self, *, client: GithubClient) -> None:
        self.output = io.StringIO()
        self.client = client

    def post_comment(self) -> None:
        comment = next(
            (
                comment
                for comment in self.client.get_comments()
                if "ADDED BY django-migrations-checker" in comment.body
            ),
            None,
        )

        body = self.output.getvalue()

        if comment:
            self.client.update_comment(comment_id=comment.id, body=body)
        else:
            self.client.create_comment(body=body)

    def no_migrations_to_apply(self) -> None:
        comment = next(
            (
                comment
                for comment in self.client.get_comments()
                if "ADDED BY django-migrations-checker" in comment.body
            ),
            None,
        )

        if comment:
            self.client.update_comment(
                comment_id=comment.id,
                body="Looks like this pull request no longer contains any migrations.",
            )

    def begin(self, num_migrations: int) -> None:
        print(get_header_md(), file=self.output)

    def migration_result(
        self,
        migration: Migration,
        queries: list[str],
        locks: list[tuple[str, str]],
        warnings: list[Warning],
    ) -> None:
        print(
            get_migration_md(
                migration=migration, queries=queries, locks=locks, warnings=warnings
            ),
            file=self.output,
        )

    def done(self) -> None:
        print(get_footer_md(), file=self.output)

        self.post_comment()


def get_header_md() -> str:
    return """\
<p>
Hi there, it looks like your pull request contains database
migrations. Below you'll find some details about each migrations. Please take
an extra look at especially the locks taken by the migrations.
</p>
"""


def get_footer_md() -> str:
    return """
---

<details>
<summary>About this bot</summary>
<br />

This message is posted by a GitHub Action that checks migrations.

</details>
<!-- ADDED BY django-migrations-checker -->
"""


def get_migration_md(
    *,
    migration: Migration,
    queries: list[str],
    locks: list[tuple[str, str]],
    warnings: list[Warning],
) -> str:
    """
    Get markdown containing details for a single migration.
    """

    source_code = inspect.getsource(migration.__class__)
    if locks:
        locks_details = "### Locks\n" + "\n".join(
            get_lock_details(table, lock) for table, lock in locks
        )
    else:
        locks_details = "This migration does not take any locks"

    sql = "\n".join(queries) if queries else "-- No queries"

    warnings_text = "\n\n".join(
        textwrap.indent(
            f"#### {warning.level.emoji} {warning.title}\n{warning.description}",
            prefix="> ",
            predicate=lambda line: True,
        )
        for warning in warnings
    )

    md = f"""
## {migration.app_label}.{migration.name}

{warnings_text}

<details>
<summary>Source code</summary>

```python
{source_code}
```

</details>

<details>
<summary>Queries</summary>

```sql
{sql}
```

</details>

{locks_details}
"""

    return md


def get_lock_details(table_name: str, lock_type: str) -> str:
    """
    Get details about a lock
    """

    if lock_type == "ShareLock":
        lock_details = (
            "This is a lock type that will block any concurrent updates to the "
            "table. That also means that it has to wait for all current updates "
            "to finish before it can be applied. If this takes long other "
            "updates are blocked in the mean time."
        )
    elif lock_type == "AccessExclusiveLock":
        lock_details = (
            "An access exclusive lock will block any other queries to the "
            "table, including reads. This is the strictest level of locking in "
            "Postgres.\nBecause this lock conflicts with any other lock type, "
            "it will have to wait until all other queries against the table have "
            "completed before being granted."
        )
    else:
        lock_details = "Unknown lock type, please check the Postgres documentation"

    emoji = "🔑"
    if lock_type in ("ShareLock", "ShareRowExclusiveLock"):
        emoji = "⚠️"
    elif lock_type in ("ExclusiveLock", "AccessExclusiveLock"):
        emoji = "🚨"

    return f"""\
<details>
<summary>{emoji }<code>{lock_type}</code> on <code>{table_name}</code></summary>
<blockquote>{lock_details}</blockquote>
</details>
"""
