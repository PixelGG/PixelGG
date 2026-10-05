#!/usr/bin/env python3
"""Validate the profile's local images with the Python standard library."""

from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_BUDGET_BYTES = 400_000
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
MARKDOWN_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\s*"
    r"(?:\((?P<inline>[^)\n]*)\)|\[(?P<label>[^\]\n]*)\])?"
)
MARKDOWN_REFERENCE = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(.+)$", re.MULTILINE)


class ImageSources(HTMLParser):
    """Collect README image paths without fetching resources."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sources = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"img", "source"}:
            return
        attrs = dict(attrs)
        if tag == "img" and not attrs.get("alt", "").strip():
            self.errors.append("README.md: an image is missing meaningful alt text")
        if not attrs.get("src") and not attrs.get("srcset"):
            self.errors.append(f"README.md: <{tag}> has no image source")
        if attrs.get("src"):
            self.sources.append(attrs["src"])
        if attrs.get("srcset"):
            for candidate in attrs["srcset"].split(","):
                parts = candidate.split()
                if parts:
                    self.sources.append(parts[0])


def markdown_destination(value):
    """Read a simple inline/reference destination and optional title."""
    value = value.strip()
    if value.startswith("<"):
        return value[1:].split(">", 1)[0]
    return value.split(maxsplit=1)[0] if value else ""


def check_readme(root):
    errors = []
    readme = root / "README.md"
    if not readme.is_file():
        return ["README.md is missing"], 0
    text = readme.read_text(encoding="utf-8")
    parser = ImageSources()
    parser.feed(text)
    errors.extend(parser.errors)
    sources = parser.sources
    references = {
        " ".join(label.casefold().split()): markdown_destination(value)
        for label, value in MARKDOWN_REFERENCE.findall(text)
    }
    for match in MARKDOWN_IMAGE.finditer(text):
        if not match.group("alt").strip():
            errors.append("README.md: a Markdown image is missing alt text")
        if match.group("inline") is not None:
            sources.append(markdown_destination(match.group("inline")))
        else:
            label = match.group("label") or match.group("alt")
            key = " ".join(label.casefold().split())
            if key not in references:
                errors.append(f"README.md: unresolved image reference {label!r}")
            else:
                sources.append(references[key])
    for source in sorted(set(sources)):
        try:
            url = urlsplit(source)
        except ValueError:
            errors.append(f"README.md: invalid image path: {source!r}")
            continue
        if url.scheme or url.netloc or source.startswith("/"):
            errors.append(f"README.md: image must use a relative repository path: {source}")
            continue
        target = (root / unquote(url.path)).resolve()
        if not source or not target.is_relative_to(root.resolve()):
            errors.append(f"README.md: image path leaves the repository: {source!r}")
        elif not target.is_file():
            errors.append(f"README.md: image does not exist: {source}")
    if not sources:
        errors.append("README.md: no local images found")
    return errors, len(set(sources))


def check_css(value, location):
    errors = []
    # Local paint servers such as url(#gradient) are allowed; downloads are not.
    if re.search(r"@import\b", value, re.IGNORECASE):
        errors.append(f"{location}: CSS imports are not allowed")
    for match in CSS_URL.finditer(value):
        if not match.group(2).strip().startswith("#"):
            errors.append(f"{location}: CSS references a nonlocal resource")
    return errors


def check_svg(path, root):
    errors = []
    location = str(path.relative_to(root))
    text = path.read_text(encoding="utf-8")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b|<\?xml-stylesheet\b", text, re.IGNORECASE):
        return [f"{location}: XML declarations for external content are not allowed"]
    try:
        svg = ET.fromstring(text)
    except ET.ParseError as error:
        return [f"{location}: invalid XML: {error}"]
    if svg.tag != f"{{{SVG_NAMESPACE}}}svg":
        errors.append(f"{location}: expected an SVG root with the SVG namespace")
    for node in svg.iter():
        tag = node.tag.rsplit("}", 1)[-1].casefold()
        if tag in {"script", "foreignobject"}:
            errors.append(f"{location}: <{tag}> is not allowed")
        if tag == "style":
            errors.extend(check_css("".join(node.itertext()), location))
        for attribute, value in node.attrib.items():
            name = attribute.rsplit("}", 1)[-1].casefold()
            if name.startswith("on"):
                errors.append(f"{location}: event handlers are not allowed")
            if name in {"href", "src"} and not value.strip().startswith("#"):
                errors.append(f"{location}: {name} must reference a local SVG fragment")
            errors.extend(check_css(value, location))
    return errors


def main():
    errors, image_count = check_readme(ROOT)
    svg_paths = sorted((ROOT / ".github" / "assets").rglob("*.svg"))
    if not svg_paths:
        errors.append(".github/assets: no SVG artwork found")
    total_bytes = sum(path.stat().st_size for path in svg_paths)
    if total_bytes >= SVG_BUDGET_BYTES:
        errors.append(
            f"SVG artwork uses {total_bytes:,} bytes; keep the total below "
            f"{SVG_BUDGET_BYTES:,} bytes"
        )
    for path in svg_paths:
        try:
            errors.extend(check_svg(path, ROOT))
        except (OSError, UnicodeError) as error:
            errors.append(f"{path.relative_to(ROOT)}: cannot read SVG: {error}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Profile valid: {image_count} local image sources, "
        f"{len(svg_paths)} SVGs, {total_bytes:,}/{SVG_BUDGET_BYTES:,} bytes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
