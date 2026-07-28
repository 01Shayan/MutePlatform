"""CLI Group Manager helpers — Target Selection UX."""

from __future__ import annotations

from mute.services.bulk_operations.group_manager.target_rules import (
    TargetRule,
    TargetRuleKind,
    compile_target_rules,
    replace_or_append,
)
from mute.services.bulk_operations.group_manager.query import MatchMode


def test_replace_or_append_keeps_one_rule_per_kind():
    rules = (TargetRule(kind=TargetRuleKind.ALL_USERS),)
    rules = replace_or_append(
        rules,
        TargetRule(kind=TargetRuleKind.WITH_GROUPS, group_ids=(1,), require_all=True),
    )
    rules = replace_or_append(
        rules,
        TargetRule(kind=TargetRuleKind.WITH_GROUPS, group_ids=(2, 3), require_all=False),
    )
    assert len(rules) == 2
    with_rule = next(r for r in rules if r.kind is TargetRuleKind.WITH_GROUPS)
    assert with_rule.group_ids == (2, 3)
    assert with_rule.require_all is False
    query = compile_target_rules(rules)
    assert query.match_mode is MatchMode.ANY
    assert query.include_group_ids == (2, 3)
