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
import unicodedata
import xml.etree.ElementTree as ET

from pixel_world import pixel_text, render_world

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(".github/assets")
LEGACY = (
    "hero.svg", "signal.svg", "footer.svg",
    "hero-dark.svg", "hero-light.svg", "hero-mobile-dark.svg", "hero-mobile-light.svg",
    "synex-dark.svg", "synex-light.svg", "dxforge-dark.svg", "dxforge-light.svg",
    "footer-dark.svg", "footer-light.svg",
)
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


def wrap_cells(value: str, width: int) -> list[str]:
    """Wrap monospaced copy, counting wide Unicode glyphs as two cells."""
    def cells(text: str) -> int:
        return sum(0 if unicodedata.combining(c) else
                   2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)

    result, line = [], ""
    for word in value.split():
        if line and cells(line + " " + word) <= width:
            line += " " + word
            continue
        if line:
            result.append(line)
            line = ""
        for char in word:
            if cells(line + char) > width:
                result.append(line)
                line = ""
            line += char
    if line:
        result.append(line)
    return result or [""]


def stepped_panel(x: int, y: int, width: int, height: int, color: str, step: int = 8) -> str:
    right, bottom = x + width, y + height
    return (f'<path d="M{x+2*step} {y}H{right-2*step}V{y+step}H{right-step}'
            f'V{y+2*step}H{right}V{bottom-2*step}H{right-step}V{bottom-step}'
            f'H{right-2*step}V{bottom}H{x+2*step}V{bottom-step}H{x+step}'
            f'V{bottom-2*step}H{x}V{y+2*step}H{x+step}V{y+step}H{x+2*step}Z" fill="{color}"/>')


