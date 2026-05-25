"""
export_csv.py
=============
Export attendance records to CSV files.
Uses Python's built-in csv module — no pandas dependency.
"""

import os
import csv

from config import EXPORTS_DIR
from logger_config import logger
import database as db
from utils import calculate_duration


def export_attendance_by_date(attendance_date: str) -> str | None:
    """
    Export all attendance records for a given date to a CSV file.

    Parameters
    ----------
    attendance_date : str
        Date in YYYY-MM-DD format.

    Returns
    -------
    str or None
        Path to the created CSV file, or None if no records found.
    """
    records = db.get_attendance_by_date(attendance_date)

    if not records:
        print(f"\n[INFO] No attendance records found for {attendance_date}.")
        return None

    # Ensure export directory exists
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    filename = f"attendance_{attendance_date}.csv"
    filepath = os.path.join(EXPORTS_DIR, filename)

    headers = [
        "attendance_date",
        "roll_no",
        "name",
        "class_name",
        "section",
        "in_time",
        "out_time",
        "total_duration",
        "status",
        "sync_status",
    ]

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for rec in records:
                in_time = rec.get("in_time", "")
                out_time = rec.get("out_time", "")
                duration = calculate_duration(in_time, out_time) if in_time and out_time else "--"

                writer.writerow([
                    rec.get("attendance_date", ""),
                    rec.get("roll_no", ""),
                    rec.get("name", ""),
                    rec.get("class_name", ""),
                    rec.get("section", ""),
                    in_time or "",
                    out_time or "",
                    duration,
                    rec.get("status", ""),
                    rec.get("sync_status", ""),
                ])

        print(f"\n[OK] Attendance exported to: {filepath}")
        print(f"     Records: {len(records)}")
        logger.info("Attendance CSV exported: %s (%d records)", filepath, len(records))
        return filepath

    except Exception as exc:
        logger.exception("CSV export failed")
        print(f"\n[ERROR] Failed to export CSV: {exc}")
        return None


def export_students_to_csv() -> str | None:
    """
    Export all active students to a CSV file.

    Returns
    -------
    str or None
        Path to the created CSV file, or None on failure.
    """
    students = db.get_all_students(active_only=False)
    if not students:
        print("\n[INFO] No students in the database.")
        return None

    os.makedirs(EXPORTS_DIR, exist_ok=True)
    filepath = os.path.join(EXPORTS_DIR, "students.csv")

    headers = ["id", "roll_no", "name", "class_name", "section", "status", "created_at"]

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for s in students:
                writer.writerow([
                    s.get("id", ""),
                    s.get("roll_no", ""),
                    s.get("name", ""),
                    s.get("class_name", ""),
                    s.get("section", ""),
                    s.get("status", ""),
                    s.get("created_at", ""),
                ])

        print(f"\n[OK] Students exported to: {filepath}")
        logger.info("Students CSV exported: %s", filepath)
        return filepath

    except Exception as exc:
        logger.exception("Student CSV export failed")
        print(f"\n[ERROR] Failed to export students CSV: {exc}")
        return None
