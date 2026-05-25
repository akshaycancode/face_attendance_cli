"""
enroll.py
=========
Student enrollment module.
Handles the interactive flow of registering a student and capturing
face samples from the webcam using InsightFace Buffalo_L.
"""

import os
import cv2

from config import (
    DEFAULT_SAMPLE_COUNT, MIN_FACE_DETECTION_CONFIDENCE,
    MIN_FACE_BBOX_AREA, STUDENT_IMAGES_DIR,
)
from logger_config import logger
import database as db
from camera import open_camera, release_camera, read_frame, show_frame, save_frame
from face_model import (
    initialize_face_model, detect_faces, get_face_embedding,
    draw_face_box, get_face_quality,
)


def enroll_student() -> None:
    """
    Interactive CLI flow to enroll a new student.
    Prompts for student details, then captures face samples via webcam.
    """
    print("\n" + "=" * 50)
    print("  STUDENT ENROLLMENT")
    print("=" * 50)

    # --- Gather student info ---
    roll_no = input("  Roll Number : ").strip()
    if not roll_no:
        print("[ERROR] Roll number cannot be empty.")
        return

    # Check if student already exists
    existing = db.get_student_by_roll(roll_no)
    if existing:
        print(f"\n  Student already exists: {existing['name']} ({existing['roll_no']})")
        choice = input("  Add more face samples? (y/n): ").strip().lower()
        if choice == "y":
            _capture_samples(existing["id"], existing["roll_no"],
                             existing["name"])
        else:
            print("  Enrollment cancelled.")
        return

    name = input("  Full Name   : ").strip()
    if not name:
        print("[ERROR] Name cannot be empty.")
        return

    class_name = input("  Class       : ").strip() or None
    section = input("  Section     : ").strip() or None

    try:
        sample_count_str = input(
            f"  Number of face samples [{DEFAULT_SAMPLE_COUNT}]: "
        ).strip()
        sample_count = int(sample_count_str) if sample_count_str else DEFAULT_SAMPLE_COUNT
        if sample_count < 1:
            sample_count = DEFAULT_SAMPLE_COUNT
    except ValueError:
        sample_count = DEFAULT_SAMPLE_COUNT

    # --- Create student record ---
    try:
        student_id = db.add_student(roll_no, name, class_name, section)
    except Exception as exc:
        logger.exception("Failed to add student")
        print(f"[ERROR] Could not add student: {exc}")
        return

    print(f"\n  Student created: {name} (ID: {student_id})")

    # --- Capture face samples ---
    _capture_samples(student_id, roll_no, name, sample_count)


def add_samples_to_existing() -> None:
    """
    Add more face samples to an already-enrolled student.
    """
    print("\n" + "=" * 50)
    print("  ADD MORE FACE SAMPLES")
    print("=" * 50)

    roll_no = input("  Roll Number : ").strip()
    if not roll_no:
        print("[ERROR] Roll number cannot be empty.")
        return

    student = db.get_student_by_roll(roll_no)
    if not student:
        print(f"[ERROR] No student found with roll number '{roll_no}'.")
        return

    if student["status"] != "active":
        print(f"[WARN] Student '{student['name']}' is inactive.")
        return

    existing_count = db.get_embedding_count_by_student(student["id"])
    print(f"\n  Student : {student['name']} ({student['roll_no']})")
    print(f"  Existing embeddings : {existing_count}")

    try:
        sample_count_str = input(
            f"  Additional samples to capture [{DEFAULT_SAMPLE_COUNT}]: "
        ).strip()
        sample_count = int(sample_count_str) if sample_count_str else DEFAULT_SAMPLE_COUNT
        if sample_count < 1:
            sample_count = DEFAULT_SAMPLE_COUNT
    except ValueError:
        sample_count = DEFAULT_SAMPLE_COUNT

    _capture_samples(student["id"], student["roll_no"],
                     student["name"], sample_count)


