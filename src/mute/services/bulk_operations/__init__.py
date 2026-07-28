"""Bulk Operations — top-level home for every future bulk modification feature.

v0.3.0 ships Group Manager. Each manager is isolated and owns its own Snapshot shape.
"""

from .group_manager import (
    ExecutionReport,
    GroupManagerApplicationService,
    GroupManagerError,
    GroupQuery,
    MatchMode,
    WorkingSet,
)

__all__ = [
    "ExecutionReport",
    "GroupManagerApplicationService",
    "GroupManagerError",
    "GroupQuery",
    "MatchMode",
    "WorkingSet",
]
