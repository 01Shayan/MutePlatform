"""Group Manager session — Catalog + Snapshot + Query + Working Set for one visit."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import GroupCatalog
from .query import GroupQuery
from .snapshot import GroupSnapshot
from .working_set import WorkingSet


@dataclass
class GroupManagerSession:
    workspace_name: str
    catalog: GroupCatalog | None = None
    snapshot: GroupSnapshot | None = None
    query: GroupQuery | None = None
    working_set: WorkingSet | None = None
    target_rules: tuple = ()
    last_report_path: str | None = None

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot is not None

    @property
    def has_working_set(self) -> bool:
        return self.working_set is not None
