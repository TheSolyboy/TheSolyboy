#!/usr/bin/env python3
"""Generate ONE terminal-window SVG that holds the whole profile:

    $ solyfetch            ascii logo + info
    $ ls ~/expertise       tech icons (embedded as base64, self-contained)
    $ github-activity      contribution grid (real data, green squares)
    $ cat ~/stats.log      computed stats (total / streaks / best day)

Everything lives inside a single faux terminal -> the README is just one image.
"""
import base64
import datetime as dt
import re
import sys
import urllib.request

USER = "thesolyboy"

# ---- palette (matches the flame-S logo: aqua -> teal -> blue) -------------
LEVELS = ["#161B22", "#1B4D52", "#2A8A8C", "#39D0C8", "#7DF0E0"]
BG = "#0D1117"
TITLEBAR = "#161B22"
BORDER = "#30363D"
ACCENT = "#39D0C8"       # teal prompt (matches logo)
TEAL = "#39D0C8"         # ascii logo
BLUE = "#6680EE"         # info / stat labels (logo gradient bottom)
TEXT = "#C9D1D9"         # values
MUTED = "#8B949E"

# ---- layout ---------------------------------------------------------------
CELL = 13
SQUARE = 11
RX = 2
PAD = 24
TITLEBAR_H = 40
LINE_H = 15
INFO_X = 268
LABEL_W = 96
LEFT = 34
TOP_LABELS = 22
ICON = 34
ICON_STEP = 48

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def load_ascii():
    """Flame-S logo as ASCII art, loaded from slogo_ascii.txt (committed)."""
    try:
        with open("slogo_ascii.txt", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f]
    except FileNotFoundError:
        return ["S"]


ASCII = load_ascii()
ASCII_FONT = 11          # logo is denser than the info text
ASCII_LH = 12.5

INFO = [
    ("Role", "Young dev from Norway"),
    ("Studying", "IT"),
    ("Learning", "Next.js · Supabase · Coolify"),
    ("Hobbies", "Volleyball · Building projects"),
    ("Editor", "VS Code"),
    ("Shell", "zsh"),
    ("Langs", "Python · HTML · JavaScript"),
    ("Stack", "Docker · n8n · Discord bots"),
]

ICONS = [
    "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg",
    "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg",
    "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-original.svg",
    "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/supabase/supabase-original.svg",
    "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg",
    "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/coolify.png",
    "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/n8n.png",
    "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/discord.png",
]


def get(url, binary=True):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if binary else r.read().decode("utf-8", "replace")


# GitHub's own calendar markup: one <td> per day (date + level) plus a matching
# <tool-tip> carrying the exact count. Read it directly so private contributions
# are included (when "Private contributions" is enabled on the profile) — the
# jogruber third-party API only ever sees public counts and caches them.
CONTRIB_URL = f"https://github.com/users/{USER}/contributions"
_DAY_RE = re.compile(
    r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="(contribution-day-component-\d+-\d+)"'
    r'\s+data-level="(\d)"')
_TIP_RE = re.compile(
    r'<tool-tip[^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>')


def fetch_contributions():
    html = get(CONTRIB_URL, binary=False)
    counts = {}
    for cid, text in _TIP_RE.findall(html):
        m = re.match(r"\s*(No|[\d,]+)\s+contribution", text)
        counts[cid] = 0 if not m or m.group(1) == "No" else int(m.group(1).replace(",", ""))
    days = [
        {"date": date, "level": int(level), "count": counts.get(cid, 0)}
        for date, cid, level in _DAY_RE.findall(html)
    ]
    days.sort(key=lambda d: d["date"])
    if not days:
        raise RuntimeError("Parsed 0 days from GitHub contributions page — "
                           "markup may have changed.")
    return {"total": {"lastYear": sum(d["count"] for d in days)},
            "contributions": days}


def icon_datauri(url):
    raw = get(url)
    mime = "image/svg+xml" if url.endswith(".svg") else "image/png"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def build_weeks(days):
    first = dt.date.fromisoformat(days[0]["date"])
    pad = (first.weekday() + 1) % 7
    cells = [None] * pad + days
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


