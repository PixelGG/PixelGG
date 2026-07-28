import html
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


OWNER = os.environ.get("OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_LIMIT = int(os.environ.get("REPO_LIMIT", "6"))

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ASSETS = ROOT / ".github" / "assets"
PROFILE_ASSETS.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update(
    {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pixelgg-profile-v5",
    }
)
if TOKEN:
    session.headers["Authorization"] = f"Bearer {TOKEN}"

PROJECT_COPY = {
    "Arvox_Core": "Sicherer Plattformkern für Accounts, Sessions, Characters und Permissions.",
    "Arvox_Inventory": "Transaktionssicheres Inventarsystem für Arvox Core.",
    "Arvox_Phone": "Gerätebasiertes, serverautorisiertes Game-Phone mit PulseOS.",
    "DXForge": "Strukturierte DX9-Lua-UI-Bibliothek für hochwertige In-Game-Overlays.",
    "LuaScripts": "Experimentierfeld und Sammlung wiederverwendbarer Lua-Systeme.",
}

PALETTE = (
    "#2DD4BF",
    "#D8B36A",
    "#55A6CF",
    "#78C8C0",
    "#A6B9C8",
    "#8C7FC2",
)


def gh(url: str):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_all_repos(owner: str):
    repos = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{quote(owner)}/repos"
            f"?per_page=100&page={page}&sort=pushed&direction=desc"
        )
        data = gh(url)
        if not data:
            break
        repos.extend(data)
        if len(data) < 100 or page >= 10:
            break
        page += 1

    profile_full_name = f"{owner}/{owner}".lower()
    return [
        repo
        for repo in repos
        if not repo.get("private")
        and not repo.get("fork")
        and repo.get("full_name", "").lower() != profile_full_name
    ]


def fetch_languages(url: str):
    if not url:
        return {}
    try:
        return gh(url)
    except Exception:
        return {}


def dt(iso: str) -> datetime:
    if not iso:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def iso_date(iso: str) -> str:
    return dt(iso).strftime("%Y-%m-%d")


