#!/usr/bin/env python3
"""Render the complete profile from a validated public repository snapshot."""
from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
import tempfile
import os
import textwrap
import xml.etree.ElementTree as ET

from pixel_world import render_world

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(".github/assets")
LEGACY = (
    "hero.svg", "signal.svg", "footer.svg",
    "hero-dark.svg", "hero-light.svg", "hero-mobile-dark.svg", "hero-mobile-light.svg",
    "synex-dark.svg", "synex-light.svg", "dxforge-dark.svg", "dxforge-light.svg",
    "footer-dark.svg", "footer-light.svg",
)
COLORS = ("#68dbe1", "#b4a4ff", "#90d99b", "#f5c783")
OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


def clean_description(value: str) -> str:
    """Display metadata as plain text, with Markdown decoration removed."""
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("**", "").replace("__", "").replace(chr(96), "")
    return " ".join(value.split())


def validate(snapshot: dict, config: dict) -> list[dict]:
    owner = config.get("owner")
    if not isinstance(owner, str) or not OWNER.fullmatch(owner):
        raise ValueError("Invalid configured GitHub owner")
    if snapshot.get("schema_version") != 1 or snapshot.get("owner", "").casefold() != owner.casefold():
        raise ValueError("Snapshot owner or version does not match the configuration")
    try:
        stamp = datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("Snapshot needs a valid timezone-aware data timestamp") from None
    repos = snapshot.get("repositories")
    limit = config.get("project_limit", 6)
    if type(limit) is not int or not 1 <= limit <= 6:
        raise ValueError("project_limit must be an integer from 1 to 6")
    if not isinstance(repos, list) or len(repos) > limit:
        raise ValueError("Invalid repository selection")
    if not isinstance(config.get("name"), str) or not isinstance(config.get("intro"), str):
        raise ValueError("Profile identity and introduction must be text")
    seen = set()
    for repo in repos:
        if not isinstance(repo, dict):
            raise ValueError("Invalid repository data")
        rid, name = repo.get("id"), repo.get("name")
        if type(rid) is not int or rid <= 0 or rid in seen:
            raise ValueError("Repository identity must be unique")
        seen.add(rid)
        if not isinstance(name, str) or not REPO.fullmatch(name):
            raise ValueError("Invalid repository name")
        if repo.get("url") != f"https://github.com/{owner}/{name}":
            raise ValueError("Repository link is not canonical")
        if not isinstance(repo.get("description"), str):
            raise ValueError("Description must be text")
        if repo.get("language") is not None and not isinstance(repo["language"], str):
            raise ValueError("Invalid repository language")
        for field in ("stars", "forks"):
            if type(repo.get(field)) is not int or repo[field] < 0:
                raise ValueError("Invalid repository counters")
        if repo.get("pushed_at") is not None:
            try:
                pushed = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
                if pushed.tzinfo is None:
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise ValueError("Invalid repository date") from None
    return repos


def svg_text(x: int, y: int, content: str, size: int, color: str,
             weight: int = 400, family: str = "Arial,Helvetica,sans-serif") -> str:
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" font-family="{family}">{escape(content)}</text>')


