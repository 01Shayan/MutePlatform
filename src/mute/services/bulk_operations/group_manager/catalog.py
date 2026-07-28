"""Group Catalog — available Group IDs from the panel (independent of Snapshot)."""

from __future__ import annotations

from dataclasses import dataclass

from ....integrations.pasarguard.client import PasarGuardClient, create_client
from ....core.workspace import Workspace


@dataclass(frozen=True)
class GroupInfo:
    id: int
    name: str = ""


@dataclass(frozen=True)
class GroupCatalog:
    """Available groups for the current Group Manager visit. Not part of Snapshot."""

    groups: tuple[GroupInfo, ...]

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(group.id for group in self.groups)

    def __len__(self) -> int:
        return len(self.groups)


def load_group_catalog(workspace: Workspace, *, client: PasarGuardClient | None = None) -> GroupCatalog:
    api = client or create_client(workspace)
    rows = api.get_groups_simple(all_groups=True)
    groups: list[GroupInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_id = row.get("id")
        if raw_id is None:
            continue
        try:
            group_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        name = row.get("name")
        groups.append(GroupInfo(id=group_id, name=str(name) if name is not None else str(group_id)))
    return GroupCatalog(groups=tuple(groups))


from ....ui.copy import LABEL_AVAILABLE_GROUPS_BLOCK


def format_available_groups(catalog: GroupCatalog | None, *, empty: str = "(none)") -> str:
    """Display block shown whenever the user must enter Group IDs."""
    if catalog is None or not catalog.groups:
        ids_line = empty
    else:
        ids_line = " ".join(str(group.id) for group in catalog.groups)
    return f"{LABEL_AVAILABLE_GROUPS_BLOCK}\n{ids_line}\n----------------"
