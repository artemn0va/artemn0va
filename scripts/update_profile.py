"""Refresh versioned profile cards without replacing good SVGs with service errors."""

import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
USERNAME = "artemn0va"
SVG_NS = "http://www.w3.org/2000/svg"
CARD_COLORS = {
    "hide_border": "true",
    "title_color": "00bfbf",
    "text_color": "c9d1d9",
    "bg_color": "0d1117",
    "disable_animations": "true",
    "card_width": "495",
}
CARD_URLS = {
    "stats.svg": "https://github-readme-stats.vercel.app/api?"
    + urllib.parse.urlencode(
        {**CARD_COLORS, "username": USERNAME, "show_icons": "true", "icon_color": "00bfbf"}
    ),
    "languages.svg": "https://github-readme-stats.vercel.app/api/top-langs/?"
    + urllib.parse.urlencode(
        {**CARD_COLORS, "username": USERNAME, "layout": "compact", "langs_count": "8"}
    ),
    "streak.svg": "https://streak-stats.demolab.com/?"
    + urllib.parse.urlencode(
        {
            "user": USERNAME,
            "theme": "black-ice",
            "hide_border": "true",
            "stroke": "0000",
            "background": "0d1117",
            "ring": "00bfbf",
            "fire": "00bfbf",
            "currStreakLabel": "00bfbf",
            "disable_animations": "true",
        }
    ),
}
CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def validate_svg(content):
    root = ET.fromstring(content)
    if root.tag != f"{{{SVG_NS}}}svg":
        raise ValueError("Response is not an SVG")
    text = " ".join(root.itertext()).lower()
    for error in ("something went wrong", "rate limit", "deployment_disabled", "could not fetch"):
        if error in text:
            raise ValueError(f"SVG contains a service error: {error}")
    return content


def download_svg(url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "artemn0va-profile/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.headers.get_content_type() != "image/svg+xml":
                    raise ValueError("Service did not return image/svg+xml")
                return validate_svg(response.read())
        except (OSError, ValueError, ET.ParseError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def write_svg(name, content):
    validate_svg(content)
    ASSETS.mkdir(exist_ok=True)
    target = ASSETS / name
    temporary = target.with_suffix(".svg.tmp")
    temporary.write_bytes(content)
    temporary.replace(target)


def pad_languages_card(content):
    """Match the stats card's canvas without stretching the language text."""
    root = ET.fromstring(content)
    root.set("height", "195")
    root.set("viewBox", "0 0 495 195")
    ET.register_namespace("", SVG_NS)
    return ET.tostring(root, encoding="utf-8")


def load_contributions():
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={CALENDAR_QUERY}", "-f", f"login={USERNAME}"],
        check=True, capture_output=True, text=True, timeout=60,
    )
    payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise ValueError("GitHub could not return the contribution calendar")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {
        day["date"]: day["contributionCount"]
        for week in weeks
        for day in week["contributionDays"]
    }


def render_activity(contributions, today):
    days = [today - timedelta(days=offset) for offset in reversed(range(31))]
    counts = [contributions[day.isoformat()] for day in days]
    if any(type(count) is not int or count < 0 for count in counts):
        raise ValueError("Contribution counts must be non-negative integers")
    ceiling = max(4, math.ceil(max(counts) / 4) * 4)
    points = [(60 + index * 29.5, 210 - count / ceiling * 140) for index, count in enumerate(counts)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    pieces = [
        f'<svg xmlns="{SVG_NS}" width="1000" height="270" viewBox="0 0 1000 270" role="img" aria-labelledby="title desc">',
        '<title id="title">GitHub activity over the last 31 days</title>',
        f'<desc id="desc">{sum(counts)} contributions from {days[0]} through {today}.</desc>',
        '<rect width="1000" height="270" rx="7" fill="#0d1117"/>',
        '<g font-family="Segoe UI, Ubuntu, sans-serif" fill="#c9d1d9">',
        '<text x="30" y="35" font-size="20" font-weight="600" fill="#00bfbf">Contribution activity</text>',
        f'<text x="970" y="35" text-anchor="end" font-size="14">{sum(counts)} contributions / 31 days</text>',
    ]
    for index in range(5):
        y = 210 - index * 35
        pieces.extend([
            f'<path d="M60 {y} H945" stroke="#21262d"/>',
            f'<text x="48" y="{y + 5}" text-anchor="end" font-size="12">{ceiling * index // 4}</text>',
        ])
    pieces.extend([
        f'<polygon points="60,210 {path} 945,210" fill="#00bfbf" fill-opacity="0.12"/>',
        f'<polyline points="{path}" fill="none" stroke="#00bfbf" stroke-width="2.5" stroke-linejoin="round"/>',
    ])
    for day, count, (x, y) in zip(days, counts, points):
        pieces.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#00bfbf">'
            f'<title>{day}: {count} contributions</title></circle>'
        )
    for index in (0, 5, 10, 15, 20, 25, 30):
        label = escape(days[index].strftime("%b %d"))
        pieces.append(f'<text x="{points[index][0]:.1f}" y="240" text-anchor="middle" font-size="12">{label}</text>')
    pieces.append("</g></svg>\n")
    return "\n".join(pieces).encode("utf-8")


def main():
    failures = []
    try:
        today = datetime.now(timezone.utc).date()
        write_svg("activity.svg", render_activity(load_contributions(), today))
        print("Updated activity.svg")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        failures.append(f"activity.svg: {error}")
    for name, url in CARD_URLS.items():
        try:
            content = download_svg(url)
            if name == "languages.svg":
                content = pad_languages_card(content)
            write_svg(name, content)
            print(f"Updated {name}")
        except (OSError, ValueError, ET.ParseError) as error:
            failures.append(f"{name}: {error}")
    for failure in failures:
        print(f"::error::{failure}. Kept the previous SVG.", file=sys.stderr)
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
