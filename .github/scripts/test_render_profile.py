"""Behavior tests for metadata-driven profile generation (standard library only)."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from render_profile import apply_outputs, build_outputs

CONFIG = {"owner": "PixelGG", "name": "Mike", "intro": "Game systems.", "project_limit": 6}


def repository(rid=123, name="Example"):
    return {
        "id": rid, "name": name, "description": "A useful project.",
        "url": f"https://github.com/PixelGG/{name}", "language": "Lua",
        "stars": 0, "forks": 0, "pushed_at": "2026-10-05T00:00:00Z",
        "default_branch": "main", "topics": [],
    }


def snapshot(repos):
    return {"schema_version": 1, "owner": "PixelGG", "observed_at": "2026-10-05T00:00:00Z",
            "repositories": repos}


class ProfileBehavior(unittest.TestCase):
    def test_repository_lifecycle_removes_deleted_assets_and_updates_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = build_outputs(snapshot([repository(10, "RenamedLater"), repository(11, "DeletedLater")]), CONFIG)
            self.assertTrue(apply_outputs(root, before))
            unrelated = root / ".github/assets/projects/handmade.svg"
            unrelated.write_text("<svg/>")
            after = build_outputs(snapshot([repository(10, "NewName")]), CONFIG)
            self.assertTrue(apply_outputs(root, after))
            readme = (root / "README.md").read_text()
            self.assertNotIn("DeletedLater", readme)
            self.assertNotIn("RenamedLater", readme)
            self.assertIn("https://github.com/PixelGG/NewName", readme)
            self.assertFalse((root / ".github/assets/projects/11.svg").exists())
            self.assertFalse((root / ".github/assets/projects/11-mobile.svg").exists())
            self.assertTrue((root / ".github/assets/projects/10.svg").exists())
            self.assertTrue(unrelated.exists())
            self.assertTrue(apply_outputs(root, after, check=True))

    def test_empty_successful_snapshot_has_no_phantom_projects(self):
        outputs = build_outputs(snapshot([]), CONFIG)
        self.assertIn("keine öffentlichen", outputs[Path("README.md")])
        self.assertFalse(any("projects" in str(path) for path in outputs))
        for path, content in outputs.items():
            if path.suffix == ".svg":
                ET.fromstring(content)

    def test_untrusted_metadata_is_text_and_cannot_inject_markup(self):
        repo = repository()
        repo["description"] = '<img src="https://attacker.test/tracker"> **useful** [click](https://attacker.test) & data'
        repo["language"] = 'Lua</text><script>alert(1)</script>'
        outputs = build_outputs(snapshot([repo]), CONFIG)
        md = outputs[Path("README.md")]
        self.assertIn("&lt;img", md)
        self.assertNotIn('<img src="https://attacker.test', md)
        self.assertNotIn("<script>", md)
        for path, content in outputs.items():
            if path.suffix == ".svg":
                tree = ET.fromstring(content)
                self.assertFalse(any(element.tag.endswith("script") for element in tree.iter()))

    def test_long_names_are_preserved_and_xml_remains_valid(self):
        name = "A" * 100
        outputs = build_outputs(snapshot([repository(name=name)]), CONFIG)
        self.assertIn(name, outputs[Path("README.md")])
        for path, content in outputs.items():
            if path.suffix == ".svg":
                ET.fromstring(content)

    def test_reproducible_rendering_and_readonly_check(self):
        data = snapshot([repository()])
        outputs = build_outputs(data, CONFIG)
        self.assertEqual(outputs, build_outputs(deepcopy(data), deepcopy(CONFIG)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apply_outputs(root, outputs)
            readme = root / "README.md"
            readme.write_text("Manual edit")
            self.assertFalse(apply_outputs(root, outputs, check=True))
            self.assertEqual("Manual edit", readme.read_text())

    def test_invalid_input_is_rejected_before_any_write(self):
        bad_cases = []
        wrong_url = repository()
        wrong_url["url"] = "https://example.com"
        bad_cases.append(snapshot([wrong_url]))
        bad_cases.append(snapshot([repository(), repository()]))
        wrong_name = repository()
        wrong_name["name"] = "<script>"
        bad_cases.append(snapshot([wrong_name]))
        bad_cases.append({**snapshot([]), "observed_at": "unverified"})
        for data in bad_cases:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    build_outputs(data, CONFIG)


if __name__ == "__main__":
    unittest.main()
