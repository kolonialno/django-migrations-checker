import argparse
import json
import os
from typing import Union

from .executor import Executor
from .github import GithubClient
from .output import ConsoleOutput, GithubCommentOutput


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check for unsafe or missing migrations"
    )
    parser.add_argument(
        "--database", type=str, help="Database connection to use", default="default"
    )
    parser.add_argument(
        "--github-token", type=str, help="Access token to use to post comment on Github"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply migrations. Without this only static checks are run.",
    )
    args = parser.parse_args()

    event_name = os.environ.get("GITHUB_EVENT_NAME", None)
    event_path = os.environ.get("GITHUB_EVENT_PATH", None)
    repository = os.environ.get("GITHUB_REPOSITORY", None)

    event_data = {}
    if event_path:
        with open(event_path, "r") as f:
            event_data = json.loads(f.read())
            assert isinstance(event_data, dict)

    outputs: list[Union[ConsoleOutput, GithubCommentOutput]] = [ConsoleOutput()]

    if args.github_token and repository and event_name == "pull_request" and event_data:
        pull_request = int(event_data["number"])
        github_client = GithubClient(
            token=args.github_token,
            repo=repository,
            pull_request=pull_request,
        )
        outputs.append(GithubCommentOutput(client=github_client))

    Executor(
        database=args.database,
        apply_migrations=args.apply,
        outputs=outputs,
    ).run()


if __name__ == "__main__":
    main()
