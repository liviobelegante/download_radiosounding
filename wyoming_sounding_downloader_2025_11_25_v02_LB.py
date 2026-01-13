#!/usr/bin/env python3
"""
Download and reformat Wyoming upper-air sounding data.

Usage examples:
    # Simple usage (default comma separator, default folder):
    python wyoming_sounding_downloader.py 15420 2025-11-02 00

    # With tab separator and custom output directory:
    python wyoming_sounding_downloader.py 15420 2025-11-02 12 \
        --sep tab --outdir /path/to/save

Library usage example:
    from wyoming_sounding_downloader import parse_date_time, fetch_sounding

    when = parse_date_time("2025-11-02", "00")
    outfile, station_name, p_hPa, z_m, T_C = fetch_sounding(
        "15420", when, sep_char=",", outdir=None
    )
"""
import argparse
import datetime as dt
import html
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple


BASE_URL = "http://weather.uwyo.edu/cgi-bin/sounding"

# Full three-line Wyoming header block to search for
START_MARKER = (
    "-----------------------------------------------------------------------------\n"
    "   PRES   HGHT   TEMP   DWPT   RELH   MIXR   DRCT   SKNT   THTA   THTE   THTV\n"
    "    hPa     m      C      C      %    g/kg    deg   knot     K      K      K \n"
    "-----------------------------------------------------------------------------"
)

# End marker in the HTML output
END_MARKER = "</PRE><H3>Station information and sounding indices</H3><PRE>"


def build_url(station_id: str, when: dt.datetime) -> str:
    """Build the Wyoming sounding URL for a given station and datetime (UTC)."""
    params = {
        "region": "europe",
        "TYPE": "TEXT:LIST",
        "YEAR": f"{when.year:04d}",
        "MONTH": f"{when.month:02d}",
        "FROM": f"{when.day:02d}{when.hour:02d}",  # DDHH
        "TO": f"{when.day:02d}{when.hour:02d}",    # DDHH
        "STNM": station_id,
    }
    return BASE_URL + "?" + urllib.parse.urlencode(params)


def parse_date_time(date_str: str, time_str: str) -> dt.datetime:
    """
    Parse date and time strings into a datetime object (assumed UTC).

    Accepted date formats:
        YYYYMMDD
        YYYY-MM-DD
        DD.MM.YYYY

    Accepted time formats:
        HH
        HHMM
        HH:MM

    Minutes are forced to 00 since Wyoming uses 00 only.
    """
    # Parse date
    date_formats = ["%Y%m%d", "%Y-%m-%d", "%d.%m.%Y"]
    last_err: Optional[Exception] = None
    for f in date_formats:
        try:
            d = dt.datetime.strptime(date_str, f)
            break
        except ValueError as e:
            last_err = e
    else:
        raise ValueError(f"Could not parse date '{date_str}': {last_err}")

    # Parse time
    t = time_str.replace(":", "").strip()
    if len(t) == 1:
        t = "0" + t
    if len(t) == 2:
        t = t + "00"
    if len(t) != 4 or not t.isdigit():
        raise ValueError(f"Time must be HH or HHMM (or HH:MM), got '{time_str}'")

    hour = int(t[:2])
    minute = int(t[2:4])
    # Wyoming uses 00 minutes only
    minute = 0

    return d.replace(hour=hour, minute=minute)


def download_sounding_text(url: str) -> str:
    """Download the raw HTML sounding page from Wyoming."""
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    # Try UTF-8 first, fall back to latin-1
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def extract_station_name(raw_html: str, station_id: str) -> str:
    """
    Extract the station name from the <H2> header.

    Example header:
      <H2>15420 LRBS Bucuresti Inmh-Banesa Observations at 00Z 02 Nov 2025</H2>

    We keep only the name part (after ID and ICAO, before 'Observations')
    and sanitize it for use as a folder name.
    """
    start_idx = raw_html.find("<H2>")
    end_idx = -1
    offset = 4
    if start_idx != -1:
        end_idx = raw_html.find("</H2>", start_idx + offset)
    else:
        start_idx = raw_html.find("<h2>")
        if start_idx != -1:
            end_idx = raw_html.find("</h2>", start_idx + offset)
        else:
            offset = 0

    if start_idx != -1 and end_idx != -1:
        header = raw_html[start_idx + offset:end_idx]
        header = html.unescape(header).strip()
        tokens = header.split()
        # Expected pattern: [station_number, ICAO, name..., 'Observations', ...]
        try:
            obs_idx = tokens.index("Observations")
        except ValueError:
            obs_idx = len(tokens)

        if len(tokens) >= 3:
            name_tokens = tokens[2:obs_idx] if obs_idx > 2 else tokens[2:]
            raw_name = "_".join(name_tokens) if name_tokens else header
        else:
            raw_name = header
    else:
        raw_name = station_id

    # Sanitize for filesystem
    name = re.sub(r"[^A-Za-z0-9_\-]+", "_", raw_name)
    name = name.strip("_") or station_id
    return name


def extract_block(raw_html: str) -> List[str]:
    """
    Extract the block between the Wyoming header (three-line marker)
    and the station-indices section.
    """
    # Normalize line endings to \n
    text = raw_html.replace("\r\n", "\n").replace("\r", "\n")

    start_idx = text.find(START_MARKER)
    if start_idx == -1:
        raise RuntimeError("Could not find the full Wyoming header block.")

    # Start extracting after the header block
    data_start = start_idx + len(START_MARKER)

    end_idx = text.find(END_MARKER, data_start)
    if end_idx == -1:
        raise RuntimeError("Could not find the station information section end marker.")

    sub = text[data_start:end_idx]
    lines = sub.split("\n")

    # Remove blank lines from edges
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return lines


