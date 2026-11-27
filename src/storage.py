"""Canonical JSON storage, deduplication, and weekly matrix grouping."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from src.parser import ORDERED_SERVICES, ServiceSnapshot

_SERVICE_ORDER: dict[str, int] = {
    key: idx for idx, (key, _) in enumerate(ORDERED_SERVICES)
}


def empty_store() -> dict[str, Any]:
    """Return an empty canonical collection store."""
    return {
        "updated_at": None,
        "updated_source": None,
        "next_collections": {},
        "collections": [],
    }


def load_store(path: Path) -> dict[str, Any]:
    """Load the collection store from JSON, or return an empty store if missing."""
    if not path.exists():
        return empty_store()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "updated_at": data.get("updated_at"),
        "updated_source": data.get("updated_source"),
        "next_collections": data.get("next_collections", {}),
        "collections": data.get("collections", []),
    }


def save_store(path: Path, store: dict[str, Any]) -> None:
    """Persist the collection store as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2) + "\n", encoding="utf-8")


def merge_snapshots(
    store: dict[str, Any],
    snapshots: list[ServiceSnapshot],
    updated_at: str,
    updated_source: str | None = None,
) -> dict[str, Any]:
    """Merge newly scraped service snapshots into the canonical store."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {
        (row["date"], row["service"]): dict(row)
        for row in store.get("collections", [])
    }
    next_collections: dict[str, dict[str, Any]] = dict(
        store.get("next_collections", {})
    )

    for snap in snapshots:
        if snap.next_collection is not None:
            next_collections[snap.service] = {
                "date": snap.next_collection.collection_date.isoformat(),
                "frequency": snap.frequency,
                "status": snap.next_collection.status,
                "adjusted": snap.next_collection.adjusted,
            }

        if snap.last_collection is not None:
            iso_date = snap.last_collection.collection_date.isoformat()
            by_key[(iso_date, snap.service)] = {
                "date": iso_date,
                "service": snap.service,
                "time": snap.last_collection.time,
                "adjusted": snap.last_collection.adjusted,
            }

    sorted_collections = sorted(
        by_key.values(),
        key=lambda r: (r["date"], -_SERVICE_ORDER.get(r["service"], 99)),
        reverse=True,
    )

    return {
        "updated_at": updated_at,
        "updated_source": updated_source,
        "next_collections": next_collections,
        "collections": sorted_collections,
    }


def week_thursday(collection_date: date) -> date:
    """Return the Thursday of the ISO week (Mon-Sun) containing collection_date."""
    monday = collection_date - timedelta(days=collection_date.weekday())
    return monday + timedelta(days=3)


def build_weekly_matrix(
    collections: list[dict[str, Any]],
) -> list[tuple[date, dict[str, dict[str, Any]]]]:
    """Group collection records into rows keyed by each week's Thursday, newest first."""
    weeks: dict[date, dict[str, dict[str, Any]]] = {}
    for record in collections:
        col_date = date.fromisoformat(record["date"])
        row_date = week_thursday(col_date)
        row = weeks.setdefault(row_date, {})
        row[record["service"]] = record

    return sorted(weeks.items(), key=lambda item: item[0], reverse=True)
