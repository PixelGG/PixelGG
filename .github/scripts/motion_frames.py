"""Sample the profile's original SVG artwork into deterministic static frames.

GitHub receives encoded GIF frames, so motion never depends on SVG CSS support.
Every pose repeats after six seconds. The source SVGs remain the web artwork and
the reduced-motion alternative; this module has no raster or browser dependency.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


SAMPLER_VERSION = 1
LOOP_SECONDS = 6.0
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
_DELAY = re.compile(r"(?:^|;)\s*animation-delay\s*:\s*([-+\d.]+)(ms|s)\s*(?:;|$)")


@lru_cache(maxsize=1)
def motion_recipe() -> str:
    """Match the encoder fingerprint so motion-only edits invalidate image URLs."""
    scripts = Path(__file__).resolve().parent
    paths = [scripts / 'render_motion.cjs', scripts / 'motion_frames.py',
             scripts.parent / 'profile/package-lock.json']
    return sha256(b''.join(path.read_bytes() for path in paths)).hexdigest()


def has_motion(svg: str) -> bool:
    """Only export illustrations that actually contain an animated element."""
    animated = set(re.findall(r'\.([\w-]+)\s*\{\s*animation:', svg))
    return any(animated.intersection(value.split())
               for value in re.findall(r'\bclass="([^"]+)"', svg))


def _phase(time: float, period: float, delay: float = 0.0) -> float:
    return ((time - delay) % period) / period


def _pulse(phase: float) -> float:
    return (1.0 - math.cos(math.tau * phase)) / 2.0


def _move(element: ET.Element, x: float = 0, y: float = 0) -> None:
    """Keep original placement/scaling, adding motion in the parent's units."""
    transform = f"translate({round(x)} {round(y)})"
    original = element.get("transform")
    element.set("transform", transform + (f" {original}" if original else ""))


def _opacity(element: ET.Element, opacity: float) -> None:
    # These classes own opacity in the original CSS. Replace their static
    # fallback (including the ember's zero), leaving ancestor opacity intact.
    element.set("opacity", f"{max(0.0, min(1.0, opacity)):.4f}")


def _rise(element: ET.Element, phase: float, x: int, y: int, peak: float) -> None:
    _move(element, x * phase, 3 + (y - 3) * phase)
    # Fade at both ends: the positional reset is invisible at the loop seam.
    _opacity(element, peak * math.sin(math.pi * phase) ** 1.25)


def _firefly(element: ET.Element, phase: float, distance: int = 4) -> None:
    _move(element, distance * math.sin(math.tau * phase), -distance * _pulse(phase))
    _opacity(element, 0.15 + 0.75 * _pulse(phase))


def _water_tile(element: ET.Element) -> None:
    """Extend one repeat above the clip so the downward wrap has no gap."""
    children = list(element)
    if not children:
        return
    min_y = min(float(child.get("y", "0")) for child in children)
    for child in children:
        y = float(child.get("y", "0"))
        if y < min_y + 18:
            extra = deepcopy(child)
            extra.set("y", f"{y - 18:g}")
            element.insert(0, extra)


def sample_frame(svg: str, time: float) -> str:
    """Return one static, namespaced SVG pose; ``time`` is seconds.

    CSS animation delays stagger stars, smoke and fireflies. Existing nested
    viewBoxes, clipping, transforms, static opacity and drawing order survive.
    No style element, animation declaration or SMIL animation is returned.
    """
    if not math.isfinite(time):
        raise ValueError("Frame time must be finite")
    # Round phase input so t and t + 6 serialize identically, including decimal
    # delays and period 1.2 which are not exactly representable as floats.
    time = round(time % LOOP_SECONDS, 9)
    root = ET.fromstring(svg)
    for parent in root.iter():
        for child in list(parent):
            if child.tag.rsplit("}", 1)[-1] in {"style", "animate", "animateTransform", "set"}:
                parent.remove(child)

    for element in root.iter():
        style = element.attrib.pop("style", "")
        match = _DELAY.search(style)
        delay = float(match.group(1)) / (1000 if match.group(2) == "ms" else 1) if match else 0.0
        # Preserve any future static inline presentation declarations.
        static_style = ";".join(decl.strip() for decl in style.split(";")
                                if decl.strip() and not decl.split(":", 1)[0].strip().startswith("animation"))
        if static_style:
            element.set("style", static_style)
        element.attrib.pop("animation-delay", None)
        classes = set(element.get("class", "").split())
        phase = _phase(time, LOOP_SECONDS, delay)

        if "cloud" in classes:
            _move(element, 4 * math.sin(math.tau * phase))
        elif "cloud-back" in classes:
            _move(element, -4 * math.sin(math.tau * phase))
        elif "water" in classes:
            _water_tile(element)
            _move(element, y=math.floor(_phase(time, 1.2) * 18 + 1e-8))
        elif "star" in classes:
            _opacity(element, 0.25 + 0.75 * _pulse(_phase(time, 3, delay)))
        elif "firefly" in classes:
            _firefly(element, phase)
        elif "smoke" in classes:
            _rise(element, phase, -8, -18, 0.6)
        elif "lamplight" in classes or "pc-lantern" in classes:
            _opacity(element, 0.6 + 0.4 * _pulse(_phase(time, 3, delay)))
        elif "traveler" in classes:
            _move(element, y=-1 if 0.7 <= phase < 0.9 else 0)
        elif "pc-ember" in classes:
            visible = max(0.0, 1.0 - abs(phase - 0.7) / 0.16)
            _opacity(element, 0.85 * visible)
            _move(element, y=-4 * visible)
        elif "pg-intro-cursor" in classes:
            blink = _phase(time, 3)
            _opacity(element, 0 if 0.58 <= blink < 0.85 else 1)
        elif classes & {"pg-intro-steam-a", "pg-intro-steam-b"}:
            steam = _phase(time, 3, -1.5 if "pg-intro-steam-b" in classes else 0)
            _rise(element, steam, -4, -14, 0.55)
        elif classes & {"pg-intro-firefly-a", "pg-intro-firefly-b", "pg-endcap-firefly-a", "pg-endcap-firefly-b"}:
            offset = -3 if any(name.endswith("-b") for name in classes) else 0
            _firefly(element, _phase(time, LOOP_SECONDS, offset), 5)
        elif classes & {"pg-nav-projects-chevron", "pg-nav-contact-chevron"}:
            nav = _phase(time, 2)
            _move(element, y=4 if 0.65 <= nav < 0.88 else 0)

    return ET.tostring(root, encoding="unicode", short_empty_elements=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--frames", type=int, default=48)
    parser.add_argument("--duration", type=float, default=LOOP_SECONDS)
    parser.add_argument("--list", action="store_true", help="List animated SVGs in a directory")
    args = parser.parse_args()
    if args.list:
        print(json.dumps([str(p.resolve()) for p in sorted(args.path.rglob('*.svg'))
                          if has_motion(p.read_text(encoding='utf-8'))]))
        return
    if not 2 <= args.frames <= 240:
        parser.error("--frames must be between 2 and 240")
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration must be positive and finite")
    svg = args.path.read_text(encoding="utf-8")
    root = ET.fromstring(svg)
    payload = {
        "width": int(float(root.attrib["width"])),
        "height": int(float(root.attrib["height"])),
        "frames": [sample_frame(svg, i * args.duration / args.frames) for i in range(args.frames)],
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
