# Render attractive charts and local repo cards; update README sections.
# No runtime dependency on third-party image services.

import os, sys, json, math, io, pathlib, textwrap
from datetime import datetime, timezone
from urllib.parse import quote
import requests

# Charts
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Cards
from PIL import Image, ImageDraw, ImageFont

OWNER = os.environ.get("OWNER")
TOKEN = os.environ.get("GH_TOKEN")
REPO_LIMIT = int(os.environ.get("REPO_LIMIT","6"))

ROOT = pathlib.Path(".").resolve()
ASSETS = ROOT / "assets"
METRICS_DIR = ASSETS / "metrics"
CARDS_DIR = ASSETS / "cards"
METRICS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "pixelgg-profile-v3"
})

def gh(url):
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_all_repos(owner):
    out = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{owner}/repos?per_page=100&page={page}&sort=pushed&direction=desc"
        data = gh(url)
        if not data: break
        out.extend(data)
        if len(data) < 100: break
        page += 1
        if page > 10: break
    prof = f"{owner}/{owner}".lower()
    out = [r for r in out if (not r.get("private")) and (not r.get("fork")) and r.get("full_name","").lower()!=prof]
    return out

def fetch_languages(url):
    try:
        return gh(url)
    except Exception:
        return {}

def dt(iso):
    if not iso: return datetime(1970,1,1,tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(iso.replace("Z","+00:00"))
    except Exception:
        return datetime(1970,1,1,tzinfo=timezone.utc)

def truncate(text, n):
    if not text: return ""
    t = " ".join(text.split())
    return t if len(t)<=n else t[:n-1]+"…"

# ---------- Styling ----------
def set_dark_style():
    plt.rcParams.update({
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
    })

PALETTE = ["#58a6ff","#f78166","#d2a8ff","#79c0ff","#ffa657","#7ee787","#1f6feb","#ff7b72"]

def bar_and_donut(language_totals):
    # Prepare data
    items = sorted(language_totals.items(), key=lambda kv: kv[1], reverse=True)
    if not items:
        # create placeholders
        fig, ax = plt.subplots(figsize=(9,5))
        ax.text(0.5,0.5,"Keine Sprachdaten", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(METRICS_DIR/"top-langs-bar.png", dpi=180)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(6,6))
        ax.text(0.5,0.5,"Keine Sprachdaten", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(METRICS_DIR/"top-langs-donut.png", dpi=180)
        plt.close(fig)
        return

    labels = [k for k,_ in items]
    vals = [v for _,v in items]
    total = sum(vals)
    pcts = [v/total*100 for v in vals]

    # Limit to top10 + 'Other'
    maxn = 10
    if len(labels) > maxn:
        other = sum(vals[maxn:])
        labels = labels[:maxn] + ["Other"]
        vals = vals[:maxn] + [other]
        pcts = [v/total*100 for v in vals]

    # BAR
    set_dark_style()
    fig, ax = plt.subplots(figsize=(9,5.5), dpi=180)
    y = list(range(len(labels)))[::-1]
    colors = [PALETTE[i%len(PALETTE)] for i in range(len(labels))][::-1]
    ax.barh(y, pcts[::-1], color=colors)
    ax.set_yticks(y, labels=labels[::-1])
    ax.set_xlabel("Anteil (%)")
    ax.set_title("Top Languages (öffentlich)")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(METRICS_DIR/"top-langs-bar.png")
    plt.close(fig)

    # DONUT
    set_dark_style()
    fig, ax = plt.subplots(figsize=(6.4,6.4), dpi=180)
    wedges, _ = ax.pie(vals, startangle=140, colors=[PALETTE[i%len(PALETTE)] for i in range(len(vals))],
                        wedgeprops=dict(width=0.38, edgecolor="#0d1117"))
    ax.set(aspect="equal", title="Language Share (Donut)")
    fig.tight_layout()
    fig.savefig(METRICS_DIR/"top-langs-donut.png")
    plt.close(fig)

# ---------- Cards ----------
def load_font(size):
    # Use a standard font available on ubuntu-latest runner
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def draw_card(repo, primary_lang, dest):
    W, H = 720, 340  # bigger, crisp
    img = Image.new("RGBA", (W, H), "#0d1117")
    draw = ImageDraw.Draw(img)

    # Card background
    bg_rect = [(18,18), (W-18, H-18)]
    draw.rounded_rectangle(bg_rect, radius=18, fill="#161b22")

    # Accent bar
    draw.rounded_rectangle([(18,18),(28,H-18)], radius=6, fill="#58a6ff")

    # Text
    title_f = load_font(36)
    sub_f = load_font(20)
    meta_f = load_font(18)

    name = repo["name"]
    desc = truncate(repo.get("description") or "", 120)
    stars = int(repo.get("stargazers_count") or 0)
    updated = dt(repo.get("pushed_at") or repo.get("updated_at") or "").strftime("%Y-%m-%d")

    # Title
    draw.text((48, 40), name, font=title_f, fill="#c9d1d9")

    # Desc
    draw.text((48, 100), desc or "—", font=sub_f, fill="#8b949e")

    # Meta row
    meta = f"⭐ {stars}    ●  {primary_lang or '—'}    ●  updated {updated}"
    draw.text((48, H-60), meta, font=meta_f, fill="#8b949e")

    img.save(dest)

def build_cards(repos, lang_map, kind):
    # kind: "latest" or "stars"
    if kind == "latest":
        chosen = sorted(repos, key=lambda r: dt(r.get("pushed_at") or r.get("updated_at")), reverse=True)[:REPO_LIMIT]
    else:
        chosen = sorted(repos, key=lambda r: (int(r.get("stargazers_count") or 0), dt(r.get("pushed_at") or r.get("updated_at"))), reverse=True)[:REPO_LIMIT]

    cards = []
    for r in chosen:
        primary = "—"
        ls = lang_map.get(r["full_name"]) or {}
        if ls:
            primary = max(ls.items(), key=lambda kv: kv[1])[0]
        dest = CARDS_DIR / f'{r["name"]}-{kind}.png'
        draw_card(r, primary, dest)
        cards.append((r, dest))
    return cards

def grid_html(cards):
    if not cards:
        return '<div align="center"><i>Keine öffentlichen Repos gefunden.</i></div>'
    cells = []
    for r, path in cards:
        cell = (
            '<td align="center" valign="top" width="50%" style="padding: 8px;">'
            f'<a href="https://github.com/{r["full_name"]}">'
            f'<img src="{path.as_posix()}" alt="{r["name"]} card" />'
            '</a></td>'
        )
        cells.append(cell)
    rows = []
    for i in range(0, len(cells), 2):
        row = cells[i:i+2]
        if len(row)==1:
            row.append('<td width="50%" style="padding: 8px;"></td>')
        rows.append("<tr>"+"".join(row)+"</tr>")
    return '<div align="center">\\n<table>\\n' + "\\n".join(rows) + '\\n</table>\\n</div>'

def replace_between(text, start_marker, end_marker, replacement):
    if start_marker not in text or end_marker not in text:
        raise SystemExit(f"Marker {start_marker} / {end_marker} nicht gefunden.")
    s = text.index(start_marker)
    e = text.index(end_marker, s)
    return text[:s+len(start_marker)] + "\\n\\n" + replacement + "\\n\\n" + text[e:]

def main():
    repos = fetch_all_repos(OWNER)
    lang_map = {}
    totals = {}
    for r in repos:
        ls = fetch_languages(r.get("languages_url",""))
        lang_map[r["full_name"]] = ls
        for k,v in (ls or {}).items():
            totals[k] = totals.get(k,0) + int(v)

    # Charts
    bar_and_donut(totals)

    # Cards
    latest_cards = build_cards(repos, lang_map, "latest")
    star_cards = build_cards(repos, lang_map, "stars")

    # Metrics summary
    total_repos = len(repos)
    total_stars = sum(int(r.get("stargazers_count") or 0) for r in repos)
    if totals:
        top_lang, top_bytes = max(totals.items(), key=lambda kv: kv[1])
        pct = (top_bytes / sum(totals.values())) * 100.0
        lang_line = f"Top Language: <b>{top_lang}</b> ({pct:.1f}%)"
    else:
        lang_line = "Top Language: —"

    summary = f"<sub>Repos: <b>{total_repos}</b> · Stars (gesamt): <b>{total_stars}</b> · {lang_line}</sub>"

    # Update README
    readme_path = ROOT / "README.md"
    md = readme_path.read_text(encoding="utf-8")
    md = replace_between(md, "<!-- start: projects-latest -->", "<!-- end: projects-latest -->", grid_html(latest_cards))
    md = replace_between(md, "<!-- start: projects-stars -->", "<!-- end: projects-stars -->", grid_html(star_cards))
    md = replace_between(md, "<!-- start: metrics-summary -->", "<!-- end: metrics-summary -->", summary)
    readme_path.write_text(md, encoding="utf-8")
    print("README aktualisiert. Visuals & Karten erzeugt.")

if __name__ == "__main__":
    if not OWNER or not TOKEN:
        print("OWNER/GH_TOKEN fehlt.", file=sys.stderr)
        sys.exit(1)
    main()
