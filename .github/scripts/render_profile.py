import os
import sys
import json
from datetime import datetime, timezone
from urllib.parse import quote

import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OWNER = os.environ.get("OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_LIMIT = int(os.environ.get("REPO_LIMIT", "6"))

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
METRICS_DIR = ASSETS / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update(
    {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "pixelgg-profile-v3",
    }
)

def gh(url: str):
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_all_repos(owner: str):
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{quote(owner)}/repos?per_page=100&page={page}&sort=pushed&direction=desc"
        data = gh(url)
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
        if page > 10:
            break

    profile_full = f"{owner}/{owner}".lower()
    repos = [
        r
        for r in repos
        if not r.get("private")
        and not r.get("fork")
        and r.get("full_name", "").lower() != profile_full
    ]
    return repos

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
    try:
        return dt(iso).strftime("%Y-%m-%d")
    except Exception:
        return iso or ""

def truncate(text: str, n: int) -> str:
    if not text:
        return ""
    t = " ".join(text.split())
    return t if len(t) <= n else t[: n - 1] + "…"

def primary_language(langs: dict) -> str:
    if not langs:
        return "—"
    return max(langs.items(), key=lambda kv: kv[1])[0]

# ---------- Charts ----------

def set_dark_style():
    plt.rcParams.update(
        {
            "figure.facecolor": "#0d1117",
            "axes.facecolor": "#0d1117",
            "savefig.facecolor": "#0d1117",
            "text.color": "#c9d1d9",
            "axes.labelcolor": "#c9d1d9",
            "axes.edgecolor": "#30363d",
            "xtick.color": "#8b949e",
            "ytick.color": "#8b949e",
            "grid.color": "#30363d",
            "font.size": 11,
        }
    )

PALETTE = [
    "#58a6ff",
    "#f78166",
    "#d2a8ff",
    "#79c0ff",
    "#ffa657",
    "#7ee787",
    "#1f6feb",
    "#ff7b72",
]

def build_language_charts(language_totals: dict):
    items = sorted(language_totals.items(), key=lambda kv: kv[1], reverse=True)

    if not items:
        # Placeholder-Bilder
        for name in ("top-langs-bar.png", "top-langs-donut.png"):
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.text(0.5, 0.5, "Keine Sprachdaten", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(METRICS_DIR / name, dpi=180)
            plt.close(fig)
        return

    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    total = sum(vals)

    # Begrenzen + "Other"
    maxn = 8
    if len(labels) > maxn:
        other = sum(vals[maxn:])
        labels = labels[:maxn] + ["Other"]
        vals = vals[:maxn] + [other]

    pcts = [v / total * 100 for v in vals]

    # Bar
    set_dark_style()
    fig, ax = plt.subplots(figsize=(9, 5), dpi=180)
    y = list(range(len(labels)))[::-1]
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))][::-1]
    ax.barh(y, pcts[::-1], color=colors)
    ax.set_yticks(y, labels=labels[::-1])
    ax.set_xlabel("Anteil (%)")
    ax.set_title("Top Languages (öffentlich)")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(METRICS_DIR / "top-langs-bar.png")
    plt.close(fig)

    # Donut
    set_dark_style()
    fig, ax = plt.subplots(figsize=(6, 6), dpi=180)
    ax.pie(
        vals,
        startangle=140,
        colors=[PALETTE[i % len(PALETTE)] for i in range(len(vals))],
        wedgeprops=dict(width=0.38, edgecolor="#0d1117"),
    )
    ax.set(aspect="equal", title="Language Share (Donut)")
    fig.tight_layout()
    fig.savefig(METRICS_DIR / "top-langs-donut.png")
    plt.close(fig)

# ---------- Projekte-HTML ----------

