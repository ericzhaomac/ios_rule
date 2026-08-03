import tempfile
import unittest
from pathlib import Path

from scripts.build_rules import (
    RULESET_SLUGS,
    build_aggregated_config,
    build_group_rule_lines,
    merge_rule_lines,
    parse_msub,
    render_rulesets_markdown,
)


SAMPLE_MSUB = """; comment
ruleset=🎯 全球直连,[]DOMAIN-SUFFIX,local
ruleset=🎯 全球直连,https://example.com/direct.list
ruleset=🛑 广告拦截,https://example.com/ads.list
ruleset=🛑 广告拦截,https://example.com/hijacking.list
ruleset=🐟 漏网之鱼,[]FINAL
custom_proxy_group=🛑 广告拦截`select`[]REJECT
"""


class ParseMsubTests(unittest.TestCase):
    def test_parse_msub_separates_remote_and_inline_rules(self) -> None:
        parsed = parse_msub(SAMPLE_MSUB)

        self.assertEqual(parsed.inline_rules["🎯 全球直连"], ["[]DOMAIN-SUFFIX,local"])
        self.assertEqual(
            parsed.remote_rules["🛑 广告拦截"],
            ["https://example.com/ads.list", "https://example.com/hijacking.list"],
        )
        self.assertEqual(parsed.other_lines, ["; comment", "custom_proxy_group=🛑 广告拦截`select`[]REJECT"])

    def test_merge_rule_lines_deduplicates_and_skips_comments(self) -> None:
        merged = merge_rule_lines(
            [
                "# comment",
                "DOMAIN-SUFFIX,example.com",
                "DOMAIN-SUFFIX,example.com",
                "",
                "IP-CIDR,1.1.1.0/24",
            ]
        )

        self.assertEqual(merged, ["DOMAIN-SUFFIX,example.com", "IP-CIDR,1.1.1.0/24"])

    def test_build_group_rule_lines_removes_cross_group_overlap_by_rule_order(self) -> None:
        parsed = parse_msub(
            """ruleset=🎯 全球直连,https://example.com/direct.list
ruleset=🛑 广告拦截,https://example.com/ads.list
ruleset=🌍 全球代理,https://example.com/global.list
"""
        )
        fetched = {
            "https://example.com/direct.list": "DOMAIN-SUFFIX,keep-direct.com\nDOMAIN-SUFFIX,shared.com\n",
            "https://example.com/ads.list": "DOMAIN-SUFFIX,shared.com\nDOMAIN-SUFFIX,keep-ads.com\n",
            "https://example.com/global.list": "DOMAIN-SUFFIX,shared.com\nDOMAIN-SUFFIX,keep-global.com\n",
        }

        grouped = build_group_rule_lines(parsed, fetched.__getitem__)

        self.assertEqual(
            grouped["🎯 全球直连"],
            ["DOMAIN-SUFFIX,keep-direct.com", "DOMAIN-SUFFIX,shared.com"],
        )
        self.assertEqual(grouped["🛑 广告拦截"], ["DOMAIN-SUFFIX,keep-ads.com"])
        self.assertEqual(grouped["🌍 全球代理"], ["DOMAIN-SUFFIX,keep-global.com"])

    def test_build_aggregated_config_rewrites_only_remote_rules(self) -> None:
        parsed = parse_msub(SAMPLE_MSUB)
        config = build_aggregated_config(parsed, "https://raw.githubusercontent.com/ericzhaomac/ios_rule/main")

        self.assertIn("; aggregated rules", config)
        self.assertIn("ruleset=🎯 全球直连,[]DOMAIN-SUFFIX,local", config)
        self.assertIn(
            "ruleset=🎯 全球直连,https://raw.githubusercontent.com/ericzhaomac/ios_rule/main/direct.list",
            config,
        )
        self.assertIn(
            "ruleset=🛑 广告拦截,https://raw.githubusercontent.com/ericzhaomac/ios_rule/main/advertising.list",
            config,
        )
        self.assertNotIn("https://example.com/ads.list", config)

    def test_render_rulesets_markdown_lists_sources(self) -> None:
        parsed = parse_msub(SAMPLE_MSUB)
        markdown = render_rulesets_markdown(parsed)

        self.assertIn("`advertising.list`", markdown)
        self.assertNotIn("https://example.com/hijacking.list", markdown)

    def test_all_remote_groups_have_slug_mapping(self) -> None:
        parsed = parse_msub(SAMPLE_MSUB)
        for group in parsed.remote_rules:
            self.assertIn(group, RULESET_SLUGS)


if __name__ == "__main__":
    unittest.main()
