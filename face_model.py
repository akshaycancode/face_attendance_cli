"""
face_model.py
=============
InsightFace Buffalo_L wrapper.
Provides functions to initialise the model, detect faces, extract
normalised 512-d embeddings, and draw annotated bounding boxes.

On first run InsightFace will automatically download the Buffalo_L
model pack (~300 MB) to ~/.insightface/models/.
"""

import numpy as np
from logger_config import logger
from config import MODEL_NAME, DET_SIZE, PROVIDERS, MIN_FACE_DETECTION_CONFIDENCE

# Global model handle — initialised lazily
_face_app = None


def initialize_face_model():
    """
    Load the InsightFace Buffalo_L model.
    Must be called once before any detection / embedding calls.
    """
    global _face_app

    if _face_app is not None:
        return _face_app

    try:
        from insightface.app import FaceAnalysis

        logger.info("Loading InsightFace model '%s' …", MODEL_NAME)
        print(f"\n[INFO] Loading face recognition model ({MODEL_NAME}) — this may take a moment …")

        _face_app = FaceAnalysis(name=MODEL_NAME, providers=PROVIDERS)
        _face_app.prepare(ctx_id=0, det_size=DET_SIZE)

        logger.info("InsightFace model loaded successfully")
        print("[INFO] Model loaded successfully.\n")
        return _face_app

    except Exception as exc:
        logger.exception("Failed to load InsightFace model")
        print(f"\n[ERROR] Could not load the face model: {exc}")
        print("  → Make sure 'insightface' and 'onnxruntime' are installed.")
        print("  → The Buffalo_L model is downloaded automatically on first run.")
        print("  → Check your internet connection if the download fails.\n")
        raise


def detect_faces(frame):
    """
    Detect all faces in a BGR frame.

    Returns
    -------
    list
        List of InsightFace Face objects (may be empty).
    """
    if _face_app is None:
        raise RuntimeError("Face model not initialised — call initialize_face_model() first")

    faces = _face_app.get(frame)
    return faces


def get_face_embedding(face) -> np.ndarray | None:
    """
    Extract and normalise the 512-d embedding from a detected Face object.
    Returns None if the embedding attribute is missing.
    """
    emb = getattr(face, "embedding", None)
    if emb is None:
        return None
    return normalize_embedding(emb)


def extract_embedding_from_frame(frame):
    """
    Convenience: detect faces in a frame and return the normalised embedding
    of the first (or only) face.

    Returns
    -------
    tuple (embedding, face, all_faces)
        - embedding: np.ndarray or None
        - face: the Face object or None
        - all_faces: list of all detected faces
    """
    faces = detect_faces(frame)
    if not faces:
        return None, None, faces

    face = faces[0]
    emb = get_face_embedding(face)
    return emb, face, faces


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2-normalise an embedding vector."""
    embedding = np.asarray(embedding, dtype=np.float32)
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


def draw_face_box(frame, face, label: str = None, color=(0, 255, 0),
                  thickness: int = 2):
    """
    Draw a bounding box (and optional label) on the frame.

    Parameters
    ----------
    frame : np.ndarray
        BGR image (modified in-place).
    face : InsightFace Face object
        Must have a ``bbox`` attribute.
    label : str, optional
        Text to display above the box.
    color : tuple
        BGR colour for the box / text.
    thickness : int
        Box line thickness.
    """
    import cv2

    bbox = face.bbox.astype(int)
    x1, y1, x2, y2 = bbox

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    if label:
        # Put text with a filled background for readability
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        txt_thickness = 1
        (tw, th), baseline = cv2.getTextSize(label, font, scale, txt_thickness)
        cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 5), font, scale,
                    (0, 0, 0), txt_thickness, cv2.LINE_AA)

    return frame


def get_face_quality(face) -> dict:
    """
    Return a dict with basic quality metrics for a detected face.

    Keys
    ----
    det_score : float   – detection confidence
    bbox_area : int     – bounding box area in pixels
    """
    bbox = face.bbox.astype(int)
    x1, y1, x2, y2 = bbox
    area = max(0, (x2 - x1) * (y2 - y1))

    return {
        "det_score": float(getattr(face, "det_score", 0.0)),
        "bbox_area": area,
    }
