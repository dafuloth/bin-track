"""Unit tests for WasteWorks HTML and date parsing."""

from datetime import date
import unittest

from src.parser import is_loading_html, parse_collection_date, parse_waste_html

SAMPLE_HTML = """
<dl class="waste__address">
  <dt class="waste__address__title">Address</dt>
  <dd class="waste__address__property">123 Example Street, London, W10 1AA</dd>
</dl>
<div class="waste__collections">
  <div class="waste-service-grid">
    <div class="waste-service-grid--service-name">
      <h3 class="govuk-heading-m waste-service-name">
        Rubbish
        collection
      </h3>
    </div>
    <div class="waste-service-grid--service-description">
      <dl class="govuk-summary-list">
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Frequency</dt>
          <dd class="govuk-summary-list__value">Every other Thursday</dd>
        </div>
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Next collection</dt>
          <dd class="govuk-summary-list__value">Thursday, 26th November</dd>
        </div>
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Last collection</dt>
          <dd class="govuk-summary-list__value">Thursday, 12th November, at 8:31am</dd>
        </div>
      </dl>
    </div>
  </div>
  <div class="waste-service-grid">
    <div class="waste-service-grid--service-name">
      <h3 class="govuk-heading-m waste-service-name">Recycling collection</h3>
    </div>
    <div class="waste-service-grid--service-description">
      <dl class="govuk-summary-list">
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Frequency</dt>
          <dd class="govuk-summary-list__value">Every other Thursday</dd>
        </div>
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Next collection</dt>
          <dd class="govuk-summary-list__value">Thursday, 19th November (In progress)</dd>
        </div>
      </dl>
    </div>
  </div>
  <div class="waste-service-grid">
    <div class="waste-service-grid--service-name">
      <h3 class="govuk-heading-m waste-service-name">Paper and cardboard (blue sacks) collection</h3>
    </div>
    <div class="waste-service-grid--service-description">
      <dl class="govuk-summary-list">
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Frequency</dt>
          <dd class="govuk-summary-list__value">Every other Thursday</dd>
        </div>
        <div class="govuk-summary-list__row">
          <dt class="govuk-summary-list__key">Last collection</dt>
          <dd class="govuk-summary-list__value">Friday, 2nd October, at 9:30am (adjusted)</dd>
        </div>
      </dl>
    </div>
  </div>
  <div class="waste-service-grid">
    <div class="waste-service-grid--service-name">
      <h3 class="govuk-heading-m waste-service-name">Small items</h3>
    </div>
  </div>
</div>
"""


class TestParser(unittest.TestCase):
    def test_parse_standard_last_collection(self) -> None:
        parsed = parse_collection_date(
            "Thursday, 12th November, at 8:31am",
            reference_date=date(2026, 11, 19),
            is_past=True,
        )
        assert parsed is not None
        self.assertEqual(parsed.collection_date, date(2026, 11, 12))
        self.assertEqual(parsed.time, "8:31am")
        self.assertFalse(parsed.adjusted)
        self.assertIsNone(parsed.status)

    def test_parse_adjusted_collection(self) -> None:
        parsed = parse_collection_date(
            "Friday, 2nd October, at 9:30am (adjusted)",
            reference_date=date(2026, 10, 4),
            is_past=True,
        )
        assert parsed is not None
        self.assertEqual(parsed.collection_date, date(2026, 10, 2))
        self.assertEqual(parsed.time, "9:30am")
        self.assertTrue(parsed.adjusted)
        self.assertIsNone(parsed.status)

    def test_parse_in_progress_next_collection(self) -> None:
        parsed = parse_collection_date(
            "Thursday, 19th November (In progress)",
            reference_date=date(2026, 11, 19),
            is_past=False,
        )
        assert parsed is not None
        self.assertEqual(parsed.collection_date, date(2026, 11, 19))
        self.assertIsNone(parsed.time)
        self.assertFalse(parsed.adjusted)
        self.assertEqual(parsed.status, "In progress")

    def test_year_rollover_past_in_january(self) -> None:
        parsed = parse_collection_date(
            "Thursday, 24th December, at 8:10am",
            reference_date=date(2027, 1, 3),
            is_past=True,
        )
        assert parsed is not None
        self.assertEqual(parsed.collection_date, date(2026, 12, 24))

    def test_year_rollover_future_in_december(self) -> None:
        parsed = parse_collection_date(
            "Thursday, 7th January",
            reference_date=date(2026, 12, 28),
            is_past=False,
        )
        assert parsed is not None
        self.assertEqual(parsed.collection_date, date(2027, 1, 7))

    def test_parse_waste_html(self) -> None:
        snapshots = parse_waste_html(SAMPLE_HTML, reference_date=date(2026, 11, 19))
        self.assertEqual(len(snapshots), 3)

        rubbish = snapshots[0]
        self.assertEqual(rubbish.service, "rubbish")
        self.assertEqual(rubbish.frequency, "Every other Thursday")
        assert rubbish.next_collection is not None
        self.assertEqual(rubbish.next_collection.collection_date, date(2026, 11, 26))
        assert rubbish.last_collection is not None
        self.assertEqual(rubbish.last_collection.collection_date, date(2026, 11, 12))
        self.assertEqual(rubbish.last_collection.time, "8:31am")

        recycling = snapshots[1]
        self.assertEqual(recycling.service, "recycling")
        assert recycling.next_collection is not None
        self.assertEqual(recycling.next_collection.status, "In progress")
        self.assertIsNone(recycling.last_collection)

        paper = snapshots[2]
        self.assertEqual(paper.service, "paper_cardboard")
        assert paper.last_collection is not None
        self.assertTrue(paper.last_collection.adjusted)
        self.assertEqual(paper.last_collection.time, "9:30am")

    def test_is_loading_html(self) -> None:
        self.assertTrue(is_loading_html('<img id="loading-indicator" src="/i/loading.svg">'))
        self.assertFalse(is_loading_html(SAMPLE_HTML))


if __name__ == "__main__":
    unittest.main()
