#!/usr/bin/env python3
"""Refresh a public-only GitHub snapshot using the Python standard library.

All pages are fetched and validated before one atomic replacement. A failed
request never turns an incomplete response into a published project list.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / ".github/profile/config.json"
DEFAULT_OUTPUT = ROOT / ".github/profile/public-repos.json"
API_VERSION = "2026-03-10"
PAGE_SIZE = 100
MAX_PAGES = 1000
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
NAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
TOPIC_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,49}\Z")


class SyncError(Exception):
    """An actionable error whose message never includes response bodies/tokens."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward an optional token to a URL supplied in an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_owner(owner: object) -> str:
    if not isinstance(owner, str) or not OWNER_RE.fullmatch(owner) or "--" in owner:
        raise SyncError("Owner must be a valid GitHub username.")
    return owner


def validate_limit(limit: object) -> int:
    if type(limit) is not int or not 1 <= limit <= 6:
        raise SyncError("project_limit must be an integer between 1 and 6.")
    return limit


def _text(value: object, field: str, maximum: int, *, nullable: bool = False) -> str:
    if nullable and value is None:
        return ""
    if not isinstance(value, str) or len(value) > maximum:
        raise SyncError(f"Invalid repository {field}; previous snapshot retained.")
    # Retain punctuation as plain data. The renderer escapes it for each output.
    if any((ord(c) < 32 and c not in "\t\r\n") or 0xD800 <= ord(c) <= 0xDFFF
           or ord(c) in (0xFFFE, 0xFFFF) for c in value):
        raise SyncError(f"Invalid characters in repository {field}.")
    return " ".join(value.split())


