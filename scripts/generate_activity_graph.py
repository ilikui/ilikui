#!/usr/bin/env python3
"""Generate a self-hosted SVG chart from the public GitHub Events API.

This visualizes observable public events, not the full private contribution
calendar. GitHub's public Events API is capped at 300 recent events.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

USERNAME = "ilikui"
OUT = Path("assets/activity-graph.svg")
UTC = timezone.utc
NOW = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
START = (NOW - timedelta(days=30)).date()
END = NOW.date()
COUNTS = Counter()
event_count = 0
oldest_seen = None

for page in range(1, 4):
    url = f"https://api.github.com/users/{USERNAME}/events?per_page=100&page={page}"
    req = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ilikui-profile-activity-graph",
    })
    try:
        with urlopen(req, timeout=20) as response:
            events = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SystemExit(f"GitHub Events API request failed: {exc}") from exc

    if not events:
        break
    event_count += len(events)
    stop = False
    for event in events:
        try:
            dt = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")).astimezone(UTC)
        except (KeyError, ValueError):
            continue
        oldest_seen = dt
        if dt.date() < START:
            stop = True
            continue
        if dt.date() <= END:
            COUNTS[dt.date()] += 1
    if stop or len(events) < 100:
        break

days = [START + timedelta(days=i) for i in range(31)]
values = [COUNTS[d] for d in days]
max_value = max(values, default=0)
plot_x, plot_y, plot_w, plot_h = 62, 82, 806, 125
bar_gap = 5
bar_w = (plot_w - bar_gap * 30) / 31
base_y = plot_y + plot_h
grid = []
for fraction in (0, 0.5, 1):
    y = plot_y + plot_h * fraction
    grid.append(f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x + plot_w}" y2="{y:.1f}" stroke="#273449" stroke-width="1"/>')
bars = []
for i, (day, value) in enumerate(zip(days, values)):
    x = plot_x + i * (bar_w + bar_gap)
    height = 3 if max_value == 0 else max(3, plot_h * value / max_value)
    y = base_y - height
    color = "#334155" if value == 0 else ("#0e7490" if value < max_value * 0.5 else "#22d3ee")
    bars.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{height:.2f}" rx="3" fill="{color}"><title>{day.isoformat()}: {value} public events</title></rect>')

week_labels = []
for i in (0, 7, 14, 21, 28, 30):
    x = plot_x + i * (bar_w + bar_gap) + bar_w / 2
    label = days[i].strftime("%b %d")
    week_labels.append(f'<text x="{x:.1f}" y="{base_y + 25}" text-anchor="middle" fill="#94a3b8" font-size="11">{escape(label)}</text>')

total = sum(values)
latest = NOW.strftime("%Y-%m-%d %H:%M UTC")
note = "Public GitHub events · last 31 days · up to 300 recent API events"
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="285" viewBox="0 0 920 285" role="img" aria-labelledby="title desc">
<title id="title">GitHub public activity for {USERNAME}</title>
<desc id="desc">{total} public events observed in the last 31 days. Generated at {latest}. This chart is based on the public Events API and does not include private contributions.</desc>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1220"/><stop offset="1" stop-color="#111827"/></linearGradient></defs>
<rect width="920" height="285" rx="18" fill="url(#bg)"/>
<text x="34" y="37" fill="#f8fafc" font-size="18" font-family="Inter,Segoe UI,Arial,sans-serif" font-weight="700">PUBLIC ACTIVITY</text>
<text x="34" y="58" fill="#94a3b8" font-size="11" font-family="Inter,Segoe UI,Arial,sans-serif">@{USERNAME} · observable events</text>
<text x="884" y="39" text-anchor="end" fill="#67e8f9" font-size="25" font-family="Inter,Segoe UI,Arial,sans-serif" font-weight="700">{total}</text>
<text x="884" y="58" text-anchor="end" fill="#94a3b8" font-size="10" font-family="Inter,Segoe UI,Arial,sans-serif">events sampled</text>
{''.join(grid)}
{''.join(bars)}
{''.join(week_labels)}
<text x="34" y="255" fill="#64748b" font-size="10" font-family="Inter,Segoe UI,Arial,sans-serif">{escape(note)}</text>
<text x="884" y="255" text-anchor="end" fill="#64748b" font-size="10" font-family="Inter,Segoe UI,Arial,sans-serif">Updated {escape(latest)}</text>
</svg>
'''
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"Wrote {OUT}; {total} public events sampled across {len(days)} days.")
