#!/usr/bin/env python3
"""Build the images the profile README is made of.

    assets/header.svg    the banner, rounded corners
    assets/toolkit.svg   tool icons in one row
    assets/activity.svg  contribution grid (refreshed by the workflow)

Toolkit and activity have transparent backgrounds so they sit on GitHub's own
light or dark page. Everything is embedded as base64, since GitHub renders
README SVGs through <img> and blocks external requests from inside them.
"""
import base64
import datetime as dt
import os
import re
import sys
import urllib.request

USER = "thesolyboy"
NAME = "Soly"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

# Gold, taken from the sun in the banner. Readable on light and dark pages.
GOLD = "#E9A64E"
LEVELS = [0.35, 0.55, 0.78, 1.0]                         # opacity, level 1..4
EMPTY = "#8B949E"                                        # drawn at low opacity
MONO = "#8B949E"                                         # tint for black marks

DASH = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons"
DEVI = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons"
# (url, tint) - tint=True for black marks that vanish on a dark page
ICONS = [
    (f"{DEVI}/html5/html5-original.svg", False),
    (f"{DEVI}/python/python-original.svg", False),
    (f"{DEVI}/ubuntu/ubuntu-original.svg", False),
    (f"{DEVI}/supabase/supabase-original.svg", False),
    (f"{DEVI}/docker/docker-original.svg", False),
    (f"{DASH}/svg/proxmox.svg", False),
    (f"{DASH}/svg/opnsense.svg", False),
    (f"{DASH}/png/coolify.png", False),
    (f"{DASH}/png/n8n.png", False),
    (f"{DASH}/png/discord.png", False),
    (f"{DASH}/svg/claude-ai.svg", False),
    (f"{DASH}/svg/chatgpt.svg", False),
    (f"{DASH}/svg/perplexity.svg", False),
    (f"{DASH}/svg/hermes.svg", True),        # NousResearch Hermes
    (f"{DASH}/svg/openclaw.svg", False),
]


def get(url, binary=True):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if binary else r.read().decode("utf-8", "replace")


def datauri(raw, mime):
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


# GitHub's own calendar markup: one <td> per day with date and level. Read
# directly so private contributions count when they are shown on the profile.
CONTRIB_URL = f"https://github.com/users/{USER}/contributions"
_DAY_RE = re.compile(
    r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="contribution-day-component-\d+-\d+"'
    r'\s+data-level="(\d)"')


def fetch_days():
    days = sorted(_DAY_RE.findall(get(CONTRIB_URL, binary=False)))
    if not days:
        raise RuntimeError("Parsed 0 days from GitHub contributions page — "
                           "markup may have changed.")
    return [(d, int(lvl)) for d, lvl in days]


def svg_open(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">')


def render_header(banner_uri, w=1400, h=502):
    serif = "Georgia,'Iowan Old Style','Palatino Linotype',Palatino,serif"
    return "\n".join([
        svg_open(w, h),
        '<defs>',
        f'<clipPath id="r"><rect width="{w}" height="{h}" rx="14"/></clipPath>',
        '<linearGradient id="dim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0.45" stop-color="#0d1117" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#0d1117" stop-opacity="0.55"/></linearGradient>',
        '<filter id="shadow" x="-20%" y="-40%" width="140%" height="180%">'
        '<feDropShadow dx="0" dy="3" stdDeviation="8" flood-color="#000" '
        'flood-opacity="0.6"/></filter>',
        '</defs>',
        '<g clip-path="url(#r)">',
        f'<image href="{banner_uri}" width="{w}" height="{h}" '
        'preserveAspectRatio="xMidYMid slice"/>',
        f'<rect width="{w}" height="{h}" fill="url(#dim)"/>',
        '</g>',
        f'<text x="{w / 2}" y="{h - 70}" text-anchor="middle" fill="#FBF3E4" '
        f'font-family="{serif}" font-size="112" filter="url(#shadow)">{NAME}</text>',
        '</svg>'])


def render_toolkit(icons, size=34, step=52):
    w = (len(icons) - 1) * step + size
    out = [svg_open(w, size),
           f'<filter id="mono"><feFlood flood-color="{MONO}"/>'
           '<feComposite in2="SourceAlpha" operator="in"/></filter>']
    for i, (uri, tint) in enumerate(icons):
        f = ' filter="url(#mono)"' if tint else ""
        out.append(f'<image href="{uri}" x="{i * step}" width="{size}" height="{size}" '
                   f'preserveAspectRatio="xMidYMid meet"{f}/>')
    out.append('</svg>')
    return "\n".join(out)


def render_activity(days, cell=15, sq=12):
    first = dt.date.fromisoformat(days[0][0])
    cells = [None] * ((first.weekday() + 1) % 7) + days
    weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)]
    out = [svg_open(len(weeks) * cell - (cell - sq), 7 * cell - (cell - sq))]
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            if day is None:
                continue
            lvl = day[1]
            fill = (f'fill="{EMPTY}" fill-opacity="0.16"' if lvl == 0
                    else f'fill="{GOLD}" fill-opacity="{LEVELS[lvl - 1]}"')
            out.append(f'<rect x="{col * cell}" y="{row * cell}" width="{sq}" '
                       f'height="{sq}" rx="3" {fill}/>')
    out.append('</svg>')
    return "\n".join(out)


def write(name, svg):
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote assets/{name} ({len(svg) // 1024} KB)")


def main():
    with open(os.path.join(ASSETS, "banner.jpg"), "rb") as f:
        write("header.svg", render_header(datauri(f.read(), "image/jpeg")))
    icons = []
    for url, tint in ICONS:
        try:
            mime = "image/svg+xml" if url.endswith(".svg") else "image/png"
            icons.append((datauri(get(url), mime), tint))
        except Exception as e:  # noqa: BLE001 - a dead icon must not fail the run
            print(f"::warning::icon skipped {url}: {e}", file=sys.stderr)
    write("toolkit.svg", render_toolkit(icons))
    write("activity.svg", render_activity(fetch_days()))


if __name__ == "__main__":
    sys.exit(main())
