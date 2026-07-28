"""Group Engine application service — offline group queries over backup files.

The Check operation is implemented here today. Future write operations (Add,
Remove, Replace) must share one engine behind this service boundary.
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
