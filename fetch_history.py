"""Fetch NSE index PE/PB/DividendYield history from Downstox (NSE source) into data/pe/."""
import os
from concurrent.futures import ThreadPoolExecutor

import requests

from registry import INDICES

BASE = "https://downstox.com/api/index-pe/{slug}/download"
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pe")
MAX_WORKERS = 8

# Single source of truth: the index list lives in registry.py.
SLUGS = list(INDICES)


def _fetch_one(session, slug, outdir):
    try:
        r = session.get(BASE.format(slug=slug), timeout=30)
        if r.status_code == 200 and b"Month,PE" in r.content[:500]:
            with open(os.path.join(outdir, f"{slug}.csv"), "wb") as f:
                f.write(r.content)
            print(f"OK {slug} ({len(r.content)} bytes)")
            return slug, True
        print(f"FAIL {slug}: {r.status_code}")
        return slug, False
    except Exception as e:
        print(f"ERR {slug}: {e}")
        return slug, False


def fetch_all(outdir=OUTDIR):
    os.makedirs(outdir, exist_ok=True)
    ok, fail = [], []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        # Downloads are independent HTTP round-trips; 20 of them serially was
        # tens of seconds of pure latency. Keep-alive + a small pool fixes it.
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            results = pool.map(lambda s: _fetch_one(session, s, outdir), SLUGS)
            for slug, success in results:
                (ok if success else fail).append(slug)
    print(f"Done: {len(ok)} ok, {len(fail)} failed: {fail}")
    return ok, fail


if __name__ == "__main__":
    fetch_all()
