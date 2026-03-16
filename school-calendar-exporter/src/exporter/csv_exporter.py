"""Export events to Google Calendar CSV format."""

import csv
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

GOOGLE_CSV_FIELDS = [
    "Subject",
    "Start Date",
    "Start Time",
    "End Date",
    "End Time",
    "All Day Event",
    "Description",
    "Location",
]


def _format_date(date_str: str | None) -> str:
    """Convert YYYY-MM-DD to MM/DD/YYYY (Google Calendar format)."""
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            d = datetime.strptime(date_str, fmt)
            return d.strftime("%m/%d/%Y")
        except ValueError:
            continue
    return date_str  # Return as-is if unparseable


def _to_google_row(ev: dict) -> dict:
    has_time = bool(ev.get("time_start"))
    description_parts = []
    if ev.get("target"):
        description_parts.append(f"対象: {ev['target']}")
    if ev.get("notes"):
        description_parts.append(ev["notes"])

    return {
        "Subject": ev.get("title") or "",
        "Start Date": _format_date(ev.get("date")),
        "Start Time": ev.get("time_start") or "",
        "End Date": _format_date(ev.get("date")),
        "End Time": ev.get("time_end") or "",
        "All Day Event": "FALSE" if has_time else "TRUE",
        "Description": " / ".join(description_parts),
        "Location": "",
    }


def export_csv(events: list[dict], output_path: str) -> str:
    """Write *events* to a Google Calendar CSV file at *output_path*."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=GOOGLE_CSV_FIELDS)
        writer.writeheader()
        for ev in events:
            writer.writerow(_to_google_row(ev))

    logger.info(f"CSV exported: {output_path} ({len(events)} events)")
    return output_path
