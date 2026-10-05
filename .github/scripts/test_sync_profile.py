"""Offline regression tests for metadata changes and fail-closed synchronization."""
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error

from sync_profile import SyncError, fetch_repositories_page, normalize_and_select, sync_profile


def repository(repo_id=1, name="Example", **updates):
    result = {
        "id": repo_id, "name": name, "owner": {"login": "PixelGG"},
        "private": False, "visibility": "public", "fork": False,
        "archived": False, "disabled": False, "description": "A useful project.",
        "html_url": f"https://github.com/PixelGG/{name}", "language": "Python",
        "stargazers_count": 2, "forks_count": 1, "pushed_at": "2026-10-01T12:00:00Z",
        "default_branch": "main", "topics": ["tools"],
    }
    result.update(updates)
    return result


class NormalizationTests(unittest.TestCase):
    def test_filters_profile_private_fork_archived_disabled_and_other_owner(self):
        raw = [repository(1), repository(2, "PixelGG"), repository(3, private=True),
               repository(4, fork=True), repository(5, archived=True),
               repository(6, disabled=True), repository(7, owner={"login": "OtherUser"}),
               repository(8, visibility="private")]
        self.assertEqual([row["id"] for row in normalize_and_select(raw, "PixelGG")], [1])

    def test_rename_keeps_id_and_rebuilds_link(self):
        before = normalize_and_select([repository()], "PixelGG")[0]
        after = normalize_and_select([repository(name="Renamed")], "PixelGG")[0]
        self.assertEqual(before["id"], after["id"])
        self.assertEqual(after["url"], "https://github.com/PixelGG/Renamed")

    def test_only_whitelisted_public_data_and_canonical_url_are_retained(self):
        row = normalize_and_select([repository(html_url="javascript:alert(1)",
                                               secret="never-publish", permissions={"admin": True})], "PixelGG")[0]
        self.assertEqual(set(row), {"id", "name", "description", "url", "language", "stars",
                                    "forks", "pushed_at", "default_branch", "topics"})
        self.assertEqual(row["url"], "https://github.com/PixelGG/Example")

    def test_description_is_data_for_renderer_to_escape(self):
        description = '<svg onload="run()"> & [a](https://bad.example)\n second line'
        row = normalize_and_select([repository(description=description)], "PixelGG")[0]
        self.assertEqual(row["description"], description.replace("\n", ""))

    def test_deterministic_newest_sort_and_id_tie_break(self):
        raw = [repository(i, f"Repo-{i}") for i in range(10, 0, -1)]
        raw.append(repository(11, "Newest", pushed_at="2026-10-02T12:00:00Z"))
        selected = normalize_and_select(raw, "PixelGG")
        self.assertEqual([row["id"] for row in selected], [11, 1, 2, 3, 4, 5])
        self.assertEqual(selected, normalize_and_select(list(reversed(raw)), "PixelGG"))

    def test_null_fields_and_empty_result(self):
        row = normalize_and_select([repository(description=None, language=None, pushed_at=None)], "PixelGG")[0]
        self.assertEqual(row["description"], "")
        self.assertIsNone(row["language"])
        self.assertIsNone(row["pushed_at"])
        self.assertEqual(normalize_and_select([], "PixelGG"), [])

    def test_limit_matches_renderer_contract(self):
        for limit in (0, 7, True, "6"):
            with self.subTest(limit=limit), self.assertRaises(SyncError):
                normalize_and_select([], "PixelGG", limit)

    def test_rejects_malformed_data_not_partial_success(self):
        cases = [{"name": "../evil"}, {"id": True}, {"private": None},
                 {"stargazers_count": -1}, {"forks_count": "1"},
                 {"pushed_at": "not-a-date"}, {"pushed_at": "2026-10-01"},
                 {"description": "bad\x00xml"}, {"topics": ["<svg>"]}]
        for update in cases:
            with self.subTest(update=update), self.assertRaises(SyncError):
                normalize_and_select([repository(**update)], "PixelGG")
        with self.assertRaises(SyncError):
            normalize_and_select([repository(), repository()], "PixelGG")


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "snapshot.json"
        self.clock = lambda: datetime(2026, 10, 5, tzinfo=timezone.utc)

    def sync(self, rows, **kwargs):
        return sync_profile("PixelGG", self.output, fetch_page=lambda page: rows, now=self.clock, **kwargs)

    def test_deletion_removes_old_project_and_last_deletion_is_empty(self):
        self.sync([repository(), repository(2, "Second")])
        self.sync([repository(2, "Second")])
        self.assertEqual([row["id"] for row in json.loads(self.output.read_text())["repositories"]], [2])
        self.sync([])
        self.assertEqual(json.loads(self.output.read_text())["repositories"], [])

    def test_no_change_preserves_exact_bytes_and_original_timestamp(self):
        rows = [repository()]
        self.assertTrue(self.sync(rows))
        old = self.output.read_bytes()
        # Noncanonical whitespace proves unchanged snapshots are not rewritten.
        self.output.write_bytes(old + b"\n")
        self.clock = lambda: datetime(2026, 10, 6, tzinfo=timezone.utc)
        self.assertFalse(self.sync(rows))
        self.assertEqual(self.output.read_bytes(), old + b"\n")

    def test_metadata_change_replaces_data_and_timestamp(self):
        self.sync([repository()])
        self.clock = lambda: datetime(2026, 10, 6, tzinfo=timezone.utc)
        self.sync([repository(name="Changed", description="Changed description", stargazers_count=8)])
        result = json.loads(self.output.read_text())
        self.assertEqual(result["observed_at"], "2026-10-06T00:00:00Z")
        self.assertEqual(result["repositories"][0]["name"], "Changed")
        self.assertEqual(result["repositories"][0]["stars"], 8)

    def test_two_page_failure_preserves_previous_snapshot_bytes(self):
        self.sync([repository()])
        old = self.output.read_bytes()
        pages = []

        def fetch(page):
            pages.append(page)
            if page == 1:
                return [repository(i, f"Repo-{i}") for i in range(1, 101)]
            raise SyncError("Simulated page-two failure")

        with self.assertRaises(SyncError):
            sync_profile("PixelGG", self.output, fetch_page=fetch)
        self.assertEqual(pages, [1, 2])
        self.assertEqual(self.output.read_bytes(), old)

    def test_two_page_success_selects_newest_from_second_page(self):
        def fetch(page):
            if page == 1:
                return [repository(i, f"Repo-{i}") for i in range(1, 101)]
            return [repository(101, "Latest", pushed_at="2026-10-03T12:00:00Z")]
        sync_profile("PixelGG", self.output, fetch_page=fetch, now=self.clock)
        self.assertEqual(json.loads(self.output.read_text())["repositories"][0]["id"], 101)

    def test_invalid_last_row_preserves_previous_snapshot(self):
        self.sync([repository()])
        old = self.output.read_bytes()
        with self.assertRaises(SyncError):
            self.sync([repository(), repository(2, "Second", private="false")])
        self.assertEqual(self.output.read_bytes(), old)


