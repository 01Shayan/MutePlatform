"""Group Manager — Required Group ID check, Working Set, and actions.

Users are never manually selected. Check produces a Working Set; every Action
operates on that Working Set.
"""

from .application_service import GroupManagerApplicationService
from .errors import GroupManagerError
from .working_set import CheckCriteria, WorkingSet, WorkingSetUser

__all__ = [
    "CheckCriteria",
    "GroupManagerApplicationService",
    "GroupManagerError",
    "WorkingSet",
    "WorkingSetUser",
]
