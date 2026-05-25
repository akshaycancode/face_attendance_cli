"""
main.py
=======
Entry point for the Face Recognition Attendance System.
Displays a CLI menu and dispatches to the appropriate module.
"""

import sys
from datetime import datetime

from config import (
    DATABASE_PATH, ENTRY_MODE, EXIT_MODE, RECOGNITION_THRESHOLD,
    MODEL_NAME, CAMERA_INDEX, DATE_FORMAT,
)
from logger_config import logger
from utils import (
    ensure_directories, today_str, print_table, is_valid_date,
    calculate_duration, backup_database,
)
import database as db
from enroll import enroll_student, add_samples_to_existing
from recognize import start_recognition
from export_csv import export_attendance_by_date, export_students_to_csv


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
 ═══════════════════════════════════════════════════════════
  FACE RECOGNITION ATTENDANCE SYSTEM
  Model : InsightFace Buffalo_L  |  Mode : Offline / CLI
 ═══════════════════════════════════════════════════════════
"""

MENU = """
  1.  Initialize Database
  2.  Add / Enroll Student
  3.  Add More Face Samples to Existing Student
  4.  Start Entry Recognition
  5.  Start Exit Recognition
  6.  View All Students
  7.  View Today's Attendance
  8.  View Attendance by Date
  9.  Export Attendance by Date to CSV
  10. Export Students List to CSV
  11. Deactivate Student
  12. Backup Database
  13. System Info
  0.  Exit
"""


# ---------------------------------------------------------------------------
# Menu handlers
# ---------------------------------------------------------------------------

def handle_init_db():
    db.init_db()
    print("[OK] Database initialised.\n")


def handle_view_students():
    students = db.get_all_students(active_only=False)
    if not students:
        print("\n  No students in the database.\n")
        return

    headers = ["ID", "Roll No", "Name", "Class", "Section", "Status", "Embeddings"]
    rows = []
    for s in students:
        emb_count = db.get_embedding_count_by_student(s["id"])
        rows.append([
            str(s["id"]),
            s["roll_no"],
            s["name"],
            s.get("class_name") or "",
            s.get("section") or "",
            s["status"],
            str(emb_count),
        ])
    print_table(headers, rows)


def handle_view_today_attendance():
    today = today_str()
    print(f"\n  Attendance for: {today}")
    _display_attendance(today)


def handle_view_attendance_by_date():
    date_str = input("\n  Enter date (YYYY-MM-DD): ").strip()
    if not is_valid_date(date_str):
        print("[ERROR] Invalid date format. Use YYYY-MM-DD.\n")
        return
    print(f"\n  Attendance for: {date_str}")
    _display_attendance(date_str)


def _display_attendance(date_str: str):
    records = db.get_attendance_by_date(date_str)
    if not records:
        print("  No attendance records found.\n")
        return

    headers = ["Roll No", "Name", "Class", "Section", "IN Time", "OUT Time", "Duration", "Status"]
    rows = []
    for r in records:
        in_t = r.get("in_time") or "--"
        out_t = r.get("out_time") or "--"
        dur = calculate_duration(r.get("in_time", ""), r.get("out_time", ""))
        rows.append([
            r.get("roll_no", ""),
            r.get("name", ""),
            r.get("class_name") or "",
            r.get("section") or "",
            in_t,
            out_t,
            dur,
            r.get("status", ""),
        ])
    print_table(headers, rows)


def handle_export_csv():
    date_str = input("\n  Enter date to export (YYYY-MM-DD): ").strip()
    if not is_valid_date(date_str):
        print("[ERROR] Invalid date format. Use YYYY-MM-DD.\n")
        return
    export_attendance_by_date(date_str)


def handle_deactivate_student():
    roll_no = input("\n  Enter Roll Number to deactivate: ").strip()
    if not roll_no:
        print("[ERROR] Roll number cannot be empty.\n")
        return
    student = db.get_student_by_roll(roll_no)
    if not student:
        print(f"[ERROR] No student found with roll number '{roll_no}'.\n")
        return
    if student["status"] == "inactive":
        print(f"  Student '{student['name']}' is already inactive.\n")
        return
    confirm = input(f"  Deactivate {student['name']} ({roll_no})? (y/n): ").strip().lower()
    if confirm == "y":
        db.delete_or_deactivate_student(student["id"])
        print(f"  [OK] Student '{student['name']}' deactivated.\n")
    else:
        print("  Cancelled.\n")


def handle_backup():
    backup_database(DATABASE_PATH)


def handle_system_info():
    print(f"""
  ─── System Info ───
  Database      : {DATABASE_PATH}
  Model         : {MODEL_NAME}
  Camera Index  : {CAMERA_INDEX}
  Threshold     : {RECOGNITION_THRESHOLD}
  Python        : {sys.version.split()[0]}
  Platform      : {sys.platform}
""")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    """Application entry point."""
    logger.info("Application started")

    # Auto-setup
    ensure_directories()
    db.init_db()

    print(BANNER)

    while True:
        print(MENU)
        choice = input("  Select option ▸ ").strip()

        if choice == "1":
            handle_init_db()
        elif choice == "2":
            enroll_student()
        elif choice == "3":
            add_samples_to_existing()
        elif choice == "4":
            start_recognition(mode=ENTRY_MODE)
        elif choice == "5":
            start_recognition(mode=EXIT_MODE)
        elif choice == "6":
            handle_view_students()
        elif choice == "7":
            handle_view_today_attendance()
        elif choice == "8":
            handle_view_attendance_by_date()
        elif choice == "9":
            handle_export_csv()
        elif choice == "10":
            export_students_to_csv()
        elif choice == "11":
            handle_deactivate_student()
        elif choice == "12":
            handle_backup()
        elif choice == "13":
            handle_system_info()
        elif choice == "0":
            print("\n  Goodbye!\n")
            logger.info("Application exited normally")
            break
        else:
            print("\n  [!] Invalid choice. Please try again.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting…\n")
        logger.info("Application interrupted by user")
    except Exception as exc:
        logger.exception("Unhandled exception in main")
        print(f"\n[FATAL] An unexpected error occurred: {exc}")
        print("  Check logs/app.log for details.\n")
        sys.exit(1)
