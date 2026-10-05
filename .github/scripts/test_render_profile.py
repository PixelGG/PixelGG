"""Behavior tests for metadata-driven profile generation (standard library only)."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit, parse_qs
import xml.etree.ElementTree as ET

from render_profile import apply_outputs, build_outputs
from motion_frames import has_motion, sample_frame

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
    def test_github_uses_versioned_gifs_and_keeps_reduced_motion_sources(self):
        class Pictures(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []
            def handle_starttag(self, tag, attrs):
                if tag in {'img', 'source'}:
                    self.tags.append((tag, dict(attrs)))
        outputs = build_outputs(snapshot([repository()]), CONFIG)
        parsed = Pictures()
        parsed.feed(outputs[Path('README.md')])
        images = [attrs for tag, attrs in parsed.tags if tag == 'img']
        self.assertTrue(images[0]['src'].split('?')[0].endswith('world.gif'))
        self.assertTrue(any('prefers-reduced-motion: reduce' in attrs.get('media', '')
                            and urlsplit(attrs['srcset']).path.endswith('world.svg')
                            for tag, attrs in parsed.tags if tag == 'source'))
        for tag, attrs in parsed.tags:
            source = attrs.get('src') or attrs['srcset']
            self.assertTrue(parse_qs(urlsplit(source).query).get('v'))
        # No mobile desk animation exists, so mobile intro must stay an SVG.
        self.assertFalse(any('intro-mobile.gif' in str(attrs) for _, attrs in parsed.tags))
        changed = repository()
        changed['description'] = 'Updated public metadata.'
        newer = build_outputs(snapshot([changed]), CONFIG)
        self.assertNotEqual(outputs[Path('README.md')], newer[Path('README.md')])

    def test_baked_motion_changes_pose_and_loops_without_css(self):
        outputs = build_outputs(snapshot([repository()]), CONFIG)
        svg = outputs[Path('.github/assets/world.svg')]
        self.assertTrue(has_motion(svg))
        first, later = sample_frame(svg, .25), sample_frame(svg, 1.75)
        self.assertNotEqual(first, later)
        self.assertEqual(first, sample_frame(svg, 6.25))
        self.assertNotIn('<style', first)
        self.assertNotIn('animation-delay', first)
        self.assertIn('url(#fall)', first)
        ET.fromstring(first)
        self.assertFalse(has_motion(outputs[Path('.github/assets/intro-mobile.svg')]))

    def test_repository_lifecycle_removes_deleted_assets_and_updates_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = build_outputs(snapshot([repository(10, "RenamedLater"), repository(11, "DeletedLater")]), CONFIG)
            self.assertTrue(apply_outputs(root, before))
            (root / '.github/assets/projects/10.gif').write_bytes(b'kept')
            (root / '.github/assets/projects/11.gif').write_bytes(b'removed')
            unrelated = root / ".github/assets/projects/handmade.svg"
            unrelated.write_text("<svg/>")
            after = build_outputs(snapshot([repository(10, "NewName")]), CONFIG)
            self.assertTrue(apply_outputs(root, after))
            readme = (root / "README.md").read_text()
            self.assertNotIn("DeletedLater", readme)
            self.assertNotIn("RenamedLater", readme)
            self.assertIn("https://github.com/PixelGG/NewName", readme)
            web = (root / "web/index.html").read_text()
            self.assertNotIn("DeletedLater", web)
            self.assertNotIn("RenamedLater", web)
            self.assertIn("https://github.com/PixelGG/NewName", web)
            self.assertFalse((root / ".github/assets/projects/11.svg").exists())
            self.assertFalse((root / ".github/assets/projects/11-mobile.svg").exists())
            self.assertFalse((root / ".github/assets/projects/11.gif").exists())
            self.assertTrue((root / ".github/assets/projects/10.gif").exists())
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
        web = outputs[Path("web/index.html")]
        self.assertIn("&lt;img", web)
        self.assertNotIn('<img src="https://attacker.test', web)
        self.assertNotIn("<script>", web)
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
