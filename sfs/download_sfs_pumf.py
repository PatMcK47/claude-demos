#!/usr/bin/env python3
"""
Download the Survey of Financial Security (SFS) Public Use Microdata File (PUMF)
from Statistics Canada.

Catalogue: 13M0006X
Source: https://www150.statcan.gc.ca/n1/en/catalogue/13M0006X

The SFS is conducted every 3 years (2016, 2019, 2023, ...).
This script attempts to download the most recent PUMF available,
starting from the newest release and falling back to older ones.
"""

import os
import sys
import zipfile
import urllib.request
import urllib.error

# Known SFS PUMF releases: (survey_year, release_year_suffix, zip_filename)
# The URL pattern is:
#   https://www150.statcan.gc.ca/n1/pub/13m0006x/{release_suffix}/{zip_filename}
#
# release_suffix encodes the publication year + issue (e.g., 2021001 = 2021, issue 1)
RELEASES = [
    # 2023 — speculative URL; the PUMF may not yet be on statcan.gc.ca
    {
        "survey_year": 2023,
        "release_suffix": "2025001",
        "zip_filename": "SFS2023__PUMF_E.zip",
        "description": "SFS 2023 PUMF (estimated release 2025)",
    },
    {
        "survey_year": 2023,
        "release_suffix": "2025001",
        "zip_filename": "SFS2023_PUMF_E.zip",
        "description": "SFS 2023 PUMF (single-underscore variant)",
    },
    # 2019 — confirmed URL from Open Government Portal & canpumf R package
    {
        "survey_year": 2019,
        "release_suffix": "2021001",
        "zip_filename": "SFS2019__PUMF_E.zip",  # double underscore is canonical
        "description": "SFS 2019 PUMF (released 2021)",
    },
]

BASE_URL = "https://www150.statcan.gc.ca/n1/pub/13m0006x"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def build_url(release):
    return f"{BASE_URL}/{release['release_suffix']}/{release['zip_filename']}"


def download_file(url, dest_path):
    """Download a file from url to dest_path with a progress indicator."""
    print(f"  Downloading: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            total = response.headers.get("Content-Length")
            total = int(total) if total else None

            with open(dest_path, "wb") as f:
                downloaded = 0
                chunk_size = 1024 * 64
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  Progress: {downloaded:,} / {total:,} bytes ({pct:.1f}%)", end="", flush=True)
                    else:
                        print(f"\r  Downloaded: {downloaded:,} bytes", end="", flush=True)
            print()  # newline after progress
        return True
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"  Failed: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def extract_zip(zip_path, extract_to):
    """Extract a zip file and list its contents."""
    print(f"  Extracting to: {extract_to}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
        names = zf.namelist()
    print(f"  Extracted {len(names)} file(s):")
    for name in names:
        full_path = os.path.join(extract_to, name)
        if os.path.isfile(full_path):
            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            print(f"    - {name} ({size_mb:.1f} MB)")
        else:
            print(f"    - {name}/")
    return names


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("SFS PUMF Downloader")
    print("Catalogue: 13M0006X — Statistics Canada")
    print("=" * 60)
    print()

    for release in RELEASES:
        url = build_url(release)
        zip_dest = os.path.join(DATA_DIR, release["zip_filename"])
        print(f"Trying: {release['description']}")

        if download_file(url, zip_dest):
            print(f"  Successfully downloaded {release['description']}")
            print()

            extract_dir = os.path.join(DATA_DIR, f"sfs_{release['survey_year']}")
            os.makedirs(extract_dir, exist_ok=True)
            extract_zip(zip_dest, extract_dir)

            print()
            print(f"Data is ready in: {extract_dir}")
            print(f"Survey year: {release['survey_year']}")
            print()
            print("Next steps:")
            print("  - Check the extracted folder for a user guide / codebook PDF")
            print("  - The microdata is typically in CSV or fixed-width TXT format")
            print("  - Load the data with pandas:")
            print(f'    import pandas as pd')
            print(f'    df = pd.read_csv("<path_to_csv>")')
            return 0

        print()

    print("ERROR: Could not download any SFS PUMF release.")
    print("The file may require manual download from:")
    print(f"  https://www150.statcan.gc.ca/n1/pub/13m0006x/13m0006x2021001-eng.htm")
    print()
    print("Or from the Open Government Portal:")
    print("  https://open.canada.ca/data/en/dataset/11aecdcb-8bec-4dbe-9da2-3b0cc4e740c9")
    return 1


if __name__ == "__main__":
    sys.exit(main())
