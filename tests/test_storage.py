"""Unit tests for canonical storage, deduplication, and weekly matrix grouping."""

from datetime import date
import unittest

from src.parser import ParsedDateInfo, ServiceSnapshot
from src.storage import build_weekly_matrix, empty_store, merge_snapshots, week_thursday


class TestStorage(unittest.TestCase):
    def test_week_thursday_maps_adjusted_days_to_same_week(self) -> None:
        self.assertEqual(week_thursday(date(2026, 10, 1)), date(2026, 10, 1))
        self.assertEqual(week_thursday(date(2026, 10, 2)), date(2026, 10, 1))
        self.assertEqual(week_thursday(date(2026, 9, 30)), date(2026, 10, 1))

    def test_merge_snapshots_deduplicates_and_updates(self) -> None:
        store = empty_store()
        snap1 = ServiceSnapshot(
            service="rubbish",
            frequency="Every other Thursday",
            next_collection=ParsedDateInfo(date(2026, 11, 26), None, False, None),
            last_collection=ParsedDateInfo(date(2026, 11, 12), "8:31am", False, None),
        )
        store = merge_snapshots(store, [snap1], updated_at="2026-11-15 15:00 UTC")
        self.assertEqual(len(store["collections"]), 1)

        # Re-scraping the same week should update in place rather than duplicate.
        snap1_updated = ServiceSnapshot(
            service="rubbish",
            frequency="Every other Thursday",
            next_collection=ParsedDateInfo(date(2026, 11, 26), None, False, None),
            last_collection=ParsedDateInfo(date(2026, 11, 12), "8:32am", False, None),
        )
        store = merge_snapshots(store, [snap1_updated], updated_at="2026-11-19 15:00 UTC")
        self.assertEqual(len(store["collections"]), 1)
        self.assertEqual(store["collections"][0]["time"], "8:32am")

    def test_build_weekly_matrix_groups_and_sorts_newest_first(self) -> None:
        collections = [
            {"date": "2026-10-01", "service": "rubbish", "time": "8:31am", "adjusted": False},
            {"date": "2026-10-02", "service": "paper_cardboard", "time": "9:30am", "adjusted": True},
            {"date": "2026-11-12", "service": "food_waste", "time": "8:15am", "adjusted": False},
        ]
        rows = build_weekly_matrix(collections)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], date(2026, 11, 12))
        self.assertEqual(rows[1][0], date(2026, 10, 1))
        self.assertIn("rubbish", rows[1][1])
        self.assertIn("paper_cardboard", rows[1][1])


if __name__ == "__main__":
    unittest.main()
