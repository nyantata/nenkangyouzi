"""Export events to ICS (iCalendar) format."""
from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path

from icalendar import Calendar, Event, vText

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(time_str: str | None) -> time | None:
    if not time_str:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def export_ics(events: list[dict], output_path: str) -> str:
    """Write *events* to an ICS file at *output_path*."""
    cal = Calendar()
    cal.add("prodid", "-//School Calendar Exporter//JA")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")

    skipped = 0
    for ev in events:
        d = _parse_date(ev.get("date"))
        if d is None:
            logger.warning(f"Skipping event with unparseable date: {ev.get('title')}")
            skipped += 1
            continue

        ical_event = Event()
        ical_event.add("summary", ev.get("title") or "（タイトルなし）")

        t_start = _parse_time(ev.get("time_start"))
        t_end = _parse_time(ev.get("time_end"))

        if t_start:
            ical_event.add("dtstart", datetime.combine(d, t_start))
            if t_end:
                ical_event.add("dtend", datetime.combine(d, t_end))
            else:
                ical_event.add("dtend", datetime.combine(d, t_start))
        else:
            # All-day event
            ical_event.add("dtstart", d)
            ical_event.add("dtend", d)

        description_parts = []
        if ev.get("target"):
            description_parts.append(f"対象: {ev['target']}")
        if ev.get("notes"):
            description_parts.append(ev["notes"])
        if description_parts:
            ical_event.add("description", "\n".join(description_parts))

        if ev.get("category"):
            ical_event.add("categories", [ev["category"]])

        cal.add_component(ical_event)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(cal.to_ical())

    logger.info(
        f"ICS exported: {output_path} ({len(events) - skipped} events, {skipped} skipped)"
    )
    return output_path
