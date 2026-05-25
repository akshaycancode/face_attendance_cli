"""
database.py
===========
SQLite database layer for the Face Recognition Attendance System.
Handles schema creation, CRUD for students, face embeddings, attendance
records, attendance events, and device info.

All queries use parameterized SQL — no string formatting.
"""

import os
import sqlite3
from datetime import datetime

import numpy as np

from config import DATABASE_PATH, DATETIME_FORMAT
from logger_config import logger


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and foreign keys enabled."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row          # Access columns by name
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not already exist."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no     TEXT    UNIQUE NOT NULL,
            name        TEXT    NOT NULL,
            class_name  TEXT,
            section     TEXT,
            status      TEXT    DEFAULT 'active',
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS face_embeddings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            embedding   BLOB    NOT NULL,
            image_path  TEXT,
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id       INTEGER NOT NULL,
            attendance_date  TEXT    NOT NULL,
            in_time          TEXT,
            out_time         TEXT,
            status           TEXT    DEFAULT 'present',
            sync_status      TEXT    DEFAULT 'pending',
            created_at       TEXT    NOT NULL,
            updated_at       TEXT    NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE (student_id, attendance_date)
        );

        CREATE TABLE IF NOT EXISTS attendance_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER,
            event_type  TEXT    NOT NULL,
            event_time  TEXT    NOT NULL,
            confidence  REAL,
            message     TEXT,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS device_info (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name     TEXT,
            device_location TEXT,
            created_at      TEXT    NOT NULL
        );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialised successfully at %s", DATABASE_PATH)


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

def add_student(roll_no: str, name: str, class_name: str = None,
                section: str = None) -> int:
    """
    Insert a new student. Returns the new student id.
    Raises sqlite3.IntegrityError if roll_no already exists.
    """
    now = datetime.now().strftime(DATETIME_FORMAT)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO students (roll_no, name, class_name, section, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (roll_no, name, class_name, section, now, now),
    )
    student_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info("Student added: roll_no=%s, name=%s (id=%d)", roll_no, name, student_id)
    return student_id


def get_student_by_roll(roll_no: str) -> dict | None:
    """Return student dict by roll_no, or None."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_by_id(student_id: int) -> dict | None:
    """Return student dict by id, or None."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_students(active_only: bool = True) -> list[dict]:
    """Return list of student dicts, optionally filtered to active only."""
    conn = _get_connection()
    if active_only:
        rows = conn.execute("SELECT * FROM students WHERE status = 'active' ORDER BY roll_no").fetchall()
    else:
        rows = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_student(student_id: int, name: str = None, class_name: str = None,
                   section: str = None, status: str = None) -> None:
    """Update non-None fields for the given student."""
    now = datetime.now().strftime(DATETIME_FORMAT)
    conn = _get_connection()
    student = get_student_by_id(student_id)
    if not student:
        conn.close()
        logger.warning("update_student: student_id=%d not found", student_id)
        return

    conn.execute(
        """UPDATE students
           SET name = ?, class_name = ?, section = ?, status = ?, updated_at = ?
           WHERE id = ?""",
        (
            name if name is not None else student["name"],
            class_name if class_name is not None else student["class_name"],
            section if section is not None else student["section"],
            status if status is not None else student["status"],
            now,
            student_id,
        ),
    )
    conn.commit()
    conn.close()
    logger.info("Student updated: id=%d", student_id)


def delete_or_deactivate_student(student_id: int) -> None:
    """Soft-delete a student by setting status to 'inactive'."""
    update_student(student_id, status="inactive")
    logger.info("Student deactivated: id=%d", student_id)


# ---------------------------------------------------------------------------
# Face Embeddings
# ---------------------------------------------------------------------------

