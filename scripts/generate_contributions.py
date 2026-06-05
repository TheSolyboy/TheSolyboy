#!/usr/bin/env python3
"""Generate ONE terminal-window SVG containing both the neofetch-style info
block (solyfetch) and the GitHub contribution grid, rendered as green squares.

Everything lives inside a single faux terminal so the contribution graph is
"in the terminal" rather than a separate widget.
"""
import datetime as dt
import json
import sys
import urllib.request

USER = "thesolyboy"

# ---- palette --------------------------------------------------------------
LEVELS = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
BG = "#0D1117"
TITLEBAR = "#161B22"
BORDER = "#30363D"
ACCENT = "#2BD96B"       # green prompt
TEAL = "#39D0C8"         # ascii logo
BLUE = "#58A6FF"         # info labels
TEXT = "#C9D1D9"         # values
MUTED = "#8B949E"

# ---- layout ---------------------------------------------------------------
CELL = 13
SQUARE = 11
RX = 2
PAD = 24
TITLEBAR_H = 40
LINE_H = 15
INFO_X = 268             # where the info column starts
LABEL_W = 96             # gap between label and value
LEFT = 34                # day-label gutter for the grid
TOP_LABELS = 22

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

ASCII = [
    "           .o+`",
    "          `ooo/",
    "         `+oooo:",
    "        `+oooooo:",
    "        -+oooooo+:",
    "      `/:-:++oooo+:",
    "     `/++++/+++++++:",
    "    `/++++++++++++++:",
    "   `/+++ooooooooooooo/`",
    "  ./ooosssso++osssssso+`",
    " .oossssso-````/ossssss+`",
    "-osssssso.      :ssssssso.",
    ":osssssss/      osssso+++.",
    "/ossssssss/     +ssssooo/-",
    "`/ossssso+/:-   -:/+osssso+-",
    " `+sso+:-`       `.-/+oso:",
    "  `++:.            `-/+/",
    "    .`                `/",
]

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


def fetch():
    url = f"https://github-contributions-api.jogruber.de/v4/{USER}?y=last"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def build_weeks(days):
    first = dt.date.fromisoformat(days[0]["date"])
    pad = (first.weekday() + 1) % 7  # Python Mon=0 -> grid Sun=0
    cells = [None] * pad + days
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data):
    days = data["contributions"]
    total = data["total"]["lastYear"]
    weeks = build_weeks(days)
    ncols = len(weeks)

    grid_w = ncols * CELL
    width = LEFT + grid_w + PAD * 2

    # vertical rhythm
    prompt1_y = TITLEBAR_H + 28
    fetch_y0 = TITLEBAR_H + 52          # first ascii / info baseline
    fetch_bottom = fetch_y0 + (len(ASCII) - 1) * LINE_H
    prompt2_y = fetch_bottom + 34
    gy = prompt2_y + TOP_LABELS + 8     # grid squares top
    legend_y = gy + 7 * CELL + 20
    height = legend_y + SQUARE + PAD

    out = []
    a = out.append
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

    # ---- prompt 1: solyfetch ----
    a(f'<text x="{PAD}" y="{prompt1_y}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan>'
      f'<tspan fill="{TEXT}"> solyfetch</tspan></text>')

    # ascii logo
    for i, line in enumerate(ASCII):
        y = fetch_y0 + i * LINE_H
        a(f'<text x="{PAD}" y="{y}" fill="{TEAL}" font-size="12" '
          f'xml:space="preserve">{esc(line)}</text>')

    # info header + rows
    a(f'<text x="{INFO_X}" y="{fetch_y0}" font-size="12.5">'
      f'<tspan fill="{ACCENT}">soly</tspan>'
      f'<tspan fill="{MUTED}">@</tspan>'
      f'<tspan fill="{BLUE}">norway</tspan></text>')
    a(f'<text x="{INFO_X}" y="{fetch_y0 + 8}" fill="{BORDER}" font-size="12" '
      f'xml:space="preserve">{"─" * 30}</text>')
    for i, (label, value) in enumerate(INFO):
        y = fetch_y0 + (i + 2) * LINE_H + 2
        a(f'<text x="{INFO_X}" y="{y}" font-size="12.5">'
          f'<tspan fill="{BLUE}">{esc(label)}</tspan></text>')
        a(f'<text x="{INFO_X + LABEL_W}" y="{y}" fill="{TEXT}" font-size="12.5">'
          f'{esc(value)}</text>')
    socy = fetch_y0 + (len(INFO) + 2) * LINE_H + 2
    a(f'<text x="{INFO_X}" y="{socy + 8}" fill="{BORDER}" font-size="12" '
      f'xml:space="preserve">{"─" * 30}</text>')
    a(f'<text x="{INFO_X}" y="{socy + LINE_H + 6}" font-size="12.5">'
      f'<tspan fill="{ACCENT}">◉ ◉ ◉</tspan>'
      f'<tspan fill="{TEXT}">   LinkedIn · YouTube · Twitter</tspan></text>')

    # ---- prompt 2: github-activity ----
    a(f'<text x="{PAD}" y="{prompt2_y}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan>'
      f'<tspan fill="{TEXT}"> github-activity --year</tspan>'
      f'<tspan fill="{MUTED}">  # {total:,} contributions</tspan></text>')

    gx = LEFT + PAD

    # month labels
    last_month = None
    for col, week in enumerate(weeks):
        first_day = next((d for d in week if d), None)
        if not first_day:
            continue
        m = dt.date.fromisoformat(first_day["date"]).month
        if m != last_month:
            last_month = m
            a(f'<text x="{gx + col*CELL}" y="{gy - 8}" fill="{MUTED}" '
              f'font-size="11">{MONTHS[m-1]}</text>')

    # day labels
    for row, lbl in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        a(f'<text x="{PAD - 2}" y="{gy + row*CELL + SQUARE - 1}" fill="{MUTED}" '
          f'font-size="11">{lbl}</text>')

    # squares
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            lvl = day["level"] if day else 0
            x = gx + col * CELL
            y = gy + row * CELL
            a(f'<rect x="{x}" y="{y}" width="{SQUARE}" height="{SQUARE}" rx="{RX}" '
              f'fill="{LEVELS[lvl]}"/>')

    # legend
    more_x = width - PAD
    a(f'<text x="{more_x}" y="{legend_y + SQUARE - 1}" fill="{MUTED}" '
      f'font-size="11" text-anchor="end">More</text>')
    squares_right = more_x - 36
    first_sq_x = squares_right - 5 * CELL
    for i, c in enumerate(LEVELS):
        lx = first_sq_x + i * CELL
        a(f'<rect x="{lx}" y="{legend_y}" width="{SQUARE}" height="{SQUARE}" rx="{RX}" fill="{c}"/>')
    a(f'<text x="{first_sq_x - 6}" y="{legend_y + SQUARE - 1}" fill="{MUTED}" '
      f'font-size="11" text-anchor="end">Less</text>')

    a('</svg>')
    return "\n".join(out)


def main():
    data = fetch()
    svg = render(data)
    with open("terminal.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote terminal.svg ({data['total']['lastYear']} contributions)")


if __name__ == "__main__":
    sys.exit(main())
