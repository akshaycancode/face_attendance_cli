"""
config.py
=========
Central configuration for the Face Recognition Attendance System.
All paths, model settings, thresholds, and constants are defined here.
Change values in this file to tune the system — no other file should
contain hardcoded magic numbers.
"""

import os

# ---------------------------------------------------------------------------
# Base directory — resolved relative to THIS file so the project stays
# portable across machines and operating systems.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATABASE_PATH = os.path.join(BASE_DIR, "data", "attendance.db")
STUDENT_IMAGES_DIR = os.path.join(BASE_DIR, "data", "student_images")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# ---------------------------------------------------------------------------
# InsightFace Model Settings
# ---------------------------------------------------------------------------
MODEL_NAME = "buffalo_l"                       # InsightFace model pack
DET_SIZE = (640, 640)                          # Detection input size
PROVIDERS = ["CPUExecutionProvider"]           # ONNX Runtime providers

# ---------------------------------------------------------------------------
# Enrollment Settings
# ---------------------------------------------------------------------------
DEFAULT_SAMPLE_COUNT = 5                       # Face samples per enrollment
MIN_FACE_DETECTION_CONFIDENCE = 0.5            # Minimum det_score to accept
MIN_FACE_BBOX_AREA = 4000                      # Minimum bounding-box area (px²)

# ---------------------------------------------------------------------------
# Recognition Settings
# ---------------------------------------------------------------------------
RECOGNITION_THRESHOLD = 0.45                   # Cosine similarity threshold
DUPLICATE_COOLDOWN_SECONDS = 60                # Seconds before re-marking
FRAME_SKIP = 2                                 # Process every Nth frame

# ---------------------------------------------------------------------------
# Camera Settings
# ---------------------------------------------------------------------------
CAMERA_INDEX = 0                               # OpenCV camera device index
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# ---------------------------------------------------------------------------
# Attendance Mode Labels
# ---------------------------------------------------------------------------
ENTRY_MODE = "ENTRY"
EXIT_MODE = "EXIT"

# ---------------------------------------------------------------------------
# Date / Time Formats
# ---------------------------------------------------------------------------
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
