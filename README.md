# ios_rule

This repository maintains aggregated proxy rulesets and the automation used to refresh them.

## Ruleset files

- `*.list`: automatically aggregated ruleset files
- `user-defined/bypass.list`: manually maintained input merged into `direct.list`
- `user-defined/barking.list`: manually maintained passthrough rules for the independent `🐶 狗叫` policy
- `RULESETS.md`: mapping from each output file to its group name

Each generated rule ends with its full policy group name, including the emoji.
For example: `DOMAIN-SUFFIX,example.com,🛑 广告拦截`.
For rules ending in `no-resolve`, the policy group is inserted immediately before
that option. `PROCESS-NAME` rules are emitted as `USER-AGENT`, and `IP-CIDR6`
rules are emitted as Quantumult X-compatible `IP6-CIDR`.
The builder validates that every rule contains its policy group exactly once.
Files under `user-defined/` are validated but never overwritten by the builder.
When referenced by the source `msub.ini`, `bypass.list` participates in Direct
aggregation and deduplication, while `barking.list` remains a standalone ruleset.

## Local rebuild

```bash
SOURCE_MSUB_URL='***' python3 scripts/build_rules.py
python3 -m unittest discover -s tests -v
```

## GitHub Actions secrets

- `SOURCE_MSUB_URL`: source configuration URL
- `GIST_TOKEN`: GitHub token with `gist` scope
- `AGGREGATED_GIST_ID`: the secret gist ID for `msub_aggregated.ini`
