"""Build the self-contained, interactive view from the README's generated SVGs."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
import re


ROOT_ID = "pixelgg-motion-profile"
ASSETS = Path(".github/assets")


def _inline_svg(source: str, name: str) -> str:
    """Keep each inline illustration's labels, clips and CSS in its own namespace."""
    prefix = ROOT_ID + "-" + re.sub(r"[^a-zA-Z0-9_-]", "-", name) + "-"
    ids = dict.fromkeys(re.findall(r'\bid="([^"]+)"', source))
    source = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}{m[1]}"', source)
    for original in ids:
        source = source.replace(f"url(#{original})", f"url(#{prefix}{original})")
        source = source.replace(f'href="#{original}"', f'href="#{prefix}{original}"')
    source = re.sub(
        r'\b(aria-labelledby|aria-describedby)="([^"]+)"',
        lambda m: f'{m[1]}="' + " ".join(prefix + value if value in ids else value
                                         for value in m[2].split()) + '"', source)

    # Preserve the public interaction hooks, while local animation rules use only
    # namespaced classes. Desktop and mobile SVGs can coexist without CSS leaks.
    classes = {value for match in re.finditer(r'\bclass="([^"]+)"', source)
               for value in match[1].split()}
    source = re.sub(r'\bclass="([^"]+)"',
                    lambda m: 'class="' + m[1] + ' ' + ' '.join(
                        prefix + value for value in m[1].split()) + '"', source)

    def local_style(match: re.Match[str]) -> str:
        css = match[1]
        for value in sorted(classes, key=len, reverse=True):
            css = re.sub(r'\.' + re.escape(value) + r'(?![\w-])',
                         '.' + prefix + value, css)
        for value in ids:
            css = re.sub(r'#' + re.escape(value) + r'(?![\w-])',
                         '#' + prefix + value, css)
        names = set(re.findall(r'@keyframes\s+([\w-]+)', css))
        for value in sorted(names, key=len, reverse=True):
            css = re.sub(r'(?<![\w-])' + re.escape(value) + r'(?![\w-])',
                         prefix + value, css)
        return '<style>' + css + '</style>'

    source = re.sub(r'<style>(.*?)</style>', local_style, source, flags=re.S)
    return source.replace('<svg ', '<svg aria-hidden="true" focusable="false" ', 1)


