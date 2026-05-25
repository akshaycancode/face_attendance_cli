"""
utils.py
========
Shared utility functions: directory creation, date/time helpers,
input validation, CLI table formatting, and database backup.
"""

import os
import shutil
from datetime import datetime, timedelta

from config import (
    STUDENT_IMAGES_DIR, EXPORTS_DIR, LOGS_DIR,
    DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT,
)
from logger_config import logger


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    """Create all required data directories if they don't exist."""
    dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
        STUDENT_IMAGES_DIR,
        EXPORTS_DIR,
        LOGS_DIR,
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    logger.debug("Directories verified/created")


# ---------------------------------------------------------------------------
# Date / Time helpers
# ---------------------------------------------------------------------------

def today_str() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now().strftime(DATE_FORMAT)


def now_time_str() -> str:
    """Return current time as HH:MM:SS."""
    return datetime.now().strftime(TIME_FORMAT)


def now_iso() -> str:
    """Return current datetime as ISO-ish string."""
    return datetime.now().strftime(DATETIME_FORMAT)


def calculate_duration(in_time: str, out_time: str) -> str:
    """
    Calculate duration between two HH:MM:SS strings.

    Returns
    -------
    str
        Duration formatted as H:MM:SS, or '--' if inputs are invalid.
    """
    if not in_time or not out_time:
        return "--"
    try:
        t_in = datetime.strptime(in_time, TIME_FORMAT)
        t_out = datetime.strptime(out_time, TIME_FORMAT)
        delta = t_out - t_in
        if delta.total_seconds() < 0:
            delta += timedelta(days=1)   # Handle midnight crossing
        total_secs = int(delta.total_seconds())
        hours, rem = divmod(total_secs, 3600)
        mins, secs = divmod(rem, 60)
        return f"{hours}:{mins:02d}:{secs:02d}"
    except ValueError:
        return "--"


def is_valid_date(date_str: str) -> bool:
    """Return True if date_str matches YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, DATE_FORMAT)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_roll_no(roll_no: str) -> bool:
    """Return True if roll_no is non-empty after stripping whitespace."""
    return bool(roll_no and roll_no.strip())


def validate_name(name: str) -> bool:
    """Return True if name is non-empty after stripping whitespace."""
    return bool(name and name.strip())


# ---------------------------------------------------------------------------
# CLI table formatting
# ---------------------------------------------------------------------------

def print_table(headers: list[str], rows: list[list[str]],
                min_width: int = 8) -> None:
    """
    Print a formatted text table to stdout.

    Parameters
    ----------
    headers : list[str]
        Column header labels.
    rows : list[list[str]]
        Each inner list is one row of string values.
    min_width : int
        Minimum column width.
    """
    if not headers:
        return

    # Calculate column widths
    col_widths = [max(min_width, len(str(h))) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)

    print(f"\n {header_line}")
    print(f" {separator}")

    # Print rows
    if not rows:
        print("  (no records)")
    for row in rows:
        line = " | ".join(
            str(row[i] if i < len(row) else "").ljust(col_widths[i])
            for i in range(len(headers))
        )
        print(f" {line}")
    print()


# ---------------------------------------------------------------------------
# Database backup
# ---------------------------------------------------------------------------

def backup_database(db_path: str) -> str | None:
    """
    Create a timestamped backup of the SQLite database.

    Returns
    -------
    str or None
        Path to the backup file, or None on failure.
    """
    if not os.path.exists(db_path):
        print("[WARN] Database file not found — nothing to back up.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f"_backup_{timestamp}.db")
    try:
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Database backed up to: {backup_path}")
        logger.info("Database backed up to %s", backup_path)
        return backup_path
    except Exception as exc:
        logger.exception("Database backup failed")
        print(f"[ERROR] Backup failed: {exc}")
        return None