def truncate(text: str, limit: int) -> str:
    normalized = " ".join((text or "").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def primary_language(languages: dict) -> str:
    if not languages:
        return "—"
    return max(languages.items(), key=lambda item: item[1])[0]


def percent_label(value: float) -> str:
    if 0 < value < 0.05:
        return "&lt;0.1%"
    return f"{value:.1f}%"


def build_language_signal(language_totals: dict, repo_count: int, star_count: int):
    ordered = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) > 6:
        ordered = ordered[:5] + [("Other", sum(value for _, value in ordered[5:]))]

    total = sum(value for _, value in ordered)
    entries = [
        (name, value / total * 100 if total else 0.0)
        for name, value in ordered
    ]
    if not entries:
        entries = [("No public language data", 100.0)]

    segments = []
    cursor = 72.0
    bar_width = 1256.0
    for index, (_, percentage) in enumerate(entries):
        width = bar_width * percentage / 100
        segments.append(
            f'<rect x="{cursor:.2f}" y="111" width="{max(width, 1):.2f}" '
            f'height="30" fill="{PALETTE[index % len(PALETTE)]}"/>'
        )
        cursor += width

    cards = []
    for index, (name, percentage) in enumerate(entries[:6]):
        column = index % 3
        row = index // 3
        x = 72 + column * 424
        y = 178 + row * 82
        color = PALETTE[index % len(PALETTE)]
        safe_name = html.escape(name)
        safe_percentage = percent_label(percentage)
        progress_width = max(2, 318 * percentage / 100)
        cards.append(
            f"""
            <g transform="translate({x} {y})">
              <circle cx="5" cy="7" r="5" fill="{color}"/>
              <text x="22" y="13" class="sans" fill="#E7EEF4" font-size="17"
                    font-weight="700">{safe_name}</text>
              <text x="358" y="13" class="mono" fill="#9CB0BF" font-size="14"
                    text-anchor="end">{safe_percentage}</text>
              <rect y="30" width="358" height="5" rx="2.5" fill="#152B3B"/>
              <rect y="30" width="{progress_width:.2f}" height="5" rx="2.5" fill="{color}"/>
            </g>"""
        )

    top_language = entries[0]
    star_part = f" · {star_count:02d} STARS" if star_count else ""
    summary = (
        f"{repo_count:02d} PUBLIC REPOSITORIES{star_part} · "
        f"PRIMARY SIGNAL {html.escape(top_language[0].upper())} {top_language[1]:.1f}%"
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 370"
     role="img" aria-labelledby="title desc">
  <title id="title">PixelGG public code signal</title>
  <desc id="desc">Automatically generated language distribution across public repositories.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1400" y2="370" gradientUnits="userSpaceOnUse">
      <stop stop-color="#050D17"/>
      <stop offset=".5" stop-color="#0A1928"/>
      <stop offset="1" stop-color="#050D17"/>
    </linearGradient>
    <pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse">
      <path d="M36 0H0v36" fill="none" stroke="#8BA7BC" stroke-opacity=".045"/>
    </pattern>
    <clipPath id="bar"><rect x="72" y="111" width="1256" height="30" rx="8"/></clipPath>
    <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      .sans{{font-family:"Segoe UI",Arial,sans-serif}}
      .mono{{font-family:Consolas,"Courier New",monospace}}
      .sweep{{animation:sweep 6s linear infinite}}
      @keyframes sweep{{0%{{transform:translateX(-80px)}}100%{{transform:translateX(1336px)}}}}
      @media (prefers-reduced-motion:reduce){{.sweep{{display:none}}}}
    </style>
  </defs>
  <rect width="1400" height="370" rx="24" fill="url(#bg)"/>
  <rect width="1400" height="370" rx="24" fill="url(#grid)"/>
  <circle cx="76" cy="62" r="5" fill="#2DD4BF"/>
  <text x="94" y="68" class="mono" fill="#D8B36A" font-size="15"
        font-weight="700" letter-spacing="2.4">PUBLIC CODE SIGNAL</text>
  <text x="1328" y="68" class="mono" fill="#617C90" font-size="12"
        text-anchor="end" letter-spacing="1.8">GENERATED DAILY / GITHUB ACTIONS</text>
  <g clip-path="url(#bar)">
    {''.join(segments)}
    <rect class="sweep" x="-80" y="111" width="60" height="30" fill="#FFFFFF"
          opacity=".18" transform="skewX(-18)"/>
  </g>
  {''.join(cards)}
  <path d="M72 332H1328" stroke="#233F53"/>
  <text x="72" y="352" class="mono" fill="#6E879A" font-size="11"
        letter-spacing="1.6">{summary}</text>
  <circle cx="1324" cy="348" r="4" fill="#2DD4BF" filter="url(#glow)"/>
  <rect x=".75" y=".75" width="1398.5" height="368.5" rx="23.25"
        fill="none" stroke="#294157" stroke-width="1.5"/>
</svg>
"""
    (PROFILE_ASSETS / "signal.svg").write_text(svg, encoding="utf-8", newline="\n")


def build_projects_table(repos, language_map) -> str:
    chosen = sorted(
        repos,
        key=lambda repo: dt(repo.get("pushed_at") or repo.get("updated_at")),
        reverse=True,
    )[:REPO_LIMIT]
    if not chosen:
        return '<div align="center"><i>Keine öffentlichen Repositories.</i></div>'

    cells = []
    for repo in chosen:
        full_name = repo["full_name"]
        name = repo["name"]
        description = truncate(
            PROJECT_COPY.get(name) or repo.get("description") or "",
            116,
        )
        language = primary_language(language_map.get(full_name) or {})
        updated = iso_date(repo.get("pushed_at") or repo.get("updated_at") or "")
        stars = int(repo.get("stargazers_count") or 0)

        safe_url = quote(full_name, safe="/")
        safe_name = html.escape(name)
        safe_description = (
            html.escape(description)
            if description
            else "<i>Noch ohne Kurzbeschreibung</i>"
        )
        safe_language = html.escape(language)
        star_part = f" · {stars} stars" if stars else ""

        cells.append(
            '<td align="left" valign="top" width="50%">'
            f'<sub><code>{safe_language} · {updated}{star_part}</code></sub><br/><br/>'
            f'<a href="https://github.com/{safe_url}"><b>{safe_name}</b></a><br/>'
            f'<sub>{safe_description}</sub><br/><br/>'
            f'<a href="https://github.com/{safe_url}"><sub>OPEN REPOSITORY →</sub></a>'
            "</td>"
        )

    rows = []
    for index in range(0, len(cells), 2):
        row = cells[index : index + 2]
        if len(row) == 1:
            row.append('<td width="50%"></td>')
        rows.append("<tr>" + "".join(row) + "</tr>")

    return '<div align="center">\n<table>\n' + "\n".join(rows) + "\n</table>\n</div>"


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str):
    if start_marker not in text or end_marker not in text:
        raise SystemExit(f"Marker {start_marker} / {end_marker} nicht gefunden.")
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return (
        text[: start + len(start_marker)]
        + "\n\n"
        + replacement
        + "\n\n"
        + text[end:]
    )


def main():
    if not OWNER:
        print("OWNER fehlt.", file=sys.stderr)
        sys.exit(1)

    repos = fetch_all_repos(OWNER)
    language_map = {}
    language_totals = {}
    for repo in repos:
        languages = fetch_languages(repo.get("languages_url", ""))
        language_map[repo["full_name"]] = languages
        for language, size in languages.items():
            language_totals[language] = language_totals.get(language, 0) + int(size)

    total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    build_language_signal(language_totals, len(repos), total_stars)

    if language_totals:
        top_language, top_size = max(language_totals.items(), key=lambda item: item[1])
        top_percentage = top_size / sum(language_totals.values()) * 100
        primary_part = f"<b>{html.escape(top_language)}</b> {top_percentage:.1f}%"
    else:
        primary_part = "—"

    star_part = f" · <b>{total_stars}</b> Stars" if total_stars else ""
    metrics_summary = (
        f"<sub><b>{len(repos)}</b> Public Repositories{star_part} "
        f"· Primary Signal {primary_part} · updated daily</sub>"
    )

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_between(
        readme,
        "<!-- start: metrics-summary -->",
        "<!-- end: metrics-summary -->",
        metrics_summary,
    )
    readme = replace_between(
        readme,
        "<!-- start: projects-latest -->",
        "<!-- end: projects-latest -->",
        build_projects_table(repos, language_map),
    )
    readme_path.write_text(readme, encoding="utf-8", newline="\n")
    print("README und .github/assets/signal.svg aktualisiert.")


if __name__ == "__main__":
    main()
