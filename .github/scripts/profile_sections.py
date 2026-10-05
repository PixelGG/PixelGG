"""Original SVG page bands for the pixel-world profile.

The illustrations use integer-coordinate primitives and the shared hand-drawn
pixel alphabet. All variable text stays escaped, selectable SVG text; the caller
supplies real Markdown links around the resulting images.
"""
from __future__ import annotations

from html import escape
import unicodedata

from pixel_world import pixel_text

BG = "#10192e"
PANEL = "#1a2641"
RAIL = "#344969"
MINT = "#82cbb9"
PAPER = "#edf0d9"
AMBER = "#ffcc7f"
BODY = "#c1ccda"
MUTED = "#a9bdd8"


def _wrap(value: str, width: int) -> list[str]:
    """Wrap arbitrary copy without truncating words or wide Unicode glyphs."""
    def cells(text: str) -> int:
        return sum(0 if unicodedata.combining(c) else
                   2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)
    result, line = [], ""
    for word in str(value).split():
        if line and cells(line + " " + word) <= width:
            line += " " + word
            continue
        if line:
            result.append(line)
            line = ""
        for char in word:
            if line and cells(line + char) > width:
                result.append(line)
                line = ""
            line += char
    if line:
        result.append(line)
    return result or [""]


def _text(x: int, y: int, value: str, size: int = 24,
          color: str = BODY, weight: int = 400) -> str:
    return (f'<text x="{x}" y="{y}" font-family="monospace" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}">'
            f'{escape(str(value))}</text>')


def _rect(x: int, y: int, w: int, h: int, fill: str) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'


def _start(width: int, height: int, title: str, desc: str,
           rails: bool = True) -> list[str]:
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(desc)}</desc>',
        _rect(0, 0, width, height, BG),
    ]
    if rails:
        out += [
            _rect(8, 0, 4, height, RAIL),
            _rect(12, 0, 4, height, PANEL),
            _rect(width - 12, 0, 4, height, RAIL),
            _rect(width - 16, 0, 4, height, PANEL),
        ]
    return out


def _end(parts: list[str]) -> str:
    return "\n".join(parts + ["</svg>"]) + "\n"


def _heading(label: str, x: int, y: int, scale: int = 4) -> str:
    return ('<g shape-rendering="crispEdges">'
            + pixel_text(label, x, y + 3, scale, PANEL)
            + pixel_text(label, x, y, scale, PAPER)
            + '</g>')


def _workbench(x: int, y: int) -> str:
    """A small, original workshop still life: terminal, mug and seedling."""
    parts = [f'<g transform="translate({x} {y})" shape-rendering="crispEdges">']
    # Quiet wall recess and shelf, kept flat so this reads as part of the page.
    for rect in [
        (4, 18, 188, 120, PANEL), (12, 10, 172, 8, PANEL),
        (0, 134, 200, 8, "#0b1324"),
        (16, 114, 170, 8, "#947368"), (20, 122, 162, 8, "#594857"),
        (26, 130, 10, 38, "#594857"), (164, 130, 10, 38, "#594857"),
        (26, 130, 4, 34, "#947368"), (164, 130, 4, 34, "#947368"),
        (34, 40, 92, 58, "#344969"), (38, 36, 84, 4, "#51627a"),
        (40, 46, 80, 42, "#0b1324"), (74, 98, 14, 12, "#51627a"),
        (62, 108, 40, 6, "#344969"),
        (48, 54, 6, 4, MINT), (58, 54, 28, 4, "#507f7b"),
        (54, 64, 44, 4, "#507f7b"), (48, 74, 26, 4, MINT),
        (80, 74, 10, 4, AMBER),
        (134, 96, 18, 18, "#b0785b"), (136, 98, 14, 12, AMBER),
        (152, 98, 8, 4, "#b0785b"), (156, 102, 4, 6, "#b0785b"),
        (152, 108, 8, 4, "#b0785b"),
        (164, 76, 14, 20, "#947368"), (160, 72, 22, 6, "#b39885"),
        (169, 54, 4, 20, "#507f7b"), (159, 56, 10, 8, "#507f7b"),
        (173, 48, 12, 8, MINT), (165, 48, 8, 8, "#507f7b"),
        (28, 16, 4, 8, AMBER), (24, 20, 12, 4, AMBER),
        (180, 36, 4, 4, "#51627a"),
    ]:
        parts.append(_rect(*rect))
    parts.append('</g>')
    return "".join(parts)