def build_projects_table(repos, lang_map, mode: str) -> str:
    if not repos:
        return '<div align="center"><i>Keine öffentlichen Repositories.</i></div>'

    if mode == "latest":
        chosen = sorted(
            repos,
            key=lambda r: dt(r.get("pushed_at") or r.get("updated_at")),
            reverse=True,
        )[:REPO_LIMIT]
    else:
        chosen = sorted(
            repos,
            key=lambda r: (
                int(r.get("stargazers_count") or 0),
                dt(r.get("pushed_at") or r.get("updated_at")),
            ),
            reverse=True,
        )[:REPO_LIMIT]

    cells = []
    for r in chosen:
        full = r["full_name"]
        name = r["name"]
        desc = truncate(r.get("description") or "", 120)
        stars = int(r.get("stargazers_count") or 0)
        langs = lang_map.get(full) or {}
        lang = primary_language(langs)
        updated = iso_date(r.get("pushed_at") or r.get("updated_at") or "")

        cell = (
            '<td align="left" valign="top" width="50%" style="padding: 8px;">'
            f'<a href="https://github.com/{full}"><b>{name}</b></a><br/>'
            f'<sub>{desc or "<i>Keine Beschreibung</i>"}</sub><br/>'
            f'<sub>⭐ {stars} · {lang} · updated {updated}</sub>'
            "</td>"
        )
        cells.append(cell)

    rows = []
    for i in range(0, len(cells), 2):
        row = cells[i : i + 2]
        if len(row) == 1:
            row.append('<td width="50%" style="padding: 8px;"></td>')
        rows.append("<tr>" + "".join(row) + "</tr>")

    html = '<div align="center">\n<table>\n' + "\n".join(rows) + "\n</table>\n</div>"
    return html

# ---------- README-Aktualisierung ----------

def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    if start_marker not in text or end_marker not in text:
        raise SystemExit(f"Marker {start_marker} / {end_marker} nicht gefunden.")
    s = text.index(start_marker)
    e = text.index(end_marker, s)
    return text[: s + len(start_marker)] + "\n\n" + replacement + "\n\n" + text[e:]

def main():
    if not OWNER or not TOKEN:
        print("OWNER oder GITHUB_TOKEN fehlt.", file=sys.stderr)
        sys.exit(1)

    repos = fetch_all_repos(OWNER)

    # Sprachen sammeln
    lang_map = {}
    totals = {}
    for r in repos:
        langs = fetch_languages(r.get("languages_url", ""))
        lang_map[r["full_name"]] = langs
        for k, v in (langs or {}).items():
            totals[k] = totals.get(k, 0) + int(v)

    # Charts generieren
    build_language_charts(totals)

    # Snapshot
    total_repos = len(repos)
    total_stars = sum(int(r.get("stargazers_count") or 0) for r in repos)
    if totals:
        top_lang, top_bytes = max(totals.items(), key=lambda kv: kv[1])
        pct = top_bytes / sum(totals.values()) * 100.0
        lang_part = f"Top Language: <b>{top_lang}</b> ({pct:.1f}%)"
    else:
        lang_part = "Top Language: —"

    metrics_summary = (
        f"<sub>Repos: <b>{total_repos}</b> · Stars (gesamt): <b>{total_stars}</b> · {lang_part}</sub>"
    )

    # Projekte
    latest_html = build_projects_table(repos, lang_map, "latest")
    stars_html = build_projects_table(repos, lang_map, "stars")

    readme_path = ROOT / "README.md"
    md = readme_path.read_text(encoding="utf-8")

    md = replace_between(
        md, "<!-- start: metrics-summary -->", "<!-- end: metrics-summary -->", metrics_summary
    )
    md = replace_between(
        md, "<!-- start: projects-latest -->", "<!-- end: projects-latest -->", latest_html
    )
    md = replace_between(
        md, "<!-- start: projects-stars -->", "<!-- end: projects-stars -->", stars_html
    )

    readme_path.write_text(md, encoding="utf-8")
    print("README, Snapshot & Projektlisten aktualisiert.")

if __name__ == "__main__":
    main()