def normalize_lines(lines: List[str], sep: str) -> str:
    """
    Convert variable whitespace separated columns into sep separated columns.

    All lines are split on arbitrary whitespace and joined with the chosen separator.
    """
    out_lines: List[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped.strip():
            continue

        parts = stripped.split()
        out_lines.append(sep.join(parts))

    return "\n".join(out_lines) + "\n"


def parse_profiles(lines: List[str]) -> Tuple[List[float], List[float], List[float]]:
    """
    Parse pressure, altitude and temperature from the sounding block.

    Input:
        lines - list of lines immediately after the units header block.

    Returns:
        pressures_hPa  - list of floats
        altitudes_m    - list of floats
        temperatures_C - list of floats

    Non numeric lines are skipped. If a particular value in a data line
    cannot be converted to float, that line is skipped.
    """
    pressures: List[float] = []
    heights: List[float] = []
    temps: List[float] = []

    for line in lines:
        s = line.strip()
        if not s:
            continue

        parts = s.split()
        if len(parts) < 3:
            continue

        try:
            p = float(parts[0])
            z = float(parts[1])
            T = float(parts[2])
        except ValueError:
            # Lines with missing data (/////) etc
            continue

        pressures.append(p)
        heights.append(z)
        temps.append(T)

    return pressures, heights, temps


def ensure_output_path(
    station_id: str,
    station_name: str,
    when: dt.datetime,
    outdir: Optional[str],
) -> str:
    """
    Determine output directory and file path.

    If outdir is None:
        radiosoundings/<station_name>/yyyymmdd_hhmm_stationID.txt
    """
    if outdir is None or outdir.strip() == "":
        base_dir = os.path.join("radiosoundings", station_name)
    else:
        base_dir = outdir

    os.makedirs(base_dir, exist_ok=True)

    filename = f"{when:%Y%m%d}_{when:%H%M}_{station_id}.txt"
    return os.path.join(base_dir, filename)


def fetch_sounding(
    station_id: str,
    when: dt.datetime,
    sep_char: str = ",",
    outdir: Optional[str] = None,
) -> Tuple[str, str, List[float], List[float], List[float]]:
    """
    High level function that:
      1. Downloads the sounding
      2. Extracts the data block
      3. Saves it to a text file with chosen separator
      4. Returns file path, station name and profiles.

    Returns:
        outfile_path
        station_name
        pressures_hPa
        altitudes_m
        temperatures_C
    """
    url = build_url(station_id, when)
    raw_html = download_sounding_text(url)

    station_name = extract_station_name(raw_html, station_id)
    lines = extract_block(raw_html)
    content = normalize_lines(lines, sep_char)

    # Build header according to separator
    if sep_char == ",":
        name_line = "PRES,HGHT,TEMP,DWPT,RELH,MIXR,DRCT,SKNT,THTA,THTE,THTV"
        unit_line = "hPa,m,C,C,%,g/kg,deg,knot,K,K,K"
    else:  # tab
        cols = ["PRES", "HGHT", "TEMP", "DWPT", "RELH", "MIXR",
                "DRCT", "SKNT", "THTA", "THTE", "THTV"]
        units = ["hPa", "m", "C", "C", "%", "g/kg",
                 "deg", "knot", "K", "K", "K"]
        name_line = "\t".join(cols)
        unit_line = "\t".join(units)

    header_block = (
        "-----------------------------------------------------------------------------\n"
        f"{name_line}\n"
        f"{unit_line}\n"
        "-----------------------------------------------------------------------------\n"
    )

    outfile = ensure_output_path(station_id, station_name, when, outdir)
    with open(outfile, "w", encoding="utf-8", newline="") as f:
        f.write(header_block)
        f.write(content)

    p_hPa, z_m, T_C = parse_profiles(lines)

    return outfile, station_name, p_hPa, z_m, T_C



def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and reformat Wyoming upper-air sounding data."
    )
    parser.add_argument("station", help="Station ID (e.g. 15420)")
    parser.add_argument(
        "date",
        help="Date (YYYYMMDD, YYYY-MM-DD, or DD.MM.YYYY)",
    )
    parser.add_argument(
        "time",
        help="Time (HH or HHMM or HH:MM, UTC; usually 00 or 12 for radiosoundings)",
    )
    parser.add_argument(
        "--sep",
        choices=["comma", "tab"],
        default="comma",
        help="Output separator: 'comma' (default) or 'tab'.",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help=(
            "Optional output directory. "
            "If omitted, uses 'radiosoundings/<station_name>/'."
        ),
    )

    args = parser.parse_args(argv)

    sep_char = "," if args.sep == "comma" else "\t"

    try:
        when = parse_date_time(args.date, args.time)
    except ValueError as e:
        print(f"Error parsing date/time: {e}", file=sys.stderr)
        return 1

    url = build_url(args.station, when)
    print(f"Fetching: {url}")

    try:
        outfile, station_name, p_hPa, z_m, T_C = fetch_sounding(
            args.station, when, sep_char=sep_char, outdir=args.outdir
        )
    except Exception as e:
        print(f"Error fetching sounding: {e}", file=sys.stderr)
        return 1

    print(f"Station name: {station_name}")
    print(f"Saved sounding to: {outfile}")
    print(f"Parsed {len(p_hPa)} data levels.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
