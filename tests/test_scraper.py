"""Unit tests for scraper helpers."""

import unittest

from src.scraper import resolve_updated_source


class TestScraper(unittest.TestCase):
    def test_resolve_updated_source(self) -> None:
        self.assertEqual(resolve_updated_source("schedule"), "schedule")
        self.assertEqual(resolve_updated_source("workflow_dispatch"), "workflow_dispatch")
        self.assertEqual(resolve_updated_source("push"), "local")
        self.assertEqual(resolve_updated_source(""), "local")
        self.assertEqual(resolve_updated_source(None), "local")


if __name__ == "__main__":
    unittest.main()
