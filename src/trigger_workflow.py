"""Local macOS launchd trigger for dispatching the GitHub Actions scrape workflow."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request

REPO = "dafuloth/bin-track"
WORKFLOW_FILE = "scrape.yml"
REF = "main"
KEYCHAIN_SERVICE = "bin-track-gh-pat"
API_BASE = "https://api.github.com"
USER_AGENT = "bin-track-trigger/1.0"


def has_successful_run_on_date(runs: list[dict[str, Any]], target_date: date) -> bool:
    """Return True if a workflow run on target_date succeeded or is still active."""
    for run in runs:
        created_at = run.get("created_at")
        if not isinstance(created_at, str) or not created_at:
            continue
        run_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
        if run_date != target_date:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if (status == "completed" and conclusion == "success") or status in (
            "queued",
            "in_progress",
        ):
            return True
    return False


def read_keychain_token(service: str = KEYCHAIN_SERVICE) -> str:
    """Read the GitHub PAT from the macOS login Keychain."""
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", service, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to read Keychain item '{service}' (exit code {result.returncode})."
        )
    token = result.stdout.strip()
    if not token:
        raise RuntimeError(f"Keychain item '{service}' is empty.")
    return token


def _api_headers(token: str) -> dict[str, str]:
    """Build standard GitHub REST API request headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }


def fetch_recent_runs(
    token: str,
    *,
    repo: str = REPO,
    workflow_file: str = WORKFLOW_FILE,
    timeout_seconds: float = 15.0,
) -> list[dict[str, Any]]:
    """Fetch the most recent GitHub Actions runs for the workflow."""
    url = f"{API_BASE}/repos/{repo}/actions/workflows/{workflow_file}/runs?per_page=5"
    req = urllib.request.Request(url, headers=_api_headers(token), method="GET")
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        payload = json.load(resp)
    return list(payload.get("workflow_runs", []))


def dispatch_workflow(
    token: str,
    *,
    repo: str = REPO,
    workflow_file: str = WORKFLOW_FILE,
    ref: str = REF,
    timeout_seconds: float = 15.0,
) -> None:
    """Trigger a workflow_dispatch event on the configured GitHub repository."""
    url = f"{API_BASE}/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
    headers = {**_api_headers(token), "Content-Type": "application/json"}
    body = json.dumps({"ref": ref}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        if not (200 <= resp.status < 300):
            raise RuntimeError(f"Unexpected GitHub API status: {resp.status}")


def _log(message: str, *, stream: Any = None) -> None:
    """Print a UTC-timestamped log line."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {message}", file=stream or sys.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dispatch bin-track GitHub Actions workflow.")
    parser.add_argument("--dry-run", action="store_true", help="Check status without dispatching.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Dispatch even if a successful or active run already exists today.",
    )
    args = parser.parse_args(argv)

    try:
        token = read_keychain_token()
        runs = fetch_recent_runs(token)
        today_utc = datetime.now(timezone.utc).date()

        if not args.force and has_successful_run_on_date(runs, today_utc):
            _log(f"Skipping dispatch: {WORKFLOW_FILE} already succeeded or is active on {today_utc}.")
            return 0

        if args.dry_run:
            _log(f"Dry run: would dispatch {WORKFLOW_FILE} on {REPO}@{REF}.")
            return 0

        dispatch_workflow(token)
        _log(f"Dispatched {WORKFLOW_FILE} on {REPO}@{REF}.")
        return 0
    except urllib.error.HTTPError as exc:
        _log(f"Error: GitHub API returned HTTP {exc.code} ({exc.reason}).", stream=sys.stderr)
        return 1
    except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
        _log(f"Error: {exc}", stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
