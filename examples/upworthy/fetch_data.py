"""Download the Upworthy Research Archive exploratory dataset (14 MB).

The archive (Matias, Munger & Watts, Scientific Data 2021,
https://doi.org/10.1038/s41597-021-00934-7) contains 32,487 real headline
A/B tests run on upworthy.com between 2013 and 2015. The exploratory split
used here holds 4,873 tests / 22,666 packages and is publicly distributed
via the Open Science Framework: https://osf.io/jd64p/

Usage: python fetch_data.py
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

URL = "https://osf.io/download/3vqmp/"
DEST = Path(__file__).parent / "data" / "upworthy-archive-exploratory-packages-03.12.2020.csv"


def main() -> None:
    if DEST.exists():
        print(f"already present: {DEST}")
        return
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL} -> {DEST}")
    urllib.request.urlretrieve(URL, DEST)
    print(f"done ({DEST.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
