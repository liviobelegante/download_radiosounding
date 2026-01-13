
README – Wyoming Radiosounding Batch Downloader

This package contains two scripts:

1. wyoming_sounding_downloader.py  
   Downloads a single radiosounding from the University of Wyoming archive,
   extracts the numerical data block, formats it using comma or tab delimiters,
   adds a dynamic header, and saves it into a structured folder.

2. wyoming_sounding_batch_downloader.py  
   Automates downloading all soundings in a date range for a specific station,
   calling the single-sounding downloader internally.

Python 3.8+ required. No external libraries needed.

-------------------------------------------------------------------------------
1. PURPOSE

The batch downloader retrieves multiple radiosoundings automatically between
two dates at specified hours (default: 00Z and 12Z). It is intended for long-term
studies, lidar validation, model comparisons, or atmospheric profiling datasets.

-------------------------------------------------------------------------------
2. BASIC USAGE

Download all soundings for station 15420 between 2022-01-10 and 2025-11-24:

    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2025-11-24

-------------------------------------------------------------------------------
3. INPUT FORMATS

Accepted date formats:
    YYYY-MM-DD
    YYYYMMDD
    DD.MM.YYYY

Accepted hours format (for --hours):
    "00,12" or "06,18" or "00" etc.

-------------------------------------------------------------------------------
4. COMMAND-LINE OPTIONS

# Custom hours (example: only midnight soundings)

    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2025-11-24 --hours 00

# Four synoptic hours

    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2022-02-01 --hours 00,06,12,18

# Tab-separated output

    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2025-11-24 --sep tab

# Custom output directory

    python wyoming_sounding_batch_downloader.py 15420 2022-01-10 2025-11-24 --outdir /data/soundings

Output structure:
    /data/soundings/<station_name>/yyyymmdd_hhmm_stationID.txt

-------------------------------------------------------------------------------
5. OUTPUT FILE FORMAT

Each saved file begins with a dynamic header adapted to the delimiter.

Comma-separated example:

-----------------------------------------------------------------------------
PRES,HGHT,TEMP,DWPT,RELH,MIXR,DRCT,SKNT,THTA,THTE,THTV
hPa,m,C,C,%,g/kg,deg,knot,K,K,K
-----------------------------------------------------------------------------

Tab-separated version uses tab characters.

After the header, the cleaned data rows follow.

-------------------------------------------------------------------------------
6. ERROR HANDLING

If a sounding does not exist for a given date/hour:

- a warning is printed
- the download continues
- a summary of all failures is shown at the end

-------------------------------------------------------------------------------
7. DIRECTORY STRUCTURE

radiosoundings/
    Bucuresti_Inmh_Banesa/
        20220110_0000_15420.txt
        20220110_1200_15420.txt
        ...

When using --outdir:
    /your_path/Bucuresti_Inmh_Banesa/

-------------------------------------------------------------------------------
8. LIBRARY USAGE

You may import the downloader in your own Python code:

    from wyoming_sounding_downloader import fetch_sounding

-------------------------------------------------------------------------------
9. NOTES

- Wyoming archives contain missing or partial days; this is normal.
- Long periods (years or decades) are fully supported.
- Do not overload the server with too many parallel requests.

-------------------------------------------------------------------------------
10. FUTURE EXTENSIONS

Possible additions:
- Parallel downloads
- Retry logic
- JSON or NetCDF output
- Automatic station availability scan
- Profile plotting utilities

-------------------------------------------------------------------------------
