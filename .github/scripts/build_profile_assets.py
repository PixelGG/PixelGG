# Builds local SVG charts (top languages & top repos), and updates README sections.
# Avoids third-party dynamic images for reliability.
#
# Requires env:
#   - OWNER (github.repository_owner)
#   - GITHUB_TOKEN (automatic token)
#
# Output:
#   - assets/top-langs.svg
#   - assets/top-repos.svg
#   - README.md (projects-list + all-repos-list sections replaced)

import os, sys, json, math, textwrap, pathlib, datetime, shutil
from urllib.request import Request, urlopen
from urllib.parse import quote
import ssl

# Matplotlib headless
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OWNER = os.environ.get("OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN")
if not OWNER or not TOKEN:
    print("Missing OWNER or GITHUB_TOKEN", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

def gh_get(url: str):
    # Basic REST GET with auth & pagination support if needed
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "pixelgg-profile-builder",
    }
    ctx = ssl.create_default_context()
    req = Request(url, headers=headers)
    with urlopen(req, context=ctx) as resp:
        data = resp.read()
        # Github may return bytes; parse JSON
        return json.loads(data.decode("utf-8"))

def fetch_all_repos(owner: str, exclude_profile=True, include_forks=False):
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{quote(owner)}/repos?per_page=100&page={page}&sort=pushed&direction=desc"
        batch = gh_get(url)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    # Filter
    out = []
    profile_full = f"{owner}/{owner}".lower()
    for r in repos:
        if r.get("private"):
            continue
        if not include_forks and r.get("fork"):
            continue
        if exclude_profile and r.get("full_name", "").lower() == profile_full:
            continue
        out.append(r)
    return out

def fetch_languages(languages_url: str):
    try:
        return gh_get(languages_url)
    except Exception as e:
        return {}

def iso_to_date(iso: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso

def trim(text: str, n: int) -> str:
    if not text:
        return ""
    t = text.strip()
    return t if len(t) <= n else t[: n - 1] + "…"

def primary_language(langs: dict) -> str:
    if not langs:
        return "—"
    return max(langs.items(), key=lambda kv: kv[1])[0]

def build_top_languages_chart(language_totals: dict, out_path: pathlib.Path):
    if not language_totals:
        # Create empty placeholder
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Keine Sprachdaten", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path, format="svg")
        plt.close(fig)
        return

    # Sort by bytes desc and compute percentages
    total_bytes = sum(language_totals.values())
    items = sorted(language_totals.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    pct = [v / total_bytes * 100 for v in values]

    # Limit to top 8 + "Other"
    max_items = 8
    if len(items) > max_items:
        top_labels = labels[:max_items]
        top_values = values[:max_items]
        other = sum(values[max_items:])
        top_labels.append("Other")
        top_values.append(other)
        labels, values = top_labels, top_values
        pct = [v / total_bytes * 100 for v in values]

    fig, ax = plt.subplots(figsize=(8, 5))
    y = list(range(len(labels)))[::-1]  # horizontal bars
    ax.barh(y, values)
    ax.set_yticks(y, labels=[f"{labels[i]}  {pct[::-1][i]:.1f}%" for i in range(len(labels))][::-1])
    ax.set_xlabel("Bytes (aggregiert)")
    ax.set_title("Top-Sprachen (öffentlich)")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, format="svg")
    plt.close(fig)

def build_top_repos_chart(repos, out_path: pathlib.Path):
    # Top by stargazers_count
    if not repos:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Keine öffentlichen Repositories", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path, format="svg")
        plt.close(fig)
        return

    items = sorted(repos, key=lambda r: (r.get("stargazers_count") or 0, r.get("pushed_at") or ""), reverse=True)[:8]
    labels = [r["name"] for r in items]
    stars = [int(r.get("stargazers_count") or 0) for r in items]

    fig, ax = plt.subplots(figsize=(8, 5))
    y = list(range(len(labels)))[::-1]
    ax.barh(y, stars)
    ax.set_yticks(y, labels=labels[::-1])
    ax.set_xlabel("Stars")
    ax.set_title("Top-Repositories (Stars)")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, format="svg")
    plt.close(fig)

def build_projects_table(repos, lang_map):
    # Most recently pushed (top 6), 2 columns
    recent = sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True)[:6]
    if not recent:
        return '<div align="center"><i>Keine öffentlichen Repositories.</i></div>'

    def card(r):
        name = r["name"]
        full = r["full_name"]
        desc = trim(r.get("description") or "", 120)
        stars = int(r.get("stargazers_count") or 0)
        lang = primary_language(lang_map.get(full, {}))
        updated = iso_to_date(r.get("pushed_at") or "")
        # Accessible, style-less card using table cell
        return (
            '<td align="left" width="50%" valign="top">'
            f'<a href="https://github.com/{full}"><b>{name}</b></a><br/>'
            f'<sub>{desc or "<i>Keine Beschreibung</i>"}</sub><br/>'
            f'<sub>⭐ {stars} · {lang} · updated {updated}</sub>'
            '</td>'
        )

    cells = [card(r) for r in recent]
    rows = []
    for i in range(0, len(cells), 2):
        row = cells[i:i+2]
        if len(row) == 1:
            row.append('<td width="50%"></td>')
        rows.append("<tr>" + "".join(row) + "</tr>")

    html = "<div align=\"center\">\n<table>\n" + "\n".join(rows) + "\n</table>\n</div>"
    return html

def build_all_repos_list(repos, lang_map):
    if not repos:
        return "<p><i>Keine öffentlichen Repositories.</i></p>"
    lines = []
    for r in sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True):
        full = r["full_name"]
        name = r["name"]
        stars = int(r.get("stargazers_count") or 0)
        lang = primary_language(lang_map.get(full, {}))
        updated = iso_to_date(r.get("pushed_at") or "")
        lines.append(f'- <a href="https://github.com/{full}"><code>{name}</code></a> — ⭐ {stars} · {lang} · updated {updated}')
    return "\n".join(lines)

def replace_between_markers(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    try:
        s = text.index(start_marker)
        e = text.index(end_marker, s)
    except ValueError:
        raise SystemExit(f"Marker {start_marker} / {end_marker} nicht gefunden.")
    return text[: s + len(start_marker)] + "\n\n" + replacement + "\n\n" + text[e:]

def main():
    repos = fetch_all_repos(OWNER, exclude_profile=True, include_forks=False)

    # Collect languages per repo + totals
    lang_map = {}
    totals = {}
    for r in repos:
        langs = fetch_languages(r.get("languages_url", "")) if r.get("languages_url") else {}
        lang_map[r["full_name"]] = langs
        for k, v in langs.items():
            totals[k] = totals.get(k, 0) + int(v)

    # Build charts
    build_top_languages_chart(totals, ASSETS / "top-langs.svg")
    build_top_repos_chart(repos, ASSETS / "top-repos.svg")

    # Build sections
    projects_html = build_projects_table(repos, lang_map)
    all_repos_md = build_all_repos_list(repos, lang_map)

    # Update README
    readme_path = ROOT / "README.md"
    md = readme_path.read_text(encoding="utf-8")

    md = replace_between_markers(md, "<!-- start: projects-list -->", "<!-- end: projects-list -->", projects_html)
    md = replace_between_markers(md, "<!-- start: all-repos-list -->", "<!-- end: all-repos-list -->", all_repos_md)

    readme_path.write_text(md, encoding="utf-8")
    print("Updated README and assets.")

if __name__ == "__main__":
    main()

