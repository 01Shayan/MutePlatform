"""Bulk Operations — top-level home for every future bulk modification feature.

v0.3.0 ships only Group Manager. Additional managers (Expire, Status, …) are out of scope.
"""

from .group_manager import GroupManagerApplicationService, GroupManagerError, WorkingSet

__all__ = [
    "GroupManagerApplicationService",
    "GroupManagerError",
    "WorkingSet",
]
