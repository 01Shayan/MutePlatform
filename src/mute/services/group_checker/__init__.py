"""Offline group-membership query internals used by Group Manager Check.

Public interfaces should prefer ``bulk_operations.group_manager``.
"""

from .models import (
    BackupSource,
    GroupCheckerResult,
    GroupCheckerUserResult,
    GroupQueryDescriptor,
    GroupQueryType,
)
from .service import (
    GroupCheckerApplicationService,
    GroupCheckerOperationError,
    format_group_ids,
    parse_group_ids,
)

__all__ = [
    "BackupSource",
    "GroupCheckerApplicationService",
    "GroupCheckerOperationError",
    "GroupCheckerResult",
    "GroupCheckerUserResult",
    "GroupQueryDescriptor",
    "GroupQueryType",
    "format_group_ids",
    "parse_group_ids",
]
