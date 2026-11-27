"""Unit tests for HTML rendering."""

import unittest

from src.render import render_html


class TestRender(unittest.TestCase):
    def test_render_html_includes_matrix_and_adjusted_badges(self) -> None:
        store = {
            "updated_at": "2026-11-19 15:00 UTC",
            "next_collections": {
                "rubbish": {
                    "date": "2026-11-26",
                    "frequency": "Every other Thursday",
                    "status": None,
                    "adjusted": False,
                },
                "food_waste": {
                    "date": "2026-11-19",
                    "frequency": "Every Thursday",
                    "status": "In progress",
                    "adjusted": False,
                },
                "paper_cardboard": {
                    "date": "2026-11-26",
                    "frequency": "Every other Thursday",
                    "status": None,
                    "adjusted": False,
                },
            },
            "collections": [
                {
                    "date": "2026-10-02",
                    "service": "paper_cardboard",
                    "time": "9:30am",
                    "adjusted": True,
                },
                {
                    "date": "2026-10-01",
                    "service": "rubbish",
                    "time": "8:31am",
                    "adjusted": False,
                },
                {
                    "date": "2026-10-01",
                    "service": "food_waste",
                    "time": "8:15am",
                    "adjusted": False,
                },
            ],
        }
        html = render_html(store)
        self.assertIn("Bin Collection Tracker", html)
        self.assertIn('<div class="card-title">Paper &amp; Cardboard</div>', html)
        self.assertIn("<th>Paper</th>", html)
        self.assertIn("Thu 1 Oct 2026", html)
        self.assertIn("8:31am", html)
        self.assertIn("9:30am", html)
        self.assertIn("Fri 2 Oct", html)
        self.assertIn("adjusted", html)
        self.assertIn("&mdash;", html)
        self.assertIn("@media (max-width: 600px)", html)
        self.assertNotIn("Food Waste", html)
        self.assertNotIn("8:15am", html)

    def test_render_html_empty_store(self) -> None:
        html = render_html({"updated_at": None, "next_collections": {}, "collections": []})
        self.assertIn("No collections recorded yet.", html)
        self.assertNotIn('<p class="sync-status', html)

    def test_render_html_sync_status_variants(self) -> None:
        base_store = {"updated_at": "2026-11-27 15:11 UTC", "next_collections": {}, "collections": []}

        scheduled_html = render_html({**base_store, "updated_source": "schedule"})
        self.assertIn('<p class="sync-status scheduled">Sync source: GitHub Actions scheduled run</p>', scheduled_html)
        self.assertLess(scheduled_html.index("sync-status"), scheduled_html.index("<h2>Next Scheduled</h2>"))

        manual_html = render_html({**base_store, "updated_source": "workflow_dispatch"})
        self.assertIn('<p class="sync-status manual">Sync source: Manual / launchd run</p>', manual_html)

        local_html = render_html({**base_store, "updated_source": "local"})
        self.assertIn('<p class="sync-status local">Sync source: Local run</p>', local_html)

        none_html = render_html({**base_store, "updated_source": None})
        self.assertNotIn('<p class="sync-status', none_html)


if __name__ == "__main__":
    unittest.main()
