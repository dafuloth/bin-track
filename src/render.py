"""Static HTML generator for the bin collection Weekly Matrix page."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from src.parser import ORDERED_SERVICES
from src.storage import build_weekly_matrix


def format_display_date(iso_or_date: str | date) -> str:
    """Format a date as e.g. 'Thu 12 Nov 2026'."""
    d = date.fromisoformat(iso_or_date) if isinstance(iso_or_date, str) else iso_or_date
    return d.strftime("%a %-d %b %Y")


def format_short_day(iso_or_date: str | date) -> str:
    """Format a date as e.g. 'Fri 2 Oct'."""
    d = date.fromisoformat(iso_or_date) if isinstance(iso_or_date, str) else iso_or_date
    return d.strftime("%a %-d %b")


def render_cell(record: dict[str, Any] | None, week_thursday: date) -> str:
    """Render a single Weekly Matrix table cell for a service."""
    if record is None:
        return '<td class="empty">&mdash;</td>'

    time_text = escape(record.get("time") or "Collected")
    record_date = date.fromisoformat(record["date"])
    is_shifted_day = record_date != week_thursday
    is_adjusted = bool(record.get("adjusted"))

    badges: list[str] = []
    if is_shifted_day:
        badges.append(f'<span class="badge day">{escape(format_short_day(record_date))}</span>')
    if is_adjusted:
        badges.append('<span class="badge adjusted">adjusted</span>')

    badge_html = f'<div class="badges">{" ".join(badges)}</div>' if badges else ""
    return f'<td><span class="time">{time_text}</span>{badge_html}</td>'


def render_next_cards(next_collections: dict[str, dict[str, Any]]) -> str:
    """Render summary cards for the upcoming scheduled collections."""
    cards: list[str] = []
    for key, label in ORDERED_SERVICES:
        info = next_collections.get(key)
        if not info:
            continue
        date_text = escape(format_display_date(info["date"]))
        freq_text = escape(info.get("frequency") or "")
        notes: list[str] = []
        if info.get("status"):
            notes.append(f'<span class="badge status">{escape(info["status"])}</span>')
        if info.get("adjusted"):
            notes.append('<span class="badge adjusted">adjusted</span>')
        notes_html = f' {" ".join(notes)}' if notes else ""
        cards.append(
            f'<div class="card">'
            f'<div class="card-title">{escape(label)}</div>'
            f'<div class="card-date">{date_text}{notes_html}</div>'
            f'<div class="card-freq">{freq_text}</div>'
            f"</div>"
        )
    return "\n        ".join(cards)


def render_html(store: dict[str, Any]) -> str:
    """Render the complete standalone HTML page from the canonical store."""
    weekly_rows = build_weekly_matrix(store.get("collections", []))
    updated_at = escape(store.get("updated_at") or "Not yet updated")
    next_cards_html = render_next_cards(store.get("next_collections", {}))

    header_cols = "".join(f"<th>{escape(label)}</th>" for _, label in ORDERED_SERVICES)

    body_rows: list[str] = []
    for week_date, services_map in weekly_rows:
        cells = "".join(
            render_cell(services_map.get(key), week_date)
            for key, _ in ORDERED_SERVICES
        )
        body_rows.append(
            f"<tr><th scope=\"row\">{escape(format_display_date(week_date))}</th>{cells}</tr>"
        )

    if not body_rows:
        colspan = len(ORDERED_SERVICES) + 1
        body_rows.append(
            f'<tr><td colspan="{colspan}" class="empty">No collections recorded yet.</td></tr>'
        )

    rows_html = "\n          ".join(body_rows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bin Collection Tracker</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --surface: #ffffff;
      --text: #1b1f23;
      --muted: #57606a;
      --border: #d0d7de;
      --accent: #0969da;
      --adj-bg: #fff8c5;
      --adj-text: #7d4e00;
      --status-bg: #ddf4ff;
      --status-text: #0550ae;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 2rem 1rem;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    main {{
      max-width: 960px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      gap: 0.5rem 1rem;
      margin-bottom: 1.5rem;
    }}
    h1 {{
      margin: 0;
      font-size: 1.75rem;
    }}
    .updated {{
      color: var(--muted);
      font-size: 0.875rem;
    }}
    h2 {{
      font-size: 1.1rem;
      margin: 1.5rem 0 0.75rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 0.75rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.85rem 1rem;
    }}
    .card-title {{
      font-weight: 600;
      font-size: 0.95rem;
    }}
    .card-date {{
      margin-top: 0.25rem;
      font-size: 1rem;
      color: var(--accent);
      font-weight: 500;
    }}
    .card-freq {{
      margin-top: 0.15rem;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .table-wrap {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.925rem;
    }}
    th, td {{
      padding: 0.7rem 0.9rem;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }}
    thead th {{
      background: #f0f2f5;
      font-weight: 600;
    }}
    tbody tr:last-child th,
    tbody tr:last-child td {{
      border-bottom: none;
    }}
    tbody th[scope="row"] {{
      font-weight: 600;
    }}
    td.empty {{
      color: var(--muted);
    }}
    .time {{
      font-variant-numeric: tabular-nums;
      font-weight: 500;
    }}
    .badges {{
      margin-top: 0.2rem;
      display: flex;
      gap: 0.3rem;
      flex-wrap: wrap;
    }}
    .badge {{
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 600;
    }}
    .badge.adjusted {{
      background: var(--adj-bg);
      color: var(--adj-text);
    }}
    .badge.day {{
      background: #eaeef2;
      color: var(--text);
    }}
    .badge.status {{
      background: var(--status-bg);
      color: var(--status-text);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Bin Collection Tracker</h1>
      <span class="updated">Last updated: {updated_at}</span>
    </header>

    <section>
      <h2>Next Scheduled</h2>
      <div class="cards">
        {next_cards_html}
      </div>
    </section>

    <section>
      <h2>Collection History (Weekly Matrix)</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Week (Thu)</th>
              {header_cols}
            </tr>
          </thead>
          <tbody>
          {rows_html}
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""