class RequestTests(unittest.TestCase):
    def test_bounded_transient_retry_then_success_and_public_endpoint(self):
        requests, delays = [], []

        def opener(request, timeout):
            requests.append((request, timeout))
            if len(requests) < 3:
                raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", {}, None)
            response = io.BytesIO(b"[]")
            response.status = 200
            return response

        self.assertEqual(fetch_repositories_page("PixelGG", 2, opener=opener, sleep=delays.append), [])
        self.assertEqual(delays, [1, 2])
        self.assertEqual(len(requests), 3)
        self.assertIn("/users/PixelGG/repos?type=owner", requests[0][0].full_url)
        self.assertIn("per_page=100&page=2", requests[0][0].full_url)
        self.assertEqual(requests[0][1], 20)

    def test_auth_error_does_not_leak_exception_or_token(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 401, "SECRET_TOKEN", {}, io.BytesIO(b"SECRET_TOKEN"))
        with self.assertRaises(SyncError) as caught:
            fetch_repositories_page("PixelGG", 1, "SECRET_TOKEN", opener=opener)
        self.assertNotIn("SECRET_TOKEN", str(caught.exception))
        self.assertIn("authentication failed", str(caught.exception))

    def test_rate_limit_is_not_retried(self):
        calls = []

        def opener(request, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(request.full_url, 429, "Rate limit", {}, None)
        with self.assertRaisesRegex(SyncError, "rate limit"):
            fetch_repositories_page("PixelGG", 1, opener=opener)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