def _count(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise SyncError(f"Invalid repository {field}; previous snapshot retained.")
    return value


def _timestamp(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 40:
        raise SyncError("Invalid repository pushed_at timestamp.")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Timezone required")
        return stamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError:
        raise SyncError("Invalid repository pushed_at timestamp.") from None


def normalize_and_select(raw_repositories: list, owner: str, limit: int = 6) -> list[dict]:
    """Validate a complete API result, then select current public source repos.

    Repository IDs remain stable across renames. URLs are constructed from
    validated names instead of trusting API-provided html_url or homepage data.
    """
    owner = validate_owner(owner)
    limit = validate_limit(limit)
    if not isinstance(raw_repositories, list):
        raise SyncError("GitHub repository response must be a list.")
    selected = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for repo in raw_repositories:
        if not isinstance(repo, dict):
            raise SyncError("Invalid repository entry in GitHub response.")
        repo_id = _count(repo.get("id"), "id")
        if repo_id == 0 or repo_id in seen_ids:
            raise SyncError("Invalid or duplicate repository ID; retry a fresh complete sync.")
        seen_ids.add(repo_id)
        for flag in ("private", "fork", "archived", "disabled"):
            if type(repo.get(flag)) is not bool:
                raise SyncError(f"Missing or invalid repository {flag} flag.")
        visibility = repo.get("visibility", "public" if not repo["private"] else "private")
        if visibility not in ("public", "private", "internal"):
            raise SyncError("Invalid repository visibility.")
        if repo["private"] or visibility != "public" or repo["fork"] or repo["archived"] or repo["disabled"]:
            continue
        repo_owner = repo.get("owner")
        if not isinstance(repo_owner, dict):
            raise SyncError("Missing repository owner.")
        login = validate_owner(repo_owner.get("login"))
        if login.casefold() != owner.casefold():
            continue
        name = repo.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name in (".", ".."):
            raise SyncError("Invalid repository name; refusing to construct a link.")
        if name.casefold() in seen_names:
            raise SyncError("Duplicate repository name; retry a fresh complete sync.")
        seen_names.add(name.casefold())
        if name.casefold() == owner.casefold():
            continue
        description = _text(repo.get("description"), "description", 4096, nullable=True)
        language = repo.get("language")
        if language is not None:
            language = _text(language, "language", 100)
        branch = _text(repo.get("default_branch"), "default_branch", 255)
        if not branch:
            raise SyncError("Repository default_branch is empty.")
        topics = repo.get("topics", [])
        if not isinstance(topics, list) or len(topics) > 20 or any(
            not isinstance(topic, str) or not TOPIC_RE.fullmatch(topic) for topic in topics
        ):
            raise SyncError("Invalid repository topics.")
        selected.append({
            "id": repo_id,
            "name": name,
            "description": description,
            "url": f"https://github.com/{owner}/{name}",
            "language": language,
            "stars": _count(repo.get("stargazers_count"), "stargazers_count"),
            "forks": _count(repo.get("forks_count"), "forks_count"),
            "pushed_at": _timestamp(repo.get("pushed_at")),
            "default_branch": branch,
            "topics": sorted(set(topics)),
        })
    # Stable tie order is ascending numeric ID; null dates sort after real dates.
    selected.sort(key=lambda repo: repo["id"])
    selected.sort(key=lambda repo: repo["pushed_at"] or "", reverse=True)
    return selected[:limit]


def fetch_repositories_page(owner: str, page: int, token: str | None = None,
                            *, opener=None, sleep: Callable[[float], None] = time.sleep) -> list:
    """Fetch only /users/{owner}/repos, with bounded transient retries."""
    owner = validate_owner(owner)
    if type(page) is not int or page < 1:
        raise SyncError("Invalid pagination request.")
    query = urllib.parse.urlencode({
        "type": "owner", "sort": "full_name", "direction": "asc",
        "per_page": PAGE_SIZE, "page": page,
    })
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "PixelGG-profile-sync/1.0",
    }
    if token:
        if "\r" in token or "\n" in token:
            raise SyncError("GitHub token has an invalid format; check the workflow secret.")
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/users/{owner}/repos?{query}", headers=headers)
    open_url = opener or urllib.request.build_opener(NoRedirect()).open
    for attempt in range(3):
        try:
            with open_url(request, timeout=20) as response:
                if response.status != 200:
                    raise SyncError("GitHub returned an unexpected response; previous snapshot retained.")
                body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise SyncError("GitHub response exceeds the safe size limit.")
            try:
                data = json.loads(body)
            except (ValueError, UnicodeError):
                raise SyncError("GitHub returned invalid JSON; previous snapshot retained.") from None
            if not isinstance(data, list) or len(data) > PAGE_SIZE:
                raise SyncError("GitHub returned an invalid repository page.")
            return data
        except urllib.error.HTTPError as error:
            # Never log exception bodies, request headers, or token values.
            if error.code in (502, 503, 504) and attempt < 2:
                sleep(attempt + 1)
                continue
            if error.code in (403, 429):
                raise SyncError("GitHub denied the request or its rate limit was reached. Retry later; check token access and the Actions log.") from None
            if error.code == 401:
                raise SyncError("GitHub authentication failed. Check GITHUB_TOKEN or retry without a token.") from None
            if error.code == 404:
                raise SyncError("GitHub user was not found. Check the configured owner.") from None
            raise SyncError(f"GitHub request failed (HTTP {error.code}); previous snapshot retained.") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt < 2:
                sleep(attempt + 1)
                continue
            raise SyncError("GitHub is unreachable after three attempts; previous snapshot retained.") from None
    raise SyncError("GitHub request could not complete.")


def collect_repositories(fetch_page: Callable[[int], list]) -> list:
    """Numbered pagination avoids following untrusted Link response URLs."""
    collected = []
    for page in range(1, MAX_PAGES + 1):
        batch = fetch_page(page)
        if not isinstance(batch, list) or len(batch) > PAGE_SIZE:
            raise SyncError("GitHub returned an invalid repository page.")
        collected.extend(batch)
        if len(batch) < PAGE_SIZE:
            return collected
    raise SyncError("Pagination safety limit reached; previous snapshot retained.")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sync_profile(owner: str, output: Path, limit: int = 6, *,
                 fetch_page: Callable[[int], list] | None = None,
                 token: str | None = None,
                 now: Callable[[], datetime] | None = None) -> bool:
    """Return whether content changed. Preserve the previous file on any failure."""
    owner = validate_owner(owner)
    limit = validate_limit(limit)
    output = Path(output)
    fetch_page = fetch_page or (lambda page: fetch_repositories_page(owner, page, token))
    repositories = normalize_and_select(collect_repositories(fetch_page), owner, limit)
    content = {"schema_version": 1, "owner": owner, "repositories": repositories}
    if output.exists():
        try:
            previous = json.loads(output.read_bytes())
        except (ValueError, UnicodeError):
            previous = None
        if isinstance(previous, dict) and set(previous) == {*content, "observed_at"}:
            if all(previous.get(key) == value for key, value in content.items()) and _timestamp(previous.get("observed_at")):
                print(f"Profile snapshot unchanged ({len(repositories)} projects).")
                return False
    stamp = now() if now else datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise SyncError("Snapshot clock must provide a timezone-aware timestamp.")
    content["observed_at"] = stamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    _atomic_write(output, (json.dumps(content, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"Profile snapshot updated ({len(repositories)} projects).")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--owner", help="Override the owner in the configuration.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        try:
            config = json.loads(args.config.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            raise SyncError("Cannot read profile configuration. Check --config and its JSON syntax.") from None
        if not isinstance(config, dict):
            raise SyncError("Profile configuration must be a JSON object.")
        sync_profile(args.owner or config.get("owner"), args.output,
                     config.get("project_limit", 6), token=os.environ.get("GITHUB_TOKEN"))
    except SyncError as error:
        print(f"Profile sync failed: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Profile sync failed: snapshot could not be read or written; previous file retained.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