def project_card(repo: dict, index: int, mobile: bool = False) -> str:
    w, h = (480, 112) if mobile else (1000, 104)
    accent = COLORS[(repo["id"] % 997) % len(COLORS)]
    max_chars = 24 if mobile else 36
    name_lines = textwrap.wrap(repo["name"], width=max_chars, break_long_words=True,
                               break_on_hyphens=True)
    # All allowed GitHub repository names remain visible, even at 100 characters.
    h += (len(name_lines) - 1) * (31 if mobile else 37)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(repo["name"])}</title>',
        '<desc id="desc">Automatisch erzeugter Projekteingang. Der vollständige Text und Link stehen auch in der README.</desc>',
        f'<path d="M8 0H{w-8}V4H{w-4}V8H{w}V{h-8}H{w-4}V{h-4}H{w-8}V{h}H8V{h-4}H4V{h-8}H0V8H4V4H8Z" fill="#111c34"/>',
        f'<path d="M8 1H{w-8}M1 8V{h-8}M{w-1} 8V{h-8}M8 {h-1}H{w-8}" stroke="#283753" fill="none"/>',
        f'<rect x="24" y="25" width="5" height="5" fill="{accent}"/>',
        svg_text(38, 31, f"PROJEKT {index:02d}", 13 if mobile else 14, accent, 700, "monospace"),
    ]
    start, size, gap = (72, 26, 31) if mobile else (75, 32, 37)
    for i, value in enumerate(name_lines):
        lines.append(svg_text(24, start+i*gap, value, size, "#edf3ff", 700, "monospace"))
    # Hand-drawn doorway: a visual continuation of the workshop world.
    x = w - (55 if mobile else 114)
    y = 36 if mobile else 20
    scale = 1 if mobile else 1.25
    lines.append(f'<g transform="translate({x} {y}) scale({scale})" shape-rendering="crispEdges">')
    lines += [
        '<path d="M0 10H5V5H10V0H28V5H33V10H38V45H0Z" fill="#344969"/>',
        '<path d="M7 12H12V7H26V12H31V45H7Z" fill="#0b1326"/>',
        f'<path d="M12 13H26V40H12Z" fill="{accent}"/>',
        '<path d="M12 13H17V40H12Z" fill="#f1f6ff" opacity=".3"/>',
        '<path d="M-5 45H43V49H-5Z" fill="#6c80a0"/>',
        '</g>', '</svg>',
    ]
    return "\n".join(lines) + "\n"


def date_label(value: str | None) -> str:
    if not value:
        return "Noch kein Push"
    return "Letzter Push " + datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y")


def description_excerpt(value: str, limit: int = 215) -> str:
    """Keep the overview compact without rewriting repository metadata."""
    value = clean_description(value)
    if len(value) <= limit:
        return value
    prefix = value[:limit + 1]
    boundary = prefix.rfind(" ")
    if boundary >= limit // 2:
        prefix = prefix[:boundary]
    return prefix[:limit].rstrip(" ,;:.-") + "…"


def readme(snapshot: dict, config: dict, repos: list[dict]) -> str:
    owner = config["owner"]
    base = f"https://github.com/{owner}"
    parts = [
        "<!-- Generated by .github/scripts/render_profile.py. Edit config.json or the renderer, not this file. -->",
        '<picture>\n  <source media="(max-width: 600px)" srcset="./.github/assets/world-mobile.svg">\n'
        '  <img src="./.github/assets/world.svg" width="100%" alt="PixelGG: eine animierte nächtliche Entwicklerinsel mit Werkstatt, Brücken, Bäumen und Wasserfall.">\n</picture>',
        f'<h2 align="center">{escape(config["name"])} / {escape(owner)}</h2>',
        f'<p align="center">{escape(config["intro"])}</p>',
        f'<p align="center"><a href="{base}?tab=repositories">Alle Repositories ↗</a> &nbsp; · &nbsp; '
        f'<a href="{base}/{owner}/issues/new">Kontakt aufnehmen ↗</a></p>',
        "## Auf der Werkbank",
        f'<p><strong>{len(repos):02d} {"Projekt" if len(repos) == 1 else "Projekte"}</strong>'
        ' &nbsp; / &nbsp; Öffentlich &amp; aktiv &nbsp; / &nbsp; Neueste Arbeit zuerst</p>',
    ]
    if not repos:
        parts.append("<p>Aktuell sind keine öffentlichen, aktiven Original-Repositories vorhanden.</p>")
    for index, repo in enumerate(repos, 1):
        rid, name, url = repo["id"], escape(repo["name"]), escape(repo["url"], quote=True)
        description = description_excerpt(repo["description"]) or "Code und weitere Informationen stehen im Repository."
        language = escape(repo.get("language") or "Keine Hauptsprache")
        # A single table cell keeps artwork, native text and actions together.
        # Native description text reflows on narrow GitHub profile columns.
        parts.append(
            '<table width="100%">\n<tr><td>\n'
            f'<a href="{url}">\n  <picture>\n'
            f'    <source media="(max-width: 600px)" srcset="./.github/assets/projects/{rid}-mobile.svg">\n'
            f'    <img src="./.github/assets/projects/{rid}.svg" width="100%" alt="Projekt {index:02d}: {name}. Repository öffnen.">\n'
            '  </picture>\n</a>\n'
            f'<p>{escape(description)}</p>\n'
            f'<p><code>{language}</code> &nbsp; · &nbsp; '
            f'<sub>{escape(date_label(repo["pushed_at"]))}</sub></p>\n'
            f'<p><a href="{url}"><strong>Repository öffnen ↗</strong></a></p>\n'
            '</td></tr>\n</table>'
        )
    parts += [
        f'<p align="right"><a href="{base}?tab=repositories">Alle Repositories ansehen →</a></p>',
        "---",
        f'<p align="center"><strong>Eine Idee oder eine Frage?</strong><br>'
        f'<a href="{base}/{owner}/issues/new">Lass uns darüber sprechen ↗</a></p>',
    ]
    return "\n\n".join(parts) + "\n"


