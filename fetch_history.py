"""Fetch NSE index PE/PB/DividendYield history from Downstox (NSE source) into data/pe/."""
import os, requests

SLUGS = [
    "nifty-50", "nifty-bank", "nifty-it", "nifty-midcap-100", "nifty-pharma",
    "nifty-fmcg", "nifty-auto", "nifty-next-50", "nifty-100", "nifty-500",
    "nifty-energy", "nifty-metal", "nifty-psu-bank", "nifty-consumption",
    "nifty-midcap-50", "nifty-smallcap-100", "nifty-smallcap-50",
    "nifty-infra", "nifty-realty", "nifty-media",
]

BASE = "https://downstox.com/api/index-pe/{slug}/download"

def fetch_all(outdir="data/pe"):
    os.makedirs(outdir, exist_ok=True)
    ok, fail = [], []
    for s in SLUGS:
        try:
            r = requests.get(BASE.format(slug=s), headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            if r.status_code == 200 and b"Month,PE" in r.content[:500]:
                with open(os.path.join(outdir, f"{s}.csv"), "wb") as f:
                    f.write(r.content)
                ok.append(s)
                print(f"OK {s} ({len(r.content)} bytes)")
            else:
                fail.append(s)
                print(f"FAIL {s}: {r.status_code}")
        except Exception as e:
            fail.append(s)
            print(f"ERR {s}: {e}")
    print(f"Done: {len(ok)} ok, {len(fail)} failed: {fail}")
    return ok, fail

if __name__ == "__main__":
    fetch_all()
