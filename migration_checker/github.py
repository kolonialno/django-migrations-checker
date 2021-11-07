"""
A super simple API client for the Github API.
"""
import json
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass
class Comment:
    id: int
    author: str
    body: str


class GithubClient:
    def __init__(self, *, token: str, repo: str, pull_request: int) -> None:
        self.token = token
        self.repo = repo
        self.pull_request = pull_request

    def get_comments(self) -> list[Comment]:
        comments = self.request(
            "GET",
            f"/repos/{self.repo}/issues/{self.pull_request}/comments",
        )
        assert isinstance(comments, list)
        return [
            Comment(
                id=comment["id"], author=comment["user"]["login"], body=comment["body"]
            )
            for comment in comments
        ]

    def create_comment(self, *, body: str) -> None:
        self.request(
            "PATCH",
            f"/repos/{self.repo}/issues/{self.pull_request}/comments",
            data={"body": body},
        )

    def update_comment(self, *, comment_id: int, body: str) -> None:
        self.request(
            "POST",
            f"/repos/{self.repo}/issues/comments/{comment_id}",
            data={"body": body},
        )

    def request(self, method: str, path: str, data: Any = None) -> Any:
        url = urljoin("https://api.github.com", path)
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-agent": "https://github.com/kolonialno/django-migrations-checker",
            "Authorization": f"Bearer {self.token}",
            "Content-type": "application/json; charset=UTF-8",
        }
        req = Request(
            url,
            method=method,
            headers=headers,
            data=json.dumps(data).encode("utf-8") if data else None,
        )

        with urlopen(req) as response:
            assert isinstance(response, HTTPResponse)
            assert "json" in response.getheader("content-type", "")
            return json.loads(response.read())
