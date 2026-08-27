# ios_rule — Project Context

## Purpose

`ios_rule` builds the rulesets used by the user's Quantumult X configuration. It reads an upstream `msub.ini`, normalizes and de-duplicates its sources, publishes generated `.list` files, and updates a private aggregated Gist.

## Pipeline

1. GitHub Actions runs every six hours (and can be triggered manually).
2. The `SOURCE_MSUB_URL` GitHub Secret supplies the raw `msub.ini` URL.
3. `scripts/build_rules.py` fetches rulesets, normalizes them, removes duplicates within and across groups, and writes generated `.list` files.
4. The workflow uploads `.generated/msub_aggregated.ini` to the private Gist identified by `AGGREGATED_GIST_ID`.

Generated root-level `.list` files are outputs; do not edit them by hand.

## Stable rules and invariants

- Every generated rule has exactly one policy-group name.
- For ordinary rules the policy group is the final field. For `no-resolve` rules it is immediately before `no-resolve`.
- Normalize `PROCESS-NAME` to `USER-AGENT` and `IP-CIDR6` to Quantumult X-compatible `IP6-CIDR`.
- Cross-list de-duplication happens before attaching the policy group; earlier groups in `msub.ini` win.
- `user-defined/bypass.list` is user-maintained input that is merged into `direct.list`; it is not separately referenced in the aggregated subscription.
- `user-defined/barking.list` is user-maintained, has its own `🐶 狗叫` policy group, and is not downloaded, aggregated, or overwritten. The aggregated subscription references it independently.

## Safe change workflow

Change the generator/tests or the upstream `msub.ini`, not generated outputs. Then run tests, commit/push, manually dispatch **Update Rules** (or wait for schedule), and verify both the workflow and the private Gist were updated.
