"""
branch_context.py
-----------------
Runtime singleton that tracks which school branch is currently active for the
logged-in user session.  All modules that need to know which database to query
(connection.py, config.py helper) read from this module.

Call `set_active_branch(...)` immediately after a successful login for a branch
user.  Call `clear_active_branch()` on logout.
"""

from __future__ import annotations
from pathlib import Path

# ---------------------------------------------------------------------------
# Internal state — never access these directly from outside this module.
# ---------------------------------------------------------------------------
_current_branch_id: int | None = None
_current_branch_name: str = "System"
_current_branch_db_path: Path | None = None


# ---------------------------------------------------------------------------
# Public setters / getters
# ---------------------------------------------------------------------------

def set_active_branch(branch_id: int, branch_name: str, db_filename: str) -> None:
    """
    Activate a branch session.

    Parameters
    ----------
    branch_id    : Primary key of the branch in the master DB.
    branch_name  : Human-readable branch name (displayed in the UI header).
    db_filename  : Basename of the branch SQLite file, e.g. ``"branch_1.db"``.
                   The full path is resolved using ``config.DATA_DIR``.
    """
    global _current_branch_id, _current_branch_name, _current_branch_db_path
    from config import DATA_DIR  # imported here to avoid circular imports at module load
    _current_branch_id = branch_id
    _current_branch_name = branch_name
    _current_branch_db_path = DATA_DIR / db_filename


def clear_active_branch() -> None:
    """Reset branch context (call on logout)."""
    global _current_branch_id, _current_branch_name, _current_branch_db_path
    _current_branch_id = None
    _current_branch_name = "System"
    _current_branch_db_path = None


# ---------------------------------------------------------------------------
# Getters
# ---------------------------------------------------------------------------

def get_active_branch_id() -> int | None:
    """Return the currently-active branch ID, or None for a System Admin session."""
    return _current_branch_id


def get_active_branch_name() -> str:
    """Return the display name of the active branch (used in the window header)."""
    return _current_branch_name


def get_active_branch_db_path() -> Path | None:
    """
    Return the absolute ``Path`` to the active branch's SQLite database file.
    Returns ``None`` when no branch is active (i.e., System Admin session).
    """
    return _current_branch_db_path


def is_branch_active() -> bool:
    """Return True when a branch user is logged in (as opposed to System Admin)."""
    return _current_branch_id is not None
