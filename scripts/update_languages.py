"""Generate a public language summary from the owner's accessible repositories."""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

API = "https://api.github.com"
COLORS = ["#3572A5", "#f1e05a", "#563d7c", "#e34c26", "#b07219", "#00ADD8"]


def get(path, token):
    request = Request(API + path, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "primeXraptor-language-card",
    })
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        # Do not log response bodies or authentication headers.
        raise RuntimeError(f"GitHub API returned HTTP {error.code}; check token access.") from None


def collect(owner, token, fetch=get):
    if fetch("/user", token)["login"].lower() != owner.lower():
        raise RuntimeError("The token must belong to the profile owner.")
    totals = Counter()
    count = 0
    private_count = 0
    page = 1
    while True:
        repos = fetch(f"/user/repos?affiliation=owner&visibility=all&per_page=100&page={page}", token)
        if not repos:
            break
        for repo in repos:
            if repo["owner"]["login"].lower() != owner.lower() or repo["fork"]:
                continue
            name = quote(repo["full_name"], safe="/")
            totals.update(fetch(f"/repos/{name}/languages", token))
            count += 1
            private_count += bool(repo["private"])
        page += 1
    if not private_count:
        raise RuntimeError("No owned private repositories were visible; refusing a public-only update.")
    if not totals or sum(totals.values()) == 0:
        raise RuntimeError("No language bytes returned; preserving the existing card.")
    return totals


def render(totals, timestamp):
    languages = totals.most_common(6)
    remainder = sum(totals.values()) - sum(value for _, value in languages)
    if remainder:
        languages.append(("Other", remainder))
    total = sum(totals.values())
    height = 110 + ((len(languages) + 1) // 2) * 24
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="{height}" viewBox="0 0 495 {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Most Used Languages</title>',
             '<desc id="desc">Language bytes across accessible owned public and private repositories, excluding forks.</desc>',
             f'<rect x="0.5" y="0.5" width="494" height="{height-1}" rx="6" fill="#151515" stroke="#c9d1d9"/>',
             '<g font-family="Arial, sans-serif"><text x="24" y="35" fill="#fff" font-size="18" font-weight="600">Most Used Languages</text>']
    x = 24.0
    for index, (language, value) in enumerate(languages):
        color = COLORS[index] if index < len(COLORS) else "#8b949e"
        width = 447 * value / total
        parts.append(f'<rect x="{x:.3f}" y="55" width="{width:.3f}" height="9" fill="{color}"/>')
        x += width
        col = 24 + (index % 2) * 232
        row = 89 + (index // 2) * 24
        parts.append(f'<circle cx="{col+5}" cy="{row-4}" r="5" fill="{color}"/><text x="{col+16}" y="{row}" fill="#b8b8b8" font-size="12">{escape(language)} {100*value/total:.2f}%</text>')
    parts.append(f'<text x="24" y="{height-15}" fill="#8b949e" font-size="10">Public + private · updated {escape(timestamp)} UTC</text></g></svg>')
    return "\n".join(parts) + "\n"


def main():
    token = os.environ.get("PRIVATE_STATS_TOKEN")
    if not token:
        raise RuntimeError("Set the PRIVATE_STATS_TOKEN Actions secret before running this job.")
    owner = os.environ.get("PROFILE_OWNER", "primeXraptor")
    totals = collect(owner, token)
    output = Path(__file__).resolve().parents[1] / "assets/top-languages.svg"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    output.write_text(render(totals, timestamp), encoding="utf-8")


if __name__ == "__main__":
    main()
