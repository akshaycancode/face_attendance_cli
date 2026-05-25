"""
attendance.py
=============
Attendance business logic: marking ENTRY / EXIT, cooldown management,
and duration calculation.

This module sits between the recognition loop and the database layer.
"""

import time
from datetime import datetime

from config import (
    DUPLICATE_COOLDOWN_SECONDS, DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT,
)
from logger_config import logger
import database as db
from utils import calculate_duration

# In-memory cooldown tracker: {student_id: last_marked_epoch}
_last_marked: dict[int, float] = {}


def can_mark_again(student_id: int) -> bool:
    """
    Return True if enough time has elapsed since the last attendance
    event for this student (controlled by DUPLICATE_COOLDOWN_SECONDS).
    """
    last = _last_marked.get(student_id)
    if last is None:
        return True
    return (time.time() - last) >= DUPLICATE_COOLDOWN_SECONDS


def _touch_cooldown(student_id: int) -> None:
    """Record the current time as the last attendance action for a student."""
    _last_marked[student_id] = time.time()


def reset_cooldowns() -> None:
    """Clear all cooldown entries (useful when restarting a session)."""
    _last_marked.clear()


# ---------------------------------------------------------------------------
# ENTRY logic
# ---------------------------------------------------------------------------

def mark_entry(student_id: int, confidence: float) -> str:
    """
    Attempt to mark an ENTRY attendance for the student today.

    Returns
    -------
    str
        A user-facing status message.
    """
    today = datetime.now().strftime(DATE_FORMAT)
    now_time = datetime.now().strftime(TIME_FORMAT)
    student = db.get_student_by_id(student_id)
    name = student["name"] if student else f"ID:{student_id}"

    # --- Cooldown check ---
    if not can_mark_again(student_id):
        db.log_attendance_event(student_id, "DUPLICATE_IGNORED",
                                confidence=confidence,
                                message="Cooldown active")
        logger.debug("Cooldown active for student_id=%d", student_id)
        return f"[COOLDOWN] {name} — already processed recently"

    # --- Check existing record ---
    existing = db.get_attendance_for_student_date(student_id, today)

    if existing and existing.get("in_time"):
        # Entry already recorded today
        db.log_attendance_event(student_id, "DUPLICATE_IGNORED",
                                confidence=confidence,
                                message="Entry already marked today")
        _touch_cooldown(student_id)
        msg = f"[ALREADY] Entry already marked for {name} today"
        logger.info(msg)
        print(msg)
        return msg

    # --- Create new entry ---
    try:
        db.create_attendance_entry(student_id, today, now_time)
        db.log_attendance_event(student_id, "ENTRY_MARKED",
                                confidence=confidence,
                                message=f"IN at {now_time}")
        _touch_cooldown(student_id)
        msg = f"[ENTRY] {name} — IN at {now_time}  (conf: {confidence:.2f})"
        logger.info(msg)
        print(msg)
        return msg

    except Exception as exc:
        logger.exception("Failed to mark entry for student_id=%d", student_id)
        db.log_attendance_event(student_id, "DUPLICATE_IGNORED",
                                confidence=confidence,
                                message=str(exc))
        _touch_cooldown(student_id)
        return f"[WARN] Could not mark entry for {name}: {exc}"


# ---------------------------------------------------------------------------
# EXIT logic
# ---------------------------------------------------------------------------

def mark_exit(student_id: int, confidence: float) -> str:
    """
    Attempt to mark an EXIT attendance for the student today.

    Returns
    -------
    str
        A user-facing status message.
    """
    today = datetime.now().strftime(DATE_FORMAT)
    now_time = datetime.now().strftime(TIME_FORMAT)
    student = db.get_student_by_id(student_id)
    name = student["name"] if student else f"ID:{student_id}"

    # --- Cooldown check ---
    if not can_mark_again(student_id):
        db.log_attendance_event(student_id, "DUPLICATE_IGNORED",
                                confidence=confidence,
                                message="Cooldown active (exit)")
        return f"[COOLDOWN] {name} — already processed recently"

    # --- Check existing record ---
    existing = db.get_attendance_for_student_date(student_id, today)

    if not existing or not existing.get("in_time"):
        # No entry record for today — cannot mark exit
        db.log_attendance_event(student_id, "NO_ENTRY_FOUND",
                                confidence=confidence,
                                message="Exit attempted without entry")
        _touch_cooldown(student_id)
        msg = f"[NO ENTRY] No entry record found for {name} today"
        logger.info(msg)
        print(msg)
        return msg

    if existing.get("out_time"):
        # Exit already marked
        db.log_attendance_event(student_id, "ALREADY_EXITED",
                                confidence=confidence,
                                message="Exit already recorded")
        _touch_cooldown(student_id)
        msg = f"[ALREADY] Exit already marked for {name} today"
        logger.info(msg)
        print(msg)
        return msg

    # --- Mark exit ---
    try:
        db.update_attendance_exit(student_id, today, now_time)
        duration = calculate_duration(existing["in_time"], now_time)
        db.log_attendance_event(student_id, "EXIT_MARKED",
                                confidence=confidence,
                                message=f"OUT at {now_time}, duration={duration}")
        _touch_cooldown(student_id)
        msg = f"[EXIT] {name} — OUT at {now_time}  (duration: {duration}, conf: {confidence:.2f})"
        logger.info(msg)
        print(msg)
        return msg

    except Exception as exc:
        logger.exception("Failed to mark exit for student_id=%d", student_id)
        _touch_cooldown(student_id)
        return f"[WARN] Could not mark exit for {name}: {exc}"
