"""Role -> permission matrix (ARCHITECTURE 9).

Guest grants (per-device / time-window) are a separate phase. Until then a guest
can only view; nothing pretends otherwise.
"""

from typing import Dict, FrozenSet

PERMISSIONS = (
    "view",
    "control_basic",
    "control_access",
    "control_power",
    "camera_live",
    "camera_archive",
    "configure",
    "manage_users",
    "view_audit",
)

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "owner": frozenset(PERMISSIONS),
    "admin": frozenset(
        {
            "view", "control_basic", "control_access", "control_power",
            "camera_live", "camera_archive", "configure", "view_audit",
        }
    ),
    # camera_live for family is "configurable" in ARCHITECTURE 9; default is deny
    # until per-member settings exist.
    "family": frozenset({"view", "control_basic", "control_access"}),
    "guest": frozenset({"view"}),
    "viewer": frozenset({"view"}),
}

ASSIGNABLE_ROLES = ("admin", "family", "guest", "viewer")


def has_permission(role: str, permission: str) -> bool:
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
