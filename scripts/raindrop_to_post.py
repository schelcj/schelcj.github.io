#!/usr/bin/env python3
"""Create one Jekyll post containing Raindrop bookmarks from the last N days."""
import json, os, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.raindrop.io/rest/v1/raindrops/0"
ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"

def date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

def api_page(token, page, per_page):
    qs = urlencode({"page": page, "perpage": per_page, "sort": "-created"})
    req = Request(f"{API}?{qs}", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        "User-Agent": "raindrop-jekyll-post-publisher/1.0",
    })
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Raindrop API HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Raindrop API: {exc}") from exc

def fetch_recent(token, cutoff, per_page):
    found, page = [], 0
    while True:
        payload = api_page(token, page, per_page)
        if payload.get("result") is False:
            raise RuntimeError(f"Raindrop API reported failure: {payload}")
        items = payload.get("items") or []
        if not items:
            break
        older = False
        now = datetime.now(timezone.utc)
        for item in items:
            try:
                created = date(item["created"])
            except (KeyError, TypeError, ValueError):
                print(f"Skipping bookmark with invalid created timestamp: {item.get('_id')}", file=sys.stderr)
                continue
            if created < cutoff:
                older = True
            elif created <= now:
                found.append(item)
        if older or len(items) < per_page:
            break
        page += 1
        time.sleep(0.15)
    unique = {str(x["_id"]): x for x in found if x.get("_id") is not None}
    return sorted(unique.values(), key=lambda x: date(x["created"]), reverse=True)

def md_text(value):
    value = str(value or "").replace("\\", "\\\\").replace("\r", " ").replace("\n", " ")
    for char in ("`", "*", "_", "{", "}", "[", "]", "<", ">", "|"):
        value = value.replace(char, "\\" + char)
    return value.strip()

def link_url(value):
    value = str(value or "").strip()
    return value.replace(" ", "%20").replace("(", "%28").replace(")", "%29") if value.startswith(("https://", "http://")) else ""

def render(items, now, days):
    lines = [
        "---",
        f'title: "Weekly links for WK{now:%V}"',
        f"date: {now.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "categories: [links]",
        "tags: [bookmarks]",
        "---", "",
        f"Links I've collected this week...",""
    ]
    if not items:
        lines += ["Nothing this week...",""]
    for item in items:
        title = md_text(item.get("title") or item.get("link") or "Untitled bookmark")
        url = link_url(item.get("link"))
        lines.append(f"- [{title}]({url})" if url else f"- {title}")
        excerpt = md_text(item.get("excerpt"))
        if excerpt:
            lines.append(f"  - {excerpt}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def main():
    token = os.environ.get("RAINDROP_TOKEN", "").strip()
    if not token:
        print("ERROR: RAINDROP_TOKEN is required.", file=sys.stderr)
        return 2
    try:
        days = float(os.environ.get("DAYS", "7"))
        per_page = int(os.environ.get("RAINDROP_PER_PAGE", "50"))
        if days <= 0 or per_page < 1:
            raise ValueError("DAYS and RAINDROP_PER_PAGE must be positive")
    except ValueError as exc:
        print(f"ERROR: invalid configuration: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    try:
        items = fetch_recent(token, now - timedelta(days=days), per_page)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    POSTS.mkdir(parents=True, exist_ok=True)
    # One post per UTC date; reruns that day replace the same post.
    path = POSTS / f"{now:%Y-%m-%d}-links.md"
    path.write_text(render(items, now, days), encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)} with {len(items)} bookmarks.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
