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
    parts += [
        '<g class="pg-intro-cursor">' + _rect(80, 74, 10, 4, AMBER) + '</g>',
        '<g class="pg-intro-steam-a" opacity=".3">'
        + _rect(139, 83, 3, 7, MUTED) + _rect(142, 79, 3, 5, MUTED) + '</g>',
        '<g class="pg-intro-steam-b" opacity=".2">'
        + _rect(147, 85, 3, 5, MUTED) + _rect(144, 81, 3, 5, MUTED) + '</g>',
        '</g>',
    ]
    return "".join(parts)


def _chapter(number: str, label: str, x: int, y: int, color: str = MINT) -> str:
    """Small shared chapter marker; headings and copy keep their own rhythm."""
    return ('<g shape-rendering="crispEdges">'
            + pixel_text(number, x, y, 2, color)
            + _rect(x + 34, y + 1, 2, 12, RAIL)
            + pixel_text(label, x + 50, y, 2, MUTED)
            + '</g>')


def render_intro(config: dict, mobile: bool = False) -> str:
    width, pad = (480, 36) if mobile else (1000, 44)
    name = str(config.get("name", ""))
    intro = " ".join(str(config.get("intro", "")).split())
    names = _wrap(name, 19 if mobile else 25)
    body = _wrap(intro, 27 if mobile else 43)
    name_y = 114
    body_y = name_y + (len(names) - 1) * 44 + 50
    height = max(body_y + (len(body) - 1) * 34 + 44, 270)
    parts = _start(width, height, "Die Werkstatt", f"{name}. {intro}")
    parts += [
        """<style>
        @keyframes pg-intro-cursor-blink{0%,58%,100%{opacity:1}59%,85%{opacity:0}}
        @keyframes pg-intro-steam-rise{0%{opacity:0;transform:translate(0,3px)}25%{opacity:.3}100%{opacity:0;transform:translate(-3px,-12px)}}
        @keyframes pg-intro-firefly-drift{0%,100%{opacity:.22;transform:translate(0,0)}45%{opacity:.7}65%{opacity:.4;transform:translate(3px,-4px)}}
        .pg-intro-cursor{animation:pg-intro-cursor-blink 3.8s steps(1,end) infinite}
        .pg-intro-steam-a{animation:pg-intro-steam-rise 5.5s steps(6,end) infinite}
        .pg-intro-steam-b{animation:pg-intro-steam-rise 5.5s steps(6,end) -2.75s infinite}
        .pg-intro-firefly-a{animation:pg-intro-firefly-drift 8s steps(5,end) infinite}
        .pg-intro-firefly-b{animation:pg-intro-firefly-drift 10s steps(5,end) -4s infinite}
        @media(prefers-reduced-motion:reduce){.pg-intro-cursor,.pg-intro-steam-a,.pg-intro-steam-b,.pg-intro-firefly-a,.pg-intro-firefly-b{animation:none!important}}
        </style>""",
        _chapter("01", "DIE WERKSTATT", pad, 36),
    ]
    for i, line in enumerate(names):
        parts.append(_text(pad, name_y + i * 44, line, 34 if mobile else 40, PAPER, 700))
    for i, line in enumerate(body):
        parts.append(_text(pad, body_y + i * 34, line))
    if not mobile:
        parts.append(_workbench(width - 254, max(50, (height - 168) // 2)))
        parts += [
            '<g class="pg-intro-firefly-a" opacity=".5">'
            + _rect(width - 286, 109, 3, 3, MINT) + '</g>',
            '<g class="pg-intro-firefly-b" opacity=".3">'
            + _rect(width - 61, 64, 3, 3, AMBER) + '</g>',
        ]
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
    height = 146 + (len(copy) - 1) * 31 + 22
    parts = _start(width, height, "Projekte", " ".join(copy))
    parts += [_rect(pad, 6, width - 2 * pad, 2, RAIL),
              _rect(pad, 6, 44, 2, MINT),
              _chapter("02", "AUS DER WERKSTATT", pad, 36),
              _heading("PROJEKTE", pad, 72, 4)]
    for i, line in enumerate(copy):
        parts.append(_text(pad, 140 + i * 31, line, 22 if mobile else 23, MUTED))
    if not mobile and count:
        # This register reports the current public selection, not a fixed claim.
        parts.append(pixel_text(f"{count:02d}", width - pad - 72, 68, 5, MINT))
        parts.append(_rect(width - pad - 72, 110, 66, 2, RAIL))
    return _end(parts)


def render_contact(config: dict, mobile: bool = False) -> str:
    width, pad = (480, 36) if mobile else (1000, 44)
    owner = str(config.get("owner", ""))
    copy = (_wrap("Eine Frage oder Idee? Schreib mir über ein GitHub-Issue.", 28) if mobile else
            ["Eine Frage oder Idee? Schreib mir über ein GitHub-Issue."])
    # The surrounding Markdown supplies the link, since images on GitHub do
    # not expose the embedded SVG's link or hover targets.
    button_y = 182 + (len(copy) - 1) * 34
    height = button_y + 105
    parts = _start(width, height, "Lass uns reden",
                   f"Eine Frage oder Idee? GitHub-Issue bei {owner}/{owner} öffnen.")
    parts += [_rect(pad, 20, width - 2 * pad, 2, RAIL),
              _rect(pad, 20, 44, 2, AMBER),
              _chapter("03", "KONTAKT", pad, 49, AMBER),
              _heading("LASS UNS REDEN", pad, 83, 4)]
    for i, line in enumerate(copy):
        parts.append(_text(pad, 158 + i * 34, line, 22 if mobile else 24))
    bw = width - 2 * pad if mobile else 400
    parts += [
        '<g class="pg-contact-button" shape-rendering="crispEdges">',
        f'<path d="M{pad+8} {button_y+4}H{pad+bw-8}v4h4v4h4v48h-4v4h-4v4H{pad+8}v-4h-4v-4h-4V{button_y+12}h4v-4h4Z" fill="#0b1324"/>',
        f'<path d="M{pad+8} {button_y}H{pad+bw-8}v4h4v4h4v48h-4v4h-4v4H{pad+8}v-4h-4v-4h-4V{button_y+8}h4v-4h4Z" fill="#426c67"/>',
        f'<rect class="pg-contact-fill" x="{pad+8}" y="{button_y+8}" width="{bw-16}" height="48" fill="#24474a"/>',
        _rect(pad + 12, button_y + 4, bw - 24, 3, "#689c8d"),
        f'<g transform="translate({pad+bw-48} {button_y+23})"><path class="pg-contact-arrow" d="M12 0h4v4h4v4h4v4h-4v4h-4v4h-4v-8H0V8h12Z" fill="{MINT}"/></g>',
        _text(pad + 22, button_y + 41, "GitHub-Issue öffnen", 25 if mobile else 26, PAPER),
        '</g>',
    ]
    return _end(parts)


def render_nav(label: str, mobile: bool = False) -> str:
    """One half-row link with a stepped inset and a real downward chevron."""
    labels = {"REPOSITORIES": "PROJEKTE", "KONTAKT": "KONTAKT"}
    if label not in labels:
        raise ValueError("Unknown navigation label")
    width, height = (240, 88) if mobile else (500, 100)
    visible = labels[label]
    scale = 3 if mobile else 4
    text_width = (len(visible) * 6 - 1) * scale
    y = (height - 7 * scale) // 2 - 1
    parts = _start(width, height, visible.title(), f"Zum Bereich {visible.title()}", rails=False)
    edge = 8 if label == "REPOSITORIES" else width - 12
    inner = 12 if label == "REPOSITORIES" else width - 16
    key = "projects" if label == "REPOSITORIES" else "contact"
    anim = f"pg-nav-{key}-step"
    klass = f"pg-nav-{key}-chevron"
    left, right = (24, width - 8) if label == "REPOSITORIES" else (8, width - 24)
    x = (left + right - text_width - 36) // 2
    top, bottom = 13, height - 15
    panel = f"M{left+8} {top}H{right-8}v4h4v4h4V{bottom-8}h-4v4h-4v4H{left+8}v-4h-4v-4h-4V{top+8}h4v-4h4Z"
    inset = f"M{left+10} {top+5}H{right-10}v3h5V{bottom-8}h-5v3H{left+10}v-3h-5V{top+8}h5Z"
    parts += [
        f'<style>@keyframes {anim}{{0%,70%,100%{{transform:translateY(0)}}80%,90%{{transform:translateY(3px)}}}}'
        f'.{klass}{{animation:{anim} 5.5s steps(1,end) infinite}}'
        f'@media(prefers-reduced-motion:reduce){{.{klass}{{animation:none!important}}}}</style>',
        _rect(edge, 0, 4, height, RAIL), _rect(inner, 0, 4, height, PANEL),
        '<g class="pg-nav-panel" shape-rendering="crispEdges">',
        f'<path d="{panel}" transform="translate(0 4)" fill="#0b1324"/>',
        f'<path d="{panel}" fill="{RAIL}"/>',
        f'<path class="pg-nav-fill" d="{inset}" fill="{PANEL}"/>',
        _rect(left + 12, top + 4, right - left - 24, 2, "#51627a"),
        pixel_text(visible, x, y, scale, PAPER),
        f'<g transform="translate({x+text_width+16} {y+(7*scale-12)//2})">',
        f'<g class="{klass}">',
        '<path d="M0 0h4v4h4v4h4V4h4V0h4v4h-4v4h-4v4H8V8H4V4H0Z" '
        f'fill="{MINT}"/>',
        '</g></g></g>',
    ]
    return _end(parts)


def render_endcap(owner: str, mobile: bool = False) -> str:
    width, pad = (480, 36) if mobile else (1000, 44)
    owner_lines = _wrap(str(owner), 27 if mobile else 60)
    height = 132 + (len(owner_lines) - 1) * 29
    parts = _start(width, height, str(owner), f"GitHub-Profil von {owner}", rails=False)
    # Replace the rectangular background with an actual stepped silhouette.
    # Transparent outside corners make the page end visibly, in either theme.
    parts[-1] = (f'<path d="M0 0H{width}V{height-28}h-8v8h-8v8h-8v8H24v-8h-8v-8H8v-8H0Z" fill="{BG}"/>')
    parts += [
        """<style>
        @keyframes pg-endcap-firefly-drift{0%,100%{opacity:.25;transform:translate(0,0)}40%{opacity:.7}65%{opacity:.35;transform:translate(3px,-4px)}}
        .pg-endcap-firefly-a{animation:pg-endcap-firefly-drift 9s steps(5,end) infinite}
        .pg-endcap-firefly-b{animation:pg-endcap-firefly-drift 11s steps(5,end) -4s infinite}
        @media(prefers-reduced-motion:reduce){.pg-endcap-firefly-a,.pg-endcap-firefly-b{animation:none!important}}
        </style>""",
        _rect(pad, 4, width - 2 * pad, 2, RAIL),
    ]
    for i, line in enumerate(owner_lines):
        parts.append(_text(pad, 48 + i * 29, line, 23, MUTED))
    parts.append('<g shape-rendering="crispEdges">')
    for x, h in [(width-150, 28), (width-128, 39), (width-100, 24), (width-76, 34), (width-52, 20)]:
        y = height - 25
        parts.append(_rect(x - 2, y - h // 2, 4, h // 2 + 6, "#344255"))
        parts.append(f'<path d="M{x-2} {y-h}h4v6h4v6h4v6h4v6h-28v-6h4v-6h4v-6h4Z" fill="#294251"/>')
    parts += [
        '<g class="pg-endcap-firefly-a" opacity=".45">'
        + _rect(width - 167, height - 65, 3, 3, MINT) + '</g>',
        '<g class="pg-endcap-firefly-b" opacity=".35">'
        + _rect(width - 66, height - 82, 3, 3, AMBER) + '</g>',
        f'<path d="M10 0V{height-30}h8v8h8v8H{width-26}v-8h8v-8h8V0" fill="none" stroke="{RAIL}" stroke-width="4"/>',
        f'<path d="M14 0V{height-34}h8v8h8v8H{width-30}v-8h8v-8h8V0" fill="none" stroke="{PANEL}" stroke-width="4"/>',
        '</g>',
    ]
    return _end(parts)
