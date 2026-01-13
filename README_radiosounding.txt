README - Wyoming Radiosounding Downloader

This tool downloads upper-air sounding data from the University of Wyoming database using their public CGI API. 
It extracts only the clean numerical part of the sounding (between the units header and the station-indices section), 
converts it into a clean comma- or tab-separated format, and saves it to a structured directory. The script can also 
be used as a Python module, returning pressure, altitude, and temperature arrays for analysis.

.............................................................................

1. Features

- Downloads sounding data for any station ID using: http://weather.uwyo.edu/cgi-bin/sounding
- Inputs: station ID, date, time
- Extracts only the scientific data block
- Cleans whitespace-separated columns into comma or tab-separated fields
- Automatically extracts station name from header
- Saves files into:
      radiosoundings/<station_name>/yyyymmdd_hhmm_stationID.txt
- Library function returns:
      pressures_hPa, altitudes_m, temperatures_C

.............................................................................

2. Installation

Requires Python 3.8+.
No external dependencies.

Store the script file:
    wyoming_sounding_downloader.py

.............................................................................

3. Command-line Usage

Basic usage:
    python wyoming_sounding_downloader.py 15420 2025-11-02 00

Choose separator:
    python wyoming_sounding_downloader.py 15420 2025-11-02 00 --sep comma
    python wyoming_sounding_downloader.py 15420 2025-11-02 00 --sep tab

Custom output directory:
    python wyoming_sounding_downloader.py 15420 2025-11-02 00 --outdir /path/to/save

If --outdir is not provided, files are saved to:
    radiosoundings/<station_name>/

.............................................................................

4. Accepted Date and Time Formats

Date formats:
    YYYYMMDD
    YYYY-MM-DD
    DD.MM.YYYY

Time formats:
    HH
    HHMM
    HH:MM
Minutes are forced to 00.

.............................................................................

5. Output Format

Clean ASCII text, for example:
    1000.0, 86.0, 12.4, 11.2, 80, 7.55, 50.0, 4, 285.1, 285.7, 285.2

.............................................................................

6. Using as a Library

Example:

    from wyoming_sounding_downloader import parse_date_time, fetch_sounding

    when = parse_date_time("2025-11-02", "00")
    outfile, station_name, p_hPa, z_m, T_C = fetch_sounding("15420", when)

    print(outfile)
    print(station_name)
    print(len(p_hPa))

Returned variables:
    outfile         - saved file path
    station_name    - parsed from header
    p_hPa           - pressure levels
    z_m             - altitude levels
    T_C             - temperature levels

.............................................................................

7. Station Name Extraction

Header example:
    <H2>15420 LRBS Bucuresti Inmh-Banesa Observations at 00Z 02 Nov 2025</H2>

Extracted station folder:
    Bucuresti_Inmh_Banesa

.............................................................................

8. Error Handling

The script reports:
    - wrong date/time formats
    - missing block markers
    - network errors
    - invalid station or missing sounding

.............................................................................

9. Directory Structure Example

radiosoundings/
    Bucuresti_Inmh_Banesa/
        20251102_0000_15420.txt
        20251102_1200_15420.txt

.............................................................................

10. Future Extensions

- Batch mode
- JSON/NetCDF output
- Plot generation
- Auto station search by coordinates

.............................................................................