def build_outputs(snapshot: dict, config: dict) -> dict[Path, str]:
    repos = validate(snapshot, config)
    outputs = {
        Path("README.md"): readme(snapshot, config, repos),
        ASSETS / "world.svg": render_world(repos, owner=config["owner"]),
        ASSETS / "world-mobile.svg": render_world(repos, owner=config["owner"], mobile=True),
    }
    for i, repo in enumerate(repos, 1):
        outputs[ASSETS / "projects" / f'{repo["id"]}.svg'] = project_card(repo, i)
        outputs[ASSETS / "projects" / f'{repo["id"]}-mobile.svg'] = project_card(repo, i, mobile=True)
    for path, content in outputs.items():
        if path.suffix == ".svg":
            ET.fromstring(content)
    return outputs


def obsolete_outputs(root: Path, outputs: dict[Path, str]) -> list[Path]:
    obsolete = [ASSETS / name for name in LEGACY if (root / ASSETS / name).exists()]
    directory = root / ASSETS / "projects"
    if directory.exists():
        obsolete += [file.relative_to(root) for file in directory.iterdir()
                     if re.fullmatch(r"\d+(?:-mobile)?\.svg", file.name)
                     and file.relative_to(root) not in outputs]
    return obsolete


def apply_outputs(root: Path, outputs: dict[Path, str], check: bool = False) -> bool:
    obsolete = obsolete_outputs(root, outputs)
    changed = [path for path, content in outputs.items()
               if not (root/path).is_file() or (root/path).read_bytes() != content.encode("utf-8")]
    if check:
        if changed or obsolete:
            print("Generated files differ: " + ", ".join(map(str, changed+obsolete)))
            return False
        return True
    # Every asset has already been rendered and XML-validated. Each write is atomic.
    for relative in changed:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
                temp_name = temp.name
                temp.write(outputs[relative].encode("utf-8"))
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_name, destination)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
    for relative in obsolete:
        (root / relative).unlink()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        config = json.loads((ROOT / ".github/profile/config.json").read_text(encoding="utf-8"))
        snapshot = json.loads((ROOT / ".github/profile/public-repos.json").read_text(encoding="utf-8"))
        outputs = build_outputs(snapshot, config)
        if not apply_outputs(ROOT, outputs, args.check):
            return 1
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
        print(f"Profile rendering failed: {error}")
        return 1
    print(f"{'Checked' if args.check else 'Rendered'} README and {len(outputs)-1} SVGs from {len(snapshot['repositories'])} public projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
