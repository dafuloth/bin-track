"""HTML and date parsing for Brent WasteWorks collection pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
import re
from typing import Optional

SERVICE_MAP: dict[str, tuple[str, str]] = {
    "rubbish collection": ("rubbish", "Rubbish"),
    "recycling collection": ("recycling", "Recycling"),
    "food waste collection": ("food_waste", "Food Waste"),
    "paper and cardboard (blue sacks) collection": ("paper_cardboard", "Paper & Cardboard"),
}

ORDERED_SERVICES: tuple[tuple[str, str], ...] = (
    ("rubbish", "Rubbish"),
    ("recycling", "Recycling"),
    ("food_waste", "Food Waste"),
    ("paper_cardboard", "Paper & Cardboard"),
)

_MONTHS: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_DATE_RE = re.compile(
    r"^(?:[A-Za-z]+,\s*)?(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)"
    r"(?:,\s*at\s+(\d{1,2}:\d{2}\s*(?:am|pm)))?"
    r"(?:\s*\(([^)]+)\))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedDateInfo:
    """Structured result from parsing a WasteWorks collection date string."""

    collection_date: date
    time: Optional[str]
    adjusted: bool
    status: Optional[str]


@dataclass(frozen=True)
class ServiceSnapshot:
    """Parsed state for a single waste service from one page scrape."""

    service: str
    frequency: Optional[str]
    next_collection: Optional[ParsedDateInfo]
    last_collection: Optional[ParsedDateInfo]


class _ServiceGridParser(HTMLParser):
    """Extract service names and <dt>/<dd> summary pairs from WasteWorks HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._in_service_name = False
        self._in_dt = False
        self._in_dd = False
        self._current_name_parts: list[str] = []
        self._current_dt_parts: list[str] = []
        self._current_dd_parts: list[str] = []
        self._pending_service: Optional[str] = None
        self._pending_dt: Optional[str] = None
        self._current_rows: dict[str, str] = {}
        self.services: list[tuple[str, dict[str, str]]] = []

    def _flush_service(self) -> None:
        if self._pending_service is not None:
            self.services.append((self._pending_service, self._current_rows))
            self._pending_service = None
            self._current_rows = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attr_map = dict(attrs)
        classes = (attr_map.get("class") or "").split()

        if tag == "div" and "waste-service-grid" in classes:
            self._flush_service()
        elif tag == "h3" and "waste-service-name" in classes:
            self._in_service_name = True
            self._current_name_parts = []
        elif tag == "dt":
            self._in_dt = True
            self._current_dt_parts = []
        elif tag == "dd":
            self._in_dd = True
            self._current_dd_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._in_service_name:
            self._in_service_name = False
            self._pending_service = " ".join("".join(self._current_name_parts).split())
        elif tag == "dt" and self._in_dt:
            self._in_dt = False
            self._pending_dt = " ".join("".join(self._current_dt_parts).split())
        elif tag == "dd" and self._in_dd:
            self._in_dd = False
            if self._pending_dt is not None:
                value = " ".join("".join(self._current_dd_parts).split())
                self._current_rows[self._pending_dt] = value
                self._pending_dt = None

    def handle_data(self, data: str) -> None:
        if self._in_service_name:
            self._current_name_parts.append(data)
        elif self._in_dt:
            self._current_dt_parts.append(data)
        elif self._in_dd:
            self._current_dd_parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush_service()


def infer_year(month: int, day: int, reference_date: date, *, is_past: bool) -> date:
    """Resolve a month/day without a year relative to reference_date."""
    year = reference_date.year
    if not is_past:
        candidate = _safe_date(year, month, day)
        if candidate < reference_date - timedelta(days=7):
            return _safe_date(year + 1, month, day)
        return candidate

    candidate = _safe_date(year, month, day)
    if candidate > reference_date + timedelta(days=7):
        return _safe_date(year - 1, month, day)
    return candidate


def _safe_date(year: int, month: int, day: int) -> date:
    # Handle Feb 29 if ever encountered during year rollover checks.
    try:
        return date(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return date(year, 2, 28)
        raise


def parse_collection_date(
    raw: str,
    reference_date: date,
    *,
    is_past: bool,
) -> Optional[ParsedDateInfo]:
    """Parse a WasteWorks date string such as 'Thursday, 12th November, at 8:31am'."""
    cleaned = " ".join(raw.split())
    match = _DATE_RE.match(cleaned)
    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2).lower()
    month = _MONTHS.get(month_name)
    if month is None:
        return None

    raw_time = match.group(3)
    time_str = raw_time.lower().replace(" ", "") if raw_time else None

    note = match.group(4).strip() if match.group(4) else None
    adjusted = bool(note and "adjusted" in note.lower())
    status = None if (note is None or adjusted) else note

    resolved_date = infer_year(month, day, reference_date, is_past=is_past)
    return ParsedDateInfo(
        collection_date=resolved_date,
        time=time_str,
        adjusted=adjusted,
        status=status,
    )


def normalize_service_name(raw_name: str) -> Optional[str]:
    """Map a WasteWorks heading to its canonical service key."""
    key = " ".join(raw_name.split()).lower()
    entry = SERVICE_MAP.get(key)
    return entry[0] if entry else None


def is_loading_html(html: str) -> bool:
    """Return True if the WasteWorks response is still showing the loading spinner."""
    return "loading-indicator" in html


def parse_waste_html(html: str, reference_date: date) -> list[ServiceSnapshot]:
    """Parse WasteWorks HTML fragment/page into structured ServiceSnapshot records."""
    parser = _ServiceGridParser()
    parser.feed(html)
    parser.close()

    snapshots: list[ServiceSnapshot] = []
    for raw_name, rows in parser.services:
        service_key = normalize_service_name(raw_name)
        if service_key is None or not rows:
            continue

        next_raw = rows.get("Next collection")
        last_raw = rows.get("Last collection")
        snapshots.append(
            ServiceSnapshot(
                service=service_key,
                frequency=rows.get("Frequency"),
                next_collection=(
                    parse_collection_date(next_raw, reference_date, is_past=False)
                    if next_raw
                    else None
                ),
                last_collection=(
                    parse_collection_date(last_raw, reference_date, is_past=True)
                    if last_raw
                    else None
                ),
            )
        )
    return snapshots
