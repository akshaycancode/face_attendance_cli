"""
recognize.py
=============
Live face recognition module.
Loads stored embeddings once, then runs the webcam loop, matching each
detected face against the database using cosine similarity.

Calls attendance.mark_entry() or attendance.mark_exit() depending on
the active mode.
"""

import time
import cv2
import numpy as np

from config import (
    RECOGNITION_THRESHOLD, FRAME_SKIP, ENTRY_MODE, EXIT_MODE,
)
from logger_config import logger
import database as db
from camera import open_camera, release_camera, read_frame, show_frame
from face_model import (
    initialize_face_model, detect_faces, get_face_embedding,
    draw_face_box,
)
from attendance import mark_entry, mark_exit, reset_cooldowns


# ---------------------------------------------------------------------------
# Embedding math
# ---------------------------------------------------------------------------

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2-normalise an embedding vector."""
    embedding = np.asarray(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.
    Assumes inputs are already L2-normalised — dot product is sufficient.
    """
    a = normalize_embedding(a)
    b = normalize_embedding(b)
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------
# Known embeddings loader
# ---------------------------------------------------------------------------

def load_known_embeddings() -> list[dict]:
    """
    Load all active student embeddings from the database.

    Returns
    -------
    list[dict]
        Each dict: {student_id, roll_no, name, embedding (np.ndarray)}.
    """
    embeddings = db.get_all_embeddings()
    logger.info("Loaded %d embeddings from database", len(embeddings))
    return embeddings


def find_best_match(query_embedding: np.ndarray,
                    known_embeddings: list[dict]) -> tuple:
    """
    Compare a query embedding against all known embeddings.
    For each student, take the *maximum* similarity across their
    multiple stored embeddings — then return the overall best student.

    Returns
    -------
    tuple (best_match_dict, best_score)
        best_match_dict has keys: student_id, roll_no, name.
        best_score is the cosine similarity (float).
        Returns (None, 0.0) if no embeddings are available.
    """
    if not known_embeddings:
        return None, 0.0

    # Aggregate best similarity per student
    student_best: dict[int, tuple[float, dict]] = {}

    for entry in known_embeddings:
        sim = cosine_similarity(query_embedding, entry["embedding"])
        sid = entry["student_id"]
        if sid not in student_best or sim > student_best[sid][0]:
            student_best[sid] = (sim, entry)

    # Find the overall best
    best_sid = max(student_best, key=lambda s: student_best[s][0])
    best_score, best_entry = student_best[best_sid]

    return {
        "student_id": best_entry["student_id"],
        "roll_no": best_entry["roll_no"],
        "name": best_entry["name"],
    }, best_score


# ---------------------------------------------------------------------------
# Main recognition loop
# ---------------------------------------------------------------------------

def start_recognition(mode: str = ENTRY_MODE) -> None:
    """
    Start the live recognition loop.

    Parameters
    ----------
    mode : str
        Either config.ENTRY_MODE or config.EXIT_MODE.
    """
    # --- Initialise model ---
    try:
        initialize_face_model()
    except Exception:
        return

    # --- Load known embeddings ---
    known = load_known_embeddings()
    if not known:
        print("\n[WARN] No face embeddings in the database.")
        print("  → Enroll at least one student before starting recognition.\n")
        return

    unique_students = len(set(e["student_id"] for e in known))
    print(f"\n  Loaded {len(known)} embeddings for {unique_students} student(s)")
    print(f"  Mode          : {mode}")
    print(f"  Threshold     : {RECOGNITION_THRESHOLD}")
    print(f"  Frame skip    : every {FRAME_SKIP} frame(s)")
    print(f"  Press 'q' to stop recognition\n")

    # --- Open camera ---
    cap = open_camera()
    if cap is None:
        return

    # Reset cooldowns for a fresh session
    reset_cooldowns()

    frame_count = 0
    fps = 0.0
    fps_start = time.time()
    fps_frame_count = 0

    logger.info("Recognition started in %s mode", mode)

    try:
        while True:
            ret, frame = read_frame(cap)
            if not ret:
                print("[ERROR] Lost camera feed.")
                break

            frame_count += 1
            display = frame.copy()

            # --- FPS calculation ---
            fps_frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps = fps_frame_count / elapsed
                fps_frame_count = 0
                fps_start = time.time()

            # --- Frame skipping: only process every Nth frame ---
            if frame_count % FRAME_SKIP != 0:
                # Still show the last annotated frame
                cv2.putText(display, f"FPS: {fps:.1f} | Mode: {mode}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 255), 2)
                show_frame("Recognition", display)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            # --- Detect faces ---
            faces = detect_faces(frame)

            for face in faces:
                embedding = get_face_embedding(face)
                if embedding is None:
                    continue

                match, score = find_best_match(embedding, known)

                if match and score >= RECOGNITION_THRESHOLD:
                    label = f"{match['name']} ({match['roll_no']}) {score:.2f}"
                    color = (0, 255, 0)     # Green for recognised

                    # Mark attendance
                    if mode == ENTRY_MODE:
                        mark_entry(match["student_id"], score)
                    elif mode == EXIT_MODE:
                        mark_exit(match["student_id"], score)

                else:
                    label = f"UNKNOWN ({score:.2f})"
                    color = (0, 0, 255)     # Red for unknown

                    db.log_attendance_event(
                        None, "UNKNOWN_FACE",
                        confidence=score,
                        message="Below threshold or no match",
                    )

                draw_face_box(display, face, label=label, color=color)

            # --- HUD overlay ---
            cv2.putText(display, f"FPS: {fps:.1f} | Mode: {mode}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 255), 2)

            show_frame("Recognition", display)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\n  Recognition interrupted.")

    finally:
        release_camera(cap)
        logger.info("Recognition stopped (%s mode)", mode)
        print(f"\n  Recognition stopped ({mode} mode).\n")
