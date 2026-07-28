"""Operation plugin package — register write operations here."""

from .base import GroupOperation
from .stubs import AddGroupsOperation, RemoveGroupsOperation, ReplaceGroupsOperation, default_operations

__all__ = [
    "AddGroupsOperation",
    "GroupOperation",
    "RemoveGroupsOperation",
    "ReplaceGroupsOperation",
    "default_operations",
]
