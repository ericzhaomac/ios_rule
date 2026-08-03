# ios_rule

This repository mirrors and aggregates remote proxy rulesets into one local file per group.

## Source of truth

- Original gist: `https://gist.githubusercontent.com/ericzhaomac/46caca8a5f226a7b7a9abbec79aba95f/raw/msub.ini`

## Generated files

- `*.list`: aggregated ruleset files, one per group
- `msub_aggregated.ini`: rewritten version of the original config that points to this repository's aggregated files
- `RULESETS.md`: mapping from each output file to its upstream sources

## Local rebuild

```bash
python3 scripts/build_rules.py
python3 -m unittest discover -s tests -v
```

## GitHub Actions secrets

- `GIST_TOKEN`: GitHub token with `gist` scope
- `AGGREGATED_GIST_ID`: the secret gist ID for `msub_aggregated.ini`
