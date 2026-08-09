from __future__ import annotations

import asyncio
import base64
import json
import ssl
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from incident_investigator.config import Settings
from incident_investigator.integrations.github.models import GitHubFile, GitHubSearchHit


class GitHubIntegrationError(RuntimeError):
    """Raised when the configured GitHub/GHE API cannot satisfy a lookup."""


@dataclass(frozen=True, slots=True)
class GitHubClient:
    api_url: str
    web_url: str
    token: str
    organization: str | None
    timeout_seconds: float
    verify_ssl: bool
    max_search_results: int

    @classmethod
    def from_settings(cls, settings: Settings) -> "GitHubClient":
        if not settings.github_token:
            raise GitHubIntegrationError("GITHUB_TOKEN is not configured.")

        web_url = (settings.github_base_url or "https://github.com").rstrip("/")
        api_url = settings.github_api_url
        if not api_url:
            hostname = (urlparse(web_url).hostname or "").lower()
            api_url = "https://api.github.com" if hostname == "github.com" else f"{web_url}/api/v3"

        return cls(
            api_url=api_url.rstrip("/"),
            web_url=web_url,
            token=settings.github_token,
            organization=settings.github_organization,
            timeout_seconds=settings.github_timeout_seconds,
            verify_ssl=settings.github_verify_ssl,
            max_search_results=settings.github_max_search_results,
        )

    def _request_json(self, path: str, *, query: dict[str, str] | None = None) -> Any:
        url = f"{self.api_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github.text-match+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "ai-incident-investigator",
            },
        )
        context = None
        if not self.verify_ssl:
            context = ssl._create_unverified_context()  # noqa: S323

        try:
            with urlopen(request, timeout=self.timeout_seconds, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = ""
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                detail = str(payload.get("message") or "")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            suffix = f": {detail}" if detail else ""
            raise GitHubIntegrationError(f"GitHub API returned HTTP {exc.code}{suffix}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubIntegrationError(
                f"GitHub API request failed: {type(exc).__name__}"
            ) from exc

    async def search_code(self, term: str) -> list[GitHubSearchHit]:
        qualifiers = []
        if self.organization:
            qualifiers.append(f"org:{self.organization}")
        query_text = " ".join([term, *qualifiers]).strip()
        payload = await asyncio.to_thread(
            self._request_json,
            "/search/code",
            query={"q": query_text, "per_page": str(self.max_search_results)},
        )
        hits: list[GitHubSearchHit] = []
        for item in payload.get("items", [])[: self.max_search_results]:
            repository = item.get("repository") or {}
            owner = repository.get("owner") or {}
            repo_name = repository.get("name")
            owner_name = owner.get("login")
            path = item.get("path")
            if not repo_name or not owner_name or not path:
                continue
            hits.append(
                GitHubSearchHit(
                    owner=owner_name,
                    repository=repo_name,
                    path=path,
                    name=item.get("name") or path.rsplit("/", 1)[-1],
                    html_url=item.get("html_url"),
                )
            )
        return hits

    async def get_file(
        self,
        *,
        owner: str,
        repository: str,
        path: str,
        ref: str | None = None,
    ) -> GitHubFile:
        query = {"ref": ref} if ref else None
        encoded_owner = quote(owner, safe="")
        encoded_repo = quote(repository, safe="")
        encoded_path = quote(path, safe="/")
        payload = await asyncio.to_thread(
            self._request_json,
            f"/repos/{encoded_owner}/{encoded_repo}/contents/{encoded_path}",
            query=query,
        )
        if payload.get("type") != "file":
            raise GitHubIntegrationError("GitHub content lookup did not return a file.")

        encoding = payload.get("encoding")
        raw_content = payload.get("content") or ""
        if encoding == "base64":
            try:
                content = base64.b64decode(raw_content).decode("utf-8", errors="replace")
            except (ValueError, UnicodeDecodeError) as exc:
                raise GitHubIntegrationError("GitHub returned invalid file content.") from exc
        else:
            content = str(raw_content)

        return GitHubFile(
            owner=owner,
            repository=repository,
            path=path,
            content=content,
            sha=payload.get("sha"),
            html_url=payload.get("html_url"),
        )
