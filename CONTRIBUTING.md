# Contributing

Thanks for helping improve the valuation dashboard.

## Development

```bash
pip install -r requirements.txt
python fetch_history.py   # optional: refresh PE/PB CSVs
streamlit run app.py
```

## Data rules (please preserve)

- Like-for-like stats use the **consolidated-earnings era only
  (Apr-2021 onward)** — NSE switched from standalone on 31 Mar 2021.
- Valuation CSVs live in `data/pe/`; refresh via `python fetch_history.py`.
- Yahoo sectoral price histories are discontinued upstream; valuation-only
  mode is intentional.

## Pull requests

- Branch from `main`: `feature/<short-description>` or `fix/<short-description>`.
- Conventional commits (`feat:` / `fix:` / `docs:`), one logical change per commit.
- CI runs a compile check (Python 3.11 to match deploy); keep modules import-clean.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
