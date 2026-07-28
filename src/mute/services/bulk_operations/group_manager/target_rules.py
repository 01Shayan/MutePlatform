"""Target Selection UI rules — presentation layer over GroupQuery.

Compiles human-friendly target rules into the existing Query Engine shape.
Does not change Query Engine or Panel API behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .query import GroupQuery, MatchMode


class TargetRuleKind(str, Enum):
    ALL_USERS = "all_users"
    WITH_GROUPS = "with_groups"
    WITHOUT_GROUPS = "without_groups"


@dataclass(frozen=True)
class TargetRule:
    kind: TargetRuleKind
    group_ids: tuple[int, ...] = ()
    require_all: bool = True  # only for WITH_GROUPS: True = all selected, False = any


def compile_target_rules(rules: Sequence[TargetRule]) -> GroupQuery:
    """Map UI rules → GroupQuery (include / exclude / match_mode)."""
    include: tuple[int, ...] = ()
    exclude: tuple[int, ...] = ()
    mode = MatchMode.ANY
    for rule in rules:
        if rule.kind is TargetRuleKind.WITH_GROUPS:
            include = tuple(rule.group_ids)
            mode = MatchMode.ALL if rule.require_all else MatchMode.ANY
        elif rule.kind is TargetRuleKind.WITHOUT_GROUPS:
            exclude = tuple(rule.group_ids)
        # ALL_USERS adds no constraint
    return GroupQuery(
        include_group_ids=include,
        exclude_group_ids=exclude,
        match_mode=mode,
    )


def format_target_rules(rules: Sequence[TargetRule]) -> list[str]:
    """Human-readable Current Target / Review target section."""
    if not rules:
        return ["(none)"]
    lines: list[str] = []
    for index, rule in enumerate(rules):
        if index:
            lines.append("AND")
        lines.extend(_format_rule(rule))
    return lines


def format_rule_checkmarks(rules: Sequence[TargetRule]) -> list[str]:
    """Current Target block with checkmarks."""
    if not rules:
        return ["(none)"]
    lines: list[str] = ["Current Target"]
    for index, rule in enumerate(rules):
        if index:
            lines.append("AND")
        body = _format_rule(rule)
        if not body:
            continue
        lines.append(f"✓ {body[0]}")
        lines.extend(body[1:])
    return lines


def _format_rule(rule: TargetRule) -> list[str]:
    if rule.kind is TargetRuleKind.ALL_USERS:
        return ["🌐 All Snapshot Users"]
    if rule.kind is TargetRuleKind.WITH_GROUPS:
        mode = "ALL" if rule.require_all else "ANY"
        # Spec: "Users with ALL groups" / plain English for review
        if rule.require_all:
            header = "🏷 Users with ALL groups"
        else:
            header = "🏷 Users with ANY group"
        return [header, *_id_lines(rule.group_ids)]
    if rule.kind is TargetRuleKind.WITHOUT_GROUPS:
        label = "🚫 Users without groups" if len(rule.group_ids) != 1 else "🚫 Users without group"
        return [label, *_id_lines(rule.group_ids)]
    return []


def has_rule_kind(rules: Sequence[TargetRule], kind: TargetRuleKind) -> bool:
    return any(rule.kind is kind for rule in rules)


def replace_or_append(rules: Sequence[TargetRule], new_rule: TargetRule) -> tuple[TargetRule, ...]:
    """One rule per kind — adding the same kind replaces the previous."""
    remaining = [rule for rule in rules if rule.kind is not new_rule.kind]
    remaining.append(new_rule)
    return tuple(remaining)


def _id_lines(values: Sequence[int]) -> list[str]:
    if not values:
        return ["—"]
    return [str(value) for value in values]
