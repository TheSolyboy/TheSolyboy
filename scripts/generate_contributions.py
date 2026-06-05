#!/usr/bin/env python3
"""Generate a terminal-window SVG of the GitHub contribution grid.

Fetches real contribution data from the public jogruber API and renders it as
green rounded squares inside a faux terminal window, matching the GitHub
contribution heatmap but styled to live "inside the terminal".
"""
import datetime as dt
import json
import sys
import urllib.request

USER = "thesolyboy"

# ---- GitHub dark contribution palette -------------------------------------
LEVELS = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]
BG = "#0D1117"
TITLEBAR = "#161B22"
BORDER = "#30363D"
ACCENT = "#2BD96B"
MUTED = "#8B949E"

# ---- Layout ---------------------------------------------------------------
CELL = 13          # square + gap
SQUARE = 11        # square size
RX = 2             # corner radius
PAD = 22           # inner padding
LEFT = 34          # space for day labels
TOP_LABELS = 22    # space for month labels
TITLEBAR_H = 38
PROMPT_H = 30
LEGEND_H = 34

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch():
    url = f"https://github-contributions-api.jogruber.de/v4/{USER}?y=last"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def build_weeks(days):
    """Organise daily entries into GitHub-style week columns (Sun..Sat)."""
    # pad the front so the first day sits on its real weekday row
    first = dt.date.fromisoformat(days[0]["date"])
    pad = (first.weekday() + 1) % 7  # Python Mon=0; GitHub grid Sun=0
    cells = [None] * pad + days
    weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)]
    return weeks


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data):
    days = data["contributions"]
    total = data["total"]["lastYear"]
    weeks = build_weeks(days)
    ncols = len(weeks)

    grid_w = ncols * CELL
    width = LEFT + grid_w + PAD * 2
    height = TITLEBAR_H + PROMPT_H + TOP_LABELS + 7 * CELL + LEGEND_H + PAD

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
      f'viewBox="0 0 {width} {height}" font-family="\'Cascadia Code\',\'Fira Code\',\'JetBrains Mono\',Consolas,monospace">')

    # window
    a(f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="10" '
      f'fill="{BG}" stroke="{BORDER}"/>')
    # title bar
    a(f'<path d="M0 10 a10 10 0 0 1 10 -10 h{width-20} a10 10 0 0 1 10 10 v{TITLEBAR_H-10} h-{width} z" '
      f'fill="{TITLEBAR}"/>')
    for i, c in enumerate(["#FF5F56", "#FFBD2E", "#27C93F"]):
        a(f'<circle cx="{20 + i*20}" cy="{TITLEBAR_H/2}" r="6" fill="{c}"/>')
    a(f'<text x="{width/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
      f'text-anchor="middle">solyboy@github: ~/contributions</text>')

    # prompt line
    py = TITLEBAR_H + 20
    a(f'<text x="{PAD}" y="{py}" font-size="13">'
      f'<tspan fill="{ACCENT}">$</tspan>'
      f'<tspan fill="#C9D1D9"> github-activity --year</tspan>'
      f'<tspan fill="{MUTED}">  # {total:,} contributions</tspan></text>')

    gx = LEFT + PAD
    gy = TITLEBAR_H + PROMPT_H + TOP_LABELS

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

    # day labels (Mon / Wed / Fri)
    for row, lbl in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        a(f'<text x="{PAD - 2}" y="{gy + row*CELL + SQUARE - 1}" fill="{MUTED}" '
          f'font-size="11" text-anchor="start">{lbl}</text>')

    # squares
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            lvl = day["level"] if day else 0
            x = gx + col * CELL
            y = gy + row * CELL
            a(f'<rect x="{x}" y="{y}" width="{SQUARE}" height="{SQUARE}" rx="{RX}" '
              f'fill="{LEVELS[lvl]}"/>')

    # legend  (Less  [][][][][]  More) laid out right-to-left
    ly = gy + 7 * CELL + 20
    more_x = width - PAD
    a(f'<text x="{more_x}" y="{ly + SQUARE - 1}" fill="{MUTED}" font-size="11" '
      f'text-anchor="end">More</text>')
    squares_right = more_x - 36
    first_sq_x = squares_right - 5 * CELL
    for i, c in enumerate(LEVELS):
        lx = first_sq_x + i * CELL
        a(f'<rect x="{lx}" y="{ly}" width="{SQUARE}" height="{SQUARE}" rx="{RX}" fill="{c}"/>')
    a(f'<text x="{first_sq_x - 6}" y="{ly + SQUARE - 1}" fill="{MUTED}" font-size="11" '
      f'text-anchor="end">Less</text>')

    a('</svg>')
    return "\n".join(out)


def main():
    data = fetch()
    svg = render(data)
    with open("contributions.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote contributions.svg ({data['total']['lastYear']} contributions)")


if __name__ == "__main__":
    sys.exit(main())
