#!/usr/bin/env python3
"""Calculate monthly overtime from copied/exported attendance rows."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


DATE_PATTERNS = [
    re.compile(r"(?P<y>20\d{2})[-/.年](?P<m>\d{1,2})[-/.月](?P<d>\d{1,2})日?"),
    re.compile(r"(?P<m>\d{1,2})[-/.月](?P<d>\d{1,2})日?"),
]

TIME_PATTERN = re.compile(
    r"(?P<mark>上午|下午|晚上|中午|AM|PM|am|pm)?\s*"
    r"(?P<h>\d{1,2})[:：](?P<m>\d{2})"
    r"\s*(?P<suffix>上午|下午|晚上|中午|AM|PM|am|pm)?"
)


@dataclass
class DayResult:
    day: str
    first_clock: str
    last_clock: str
    overtime_minutes: int
    rule: str
    source: str


def parse_date(text: str, default_year: int | None) -> str | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groupdict()
        year = int(groups.get("y") or default_year or date.today().year)
        month = int(groups["m"])
        day = int(groups["d"])
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def normalize_time(hour: int, minute: int, marker: str) -> tuple[int, int] | None:
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    marker = marker.lower()
    if marker in {"下午", "晚上", "pm"} and hour < 12:
        hour += 12
    elif marker in {"上午", "am"} and hour == 12:
        hour = 0
    elif marker == "中午" and hour < 11:
        hour += 12
    return hour, minute


def parse_times(text: str, short_evening: bool) -> list[tuple[int, int]]:
    matches = list(TIME_PATTERN.finditer(text))
    times: list[tuple[int, int]] = []
    for index, match in enumerate(matches):
        marker = (match.group("mark") or match.group("suffix") or "").strip()
        hour = int(match.group("h"))
        minute = int(match.group("m"))
        if short_evening and not marker and index == len(matches) - 1 and 1 <= hour <= 11:
            hour += 12
        parsed = normalize_time(hour, minute, marker)
        if parsed is not None:
            times.append(parsed)
    return times


def read_records(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:2048]
    delimiter = "\t" if "\t" in sample and "," not in sample else None

    if delimiter or path.suffix.lower() in {".csv", ".tsv"}:
        dialect = csv.excel_tab if delimiter == "\t" or path.suffix.lower() == ".tsv" else csv.excel
        return [" ".join(cell.strip() for cell in row if cell.strip()) for row in csv.reader(text.splitlines(), dialect)]

    return [line.strip() for line in text.splitlines() if line.strip()]


def format_minutes(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours}:{mins:02d}"


def format_clock(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def calculate(records: list[str], default_year: int | None, short_evening: bool) -> list[DayResult]:
    results: list[DayResult] = []
    for record in records:
        day = parse_date(record, default_year)
        if not day:
            continue

        times = parse_times(record, short_evening)
        if not times:
            continue

        work_date = date.fromisoformat(day)
        first_hour, first_minute = min(times)
        last_hour, last_minute = max(times)
        first_total = first_hour * 60 + first_minute
        last_total = last_hour * 60 + last_minute
        if work_date.weekday() >= 5:
            overtime = max(0, min(last_total, 18 * 60) - max(first_total, 9 * 60)) if len(times) >= 2 else 0
            rule = "weekend 09-18"
        else:
            overtime = max(0, last_total - 19 * 60)
            rule = "weekday >19"
        results.append(
            DayResult(
                day=day,
                first_clock=format_clock(first_hour, first_minute),
                last_clock=format_clock(last_hour, last_minute),
                overtime_minutes=overtime,
                rule=rule,
                source=record,
            )
        )

    return sorted(results, key=lambda item: item.day)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate Quectel HR monthly overtime from attendance rows.")
    parser.add_argument("file", type=Path, help="Attendance text/CSV/TSV file copied or exported from HR.")
    parser.add_argument("--year", type=int, default=None, help="Default year for rows that only show month/day.")
    parser.add_argument(
        "--short-evening",
        action="store_true",
        help="Treat the row's final unmarked 1:00-11:59 time as evening, useful when HR displays 20:40 as 8:40.",
    )
    parser.add_argument("--show-source", action="store_true", help="Print the source row after each calculated day.")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2

    results = calculate(read_records(args.file), args.year, args.short_evening)
    if not results:
        print("No attendance rows with dates and clock times were found.", file=sys.stderr)
        return 1

    total = sum(item.overtime_minutes for item in results)
    print("Date        First  Last   Overtime  Rule")
    print("----------------------------------------------")
    for item in results:
        print(
            f"{item.day}  {item.first_clock}  {item.last_clock}  "
            f"{format_minutes(item.overtime_minutes):>8}  {item.rule}"
        )
        if args.show_source:
            print(f"  {item.source}")
    print("----------------------------------------------")
    print(f"Total overtime: {format_minutes(total)} ({total} minutes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