def project_card(repo: dict, index: int, mobile: bool = False) -> str:
    w, pad = (480, 36) if mobile else (1000, 44)
    name_size, name_gap = (28, 36) if mobile else (34, 42)
    name_lines = textwrap.wrap(repo["name"], width=24 if mobile else 40,
                               break_long_words=True, break_on_hyphens=False)
    description = description_excerpt(repo["description"]) or "Code und weitere Informationen stehen im Repository."
    body_lines = wrap_cells(description, 28 if mobile else 60)
    body_size, body_gap = (23, 31) if mobile else (24, 32)
    body_y = 105 + (len(name_lines)-1)*name_gap + 42
    divider_y = body_y + (len(body_lines)-1)*body_gap + 30
    language_lines = wrap_cells(repo.get("language") or "Keine Hauptsprache", 28 if mobile else 36)
    # Metadata and the action stack on mobile; every row contributes to height.
    date_y = divider_y + 70 + (len(language_lines)-1)*29
    button_y = date_y + 22 if mobile else divider_y + 22
    h = (button_y + 82) if mobile else (date_y + 44)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(repo["name"])}</title>',
        f'<desc id="desc">{escape(clean_description(repo["description"]))} '
        f'{escape(repo.get("language") or "Keine Hauptsprache")}. {escape(date_label(repo["pushed_at"]))}. Repository öffnen.</desc>',
        '<g shape-rendering="crispEdges">',
        stepped_panel(4, 8, w-8, h-8, "#080f1d"),
        stepped_panel(0, 0, w, h-8, "#344969"),
        stepped_panel(4, 4, w-8, h-16, "#51627a"),
        stepped_panel(8, 8, w-16, h-24, "#10192e"),
        stepped_panel(12, 12, w-24, h-32, "#1a2641"),
        f'<path d="M24 4H{w-24}V8H24Z" fill="#8592a0"/>',
        f'<path d="M24 {h-20}H{w-24}V{h-16}H24Z" fill="#0c1426"/>',
        f'<path d="M{pad} {divider_y}H{w-pad}v2H{pad}Z" fill="#344969"/>',
        f'<path d="M{pad} {divider_y}h40v2H{pad}Z" fill="#82cbb9"/>',
    ]
    # Small fittings repeat the stone, timber and lantern palette of the island.
    for x, y in ((20,20), (w-26,20), (20,h-34), (w-26,h-34)):
        lines.append(f'<rect x="{x}" y="{y}" width="6" height="6" fill="#8592a0"/>')
        lines.append(f'<rect x="{x+2}" y="{y+2}" width="4" height="4" fill="#344969"/>')
    lines += [
        pixel_text(f"PROJEKT {index:02d}", pad, 35, 3, "#82cbb9"),
        f'<g transform="translate({w-74} 30)">',
        '<path d="M6 0H24V4H28V8H24V12H22V8H8V12H6V8H2V4H6Z" fill="#947368"/>',
        '<path d="M8 10H22V14H26V36H4V14H8Z" fill="#0c1426"/>',
        '<path d="M8 15H22V31H8Z" fill="#b0785b"/>',
        '<path d="M11 17H19V28H11Z" fill="#ffcc7f"/>',
        '<path d="M13 17H17V25H13Z" fill="#edf0d9"/>',
        '<path d="M6 32H24V36H6Z" fill="#947368"/>',
        '</g>', '</g>',
    ]
    for i, value in enumerate(name_lines):
        lines.append(svg_text(pad, 105+i*name_gap, value, name_size, "#edf0d9", 700, "monospace"))
    for i, value in enumerate(body_lines):
        lines.append(svg_text(pad, body_y+i*body_gap, value, body_size, "#c1ccda", family="monospace"))
    for i, value in enumerate(language_lines):
        lines.append(svg_text(pad, divider_y+38+i*29, value, 23 if mobile else 22, "#82cbb9", 700, "monospace"))
    lines.append(svg_text(pad, date_y, date_label(repo["pushed_at"]), 22 if mobile else 21, "#a9bdd8", family="monospace"))
    bx, bw = (pad, w-2*pad) if mobile else (w-pad-296, 296)
    lines += [
        '<g shape-rendering="crispEdges">',
        stepped_panel(bx, button_y, bw, 50, "#426c67", step=4),
        stepped_panel(bx+4, button_y+4, bw-8, 42, "#24474a", step=4),
        f'<path transform="translate({bx+bw-46} {button_y+15})" d="M14 0H18V4H22V8H26V12H22V16H18V20H14V12H0V8H14Z" fill="#b4e0ce"/>',
        '</g>',
        svg_text(bx+20, button_y+32, "Repository öffnen", 22, "#d3eedf", family="Arial,Helvetica,sans-serif"),
        '</svg>',
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
    text_fallback = []
    for index, repo in enumerate(repos, 1):
        rid, name, url = repo["id"], escape(repo["name"]), escape(repo["url"], quote=True)
        description = clean_description(repo["description"]) or "Code und weitere Informationen stehen im Repository."
        language = escape(repo.get("language") or "Keine Hauptsprache")
        alt = escape(f'Projekt {index:02d}: {repo["name"]}. {description_excerpt(description)} '
                     f'{repo.get("language") or "Keine Hauptsprache"}. {date_label(repo["pushed_at"])}. Repository öffnen.', quote=True)
        parts.append(
            f'<a href="{url}">\n  <picture>\n'
            f'    <source media="(max-width: 600px)" srcset="./.github/assets/projects/{rid}-mobile.svg">\n'
            f'    <img src="./.github/assets/projects/{rid}.svg" width="100%" alt="{alt}">\n'
            '  </picture>\n</a>'
        )
        text_fallback.append(
            f'<h3><a href="{url}">{name}</a></h3>\n'
            f'<p>{escape(description)}</p>\n'
            f'<p>{language} · {escape(date_label(repo["pushed_at"]))}</p>'
        )
    if text_fallback:
        parts.append('<details>\n<summary>Projektübersicht als Text</summary>\n\n'
                     + "\n\n".join(text_fallback) + '\n\n</details>')
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
