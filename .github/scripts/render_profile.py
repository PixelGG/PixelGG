#!/usr/bin/env python3
"""Draw PixelGG's profile assets. Python standard library; no network or packages."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / ".github" / "assets"


@dataclass(frozen=True)
class Palette:
    background: str
    panel: str
    ink: str
    muted: str
    line: str
    accent: str
    ghost: str


PALETTES = {
    "dark": Palette("#151719", "#1d2023", "#f3f0e9", "#a4a5a2", "#35393c", "#ff784f", "#25282b"),
    "light": Palette("#f2f0e9", "#e8e5dd", "#232629", "#62635f", "#ccc9c0", "#b83d1b", "#dfdcd4"),
}


def text(x: float, y: float, value: str, size: int, color: str,
         weight: int = 400, mono: bool = False, extra: str = "") -> str:
    family = "'Courier New',monospace" if mono else "Arial,Helvetica,sans-serif"
    return (f'<text x="{x:g}" y="{y:g}" fill="{color}" font-family="{family}" '
            f'font-size="{size}" font-weight="{weight}" {extra}>{escape(value)}</text>')


def rect(x: float, y: float, w: float, h: float, color: str, extra: str = "") -> str:
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{color}" {extra}/>'


def line(x1: float, y1: float, x2: float, y2: float, color: str, extra: str = "") -> str:
    return f'<path d="M{x1:g} {y1:g}L{x2:g} {y2:g}" stroke="{color}" fill="none" {extra}/>'


def svg(w: int, h: int, title: str, description: str, body: list[str]) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">\n'
            f'<title id="title">{escape(title)}</title>\n'
            f'<desc id="desc">{escape(description)}</desc>\n'
            + "\n".join(body) + "\n</svg>\n")


def pixel_mark(x: int, y: int, size: int, p: Palette) -> str:
    """An original seven-row P: orthogonal pixels with shallow extruded faces."""
    rows = ("11110", "11011", "11011", "11110", "11000", "11000", "11000")
    step, depth = size + 5, 7
    parts = []
    for row in range(7):
        for col in range(5):
            xx, yy = x + col * step, y + row * step
            parts.append(rect(xx, yy, size, size, p.ghost))
    colors = ("#ffad7d", "#ff9868", "#ff8354", "#f36c43", "#e35b35", "#ce4b2b", "#b93e23")
    for row, cells in enumerate(rows):
        for col, cell in enumerate(cells):
            if cell == "0":
                continue
            xx, yy = x + col * step, y + row * step
            delay = (row * 5 + col) * 18
            parts.append(f'<g class="tile" style="animation-delay:{delay}ms">')
            parts.append(f'<path d="M{xx+size} {yy}l{depth} {depth}v{size}l-{depth} -{depth}Z" fill="#87351f"/>')
            parts.append(f'<path d="M{xx} {yy+size}l{depth} {depth}h{size}l-{depth} -{depth}Z" fill="#a94126"/>')
            parts.append(rect(xx, yy, size, size, colors[row]))
            parts.append(line(xx+1, yy+1, xx+size-1, yy+1, "#ffe1bf", 'opacity=".55"'))
            parts.append("</g>")
    return "\n".join(parts)


def hero(p: Palette, mobile: bool = False) -> str:
    w, h = (480, 580) if mobile else (960, 480)
    margin = 28 if mobile else 48
    body = [
        "<style>.tile{animation:assemble 900ms cubic-bezier(.2,.8,.2,1) both}"
        "@keyframes assemble{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}"
        "@media(prefers-reduced-motion:reduce){.tile{animation:none}}</style>",
        rect(0, 0, w, h, p.background, 'rx="14"'),
        rect(margin, 34, 9, 9, p.accent),
        text(margin+20, 43, "MIKE / DEVELOPER", 13, p.muted, mono=True, extra='letter-spacing="1.4"'),
    ]
    if mobile:
        body += [
            text(26, 141, "PixelGG", 76, p.ink, 700, extra='letter-spacing="-5"'),
            rect(302, 128, 12, 12, p.accent),
            text(29, 194, "From pixels", 32, p.ink, extra='letter-spacing="-1"'),
            text(29, 234, "to systems.", 32, p.muted, extra='letter-spacing="-1"'),
            pixel_mark(160, 280, 25, p),
            line(28, 533, 452, 533, p.line),
            text(28, 556, "GAMES / INTERFACES / TOOLS", 12, p.muted, mono=True),
        ]
    else:
        body += [
            text(912, 43, "INDEPENDENT WORK / GERMANY", 12, p.muted, mono=True, extra='text-anchor="end"'),
            line(48, 72, 912, 72, p.line),
            text(43, 196, "PixelGG", 100, p.ink, 700, extra='letter-spacing="-6"'),
            rect(409, 180, 15, 15, p.accent),
            text(48, 270, "From pixels", 45, p.ink, extra='letter-spacing="-1.8"'),
            text(48, 323, "to systems.", 45, p.muted, extra='letter-spacing="-1.8"'),
            text(50, 371, "CODE. FORM. FUNCTION.", 12, p.muted, mono=True, extra='letter-spacing="1.8"'),
            pixel_mark(670, 120, 34, p),
            line(626, 112, 644, 112, p.muted), line(635, 103, 635, 121, p.muted),
            line(883, 393, 901, 393, p.muted), line(892, 384, 892, 402, p.muted),
            line(48, 426, 912, 426, p.line),
            text(48, 453, "GAME SYSTEMS", 13, p.muted, mono=True, extra='letter-spacing="1"'),
            text(386, 453, "UI ENGINEERING", 13, p.muted, mono=True, extra='letter-spacing="1"'),
            text(912, 453, "AUTOMATION", 13, p.muted, mono=True, extra='text-anchor="end" letter-spacing="1"'),
        ]
    return svg(w, h, "Mike / PixelGG — From pixels to systems.",
               "Eigene Pixel-P-Marke aus orangefarbenen, räumlich gezeichneten Kacheln. Game-Systeme, Oberflächen und Werkzeuge.", body)


def project(p: Palette, name: str) -> str:
    synex = name == "synex"
    body = [rect(0, 0, 960, 204, p.background, 'rx="12"'),
            text(34, 37, "01 / GAME SYSTEMS" if synex else "02 / UI ENGINEERING", 13, p.accent, 700, True, 'letter-spacing="1.4"'),
            text(30, 119, "SYNEX" if synex else "DXFORGE", 64, p.ink, 700, extra='letter-spacing="-2.5"'),
            text(34, 165, "FiveM Framework" if synex else "Lua Interface Library", 21, p.muted),
            line(517, 28, 517, 176, p.line)]
    if synex:
        # Abstract module illustration; not a screenshot or a status display.
        body += [line(583, 100, 882, 100, p.line, 'stroke-width="2"'),
                 line(733, 43, 733, 162, p.line, 'stroke-width="2"')]
        for x, y in ((574, 70), (844, 70), (703, 24), (703, 122)):
            body += [rect(x, y, 58, 58, p.panel, f'rx="6" stroke="{p.line}"'),
                     rect(x+21, y+21, 16, 16, p.muted)]
        body += [rect(686, 59, 94, 84, p.accent, 'rx="8"'),
                 text(733, 108, "S", 36, p.background, 700, extra='text-anchor="middle"')]
    else:
        body += [rect(612, 27, 258, 129, p.panel, f'rx="7" stroke="{p.line}"'),
                 rect(586, 49, 258, 129, p.background, f'rx="7" stroke="{p.muted}"'),
                 line(586, 74, 844, 74, p.line),
                 rect(600, 59, 7, 7, p.accent),
                 line(616, 62, 673, 62, p.line, 'stroke-width="3"'),
                 rect(600, 87, 50, 77, p.panel, 'rx="3"'),
                 line(609, 101, 639, 101, p.accent, 'stroke-width="3"'),
                 line(609, 115, 633, 115, p.line, 'stroke-width="3"'),
                 line(609, 129, 637, 129, p.line, 'stroke-width="3"'),
                 line(664, 96, 741, 96, p.muted, 'stroke-width="3"'),
                 rect(664, 109, 158, 6, p.panel, 'rx="3"'),
                 rect(664, 109, 108, 6, p.accent, 'rx="3"'),
                 rect(664, 132, 69, 28, p.accent, 'rx="4"'),
                 rect(743, 132, 79, 28, p.panel, 'rx="4"')]
    return svg(960, 204, "SYNEX — FiveM Framework" if synex else "DXForge — Lua Interface Library",
               "Abstrakte Illustration eines modularen Systems." if synex else
               "Abstrakte Illustration eigener UI-Bausteine; kein Produkt-Screenshot.", body)


def footer(p: Palette) -> str:
    return svg(960, 82, "PixelGG / Code und Gestaltung", "Einzelne Pixel. Eigene Systeme.", [
        line(0, 1, 960, 1, p.line),
        rect(0, 30, 10, 10, p.accent), rect(14, 30, 10, 10, p.accent), rect(0, 44, 10, 10, p.accent),
        text(40, 48, "PIXELGG", 16, p.ink, 700, True, 'letter-spacing="2"'),
        text(960, 48, "SMALL DETAILS. COMPLETE SYSTEMS.", 13, p.muted, mono=True, extra='text-anchor="end"'),
    ])


def build_assets() -> dict[str, str]:
    outputs = {}
    for theme, palette in PALETTES.items():
        outputs[f"hero-{theme}.svg"] = hero(palette)
        outputs[f"hero-mobile-{theme}.svg"] = hero(palette, mobile=True)
        for name in ("synex", "dxforge"):
            outputs[f"{name}-{theme}.svg"] = project(palette, name)
        outputs[f"footer-{theme}.svg"] = footer(palette)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check committed assets without writing files.")
    args = parser.parse_args()
    outputs = build_assets()
    stale = []
    if not args.check:
        ASSETS.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        path = ASSETS / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                stale.append(name)
        else:
            path.write_bytes(content.encode("utf-8"))
    if stale:
        print("Regenerate profile assets: " + ", ".join(stale))
        return 1
    total = sum(len(content.encode("utf-8")) for content in outputs.values())
    print(f"{'Checked' if args.check else 'Rendered'} {len(outputs)} SVGs ({total:,} bytes). No external packages or network.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
