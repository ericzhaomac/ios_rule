from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
import argparse
import os


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_BASE_URL = "https://raw.githubusercontent.com/ericzhaomac/ios_rule/main"
DEFAULT_AGGREGATED_CONFIG = ROOT / ".generated" / "msub_aggregated.ini"
DEFAULT_RULESETS_DOC = ROOT / "RULESETS.md"

RULESET_SLUGS = {
    "🎯 全球直连": "direct",
    "🛑 广告拦截": "advertising",
    "📲 电报消息": "telegram",
    "🤖 AI 服务": "ai",
    "🎬 流媒体": "streaming",
    "🇬🇧 BBC": "bbc",
    "🇹🇼 巴哈姆特": "bahamut",
    "🍎 苹果服务": "apple",
    "🐶 狗叫": "barking",
    "🌍 全球代理": "global",
    "🇨🇳 中国代理": "china",
}
MANUALLY_MANAGED_GROUPS = {"🐶 狗叫"}


@dataclass
class ParsedMsub:
    original_lines: list[str]
    rule_order: list[tuple[str, str]]
    remote_rules: dict[str, list[str]]
    inline_rules: dict[str, list[str]]
    other_lines: list[str]


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ios_rule-builder/1.0"})
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def parse_msub(content: str) -> ParsedMsub:
    rule_order: list[tuple[str, str]] = []
    remote_rules: dict[str, list[str]] = {}
    inline_rules: dict[str, list[str]] = {}
    other_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            other_lines.append("")
            continue
        if not line.startswith("ruleset="):
            other_lines.append(raw_line)
            continue

        group, source = raw_line[len("ruleset=") :].split(",", 1)
        source = source.strip()
        rule_order.append((group, source))
        target = remote_rules if source.startswith(("http://", "https://")) else inline_rules
        target.setdefault(group, []).append(source)

    return ParsedMsub(
        original_lines=content.splitlines(),
        rule_order=rule_order,
        remote_rules=remote_rules,
        inline_rules=inline_rules,
        other_lines=other_lines,
    )


def merge_rule_lines(contents: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for content in contents:
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if line not in seen:
                seen.add(line)
                merged.append(line)
    return merged


def normalize_rule_line(line: str) -> str:
    if line.upper().startswith("PROCESS-NAME,"):
        return f"USER-AGENT,{line.split(',', 1)[1]}"
    if line.upper().startswith("IP-CIDR6,"):
        return f"IP6-CIDR,{line.split(',', 1)[1]}"
    return line


def remove_policy_groups(line: str) -> str:
    return ",".join(field for field in line.split(",") if field.strip() not in RULESET_SLUGS)


def append_policy_group(line: str, group: str) -> str:
    fields = remove_policy_groups(line).split(",")
    if fields[-1].strip().lower() == "no-resolve":
        fields.insert(-1, group)
    else:
        fields.append(group)
    return ",".join(fields)


def validate_policy_group_lines(lines: list[str], group: str, source: str) -> None:
    for line_number, line in enumerate(lines, 1):
        if not line or line.startswith(("#", ";")):
            continue
        fields = [field.strip() for field in line.split(",")]
        policies = [(index, field) for index, field in enumerate(fields) if field in RULESET_SLUGS]
        expected_position = len(fields) - 2 if fields[-1].lower() == "no-resolve" else len(fields) - 1
        if policies != [(expected_position, group)]:
            raise ValueError(
                f"{source}:{line_number}: expected exactly one {group!r} policy group at the end: {line}"
            )


def build_group_rule_lines(parsed: ParsedMsub, fetcher) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    claimed: set[str] = set()

    for group, sources in parsed.remote_rules.items():
        if group in MANUALLY_MANAGED_GROUPS:
            continue
        merged = merge_rule_lines([fetcher(source) for source in sources])
        filtered: list[str] = []
        for line in merged:
            line = remove_policy_groups(normalize_rule_line(line))
            if line in claimed:
                continue
            claimed.add(line)
            filtered.append(append_policy_group(line, group))
        grouped[group] = filtered

    return grouped


def build_aggregated_config(parsed: ParsedMsub, output_base_url: str) -> str:
    emitted_remote_groups: set[str] = set()
    output_lines = ["; aggregated rules"]

    for raw_line in parsed.original_lines:
        if not raw_line.startswith("ruleset="):
            output_lines.append(raw_line)
            continue

        group, source = raw_line[len("ruleset=") :].split(",", 1)
        source = source.strip()
        if not source.startswith(("http://", "https://")):
            output_lines.append(raw_line)
            continue
        if group in emitted_remote_groups:
            continue
        emitted_remote_groups.add(group)
        slug = RULESET_SLUGS[group]
        output_lines.append(f"ruleset={group},{output_base_url}/{slug}.list")

    return "\n".join(output_lines) + "\n"


def render_rulesets_markdown(parsed: ParsedMsub) -> str:
    lines = [
        "# Aggregated Rulesets",
        "",
        "This repository builds one local `.list` file per ruleset group.",
        "",
        "| Group | Output File |",
        "| --- | --- |",
    ]
    for group in parsed.remote_rules:
        slug = RULESET_SLUGS[group]
        lines.append(f"| {group} | `{slug}.list` |")
    return "\n".join(lines) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build(source_url: str, output_base_url: str, aggregated_config_path: Path, rulesets_doc_path: Path) -> None:
    parsed = parse_msub(fetch_text(source_url))

    missing = sorted(set(parsed.remote_rules) - set(RULESET_SLUGS))
    if missing:
        raise KeyError(f"Missing slug mapping for: {', '.join(missing)}")

    grouped = build_group_rule_lines(parsed, fetch_text)

    for group, merged in grouped.items():
        slug = RULESET_SLUGS[group]
        validate_policy_group_lines(merged, group, f"{slug}.list")
        write_text(ROOT / f"{slug}.list", "\n".join(merged) + "\n")

    for group in MANUALLY_MANAGED_GROUPS.intersection(parsed.remote_rules):
        path = ROOT / f"{RULESET_SLUGS[group]}.list"
        if not path.exists():
            raise FileNotFoundError(f"Missing manually managed ruleset: {path}")
        validate_policy_group_lines(path.read_text(encoding="utf-8").splitlines(), group, path.name)

    write_text(aggregated_config_path, build_aggregated_config(parsed, output_base_url))
    write_text(rulesets_doc_path, render_rulesets_markdown(parsed))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default=os.getenv("SOURCE_MSUB_URL"))
    parser.add_argument("--output-base-url", default=os.getenv("OUTPUT_BASE_URL", DEFAULT_OUTPUT_BASE_URL))
    parser.add_argument(
        "--aggregated-config-path",
        type=Path,
        default=Path(os.getenv("AGGREGATED_CONFIG_PATH", DEFAULT_AGGREGATED_CONFIG)),
    )
    parser.add_argument(
        "--rulesets-doc-path",
        type=Path,
        default=Path(os.getenv("RULESETS_DOC_PATH", DEFAULT_RULESETS_DOC)),
    )
    args = parser.parse_args()
    if not args.source_url:
        raise SystemExit("Missing SOURCE_MSUB_URL")

    build(args.source_url, args.output_base_url, args.aggregated_config_path, args.rulesets_doc_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
