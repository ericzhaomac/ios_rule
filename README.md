# ios_rule

This repository maintains aggregated proxy rulesets and the automation used to refresh them.

## Generated files

- `*.list`: aggregated ruleset files, one per group
- `RULESETS.md`: mapping from each output file to its group name

## Local rebuild

```bash
SOURCE_MSUB_URL='***' python3 scripts/build_rules.py
python3 -m unittest discover -s tests -v
```

## GitHub Actions secrets

- `SOURCE_MSUB_URL`: source configuration URL
- `GIST_TOKEN`: GitHub token with `gist` scope
- `AGGREGATED_GIST_ID`: the secret gist ID for `msub_aggregated.ini`