def compute_stats(days):
    counts = [d["count"] for d in days]
    total = sum(counts)
    # current streak (a trailing zero == "today, not done yet" is ignored)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    cur = 0
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    # longest streak
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    best = max(counts) if counts else 0
    return total, cur, longest, best


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data, icons):
    days = data["contributions"]
    year_total = data["total"]["lastYear"]
    total, cur, longest, best = compute_stats(days)
    weeks = build_weeks(days)
    ncols = len(weeks)

    grid_w = ncols * CELL
    width = LEFT + grid_w + PAD * 2
    gx = LEFT + PAD

    out = []
    a = out.append

    # ---- vertical cursor ----
    p1 = TITLEBAR_H + 28
    fetch_top = p1 + 22
    fetch_bottom = fetch_top + max(len(ASCII) * ASCII_LH, 11 * LINE_H)
    p2 = fetch_bottom + 26
    icons_y = p2 + 12
    p3 = icons_y + ICON + 30
    grid_top = p3 + TOP_LABELS + 8
    legend_y = grid_top + 7 * CELL + 18
    p4 = legend_y + SQUARE + 26
    stats_top = p4 + 20
    height = stats_top + 4 * LINE_H + PAD - 6

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
      f'viewBox="0 0 {width} {height}" '
      f'font-family="\'Cascadia Code\',\'Fira Code\',\'JetBrains Mono\',Consolas,monospace">')

    # window + title bar
    a(f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="10" '
      f'fill="{BG}" stroke="{BORDER}"/>')
    a(f'<path d="M0 10 a10 10 0 0 1 10 -10 h{width-20} a10 10 0 0 1 10 10 '
      f'v{TITLEBAR_H-10} h-{width} z" fill="{TITLEBAR}"/>')
    for i, c in enumerate(["#FF5F56", "#FFBD2E", "#27C93F"]):
        a(f'<circle cx="{22 + i*20}" cy="{TITLEBAR_H/2}" r="6" fill="{c}"/>')
    a(f'<text x="{width/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12.5" '
      f'text-anchor="middle">soly@norway — zsh</text>')

    # ---- $ solyfetch ----
    a(f'<text x="{PAD}" y="{p1}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan><tspan fill="{TEXT}"> solyfetch</tspan></text>')
    for i, line in enumerate(ASCII):
        a(f'<text x="{PAD}" y="{fetch_top + i*ASCII_LH}" fill="{TEAL}" '
          f'font-size="{ASCII_FONT}" xml:space="preserve">{esc(line)}</text>')
    a(f'<text x="{INFO_X}" y="{fetch_top}" font-size="12.5">'
      f'<tspan fill="{ACCENT}">soly</tspan><tspan fill="{MUTED}">@</tspan>'
      f'<tspan fill="{BLUE}">norway</tspan></text>')
    a(f'<text x="{INFO_X}" y="{fetch_top + 8}" fill="{BORDER}" font-size="12" '
      f'xml:space="preserve">{"─" * 30}</text>')
    for i, (label, value) in enumerate(INFO):
        y = fetch_top + (i + 2) * LINE_H + 2
        a(f'<text x="{INFO_X}" y="{y}" fill="{BLUE}" font-size="12.5">{esc(label)}</text>')
        a(f'<text x="{INFO_X + LABEL_W}" y="{y}" fill="{TEXT}" font-size="12.5">{esc(value)}</text>')
    socy = fetch_top + (len(INFO) + 2) * LINE_H + 2
    a(f'<text x="{INFO_X}" y="{socy + 8}" fill="{BORDER}" font-size="12" '
      f'xml:space="preserve">{"─" * 30}</text>')
    a(f'<text x="{INFO_X}" y="{socy + LINE_H + 6}" font-size="12.5">'
      f'<tspan fill="{ACCENT}">◉ ◉ ◉</tspan>'
      f'<tspan fill="{TEXT}">   LinkedIn · YouTube · Twitter</tspan></text>')

    # ---- $ ls ~/expertise ----
    a(f'<text x="{PAD}" y="{p2}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan><tspan fill="{TEXT}"> ls ~/expertise</tspan></text>')
    for i, uri in enumerate(icons):
        x = PAD + 4 + i * ICON_STEP
        a(f'<image href="{uri}" x="{x}" y="{icons_y}" width="{ICON}" height="{ICON}" '
          f'preserveAspectRatio="xMidYMid meet"/>')

    # ---- $ github-activity --year ----
    a(f'<text x="{PAD}" y="{p3}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan>'
      f'<tspan fill="{TEXT}"> github-activity --year</tspan>'
      f'<tspan fill="{MUTED}">  # {year_total:,} contributions</tspan></text>')
    last_month = None
    for col, week in enumerate(weeks):
        fd = next((d for d in week if d), None)
        if not fd:
            continue
        m = dt.date.fromisoformat(fd["date"]).month
        if m != last_month:
            last_month = m
            a(f'<text x="{gx + col*CELL}" y="{grid_top - 8}" fill="{MUTED}" '
              f'font-size="11">{MONTHS[m-1]}</text>')
    for row, lbl in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        a(f'<text x="{PAD - 2}" y="{grid_top + row*CELL + SQUARE - 1}" fill="{MUTED}" '
          f'font-size="11">{lbl}</text>')
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            lvl = day["level"] if day else 0
            a(f'<rect x="{gx + col*CELL}" y="{grid_top + row*CELL}" width="{SQUARE}" '
              f'height="{SQUARE}" rx="{RX}" fill="{LEVELS[lvl]}"/>')
    # legend
    more_x = width - PAD
    a(f'<text x="{more_x}" y="{legend_y + SQUARE - 1}" fill="{MUTED}" '
      f'font-size="11" text-anchor="end">More</text>')
    first_sq_x = (more_x - 36) - 5 * CELL
    for i, c in enumerate(LEVELS):
        a(f'<rect x="{first_sq_x + i*CELL}" y="{legend_y}" width="{SQUARE}" '
          f'height="{SQUARE}" rx="{RX}" fill="{c}"/>')
    a(f'<text x="{first_sq_x - 6}" y="{legend_y + SQUARE - 1}" fill="{MUTED}" '
      f'font-size="11" text-anchor="end">Less</text>')

    # ---- $ cat ~/stats.log ----
    a(f'<text x="{PAD}" y="{p4}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan><tspan fill="{TEXT}"> cat ~/stats.log</tspan></text>')
    stats = [
        ("total", f"{total:,} contributions"),
        ("current streak", f"{cur} day{'s' if cur != 1 else ''} 🔥"),
        ("longest streak", f"{longest} days"),
        ("best day", f"{best} contributions"),
    ]
    for i, (label, value) in enumerate(stats):
        y = stats_top + i * LINE_H
        a(f'<text x="{PAD + 4}" y="{y}" fill="{BLUE}" font-size="12.5">{esc(label)}</text>')
        a(f'<text x="{PAD + 4 + 130}" y="{y}" fill="{TEXT}" font-size="12.5">{esc(value)}</text>')

    a('</svg>')
    return "\n".join(out)


def main():
    data = fetch_contributions()
    icons = [icon_datauri(u) for u in ICONS]
    svg = render(data, icons)
    with open("terminal.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote terminal.svg ({data['total']['lastYear']} contributions, "
          f"{len(icons)} icons embedded)")


if __name__ == "__main__":
    sys.exit(main())
