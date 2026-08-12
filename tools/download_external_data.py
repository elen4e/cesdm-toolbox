"""download_external_data.py

Downloads and extracts the external CESDM reference datasets (TYNDP 2024,
PyPSA network files) used by examples/example_import_tyndp_proxy_api.py's
full-pipeline mode and examples/example_import_pypsa.py.

Usage (from repository root or anywhere after install)::

    cesdm-download-data
    cesdm-download-data --insecure

    python -m tools.download_external_data
    python tools/download_external_data.py --insecure
"""

from __future__ import annotations

import argparse
import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import zipfile

URL = "https://ethz.ch/content/dam/ethz/special-interest/mavt/ctr-energy-networks-fen-dam/data/cesdm_external_data.zip"

_SSL_HELP = """\
SSL errors here are almost always one of two things, not a problem
with this script or with ethz.ch itself:

  1. Your network intercepts HTTPS traffic for inspection (common on
     corporate/institutional staff networks and VPNs) and presents its
     own certificate instead of the real one. Try a different network
     (mobile hotspot, home network, a VPN split tunnel that excludes
     this domain) to confirm, then ask your IT department for the
     proxy's CA certificate if you need to stay on this network.
  2. Your Python installation is missing an up-to-date certificate
     bundle -- on macOS with python.org's installer, run the
     "Install Certificates.command" script it ships with (in
     /Applications/Python <version>/), or `pip install --upgrade certifi`.

Only if you understand and accept the risk (this disables protection
against a man-in-the-middle attack, not just a certificate warning):
rerun with --insecure.\
"""


def _repo_root() -> Path:
    """Toolbox root (parent of ``tools/``), so extract always lands correctly."""
    return Path(__file__).resolve().parents[1]


def _download(target: Path, *, ssl_context: "ssl.SSLContext | None") -> None:
    request = Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/zip,*/*",
        },
    )

    with urlopen(request, context=ssl_context) as response:
        total = int(response.headers.get("Content-Length", 0))

        with target.open("wb") as out:
            downloaded = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = downloaded / total * 100
                    print(f"\rDownloaded {percent:5.1f}%", end="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--insecure", action="store_true",
        help="Skip TLS certificate verification for this download. Only use "
             "this if you understand why verification is failing (see the "
             "message printed on failure) and trust the network you're on "
             "-- it removes protection against a man-in-the-middle attack, "
             "not just a certificate warning.",
    )
    args = parser.parse_args()

    ssl_context = None
    if args.insecure:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    root = _repo_root()
    target = root / "cesdm_external_data.zip"

    try:
        print(f"Downloading external CESDM data from:\n{URL}")
        if args.insecure:
            print("(TLS certificate verification disabled via --insecure)")
        _download(target, ssl_context=ssl_context)

        print("\nExtracting archive...")
        with zipfile.ZipFile(target, "r") as zf:
            zf.extractall(root)

        print(f"External CESDM example data downloaded and extracted under:\n{root}")

    except HTTPError as e:
        raise SystemExit(f"Download failed: HTTP {e.code}")

    except URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            print(f"Download failed: {e}\n", file=sys.stderr)
            print("This network intercepts HTTPS traffic or your certificate "
                  "bundle is outdated.\n" + _SSL_HELP, file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit(f"Download failed: {e}")


if __name__ == "__main__":
    main()
