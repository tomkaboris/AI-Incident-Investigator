from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitHubSearchHit:
    owner: str
    repository: str
    path: str
    name: str
    html_url: str | None = None


@dataclass(frozen=True, slots=True)
class GitHubFile:
    owner: str
    repository: str
    path: str
    content: str
    sha: str | None = None
    html_url: str | None = None
