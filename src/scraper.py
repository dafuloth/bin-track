"""HTTP client and CLI entrypoint for scraping Brent WasteWorks."""

from __future__ import annotations

from datetime import datetime, timezone
import http.cookiejar
import os
from pathlib import Path
import sys
import time
import urllib.request

from src.parser import is_loading_html, parse_waste_html
from src.render import render_html
from src.storage import load_store, merge_snapshots, save_store

BASE_URL = "https://recyclingservices.brent.gov.uk/waste/{property_id}"
USER_AGENT = "bin-track/1.0 (+https://github.com/)"


def fetch_waste_html(
    property_id: str,
    *,
    max_attempts: int = 15,
    poll_interval_seconds: float = 2.0,
    timeout_seconds: float = 15.0,
) -> str:
    """Fetch the loaded WasteWorks HTML fragment by establishing a session and polling."""
    if not property_id.strip():
        raise ValueError("WASTE_PROPERTY_ID must not be empty.")

    url = BASE_URL.format(property_id=property_id.strip())
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    initial_req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(initial_req, timeout=timeout_seconds) as resp:
        initial_html = resp.read().decode("utf-8", errors="replace")

    if not is_loading_html(initial_html):
        return initial_html

    poll_url = f"{url}?page_loading=1"
    for _ in range(max_attempts):
        time.sleep(poll_interval_seconds)
        poll_req = urllib.request.Request(
            poll_url,
            headers={
                "User-Agent": USER_AGENT,
                "x-requested-with": "fetch",
            },
        )
        with opener.open(poll_req, timeout=timeout_seconds) as resp:
            fragment = resp.read().decode("utf-8", errors="replace")
        if not is_loading_html(fragment):
            return fragment

    raise TimeoutError("WasteWorks page did not finish loading within polling limit.")


def resolve_updated_source(github_event_name: str | None) -> str:
    """Map GitHub Actions event names to canonical sync source identifiers."""
    event = (github_event_name or "").strip()
    if event in ("schedule", "workflow_dispatch"):
        return event
    return "local"


def run_scrape(
    property_id: str,
    data_path: Path,
    html_path: Path,
    *,
    now: datetime | None = None,
    updated_source: str | None = None,
) -> None:
    """Scrape current bin collection data, update JSON store, and regenerate HTML."""
    current_time = now or datetime.now(timezone.utc)
    html = fetch_waste_html(property_id)
    snapshots = parse_waste_html(html, reference_date=current_time.date())
    if not snapshots:
        raise RuntimeError("No waste collection services found in response HTML.")

    store = load_store(data_path)
    updated_at = current_time.strftime("%Y-%m-%d %H:%M UTC")
    updated_store = merge_snapshots(
        store,
        snapshots,
        updated_at=updated_at,
        updated_source=updated_source,
    )
    save_store(data_path, updated_store)

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_html(updated_store), encoding="utf-8")


def main() -> int:
    property_id = os.environ.get("WASTE_PROPERTY_ID", "")
    if not property_id.strip():
        print("Error: WASTE_PROPERTY_ID environment variable is not set.", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    data_path = repo_root / "data" / "collections.json"
    html_path = repo_root / "docs" / "index.html"
    updated_source = resolve_updated_source(os.environ.get("GITHUB_EVENT_NAME"))

    run_scrape(property_id, data_path, html_path, updated_source=updated_source)
    print(f"Updated {data_path.relative_to(repo_root)} and {html_path.relative_to(repo_root)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