def add_embedding(student_id: int, embedding: np.ndarray,
                  image_path: str = None) -> int:
    """
    Store a face embedding (512-d float32 ndarray) as BLOB.
    Returns the new embedding row id.
    """
    now = datetime.now().strftime(DATETIME_FORMAT)
    blob = embedding.astype(np.float32).tobytes()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO face_embeddings (student_id, embedding, image_path, created_at)
           VALUES (?, ?, ?, ?)""",
        (student_id, blob, image_path, now),
    )
    emb_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.debug("Embedding stored: student_id=%d, emb_id=%d", student_id, emb_id)
    return emb_id


def get_all_embeddings() -> list[dict]:
    """
    Return all embeddings joined with student info.
    Each dict has keys: student_id, roll_no, name, embedding (np.ndarray).
    """
    conn = _get_connection()
    rows = conn.execute(
        """SELECT fe.student_id, s.roll_no, s.name, fe.embedding
           FROM face_embeddings fe
           JOIN students s ON fe.student_id = s.id
           WHERE s.status = 'active'"""
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        emb = np.frombuffer(r["embedding"], dtype=np.float32).copy()
        results.append({
            "student_id": r["student_id"],
            "roll_no": r["roll_no"],
            "name": r["name"],
            "embedding": emb,
        })
    return results


def get_embeddings_by_student(student_id: int) -> list[dict]:
    """Return list of embedding dicts for a specific student."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM face_embeddings WHERE student_id = ?", (student_id,)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        emb = np.frombuffer(r["embedding"], dtype=np.float32).copy()
        results.append({
            "id": r["id"],
            "student_id": r["student_id"],
            "embedding": emb,
            "image_path": r["image_path"],
            "created_at": r["created_at"],
        })
    return results


def get_embedding_count_by_student(student_id: int) -> int:
    """Return the number of stored embeddings for a student."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM face_embeddings WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

def create_attendance_entry(student_id: int, attendance_date: str,
                            in_time: str) -> int:
    """
    Create a new attendance row with in_time.
    Returns the new row id.
    Raises sqlite3.IntegrityError if a record already exists for this
    student + date combination.
    """
    now = datetime.now().strftime(DATETIME_FORMAT)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO attendance
               (student_id, attendance_date, in_time, status, sync_status, created_at, updated_at)
           VALUES (?, ?, ?, 'present', 'pending', ?, ?)""",
        (student_id, attendance_date, in_time, now, now),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info("Attendance ENTRY created: student_id=%d, date=%s, in=%s",
                student_id, attendance_date, in_time)
    return row_id


def update_attendance_exit(student_id: int, attendance_date: str,
                           out_time: str) -> bool:
    """
    Set out_time on an existing attendance row.
    Returns True if a row was updated, False otherwise.
    """
    now = datetime.now().strftime(DATETIME_FORMAT)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE attendance
           SET out_time = ?, updated_at = ?
           WHERE student_id = ? AND attendance_date = ? AND out_time IS NULL""",
        (out_time, now, student_id, attendance_date),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if updated:
        logger.info("Attendance EXIT updated: student_id=%d, date=%s, out=%s",
                     student_id, attendance_date, out_time)
    return updated


def get_attendance_for_student_date(student_id: int,
                                    attendance_date: str) -> dict | None:
    """Return the attendance record for a student on a given date, or None."""
    conn = _get_connection()
    row = conn.execute(
        """SELECT * FROM attendance
           WHERE student_id = ? AND attendance_date = ?""",
        (student_id, attendance_date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_attendance_by_date(attendance_date: str) -> list[dict]:
    """Return all attendance records for a given date, joined with student info."""
    conn = _get_connection()
    rows = conn.execute(
        """SELECT a.*, s.roll_no, s.name, s.class_name, s.section
           FROM attendance a
           JOIN students s ON a.student_id = s.id
           WHERE a.attendance_date = ?
           ORDER BY s.roll_no""",
        (attendance_date,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_attendance() -> list[dict]:
    """Return every attendance record joined with student info."""
    conn = _get_connection()
    rows = conn.execute(
        """SELECT a.*, s.roll_no, s.name, s.class_name, s.section
           FROM attendance a
           JOIN students s ON a.student_id = s.id
           ORDER BY a.attendance_date DESC, s.roll_no"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Attendance Events (audit trail)
# ---------------------------------------------------------------------------

def log_attendance_event(student_id: int | None, event_type: str,
                         confidence: float = None,
                         message: str = None) -> None:
    """Insert an attendance event for auditing."""
    now = datetime.now().strftime(DATETIME_FORMAT)
    event_time = datetime.now().strftime("%H:%M:%S")
    conn = _get_connection()
    conn.execute(
        """INSERT INTO attendance_events
               (student_id, event_type, event_time, confidence, message, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (student_id, event_type, event_time, confidence, message, now),
    )
    conn.commit()
    conn.close()
    logger.debug("Event logged: type=%s, student_id=%s, confidence=%s",
                 event_type, student_id, confidence)