def render_intro(config: dict, mobile: bool = False) -> str:
    width, pad = (480, 36) if mobile else (1000, 44)
    name = str(config.get("name", ""))
    intro = " ".join(str(config.get("intro", "")).split())
    names = _wrap(name, 21 if mobile else 30)
    body = _wrap(intro, 27 if mobile else 43)
    name_y = 128
    body_y = name_y + (len(names) - 1) * 39 + 48
    height = body_y + (len(body) - 1) * 34 + 44
    height = max(height, 266 if not mobile else 268)
    parts = _start(width, height, "Die Werkstatt", f"{name}. {intro}")
    parts += [_heading("DIE WERKSTATT", pad, 38, 4),
              _rect(pad, 82, 44, 3, MINT)]
    for i, line in enumerate(names):
        parts.append(_text(pad, name_y + i * 39, line, 32, PAPER, 700))
    for i, line in enumerate(body):
        parts.append(_text(pad, body_y + i * 34, line))
    if not mobile:
        parts.append(_workbench(width - 254, 61))
    return _end(parts)


def render_section(count: int, mobile: bool = False) -> str:
    if type(count) is not int or count < 0:
        raise ValueError("Project count must be a nonnegative integer")
    width, pad = (480, 36) if mobile else (1000, 44)
    subtitle = ("1 öffentliches Projekt" if count == 1 else f"{count} öffentliche Projekte")
    if count == 0:
        copy = _wrap("Hier ist Platz für neue Projekte. Aktuell keine öffentlichen Projekte in der Auswahl.", 28) if mobile else [
            "Hier ist Platz für neue Projekte.", "Aktuell keine öffentlichen Projekte in der Auswahl."]
    else:
        copy = [subtitle, "Zuletzt aktualisierte zuerst."] if mobile else [
            subtitle + " · Zuletzt aktualisierte zuerst."]
    height = 113 + len(copy) * 31
    parts = _start(width, height, "Projekte", " ".join(copy))
    parts += [_rect(pad, 14, width - 2 * pad, 2, RAIL),
              _rect(pad, 14, 44, 2, MINT),
              _heading("PROJEKTE", pad, 43, 4)]
    for i, line in enumerate(copy):
        parts.append(_text(pad, 108 + i * 31, line, 22 if mobile else 23, MUTED))
    if not mobile and count:
        # A register count is functional: it changes with the live selection.
        parts.append(pixel_text(f"{count:02d}", width - pad - 72, 45, 5, MINT))
    return _end(parts)


