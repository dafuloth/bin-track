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
            ],
        }
        html = render_html(store)
        self.assertIn("Bin Collection Tracker", html)
        self.assertIn("Thu 1 Oct 2026", html)
        self.assertIn("8:31am", html)
        self.assertIn("9:30am", html)
        self.assertIn("Fri 2 Oct", html)
        self.assertIn("adjusted", html)
        self.assertIn("&mdash;", html)

    def test_render_html_empty_store(self) -> None:
        html = render_html({"updated_at": None, "next_collections": {}, "collections": []})
        self.assertIn("No collections recorded yet.", html)


if __name__ == "__main__":
    unittest.main()
