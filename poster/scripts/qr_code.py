"""QR code for the poster header, pointing at the CHLA-Z website.

Writes figures/qr_code.svg.

Run from anywhere: python poster/scripts/qr_code.py
"""

from pathlib import Path

import segno

URL = "https://fish-pace.github.io/chla-z/"
OUT = Path(__file__).resolve().parent.parent / "figures" / "qr_code.svg"


def main():
    OUT.parent.mkdir(exist_ok=True)
    segno.make(URL, error="m").save(OUT, scale=10, border=0)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