def render_contact(config: dict, mobile: bool = False) -> str:
    width, pad = (480, 36) if mobile else (1000, 44)
    owner = str(config.get("owner", ""))
    copy = (_wrap("Eine Frage oder Idee? Schreib mir über ein GitHub-Issue.", 28) if mobile else
            ["Eine Frage oder Idee? Schreib mir über ein GitHub-Issue."])
    # The link is supplied by the surrounding Markdown, keeping GitHub's image
    # rendering compatible. The visible action names exactly that destination.
    button_y = 115 + len(copy) * 34
    height = button_y + 107
    parts = _start(width, height, "Lass uns reden", 
                   f"Eine Frage oder Idee? GitHub-Issue bei {owner}/{owner} öffnen.")
    parts += [_rect(pad, 26, width - 2 * pad, 2, RAIL),
              _rect(pad, 26, 44, 2, AMBER),
              _heading("LASS UNS REDEN", pad, 54, 4)]
    for i, line in enumerate(copy):
        parts.append(_text(pad, 122 + i * 34, line, 22 if mobile else 24))
    bw = width - 2 * pad if mobile else 400
    parts += [
        '<g shape-rendering="crispEdges">',
        f'<path d="M{pad+8} {button_y}H{pad+bw-8}v4h4v4h4v48h-4v4h-4v4H{pad+8}v-4h-4v-4h-4V{button_y+8}h4v-4h4Z" fill="#426c67"/>',
        _rect(pad + 8, button_y + 8, bw - 16, 48, "#24474a"),
        f'<path transform="translate({pad+bw-48} {button_y+23})" d="M12 0h4v4h4v4h4v4h-4v4h-4v4h-4v-8H0V8h12Z" fill="{MINT}"/>',
        '</g>',
        _text(pad + 22, button_y + 41, "GitHub-Issue öffnen", 25 if mobile else 26, PAPER),
    ]
    return _end(parts)


def render_nav(label: str, mobile: bool = False) -> str:
    """Render one half-row link: 500×100 desktop or 240×88 mobile."""
    labels = {"REPOSITORIES": "PROJEKTE", "KONTAKT": "KONTAKT"}
    if label not in labels:
        raise ValueError("Unknown navigation label")
    width, height = (240, 88) if mobile else (500, 100)
    visible = labels[label]
    scale = 3 if mobile else 4
    text_width = (len(visible) * 6 - 1) * scale
    x = (width - text_width) // 2 - 8
    y = 26 if mobile else 30
    parts = _start(width, height, visible.title(), f"Zum Bereich {visible.title()}", rails=False)
    edge = 8 if label == "REPOSITORIES" else width - 12
    inner = 12 if label == "REPOSITORIES" else width - 16
    parts += [_rect(edge, 0, 4, height, RAIL), _rect(inner, 0, 4, height, PANEL)]
    parts += [
        '<g shape-rendering="crispEdges">',
        _rect(16, 12, width - 32, height - 24, PANEL),
        _rect(20, 12, width - 40, 4, RAIL),
        _rect(20, height - 16, width - 40, 4, "#0b1324"),
        pixel_text(visible, x, y, scale, PAPER),
        f'<path transform="translate({x+text_width+14} {y+5})" d="M0 0h4v4h4v4h-4v4H0V8h-4V4H0Z" fill="{MINT}"/>',
        '</g>',
    ]
    return _end(parts)


def render_endcap(owner: str, mobile: bool = False) -> str:
    width, pad = (480, 36) if mobile else (1000, 44)
    owner_lines = _wrap(str(owner), 27 if mobile else 60)
    height = 114 + (len(owner_lines) - 1) * 29
    parts = _start(width, height, str(owner), f"GitHub-Profil von {owner}")
    parts.append(_rect(pad, 4, width - 2 * pad, 2, RAIL))
    for i, line in enumerate(owner_lines):
        parts.append(_text(pad, 48 + i * 29, line, 23, MUTED))
    # A quiet closing treeline, deliberately below the signature.
    parts.append('<g shape-rendering="crispEdges">')
    for x, h in [(width-144, 28), (width-122, 39), (width-94, 24), (width-70, 34), (width-46, 20)]:
        y = height - 20
        parts.append(_rect(x - 2, y - h // 2, 4, h // 2 + 6, "#344255"))
        parts.append(f'<path d="M{x-2} {y-h}h4v6h4v6h4v6h4v6h-28v-6h4v-6h4v-6h4Z" fill="#294251"/>')
    for x, y in [(width - 156, height - 63), (width - 70, height - 76), (width - 39, height - 55)]:
        parts.append(_rect(x, y, 3, 3, "#647b8f"))
    parts += [
        _rect(8, height - 8, width - 16, 4, RAIL),
        _rect(16, height - 4, width - 32, 4, PANEL),
        '</g>',
    ]
    return _end(parts)