def _description(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    return " ".join(value.replace("**", "").replace("__", "").replace("`", "").split())


def _date(value: str | None) -> str:
    return ("Letzter Push " + datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y")
            if value else "Noch kein Push")


def render_web(config: dict, repos: list[dict], assets: dict[Path, str]) -> str:
    """Render matching desktop/mobile art with native links and real hover/focus."""
    owner, name = config["owner"], config["name"]
    base = f"https://github.com/{owner}"
    catalog_url = escape(base + "?tab=repositories", quote=True)
    contact_url = escape(f"{base}/{owner}/issues/new", quote=True)

    def art(asset: str) -> str:
        versions = []
        for mobile in (False, True):
            stem = asset + ("-mobile" if mobile else "")
            svg = _inline_svg(assets[ASSETS / f"{stem}.svg"], stem)
            versions.append(f'<span class="{"mobile" if mobile else "desktop"}-art">{svg}</span>')
        return '<span class="art">' + ''.join(versions) + '</span>'

    css = f"""<style>
#{ROOT_ID} {{width:min(100%,1000px);margin:32px auto;color:#edf0d9;font-family:monospace;isolation:isolate;line-height:1.5;color-scheme:dark}}
#{ROOT_ID},#{ROOT_ID} * {{box-sizing:border-box}}
#{ROOT_ID} .sr-only {{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0}}
#{ROOT_ID} .art,#{ROOT_ID} .desktop-art,#{ROOT_ID} .desktop-art>svg,#{ROOT_ID} .mobile-art>svg {{display:block;width:100%;height:auto}}
#{ROOT_ID} .mobile-art {{display:none}}
#{ROOT_ID} .pixel-band,#{ROOT_ID} .pixel-nav {{margin:0;padding:0;line-height:0}}
#{ROOT_ID} .pixel-nav {{display:flex}}
#{ROOT_ID} .pixel-nav>a {{width:50%}}
#{ROOT_ID} .art-link {{display:block;color:inherit;text-decoration:none;position:relative;-webkit-tap-highlight-color:#82cbb933}}
#{ROOT_ID} .art-link:focus-visible {{outline:3px solid #f0cb85;outline-offset:-10px;z-index:1}}
#{ROOT_ID} .pc-rim,#{ROOT_ID} .pc-surface,#{ROOT_ID} .pc-button-fill,#{ROOT_ID} .catalog-fill,#{ROOT_ID} .pg-nav-fill,#{ROOT_ID} .pg-contact-fill {{transition:fill 180ms ease-out}}
#{ROOT_ID} .pc-arrow,#{ROOT_ID} .pg-contact-arrow,#{ROOT_ID} .pg-nav-projects-chevron,#{ROOT_ID} .pg-nav-contact-chevron {{transition:transform 180ms steps(2,end),fill 180ms ease-out}}
#{ROOT_ID} .repo-link:is(:hover,:focus-visible) .pc-rim {{fill:#688298}}
#{ROOT_ID} .repo-link:is(:hover,:focus-visible) .pc-surface {{fill:#202f4a}}
#{ROOT_ID} .repo-link:is(:hover,:focus-visible) .pc-button-fill,#{ROOT_ID} .catalog-link:is(:hover,:focus-visible) .catalog-fill,#{ROOT_ID} .contact-link:is(:hover,:focus-visible) .pg-contact-fill {{fill:#326663}}
#{ROOT_ID} .repo-link:is(:hover,:focus-visible) .pc-arrow {{animation:none;transform:translateX(4px);fill:#f0cb85}}
#{ROOT_ID} .contact-link:is(:hover,:focus-visible) .pg-contact-arrow {{transform:translateX(4px);fill:#f0cb85}}
#{ROOT_ID} .nav-link:is(:hover,:focus-visible) .pg-nav-fill {{fill:#263b50}}
#{ROOT_ID} .nav-link:is(:hover,:focus-visible) :is(.pg-nav-projects-chevron,.pg-nav-contact-chevron) {{animation:none;transform:translateY(4px);fill:#f0cb85}}
#{ROOT_ID} section[id] {{scroll-margin-top:20px}}
#{ROOT_ID} .text-view {{margin:22px 28px 0;padding:16px;background:#10192e;color:#c1ccda;font-size:14px;line-height:1.75}}
#{ROOT_ID} .text-view summary {{width:fit-content;padding:8px 12px;color:#a9bdd8;border:1px solid #344969;transition:color 160ms ease,border-color 160ms ease}}
#{ROOT_ID} .text-view summary:is(:hover,:focus-visible) {{color:#edf0d9;border-color:#82cbb9}}
#{ROOT_ID} .text-copy {{padding:10px 0 20px;overflow-wrap:anywhere}}
#{ROOT_ID} .text-copy h2 {{font-size:22px;margin:20px 0 8px;color:#edf0d9}}
#{ROOT_ID} .text-copy h3 {{font-size:17px;margin:24px 0 8px}}
#{ROOT_ID} .text-copy p {{margin:8px 0}}
#{ROOT_ID} .text-copy a {{color:#82cbb9;text-underline-offset:4px}}
#{ROOT_ID} .text-copy a:is(:hover,:focus-visible) {{color:#f0cb85}}
@media(max-width:600px) {{
  #{ROOT_ID} {{margin:0 auto}}
  #{ROOT_ID} .desktop-art {{display:none}}
  #{ROOT_ID} .mobile-art {{display:block}}
  #{ROOT_ID} .text-view {{margin:16px 22px 0}}
}}
@media(prefers-reduced-motion:reduce) {{
  #{ROOT_ID} *,#{ROOT_ID} *::before,#{ROOT_ID} *::after {{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
  #{ROOT_ID} .art-link:is(:hover,:focus-visible) :is(.pc-arrow,.pg-contact-arrow,.pg-nav-projects-chevron,.pg-nav-contact-chevron) {{transform:none}}
}}
</style>"""

    sections = [
        f'<main id="{ROOT_ID}" aria-labelledby="{ROOT_ID}-title">',
        f'<h1 id="{ROOT_ID}-title" class="sr-only">{escape(name)} / {escape(owner)}</h1>',
        '<div class="pixel-band">' + art("world") + '</div>',
        '<nav class="pixel-nav" aria-label="Profil">'
        f'<a class="art-link nav-link" href="#{ROOT_ID}-projekte" aria-label="Zu den Projekten">'
        + art("nav-workbench") + '</a>'
        f'<a class="art-link nav-link" href="#{ROOT_ID}-kontakt" aria-label="Zum Kontakt">'
        + art("nav-contact") + '</a></nav>',
        f'<section class="pixel-band" aria-labelledby="{ROOT_ID}-intro">'
        f'<h2 class="sr-only" id="{ROOT_ID}-intro">Die Werkstatt</h2>'
        f'<p class="sr-only">{escape(config["intro"])}</p>' + art("intro") + '</section>',
        f'<section class="pixel-band" id="{ROOT_ID}-projekte" aria-labelledby="{ROOT_ID}-projects-title">'
        f'<h2 class="sr-only" id="{ROOT_ID}-projects-title">Projekte</h2>' + art("workbench"),
    ]
    text_repos = []
    for index, repo in enumerate(repos, 1):
        url = escape(repo["url"], quote=True)
        repo_name = escape(repo["name"])
        description = _description(repo["description"]) or "Code und weitere Informationen stehen im Repository."
        language = escape(repo.get("language") or "Keine Hauptsprache")
        updated = escape(_date(repo["pushed_at"]))
        label = escape(f'Projekt {index:02d}: {repo["name"]}. Repository öffnen.', quote=True)
        sections.append(f'<a class="art-link repo-link" href="{url}" aria-label="{label}">'
                        + art(f'projects/{repo["id"]}') + '</a>')
        text_repos.append(f'<h3><a href="{url}">{repo_name}</a></h3>'
                          f'<p>{escape(description)}</p><p>{language} · {updated}</p>')
    if not repos:
        sections.append('<p class="sr-only">Aktuell sind keine öffentlichen, aktiven Original-Repositories vorhanden.</p>')
    sections.extend([
        f'<a class="art-link catalog-link" href="{catalog_url}" aria-label="Alle Repositories auf GitHub ansehen">'
        + art("catalog") + '</a></section>',
        f'<section class="pixel-band" id="{ROOT_ID}-kontakt" aria-labelledby="{ROOT_ID}-contact-heading">'
        f'<h2 class="sr-only" id="{ROOT_ID}-contact-heading">Kontakt</h2>'
        f'<a class="art-link contact-link" href="{contact_url}" aria-label="Eine Idee oder eine Frage? Kontakt aufnehmen: einen GitHub-Issue öffnen.">'
        + art("contact") + '</a></section>',
        '<footer class="pixel-band">' + art("endcap") + '</footer>',
        '<details class="text-view"><summary class="cursor-interaction">Textansicht</summary><div class="text-copy">'
        f'<h2>{escape(name)} / {escape(owner)}</h2><p>{escape(config["intro"])}</p>'
        + ''.join(text_repos)
        + f'<p><a href="{catalog_url}">Alle Repositories</a> · '
        f'<a href="{contact_url}">Kontakt aufnehmen</a></p></div></details>',
        '</main>',
    ])
    return ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="description" content="{escape(config["intro"], quote=True)}">\n'
            f'<title>{escape(name)} / {escape(owner)}</title>\n' + css
            + '\n</head>\n<body style="margin:0;background:#0a1120">\n'
            + '\n'.join(sections) + '\n</body>\n</html>\n')
