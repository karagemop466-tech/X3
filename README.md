# X3

NFL research workspace: official injury and schedule data, strategy validation framework, suggestions and open questions.

**Live site:** https://karagemop466-tech.github.io/X3/ (published from `docs/` on `main`)

**Research only. Not betting advice.** Wagering with private bookmakers from Japan is a criminal offence for the bettor under Penal Code Article 185 ([official text](https://www.japaneselawtranslation.go.jp/en/laws/view/3581/tb)).

## Layout

| Path | Contents |
|------|----------|
| `docs/` | Static GitHub Pages site (generated) |
| `data/` | Source-of-truth CSVs: injuries, schedule, strategies, gates, correlations, questions, suggestions, requirements, flags, sources |
| `scripts/build_site.py` | Builds `docs/` from `data/` (standard library only) |
| `scripts/check_site.py` | Checks internal links and that every table row has a source link or unverified flag |
| `COORDINATION.md` | Shared task board, claims, verification log, integration log |

## Rebuild and check

```bash
python3 scripts/build_site.py
python3 scripts/check_site.py
```

## Rules for data

- Table values come only from official sources, each linked. Anything that cannot be confirmed is left blank and flagged `unverified`.
- Suggestions are not implemented until a decision is recorded.
- See `data/sources.csv` for the registry and `data/flags.csv` for irregularities.
