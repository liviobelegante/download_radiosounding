#!/usr/bin/env python3
"""
Batch downloader for Wyoming upper air soundings.

This script uses wyoming_sounding_downloader.fetch_sounding to download
all available soundings for a given station between two dates.

Usage example:

    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2025-11-24

Options:

    # Tab separated instead of comma
    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2022-01-15 --sep tab

    # Custom output directory and custom hours (only 00Z for example)
    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2022-01-15 \
        --hours 00 --sep comma --outdir /path/to/save

By default, the script requests soundings at 00Z and 12Z for every day in the interval.
"""

import argparse
import datetime as dt
import sys
from typing import List

try:
    # This assumes wyoming_sounding_downloader.py is in the same directory
    from wyoming_sounding_downloader_2025_11_25_v02_LB import fetch_sounding
except ImportError as e:
    print("Error: could not import wyoming_sounding_downloader.", file=sys.stderr)
    print("Make sure wyoming_sounding_downloader.py is in the same directory or in PYTHONPATH.", file=sys.stderr)
    raise


def parse_date_only(date_str: str) -> dt.date:
    """
    Parse a date string into a date object.

    Accepted formats:
        YYYY-MM-DD
        YYYYMMDD
        DD.MM.YYYY
    """
    formats = ["%Y-%m-%d", "%Y%m%d", "%d.%m.%Y"]
    last_err = None
    for f in formats:
        try:
            return dt.datetime.strptime(date_str, f).date()
        except ValueError as e:
            last_err = e
    raise ValueError(f"Could not parse date '{date_str}': {last_err}")


def parse_hours(hours_str: str) -> List[int]:
    """
    Parse a comma separated list of hours (e.g. '00,12' or '0,12').

    Returns a list of integers in [0, 23].
    """
    hours: List[int] = []
    for token in hours_str.split(","):
        token = token.strip()
        if not token:
            continue
        if len(token) == 1:
            token = "0" + token
        if len(token) != 2 or not token.isdigit():
            raise ValueError(f"Invalid hour token '{token}'. Expected HH like 00 or 12.")
        h = int(token)
        if not (0 <= h <= 23):
            raise ValueError(f"Hour out of range: {h}")
        hours.append(h)
    if not hours:
        raise ValueError("No valid hours parsed.")
    return sorted(set(hours))


def daterange(start_date: dt.date, end_date: dt.date):
    """
    Yield all dates from start_date to end_date inclusive.
    """
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")
    delta = end_date - start_date
    for i in range(delta.days + 1):
        yield start_date + dt.timedelta(days=i)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch download Wyoming upper air soundings for a date range."
    )
    parser.add_argument(
        "station",
        help="Station ID (e.g. 15420).",
    )
    parser.add_argument(
        "start_date",
        help="Start date (YYYY-MM-DD, YYYYMMDD, or DD.MM.YYYY).",
    )
    parser.add_argument(
        "end_date",
        help="End date (YYYY-MM-DD, YYYYMMDD, or DD.MM.YYYY).",
    )
    parser.add_argument(
        "--hours",
        default="00,12",
        help="Comma separated list of UTC hours to download (default: '00,12').",
    )
    parser.add_argument(
        "--sep",
        choices=["comma", "tab"],
        default="comma",
        help="Output separator for the data files: 'comma' (default) or 'tab'.",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Optional base output directory. "
             "If omitted, uses 'radiosoundings/<station_name>/' like the single downloader.",
    )

    args = parser.parse_args(argv)

    try:
        start_date = parse_date_only(args.start_date)
        end_date = parse_date_only(args.end_date)
    except ValueError as e:
        print(f"Error parsing dates: {e}", file=sys.stderr)
        return 1

    try:
        hours = parse_hours(args.hours)
    except ValueError as e:
        print(f"Error parsing hours: {e}", file=sys.stderr)
        return 1

    sep_char = "," if args.sep == "comma" else "\t"

    print(f"Station: {args.station}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Hours (UTC): {hours}")
    print(f"Separator: {repr(sep_char)}")
    if args.outdir:
        print(f"Output directory base: {args.outdir}")
    else:
        print("Output directory base: radiosoundings/<station_name>/")

    failures = []

    for current_date in daterange(start_date, end_date):
        for hour in hours:
            when = dt.datetime(
                year=current_date.year,
                month=current_date.month,
                day=current_date.day,
                hour=hour,
                minute=0,
                second=0,
            )

            stamp = when.strftime("%Y-%m-%d %H:%M")
            print(f"\nRequesting sounding for {stamp} UTC...")

            try:
                outfile, station_name, p_hPa, z_m, T_C = fetch_sounding(
                    station_id=args.station,
                    when=when,
                    sep_char=sep_char,
                    outdir=args.outdir,
                )
            except Exception as e:
                print(f"  Failed: {e}")
                failures.append((when, str(e)))
                continue

            print(f"  OK: {outfile} (levels: {len(p_hPa)})")

    if failures:
        print("\nSummary of failures:")
        for when, reason in failures:
            print(f"  {when:%Y-%m-%d %H:%M} UTC -> {reason}")
    else:
        print("\nAll requested soundings downloaded successfully (no failures reported).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
