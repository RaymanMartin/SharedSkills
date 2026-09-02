#!/usr/bin/env python3
"""Convert HR daily attendance blocks into one calculator row per day."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DATE_HEADER_PATTERN = re.compile(r"^=+\s*(20\d{2}-\d{2}-\d{2})\s*=+\s*$", re.MULTILINE)
CLOCK_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?")


def convert(raw_text: str) -> list[str]:
    parts = DATE_HEADER_PATTERN.split(raw_text)
    rows: list[str] = []
    for index in range(1, len(parts), 2):
        day = parts[index]
        block = parts[index + 1]
        clocks = CLOCK_PATTERN.findall(block)
        rows.append(" ".join([day, *clocks]) if clocks else day)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert HR daily clock-log blocks into calculator rows.")
    parser.add_argument("input", type=Path, help="Raw HR daily blocks separated by ===== YYYY-MM-DD =====.")
    parser.add_argument("output", type=Path, help="Output text file with one row per day.")
    args = parser.parse_args()

    rows = convert(args.input.read_text(encoding="utf-8-sig"))
    args.output.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
