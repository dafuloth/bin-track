"""Unit tests for the local launchd workflow trigger."""

from datetime import date
import unittest

from src.trigger_workflow import has_successful_run_on_date


class TestTriggerWorkflow(unittest.TestCase):
    def test_completed_success_on_target_date(self) -> None:
        runs = [
            {
                "created_at": "2026-11-27T15:12:04Z",
                "status": "completed",
                "conclusion": "success",
            }
        ]
        self.assertTrue(has_successful_run_on_date(runs, date(2026, 11, 27)))

    def test_queued_and_in_progress_on_target_date(self) -> None:
        self.assertTrue(
            has_successful_run_on_date(
                [{"created_at": "2026-11-27T15:12:04Z", "status": "queued", "conclusion": None}],
                date(2026, 11, 27),
            )
        )
        self.assertTrue(
            has_successful_run_on_date(
                [
                    {
                        "created_at": "2026-11-27T15:12:04Z",
                        "status": "in_progress",
                        "conclusion": None,
                    }
                ],
                date(2026, 11, 27),
            )
        )

    def test_failed_or_cancelled_on_target_date(self) -> None:
        runs = [
            {
                "created_at": "2026-11-27T15:12:04Z",
                "status": "completed",
                "conclusion": "failure",
            },
            {
                "created_at": "2026-11-27T15:14:00Z",
                "status": "completed",
                "conclusion": "cancelled",
            },
        ]
        self.assertFalse(has_successful_run_on_date(runs, date(2026, 11, 27)))

    def test_success_on_another_date_and_empty_runs(self) -> None:
        runs = [
            {
                "created_at": "2026-11-20T15:12:04Z",
                "status": "completed",
                "conclusion": "success",
            }
        ]
        self.assertFalse(has_successful_run_on_date(runs, date(2026, 11, 27)))
        self.assertFalse(has_successful_run_on_date([], date(2026, 11, 27)))


if __name__ == "__main__":
    unittest.main()
