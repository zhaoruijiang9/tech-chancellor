import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .models import EnrichmentEvidence, RepositoryRecord, utc_now


class HttpFailure(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class BudgetExceeded(Exception):
    pass


@dataclass
class RequestBudget:
    maximum: int
    used: int = 0

    def consume(self) -> None:
        if self.used >= self.maximum:
            raise BudgetExceeded(f"request budget exhausted at {self.maximum}")
        self.used += 1


@dataclass
class TransportResponse:
    data: Any
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ApiFailure:
    code: str
    message: str


@dataclass
class ApiResult:
    items: list[RepositoryRecord] = field(default_factory=list)
    raw: Any = None
    failure: ApiFailure | None = None
    rate_headers: dict[str, str] = field(default_factory=dict)


class UrllibTransport:
    def get(self, path: str, params: dict[str, Any]) -> TransportResponse:
        url = "https://api.github.com" + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "personal-tech-intelligence/0.1"}
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
                headers = {key: response.headers.get(key, "") for key in (
                    "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "X-RateLimit-Resource"
                )}
                return TransportResponse(data, headers)
        except urllib.error.HTTPError as error:
            raise HttpFailure(error.code, error.reason or "HTTP failure") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise HttpFailure(0, _redact(str(error))) from error


def _redact(value: str) -> str:
    return re.sub(r"(?i)(token|authorization|password|secret)=?[^\s,;]+", r"\1=[REDACTED]", value)


def normalize_repository(item: dict[str, Any]) -> RepositoryRecord:
    license_data = item.get("license") or {}
    parent = item.get("parent") or {}
    owner_repo = item.get("full_name") or f"{(item.get('owner') or {}).get('login', '')}/{item.get('name', '')}"
    return RepositoryRecord(
        github_repository_id=int(item["id"]),
        canonical_owner_repo=owner_repo,
        url=item.get("html_url") or item.get("url") or "",
        last_seen=utc_now(),
        stars=int(item.get("stargazers_count") or 0),
        forks=int(item.get("forks_count") or 0),
        pushed_at=item.get("pushed_at"),
        license_spdx=license_data.get("spdx_id"),
        is_fork=bool(item.get("fork")),
        parent_repository_id=parent.get("id"),
        description=item.get("description") or "",
        topics=list(item.get("topics") or []),
        default_branch=item.get("default_branch"),
    )


class GitHubClient:
    def __init__(self, transport: Any | None = None, budget: RequestBudget | None = None):
        self.transport = transport or UrllibTransport()
        self.budget = budget or RequestBudget(20)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, str], ApiFailure | None]:
        try:
            self.budget.consume()
            response = self.transport.get(path, params or {})
            if isinstance(response, TransportResponse):
                return response.data, response.headers, None
            return response, {}, None
        except BudgetExceeded as error:
            return None, {}, ApiFailure("REQUEST_BUDGET_EXCEEDED", str(error))
        except HttpFailure as error:
            return None, {}, ApiFailure(f"HTTP_{error.status}" if error.status else "NETWORK_ERROR", error.message)
        except Exception as error:
            return None, {}, ApiFailure("CLIENT_ERROR", str(error))

    def search_repositories(self, query: str, page: int = 1, per_page: int = 10) -> ApiResult:
        data, headers, failure = self._request(
            "/search/repositories", {"q": query, "sort": "stars", "order": "desc", "page": page, "per_page": per_page}
        )
        if failure:
            return ApiResult(failure=failure, rate_headers=headers)
        items = [normalize_repository(item) for item in (data or {}).get("items", [])]
        return ApiResult(items=items, raw=data, rate_headers=headers)

    def get_repository(self, owner: str, repo: str) -> ApiResult:
        data, headers, failure = self._request(f"/repos/{owner}/{repo}")
        if failure:
            return ApiResult(failure=failure, rate_headers=headers)
        return ApiResult(items=[normalize_repository(data)], raw=data, rate_headers=headers)

    def get_latest_release(self, owner: str, repo: str) -> ApiResult:
        data, headers, failure = self._request(f"/repos/{owner}/{repo}/releases/latest")
        return ApiResult(raw=data, rate_headers=headers, failure=failure)

    def get_latest_commit(self, owner: str, repo: str) -> ApiResult:
        data, headers, failure = self._request(f"/repos/{owner}/{repo}/commits", {"per_page": 1})
        return ApiResult(raw=data, rate_headers=headers, failure=failure)

    def get_readme(self, owner: str, repo: str) -> ApiResult:
        data, headers, failure = self._request(f"/repos/{owner}/{repo}/readme")
        if failure:
            return ApiResult(raw=None, rate_headers=headers, failure=failure)
        return ApiResult(raw=data, rate_headers=headers)

    def get_tree(self, owner: str, repo: str, branch: str | None = None) -> ApiResult:
        path = f"/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(branch or 'HEAD', safe='')}"
        data, headers, failure = self._request(path, {"recursive": 1})
        return ApiResult(raw=data, rate_headers=headers, failure=failure)

    def enrich_repository(self, owner: str, repo: str, level: str = "LIGHT", text_limit: int = 12000) -> EnrichmentEvidence:
        level = level.upper()
        evidence = EnrichmentEvidence(level=level)
        def capture(label: str, result: ApiResult) -> Any:
            if result.failure:
                evidence.failures.append({"source": label, "code": result.failure.code, "message": _redact(result.failure.message)})
                return None
            return result.raw
        readme = capture("README", self.get_readme(owner, repo))
        if isinstance(readme, dict):
            raw = readme.get("content", "")
            try:
                evidence.readme = base64.b64decode(raw).decode("utf-8", errors="replace")[:text_limit]
            except (ValueError, UnicodeError):
                evidence.failures.append({"source": "README", "code": "INVALID_CONTENT", "message": "README content was not valid base64"})
        if level in {"STANDARD", "DEEP_REVIEW"}:
            evidence.release = capture("RELEASE", self.get_latest_release(owner, repo))
            commits = capture("COMMIT", self.get_latest_commit(owner, repo))
            if isinstance(commits, list) and commits:
                evidence.latest_commit = commits[0]
        if level in {"STANDARD", "DEEP_REVIEW"}:
            tree = capture("TREE", self.get_tree(owner, repo))
            if isinstance(tree, dict):
                evidence.tree_paths = [str(item.get("path", "")) for item in tree.get("tree", []) if item.get("path")][:200]
        return evidence
