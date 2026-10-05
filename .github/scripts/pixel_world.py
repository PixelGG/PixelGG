"""An original, dependency-free pixel landscape for PixelGG's profile.

The SVG is assembled from integer-coordinate drawing primitives.  The islands,
workshop, lettering and sprites are drawn here, rather than fetched from an art
pack or a rendering service.  All animation is declarative and optional.
"""

from __future__ import annotations

from html import escape
import random


_LETTERS = {
    "A": ("01110", "11011", "11011", "11111", "11011", "11011", "11011"),
    "B": ("11110", "11011", "11011", "11110", "11011", "11011", "11110"),
    "C": ("01111", "11000", "11000", "11000", "11000", "11000", "01111"),
    "D": ("11110", "11011", "11011", "11011", "11011", "11011", "11110"),
    "E": ("11111", "11000", "11000", "11110", "11000", "11000", "11111"),
    "F": ("11111", "11000", "11000", "11110", "11000", "11000", "11000"),
    "G": ("01111", "11000", "11000", "11011", "11011", "11011", "01111"),
    "H": ("11011", "11011", "11011", "11111", "11011", "11011", "11011"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "11010", "11010", "01100"),
    "K": ("11011", "11011", "11110", "11100", "11110", "11011", "11011"),
    "L": ("11000", "11000", "11000", "11000", "11000", "11000", "11111"),
    "M": ("10001", "11011", "11111", "10101", "10101", "10001", "10001"),
    "N": ("11001", "11001", "11101", "11111", "11011", "11001", "11001"),
    "O": ("01110", "11011", "11011", "11011", "11011", "11011", "01110"),
    "P": ("11110", "11011", "11011", "11110", "11000", "11000", "11000"),
    "Q": ("01110", "11011", "11011", "11011", "11011", "01110", "00011"),
    "R": ("11110", "11011", "11011", "11110", "11100", "11010", "11011"),
    "S": ("01111", "11000", "11000", "01110", "00011", "00011", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("11011", "11011", "11011", "11011", "11011", "11011", "01110"),
    "V": ("11011", "11011", "11011", "11011", "11011", "01110", "00100"),
    "W": ("10001", "10001", "10101", "10101", "11111", "11011", "10001"),
    "X": ("11011", "11011", "01110", "00100", "01110", "11011", "11011"),
    "Y": ("11011", "11011", "01110", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00011", "00110", "00100", "01100", "11000", "11111"),
    "0": ("01110", "11011", "11011", "11011", "11011", "11011", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "11011", "00011", "00110", "01100", "11000", "11111"),
    "3": ("11110", "00011", "00011", "01110", "00011", "00011", "11110"),
    "4": ("11011", "11011", "11011", "11111", "00011", "00011", "00011"),
    "5": ("11111", "11000", "11000", "11110", "00011", "00011", "11110"),
    "6": ("01110", "11000", "11000", "11110", "11011", "11011", "01110"),
    "7": ("11111", "00011", "00011", "00110", "00110", "01100", "01100"),
    "8": ("01110", "11011", "11011", "01110", "11011", "11011", "01110"),
    "9": ("01110", "11011", "11011", "01111", "00011", "00011", "01110"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
    " ": ("00000",) * 7,
}


def pixel_text(text: str, x: float, y: float, scale: float, color: str) -> str:
    """Draw the shared pixel alphabet as one dependency-free SVG path."""
    d = []
    for i, char in enumerate(text.upper()):
        for row, cells in enumerate(_LETTERS.get(char, _LETTERS[" "])):
            for col, bit in enumerate(cells):
                if bit == "1":
                    px, py = x + (i * 6 + col) * scale, y + row * scale
                    d.append(f"M{px:g} {py:g}h{scale:g}v{scale:g}h{-scale:g}z")
    return f'<path d="{"".join(d)}" fill="{color}"/>'


def render_world(repositories: list[dict], owner: str = "PixelGG", mobile: bool = False) -> str:
    """Return a self-contained SVG; ``repositories`` supplies waypoint count.

    The mobile option crops unimportant outer sky, keeping the entire workshop,
    wordmark and waterfall.  The normal artwork also scales without cropping.
    No repository names, descriptions, secrets or network resources are embedded.
    """
    p: list[str] = []
    rng = random.Random(73191)
    count = len(repositories)
    label = escape(owner, quote=True)

    def add(value: str) -> None:
        p.append(value)

    def rect(x: float, y: float, w: float, h: float, color: str, attrs: str = "") -> None:
        add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{color}"{attrs}/>')

    def poly(points: list[tuple[int, int]], color: str, attrs: str = "") -> None:
        coords = " ".join(f"{x},{y}" for x, y in points)
        add(f'<polygon points="{coords}" fill="{color}"{attrs}/>')

    def line(points: list[tuple[int, int]], color: str, width: int = 1, attrs: str = "") -> None:
        coords = " ".join(f"{x},{y}" for x, y in points)
        add(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}"{attrs}/>')

    def lettering(text: str, x: float, y: float, scale: float, color: str) -> None:
        # A single path keeps the wordmark compact and independent of web fonts.
        add(pixel_text(text, x, y, scale, color))

    def pine(x: int, y: int, size: float = 1, tint: str = "main") -> None:
        colors = {"main": ("#233f53", "#315c64", "#4a7a78"),
                  "back": ("#25354c", "#304760", "#3e5770"),
                  "blue": ("#244b59", "#386c70", "#619089")}[tint]
        add(f'<g transform="translate({x} {y}) scale({size:g})">')
        rect(-2, -22, 5, 24, "#5c4750")
        rect(1, -19, 2, 19, "#806363")
        poly([(-19, -9), (-13, -16), (-16, -16), (-9, -25), (-12, -25), (-5, -35),
              (-7, -35), (0, -47), (7, -35), (5, -35), (12, -25), (9, -25),
              (16, -16), (13, -16), (19, -9)], colors[0])
        poly([(-19, -9), (-13, -16), (-16, -16), (-9, -25), (-12, -25), (-5, -35),
              (-7, -35), (0, -47), (0, -9)], colors[1])
        for xx, yy, ww in [(-6, -34, 5), (-10, -24, 7), (-14, -15, 10), (-18, -9, 12)]:
            rect(xx, yy, ww, 1, colors[2])
        rect(3, -26, 2, 1, colors[1])
        rect(6, -16, 3, 1, colors[1])
        add('</g>')

    def grass(x: int, y: int, color: str = "#75a18b") -> None:
        rect(x, y - 2, 1, 3, color)
        rect(x - 2, y - 1, 1, 1, color)
        rect(x + 2, y - 1, 1, 2, color)

    def lantern(x: int, y: int) -> None:
        rect(x, y - 18, 2, 19, "#6c535c")
        rect(x - 5, y - 18, 7, 2, "#967074")
        rect(x - 5, y - 16, 1, 3, "#c1947e")
        rect(x - 8, y - 14, 7, 9, "#2b283b")
        rect(x - 7, y - 13, 5, 6, "#b0785b")
        rect(x - 6, y - 12, 3, 5, "#ffcc7f", ' class="lamplight"')
        rect(x - 7, y - 14, 5, 1, "#d69b6d")
        rect(x - 7, y - 6, 5, 1, "#926959")

    def waypoint(x: int, y: int, number: int) -> None:
        rect(x, y - 19, 2, 20, "#947368")
        rect(x - 2, y - 18, 17, 10, "#392f48")
        rect(x - 2, y - 18, 17, 1, "#a98c88")
        rect(x + 15, y - 16, 1, 6, "#725d69")
        lettering(f"{number:02}", x + 1, y - 16, 0.7, "#dfcca2")

    view = "24 0 448 280" if mobile else "0 0 500 280"
    width = 896 if mobile else 1000
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="560" viewBox="{view}" role="img" aria-labelledby="title desc" shape-rendering="crispEdges">')
    add(f'<title id="title">{label} — a little world, built from scratch</title>')
    add(f'<desc id="desc">An original animated pixel landscape: a warm developer workshop on a floating pine-covered island, rope bridges, moonlit mountains and a turquoise waterfall. A selection of {count} projects, with numbered waypoints for the first three. All illustration is drawn in Python and SVG. Animation stops when reduced motion is requested.</desc>')
    add('''<style>
      @keyframes drift {0%,100%{transform:translateX(0)}50%{transform:translateX(6px)}}
      @keyframes driftback {0%,100%{transform:translateX(0)}50%{transform:translateX(-5px)}}
      @keyframes water {to{transform:translateY(18px)}}
      @keyframes sparkle {0%,100%{opacity:.35}50%{opacity:1}}
      @keyframes firefly {0%,100%{opacity:.15;transform:translate(0,0)}40%{opacity:.9}70%{opacity:.65;transform:translate(2px,-3px)}}
      @keyframes smoke {0%{opacity:0;transform:translate(0,3px)}25%{opacity:.45}100%{opacity:0;transform:translate(-8px,-16px)}}
      @keyframes warm {0%,100%{opacity:.82}50%{opacity:1}}
      @keyframes breathe {0%,65%,100%{transform:translateY(0)}70%,90%{transform:translateY(-1px)}}
      .cloud{animation:drift 22s ease-in-out infinite}.cloud-back{animation:driftback 29s ease-in-out infinite}
      .water{animation:water 1.3s linear infinite}.star{animation:sparkle 4s ease-in-out infinite}
      .firefly{animation:firefly 7s ease-in-out infinite}.smoke{animation:smoke 7s linear infinite}
      .lamplight{animation:warm 6s ease-in-out infinite}.traveler{animation:breathe 5s steps(1,end) infinite}
      @media(prefers-reduced-motion:reduce){.cloud,.cloud-back,.water,.star,.firefly,.smoke,.lamplight,.traveler{animation:none!important}.smoke{opacity:.2}}
    </style>''')
    add('<defs><clipPath id="scene"><rect width="500" height="280"/></clipPath><clipPath id="fall"><path d="M322 190h15v82h-3v8h-18v-10h3v-43h3z"/></clipPath></defs>')
    add('<g clip-path="url(#scene)">')

    # The sky is made of restrained flat color bands, not a gradient.
    rect(0, 0, 500, 280, "#10192e")
    rect(0, 78, 500, 66, "#141e35")
    rect(0, 144, 500, 136, "#1a2641")
    rect(0, 218, 500, 62, "#18243c")
    for i in range(66):
        x, y = rng.randrange(14, 488), rng.randrange(11, 143)
        if (27 < x < 191 and y < 86) or (370 < x < 425 and 26 < y < 82):
            continue
        color = rng.choice(["#38516f", "#47657e", "#647b8f", "#9cabae"])
        rect(x, y, 1, 1, color, f' class="star" style="animation-delay:-{i % 7}s"' if i % 6 == 0 else "")
    for x, y in [(217, 27), (342, 34), (459, 54), (177, 96), (77, 100), (300, 69)]:
        rect(x - 1, y, 3, 1, "#7e9aa9")
        rect(x, y - 1, 1, 3, "#a8bbbc", ' class="star"')

    # A stepped crescent with its own crater pixels.
    moon = [(385, 30), (401, 30), (401, 33), (408, 33), (408, 38), (412, 38), (412, 54),
            (409, 54), (409, 61), (404, 61), (404, 65), (397, 65), (397, 68), (383, 68),
            (383, 65), (376, 65), (376, 60), (372, 60), (372, 53), (369, 53), (369, 42),
            (373, 42), (373, 36), (379, 36), (379, 33), (385, 33)]
    poly(moon, "#d8dfc5")
    poly([(382, 30), (391, 30), (391, 34), (396, 34), (396, 39), (400, 39), (400, 53),
          (397, 53), (397, 59), (392, 59), (392, 63), (384, 63), (384, 69), (374, 69),
          (374, 65), (369, 65), (369, 59), (365, 59), (365, 39), (371, 39), (371, 34), (382, 34)], "#10192e")
    rect(405, 43, 3, 6, "#becdaf")
    rect(400, 55, 4, 3, "#bbcaae")
    rect(398, 35, 3, 2, "#f0edd1")

    # The lettering is deliberately part of the artwork; body copy lives in Markdown.
    title_scale = 4 if mobile else 3
    lettering("PIXELGG", 32, 31, title_scale, "#36465e")
    lettering("PIXELGG", 32, 28, title_scale, "#edf0d9")
    rect(32, 63 if mobile else 57, 24 if mobile else 17, 2, "#82cbb9")
    lettering("MIKE / DEVELOPER", 32, 73 if mobile else 66, 1.5 if mobile else 1, "#92aaa9")

    # Distant mountain silhouettes, with a sparse, tiny faraway settlement.
    poly([(0, 154), (0, 143), (20, 143), (20, 134), (31, 134), (31, 126), (43, 126),
          (43, 120), (52, 120), (52, 111), (61, 111), (61, 121), (70, 121), (70, 133),
          (91, 133), (91, 142), (111, 142), (111, 136), (128, 136), (128, 126),
          (142, 126), (142, 117), (155, 117), (155, 103), (164, 103), (164, 91),
          (171, 91), (171, 104), (179, 104), (179, 119), (191, 119), (191, 134),
          (214, 134), (214, 153), (254, 153), (254, 131), (270, 131), (270, 119),
          (287, 119), (287, 109), (300, 109), (300, 116), (310, 116), (310, 131),
          (328, 131), (328, 135), (345, 135), (345, 116), (360, 116), (360, 104),
          (374, 104), (374, 95), (384, 95), (384, 108), (399, 108), (399, 120),
          (418, 120), (418, 128), (438, 128), (438, 113), (450, 113), (450, 105),
          (462, 105), (462, 120), (479, 120), (479, 132), (500, 132), (500, 190), (0, 190)], "#202e4a")
    poly([(0, 179), (24, 165), (55, 170), (81, 154), (102, 162), (131, 149), (150, 156),
          (181, 146), (202, 166), (233, 154), (260, 161), (288, 147), (320, 154),
          (345, 141), (375, 155), (395, 144), (424, 161), (454, 147), (482, 158),
          (500, 151), (500, 218), (0, 218)], "#2a3a55")
    for x, y, w, h in [(301, 123, 7, 12), (311, 129, 10, 8), (324, 124, 6, 13), (332, 130, 8, 7)]:
        rect(x, y, w, h, "#35445c")
        rect(x + 2, y + 3, 1, 2, "#a19279")

    add('<g class="cloud-back" fill="#283751">')
    for x, y, w, h in [(14, 91, 43, 4), (23, 87, 23, 4), (40, 95, 44, 3),
                        (299, 88, 61, 4), (315, 83, 25, 5), (339, 92, 33, 3),
                        (444, 87, 47, 4), (459, 83, 23, 4)]:
        rect(x, y, w, h, "#283751")
    add('</g>')

    # Tiny island far behind the workshop.
    poly([(326, 113), (358, 113), (354, 119), (347, 119), (347, 124), (339, 124), (336, 119), (330, 119)], "#344056")
    rect(326, 112, 32, 3, "#466b71")
    pine(344, 112, 0.43, "back")

    # Bridges are hand-built from separate suspended planks and stepped ropes.
    def bridge(x1: int, y1: int, x2: int, y2: int, planks: int, sag: int) -> None:
        points = []
        for i in range(planks + 1):
            t = i / planks
            x = round(x1 + (x2 - x1) * t)
            y = round(y1 + (y2 - y1) * t + sag * 4 * t * (1 - t))
            points.append((x, y))
            rect(x, y, max(3, round((x2 - x1) / planks) - 1), 3, "#80676b")
            rect(x, y, max(3, round((x2 - x1) / planks) - 1), 1, "#b39885")
            if i % 2 == 0:
                rect(x + 1, y - 10, 1, 11, "#786975")
        line([(x, y - 11) for x, y in points], "#b39a83")
        line([(x, y - 1) for x, y in points], "#56475e")
        rect(x1, y1 - 16, 2, 19, "#987d73")
        rect(x2, y2 - 16, 2, 19, "#987d73")

    bridge(86, 168, 148, 183, 14, 6)
    bridge(363, 183, 424, 161, 13, 7)

    # Left island and its hanging roots.
    poly([(27, 157), (96, 157), (104, 165), (98, 175), (89, 175), (89, 185),
          (79, 185), (79, 197), (66, 202), (63, 194), (49, 194), (49, 186),
          (38, 182), (38, 173), (30, 169)], "#3b3851")
    poly([(29, 162), (61, 164), (61, 173), (71, 179), (64, 196), (49, 194), (49, 186), (38, 182), (38, 173)], "#514459")
    poly([(58, 171), (87, 168), (84, 182), (74, 182), (74, 192), (66, 199), (63, 182)], "#2b3049")
    rect(39, 172, 10, 2, "#76566a")
    rect(47, 184, 11, 2, "#675164")
    rect(83, 173, 9, 2, "#675164")
    poly([(26, 157), (34, 153), (52, 153), (52, 150), (76, 150), (76, 153), (94, 153),
          (94, 156), (102, 156), (102, 161), (87, 161), (87, 164), (49, 164), (49, 161), (26, 161)], "#466d6c")
    rect(34, 153, 18, 2, "#7da38a")
    rect(53, 150, 22, 2, "#7da38a")
    rect(77, 153, 15, 2, "#6e9883")
    line([(39, 164), (39, 173), (42, 173), (42, 184), (45, 184), (45, 190)], "#487264")
    line([(92, 164), (92, 180), (88, 180), (88, 188)], "#4c7769")
    pine(50, 155, 0.95, "blue")
    pine(31, 158, 0.55, "main")
    if count:
        waypoint(76, 158, 1)
    grass(69, 160)
    rect(60, 159, 3, 2, "#8ba591")

    # Right island: a weather station, a lookout tree and an old cairn.
    poly([(410, 151), (471, 151), (480, 160), (472, 170), (468, 170), (468, 180),
          (457, 180), (457, 193), (446, 199), (439, 190), (431, 190), (431, 180),
          (420, 180), (420, 169), (411, 166)], "#36384f")
    poly([(412, 157), (439, 158), (439, 177), (446, 180), (446, 195), (439, 190),
          (431, 190), (431, 180), (420, 180), (420, 169), (411, 166)], "#504459")
    rect(421, 168, 13, 2, "#77586b")
    rect(431, 181, 9, 2, "#71576a")
    rect(457, 169, 9, 2, "#505067")
    poly([(408, 153), (417, 148), (435, 148), (435, 145), (457, 145), (457, 148),
          (471, 148), (479, 155), (479, 160), (456, 160), (456, 163), (424, 163), (424, 159), (408, 159)], "#4c736d")
    rect(418, 148, 17, 2, "#7ba084")
    rect(436, 145, 19, 2, "#85aa8c")
    pine(458, 150, 1.05, "blue")
    pine(476, 155, 0.47, "main")
    if count > 1:
        waypoint(429, 154, min(3, count))
    rect(446, 157, 9, 3, "#78908a")
    rect(448, 155, 5, 2, "#abb29b")
    line([(466, 160), (466, 170), (463, 170), (463, 181)], "#4d796a")
    grass(417, 156)

    # Main landmass: a deliberately irregular silhouette and layered strata.
    poly([(118, 185), (138, 175), (171, 174), (182, 168), (266, 169), (280, 176),
          (335, 176), (348, 181), (372, 181), (385, 190), (380, 202), (367, 207),
          (367, 219), (351, 222), (351, 236), (335, 236), (335, 249), (320, 249),
          (320, 259), (300, 260), (296, 270), (282, 270), (270, 261), (250, 261),
          (239, 253), (215, 256), (203, 247), (181, 247), (181, 236), (165, 236),
          (159, 225), (144, 225), (144, 214), (132, 214), (128, 202), (118, 198)], "#34354e")
    poly([(119, 192), (181, 181), (208, 186), (208, 208), (199, 216), (199, 233),
          (214, 246), (215, 256), (203, 247), (181, 247), (181, 236), (165, 236),
          (159, 225), (144, 225), (144, 214), (132, 214), (128, 202), (118, 198)], "#51435b")
    poly([(209, 193), (237, 193), (244, 206), (244, 222), (255, 229), (255, 243),
          (269, 243), (270, 261), (250, 261), (239, 253), (215, 256), (217, 239), (207, 231)], "#443d57")
    poly([(272, 198), (311, 198), (311, 218), (298, 229), (298, 251), (289, 264),
          (283, 264), (270, 256), (268, 239), (263, 230)], "#282e49")
    poly([(345, 193), (382, 192), (379, 202), (367, 207), (367, 219), (351, 222),
          (351, 236), (335, 236), (335, 249), (321, 251), (328, 226), (341, 221)], "#444058")
    for x, y, w, color in [(129, 204, 29, "#806073"), (147, 216, 20, "#77556d"),
                            (162, 227, 29, "#785c70"), (181, 238, 14, "#6d536c"),
                            (199, 203, 29, "#67516c"), (221, 230, 25, "#615069"),
                            (226, 245, 12, "#746074"), (253, 253, 9, "#635269"),
                            (351, 207, 18, "#6c5b70"), (341, 223, 10, "#706071"),
                            (294, 214, 15, "#4a4864"), (283, 241, 8, "#41425c")]:
        rect(x, y, w, 2, color)
        rect(x + 3, y + 2, max(3, w - 9), 2, "#3a364f")
    for x, y in [(151, 204), (168, 214), (190, 224), (219, 213), (247, 236), (274, 216), (305, 250), (342, 212), (359, 201)]:
        rect(x, y, 2, 4, "#716079")
        rect(x + 2, y + 1, 1, 2, "#a08a96")

    # A few mineral seams are only revealed at the cliff's shadow edge.
    for x, y in [(177, 222), (181, 226), (179, 232), (299, 235), (302, 230), (350, 217)]:
        rect(x, y, 2, 3, "#467d88")
        rect(x, y, 1, 1, "#8bd3ca")

    # Roots and vines: separately drawn, with small leaves, no repeated wallpaper.
    for points in [[(149, 198), (149, 205), (154, 205), (154, 221), (151, 221), (151, 229)],
                   [(189, 198), (189, 214), (185, 214), (185, 225)],
                   [(363, 195), (363, 211), (358, 211), (358, 228)],
                   [(239, 204), (239, 214), (235, 214), (235, 226)]]:
        line(points, "#487667", 2)
        for x, y in points[1:-1]:
            rect(x - 3, y + 3, 3, 2, "#60907b")
            rect(x + 1, y - 2, 3, 2, "#3e655e")

    # Turf, its broken highlight, and paths connect every actual place.
    poly([(118, 185), (137, 175), (170, 175), (182, 170), (268, 171), (280, 177),
          (335, 177), (348, 182), (372, 182), (385, 190), (380, 196), (361, 196),
          (355, 200), (337, 200), (337, 196), (320, 196), (309, 202), (266, 202),
          (256, 208), (224, 208), (214, 203), (183, 203), (176, 199), (145, 199), (145, 194), (123, 194)], "#3e6b65")
    poly([(125, 185), (140, 178), (174, 178), (184, 173), (264, 174), (279, 181),
          (333, 181), (347, 186), (371, 186), (379, 191), (352, 192), (342, 195),
          (316, 192), (296, 198), (267, 198), (252, 203), (226, 203), (214, 198),
          (183, 198), (176, 194), (147, 194), (145, 190), (126, 190)], "#537f70")
    for x, y, w in [(137, 175, 30), (183, 170, 28), (248, 171, 18), (280, 177, 29),
                     (348, 182, 19), (125, 193, 17), (147, 198, 26), (228, 207, 23), (270, 201, 22), (357, 198, 13)]:
        rect(x, y, w, 1, "#83a28a")
    poly([(145, 183), (182, 182), (210, 179), (239, 180), (247, 183), (267, 183),
          (282, 186), (307, 186), (324, 188), (323, 193), (303, 192), (279, 192),
          (264, 189), (247, 188), (249, 196), (243, 201), (229, 199), (225, 193),
          (228, 186), (209, 185), (182, 186), (145, 187)], "#9a9a80")
    poly([(267, 183), (292, 181), (315, 182), (343, 185), (369, 185), (373, 188),
          (343, 189), (313, 186), (292, 185), (280, 187)], "#87917a")
    for x, y, w in [(155, 184, 9), (181, 183, 5), (209, 182, 8), (231, 189, 8), (237, 196, 6), (274, 186, 7), (303, 184, 6), (350, 186, 8)]:
        rect(x, y, w, 1, "#c1b394")

    # Trees behind the roof establish height without hiding the focal point.
    pine(157, 176, 1.25, "main")
    pine(133, 181, 0.77, "blue")
    pine(307, 180, 1.04, "main")
    pine(333, 182, 0.72, "blue")

    # The workshop has a front gable and a receding right wall.
    poly([(204, 181), (204, 186), (261, 189), (296, 178), (296, 172)], "#2a3d44")
    rect(199, 138, 62, 43, "#8c6967")
    poly([(259, 139), (291, 132), (291, 174), (259, 183)], "#685565")
    for y in [146, 154, 162, 170, 178]:
        rect(201, y, 57, 1, "#5f4b59")
        line([(260, y + 1), (289, y - 6)], "#453f53")
    rect(200, 139, 4, 43, "#483e50")
    rect(256, 139, 4, 44, "#483e50")
    rect(287, 135, 4, 40, "#423d50")
    rect(201, 178, 57, 4, "#5b4b59")
    rect(203, 180, 7, 4, "#b49a84")
    rect(248, 182, 11, 3, "#8d807a")

    # Roof silhouette, front gable, and individual staggered copper-blue shingles.
    poly([(192, 139), (225, 102), (263, 94), (301, 132), (300, 138), (261, 147),
          (225, 115), (198, 145), (192, 145)], "#302d46")
    poly([(198, 136), (225, 106), (258, 138), (258, 145), (199, 145)], "#805f63")
    poly([(225, 105), (262, 97), (296, 132), (259, 141)], "#57637c")
    for i in range(6):
        y = 102 + i * 6
        x1 = 228 + i * 5
        x2 = 265 + i * 5
        line([(x1, y), (x2, y - 8)], "#899095")
        line([(x1 + 1, y + 2), (x2, y - 6)], "#3a435e")
        for j in range(4):
            x = x1 + j * 9 + (4 if i % 2 else 0)
            if x < x2 - 2:
                rect(x, round(y - (x - x1) * 0.21), 1, 3, "#b29a94" if (i + j) % 4 == 0 else "#697891")
    line([(193, 139), (225, 103), (260, 139)], "#b48b83", 3)
    line([(193, 143), (225, 110), (259, 144), (298, 135)], "#453c52", 2)
    rect(202, 142, 53, 3, "#ba8d79")
    # The attic window and its wooden brace.
    rect(221, 122, 10, 13, "#423647")
    rect(223, 124, 6, 9, "#f0bd72", ' class="lamplight"')
    rect(225, 123, 2, 12, "#735056")
    rect(222, 128, 8, 2, "#735056")
    rect(219, 135, 14, 2, "#493e4e")

    # Chimney and slow square wisps: the draft is to the left.
    rect(245, 89, 9, 19, "#69576b")
    rect(245, 91, 3, 15, "#9b7880")
    rect(243, 87, 13, 4, "#443c54")
    rect(244, 87, 11, 1, "#ba8b86")
    rect(249, 95, 5, 1, "#453f56")
    rect(245, 101, 5, 1, "#453f56")
    for i in range(3):
        add(f'<g class="smoke" style="animation-delay:-{i * 2.3:g}s">')
        rect(246, 77, 6, 6, "#718294")
        rect(243, 73, 7, 5, "#63748a")
        add('</g>')

    # A rooftop telescope looking toward the moon, built from simple facets.
    line([(278, 115), (273, 124)], "#c4a491", 2)
    line([(278, 115), (285, 121)], "#977f86", 2)
    rect(277, 108, 2, 10, "#c5a490")
    poly([(267, 110), (283, 99), (288, 104), (272, 115)], "#b0b7b1")
    poly([(268, 112), (284, 101), (287, 104), (272, 115)], "#627486")
    poly([(281, 99), (285, 96), (291, 102), (287, 105)], "#d1c4ad")
    poly([(285, 97), (289, 101), (288, 102), (284, 98)], "#5dd0c2")
    rect(266, 110, 3, 3, "#3f435a")

    # Warm front window, including an actual tiny desk and computer silhouette.
    rect(207, 151, 20, 22, "#403344")
    rect(209, 153, 16, 17, "#e9a45f", ' class="lamplight"')
    rect(210, 154, 14, 8, "#f7cb7c")
    rect(210, 162, 14, 7, "#b57b53")
    rect(211, 158, 10, 7, "#3a414a")
    rect(212, 159, 8, 5, "#75c9b9")
    rect(213, 160, 4, 1, "#d6e8c5")
    rect(213, 162, 6, 1, "#458a92")
    rect(215, 165, 2, 2, "#383542")
    rect(210, 167, 14, 2, "#5b4548")
    rect(216, 152, 2, 5, "#7c5653")
    rect(205, 173, 24, 3, "#b58a70")
    rect(205, 151, 2, 20, "#b99479")
    # Door, stoop and a line of window light over the garden path.
    rect(235, 151, 17, 31, "#413748")
    rect(237, 153, 13, 28, "#524755")
    rect(239, 155, 9, 11, "#e5ae6e", ' class="lamplight"')
    rect(240, 156, 7, 9, "#f6ca83")
    rect(242, 154, 2, 13, "#7c5d5a")
    rect(237, 169, 13, 1, "#9d7b68")
    rect(247, 172, 1, 2, "#f7d394")
    rect(233, 182, 21, 3, "#c1a58b")
    rect(231, 185, 25, 3, "#907f76")
    poly([(237, 188), (250, 188), (252, 195), (234, 195)], "#bca783", ' opacity=".5"')
    # Side window.
    poly([(268, 148), (281, 145), (281, 161), (268, 165)], "#382f44")
    poly([(270, 150), (279, 148), (279, 159), (270, 162)], "#c78b60", ' class="lamplight"')
    line([(274, 149), (274, 161)], "#5b4451", 2)
    line([(269, 156), (280, 153)], "#5b4451")
    # Handpainted workshop sign, small but fully custom pixel text.
    rect(205, 143, 31, 6, "#433a4b")
    lettering("BUILD", 207, 144, 0.6, "#d8bc91")

    # Garden furniture, a stack of logs, mushrooms, and the walking path.
    rect(180, 177, 12, 3, "#b18c70")
    rect(181, 174, 10, 3, "#92705e")
    rect(178, 180, 16, 2, "#644b50")
    for x in [181, 187]:
        rect(x, 177, 3, 3, "#d2ac7d")
        rect(x + 1, 178, 1, 1, "#7a5b55")
    rect(281, 178, 18, 3, "#a1836c")
    rect(283, 181, 2, 7, "#614d54")
    rect(295, 181, 2, 7, "#614d54")
    rect(281, 174, 18, 2, "#80665f")
    rect(285, 172, 2, 8, "#947566")
    rect(295, 172, 2, 8, "#947566")
    lantern(178, 189)
    lantern(355, 191)
    if count > 2:
        waypoint(299, 182, 2)

    # A tiny backpacked maker; boots, hair, skin, jacket and scarf are explicit.
    add('<g class="traveler">')
    rect(264, 185, 11, 2, "#3a5655")
    rect(267, 173, 5, 4, "#cf9c79")
    rect(266, 171, 6, 3, "#333448")
    rect(270, 172, 3, 3, "#333448")
    rect(267, 177, 6, 6, "#7ea4a1")
    rect(265, 178, 2, 5, "#ae785c")
    rect(272, 178, 2, 4, "#dab38b")
    rect(268, 178, 6, 1, "#f2bd6e")
    rect(272, 179, 2, 3, "#e6a86c")
    rect(267, 183, 2, 3, "#303448")
    rect(271, 183, 2, 3, "#303448")
    rect(266, 186, 3, 1, "#c0aa90")
    rect(271, 186, 3, 1, "#c0aa90")
    add('</g>')

    # Stream and waterfall.  Horizontal ripple fragments move through a clip.
    poly([(313, 183), (322, 183), (322, 186), (331, 186), (335, 190), (335, 196),
          (321, 196), (321, 192), (315, 191), (315, 187), (310, 187)], "#4d9d9c")
    rect(315, 184, 6, 2, "#a0d4bb")
    rect(320, 188, 12, 2, "#8ccac0")
    rect(322, 190, 15, 6, "#b5e0c5")
    add('<g clip-path="url(#fall)">')
    rect(316, 194, 21, 89, "#3c858f")
    rect(322, 194, 5, 89, "#77c7bb")
    rect(327, 194, 5, 89, "#56ada8")
    rect(333, 194, 4, 89, "#356d83")
    rect(320, 212, 3, 70, "#9cdac5")
    add('<g class="water">')
    for y in range(180, 282, 18):
        rect(322, y, 2, 7, "#d8ead1")
        rect(326, y + 9, 2, 9, "#a6ddcb")
        rect(331, y + 5, 2, 5, "#8bc8bd")
        rect(319, y + 11, 2, 3, "#d2e9d0")
    add('</g></g>')
    for x, y in [(316, 206), (338, 220), (315, 245), (339, 258)]:
        rect(x, y, 1, 2, "#90cabc", ' class="star"')
    rect(320, 193, 3, 2, "#d9ebd3")
    rect(325, 193, 5, 1, "#e0ecd6")

    # Deliberately sparse surface details retain the terrain silhouette.
    for x, y in [(127, 190), (142, 180), (164, 192), (174, 197), (193, 191), (207, 198),
                 (218, 188), (254, 198), (281, 197), (307, 197), (344, 195), (369, 190)]:
        grass(x, y)
    for x, y in [(166, 187), (204, 192), (286, 195), (340, 191), (459, 157)]:
        rect(x, y - 2, 1, 3, "#a5b59a")
        rect(x - 2, y - 3, 5, 2, "#bc837b")
        rect(x - 1, y - 4, 3, 1, "#e2af8d")
        rect(x, y - 3, 1, 1, "#f3cdaa")
    for x, y, w in [(134, 188, 5), (187, 195, 7), (215, 202, 5), (258, 193, 4), (350, 188, 5), (371, 193, 4)]:
        rect(x, y, w, 2, "#6d8177")
        rect(x + 1, y - 1, max(w - 2, 1), 1, "#a6ae91")
    for x, y in [(153, 191), (196, 185), (212, 194), (279, 194), (346, 191), (432, 158)]:
        rect(x, y - 1, 1, 2, "#d2bd87")

    # Low foreground cloudbanks frame the descending island, without a hard card.
    add('<g class="cloud" opacity=".8">')
    for x, y, w, h in [(-10, 232, 92, 7), (6, 227, 52, 5), (44, 239, 71, 5),
                       (387, 223, 119, 6), (411, 217, 68, 6), (371, 230, 77, 4),
                       (-9, 264, 142, 8), (14, 258, 86, 6), (88, 272, 70, 8),
                       (381, 261, 126, 8), (417, 254, 79, 7), (351, 269, 107, 5)]:
        rect(x, y, w, h, "#29394f")
    add('</g>')
    for i, (x, y) in enumerate([(113, 169), (186, 160), (340, 159), (395, 178), (279, 208), (85, 147), (303, 165)]):
        add(f'<g class="firefly" style="animation-delay:-{i * 1.1:g}s">')
        rect(x - 1, y, 3, 1, "#6daca0", ' opacity=".4"')
        rect(x, y - 1, 1, 3, "#6daca0", ' opacity=".4"')
        rect(x, y, 1, 1, "#dce6ad")
        add('</g>')

    # A quiet map legend: the count is real, not an invented contribution metric.
    lettering(f"{count:02} PROJECTS", 32, 256, 1.5 if mobile else 0.8, "#809a9e")
    rect(32, 249, 8, 1, "#5c8e87")
    add('</g></svg>')
    return "\n".join(p) + "\n"