def _capture_samples(student_id: int, roll_no: str, name: str,
                     sample_count: int = DEFAULT_SAMPLE_COUNT) -> None:
    """
    Open webcam and capture face samples for a student.

    Controls
    --------
    - Press 'c' to capture a sample.
    - Press 'q' to cancel enrollment early.
    """
    # Initialise the face model
    try:
        initialize_face_model()
    except Exception:
        return

    # Open camera
    cap = open_camera()
    if cap is None:
        return

    # Prepare image directory
    img_dir = os.path.join(STUDENT_IMAGES_DIR, roll_no)
    os.makedirs(img_dir, exist_ok=True)

    # Count existing images to continue numbering
    existing_images = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]
    img_counter = len(existing_images)

    captured = 0
    print(f"\n  Capturing {sample_count} face samples for {name} ({roll_no})")
    print("  Press 'c' to capture  |  Press 'q' to quit\n")

    while captured < sample_count:
        ret, frame = read_frame(cap)
        if not ret:
            print("[ERROR] Cannot read from camera.")
            break

        # Detect faces for live preview
        faces = detect_faces(frame)
        display = frame.copy()

        if len(faces) == 0:
            cv2.putText(display, "No face detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        elif len(faces) > 1:
            cv2.putText(display, "Multiple faces — show only ONE face", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            for f in faces:
                draw_face_box(display, f, label="?", color=(0, 0, 255))
        else:
            face = faces[0]
            quality = get_face_quality(face)
            draw_face_box(display, face,
                          label=f"{name} | score: {quality['det_score']:.2f}",
                          color=(0, 255, 0))

        # Status bar
        status = f"Captured: {captured}/{sample_count}  |  'c' capture  |  'q' quit"
        cv2.putText(display, status, (20, display.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        show_frame("Enrollment", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("\n  Enrollment cancelled by user.")
            logger.info("Enrollment cancelled for %s (%s)", name, roll_no)
            break

        if key == ord("c"):
            # Validate capture
            if len(faces) == 0:
                print("  [SKIP] No face detected — try again.")
                continue

            if len(faces) > 1:
                print("  [SKIP] Multiple faces detected — ensure only ONE face is visible.")
                continue

            face = faces[0]
            quality = get_face_quality(face)

            # Quality gate: detection score
            if quality["det_score"] < MIN_FACE_DETECTION_CONFIDENCE:
                print(f"  [SKIP] Low detection confidence ({quality['det_score']:.2f} "
                      f"< {MIN_FACE_DETECTION_CONFIDENCE}). Move closer or improve lighting.")
                continue

            # Quality gate: bounding box size
            if quality["bbox_area"] < MIN_FACE_BBOX_AREA:
                print(f"  [SKIP] Face too small (area={quality['bbox_area']}px²). "
                      f"Move closer to the camera.")
                continue

            # Extract embedding
            embedding = get_face_embedding(face)
            if embedding is None:
                print("  [SKIP] Could not extract embedding — try again.")
                continue

            # Save image
            img_counter += 1
            img_filename = f"sample_{img_counter:03d}.jpg"
            img_path = os.path.join(img_dir, img_filename)
            save_frame(img_path, frame)

            # Store embedding
            db.add_embedding(student_id, embedding, image_path=img_path)

            captured += 1
            print(f"  ✓ Captured {captured}/{sample_count} samples")

    # Cleanup
    release_camera(cap)

    # Summary
    total_embeddings = db.get_embedding_count_by_student(student_id)
    print(f"\n  ─── Enrollment Summary ───")
    print(f"  Student   : {name}")
    print(f"  Roll No   : {roll_no}")
    print(f"  Captured  : {captured} new sample(s)")
    print(f"  Total embeddings stored: {total_embeddings}")
    print(f"  Images saved in: {img_dir}")
    print()

    logger.info("Enrollment complete for %s (%s): %d new samples, %d total embeddings",
                name, roll_no, captured, total_embeddings)
