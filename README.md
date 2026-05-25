# Face Recognition Attendance System

A **complete, offline-first, CLI-based** face recognition attendance system built with Python.  
Uses **InsightFace Buffalo_L** for face detection and recognition, **OpenCV** for webcam handling, and **SQLite** for local data storage.

> **This laptop prototype is the software base for a future portable hardware system** (Raspberry Pi / Jetson Nano). The modular architecture is designed so that only camera, ONNX provider, and display layers need changes during migration.

---

## Features

- **Face enrollment** with multiple samples per student
- **Live recognition** using webcam with real-time bounding boxes
- **ENTRY / EXIT attendance** with automatic time stamps
- **Duplicate prevention** — same student won't be marked twice within cooldown
- **Offline operation** — no internet required after initial model download
- **SQLite database** — all data stored locally
- **CSV export** — attendance by date, student list
- **Audit trail** — every recognition event logged to `attendance_events` table
- **Sync-ready fields** — `sync_status` column for future cloud integration
- **Database backup** — one-click DB backup
- **FPS counter** — displayed on recognition window
- **Frame skipping** — for better CPU performance
- **Modular code** — each concern in its own file

---

## Folder Structure

```
face_attendance_cli/
│
├── main.py               # CLI entry point & menu
├── config.py             # All constants & settings
├── database.py           # SQLite schema & CRUD functions
├── face_model.py         # InsightFace Buffalo_L wrapper
├── camera.py             # OpenCV webcam abstraction
├── enroll.py             # Student enrollment module
├── recognize.py          # Live recognition loop
├── attendance.py         # Entry/Exit attendance logic
├── export_csv.py         # CSV export functions
├── utils.py              # Shared utilities
├── logger_config.py      # Logging setup
├── requirements.txt      # Python dependencies
├── README.md             # This file
│
├── data/
│   ├── attendance.db         # SQLite database (auto-created)
│   └── student_images/       # Captured face images per student
│       └── <roll_no>/
│           ├── sample_001.jpg
│           └── ...
│
├── exports/                  # CSV export files
│
├── logs/
│   └── app.log               # Application log
│
└── tests/
    └── optional_test_notes.md
```

---

## Installation

### 1. Clone / copy the project

```bash
cd face_attendance_cli
```

### 2. Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python main.py
```

> **Note:** On first run, InsightFace will **automatically download** the Buffalo_L model (~300 MB) to `~/.insightface/models/buffalo_l/`. You need an internet connection for this one-time download only.

---

## How to Use

### Initialize Database

Select **option 1** from the menu (also happens automatically on startup).

### Enroll a Student

1. Select **option 2** from the menu.
2. Enter:
   - Roll Number (unique, e.g. `23BCS001`)
   - Full Name
   - Class (optional)
   - Section (optional)
   - Number of face samples (default 5)
3. The webcam will open. Press **`c`** to capture each sample.
4. Press **`q`** to cancel early.
5. Ensure only **one face** is visible per capture.

### Add More Face Samples

Select **option 3** and enter the existing student's roll number.  
Additional samples improve recognition accuracy.

### Start Entry Recognition

Select **option 4**. The system will:
- Open the webcam
- Detect and recognise faces in real-time
- Automatically mark **IN time** for recognised students
- Show `UNKNOWN` for unrecognised faces
- Press **`q`** to stop

### Start Exit Recognition

Select **option 5**. Same as entry mode but marks **OUT time**.  
Exit will only be recorded if an entry exists for that student today.

### View Attendance

- **Option 7** — Today's attendance
- **Option 8** — Attendance for a specific date (YYYY-MM-DD)

### Export Attendance to CSV

Select **option 9** and enter the date. The CSV file is saved to `exports/attendance_YYYY-MM-DD.csv`.

### Export Students List

Select **option 10** to export all students to `exports/students.csv`.

### Deactivate a Student

Select **option 11** and enter the roll number. Deactivated students are excluded from recognition.

### Backup Database

Select **option 12** to create a timestamped copy of the database file.

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `students` | Student records (roll_no, name, class, section, status) |
| `face_embeddings` | 512-d face embeddings stored as BLOBs |
| `attendance` | Daily attendance with in_time, out_time, sync_status |
| `attendance_events` | Audit trail of every recognition event |
| `device_info` | Device metadata (for future multi-device sync) |

### Key Constraints

- `students.roll_no` is **UNIQUE**
- `attendance(student_id, attendance_date)` is **UNIQUE** — one record per student per day
- Embeddings are stored as `numpy.float32` arrays serialised to bytes

---

## Recognition Threshold

The recognition threshold is set in `config.py`:

```python
RECOGNITION_THRESHOLD = 0.45
```

- **Higher value** (e.g. 0.55) = stricter matching, fewer false positives, may miss real students
- **Lower value** (e.g. 0.35) = looser matching, more false positives, catches more students

**Recommended range:** 0.40 – 0.55

You can also adjust:
- `DUPLICATE_COOLDOWN_SECONDS` — how long before re-marking the same student (default 60s)
- `FRAME_SKIP` — process every Nth frame (default 2)
- `MIN_FACE_DETECTION_CONFIDENCE` — minimum face detector score (default 0.5)

---

## Troubleshooting

### Camera not opening

```
[ERROR] Cannot open camera at index 0.
```

- Ensure your webcam is connected and not used by another application
- Try changing `CAMERA_INDEX` in `config.py` (e.g. `1` for external webcam)
- On Linux, check permissions: `ls -l /dev/video*`

### InsightFace model download

The Buffalo_L model is downloaded automatically to `~/.insightface/models/buffalo_l/` on first run.

- If the download fails, check your internet connection
- You can manually download from [InsightFace Model Zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo) and place in `~/.insightface/models/buffalo_l/`

### NumPy compatibility issue

If you see errors related to NumPy (especially on Windows with older packages):

```bash
pip install "numpy<2"
```

### ONNX Runtime issue

If ONNX Runtime fails to load:

```bash
pip install onnxruntime --force-reinstall
```

For GPU support (optional):
```bash
pip install onnxruntime-gpu
```
Then change `PROVIDERS` in `config.py` to `["CUDAExecutionProvider", "CPUExecutionProvider"]`.

### Low recognition accuracy

- Enroll more face samples (option 3) — 8-10 samples recommended
- Ensure good lighting during enrollment and recognition
- Lower the threshold in `config.py` (try 0.40)
- Make sure the face is clearly visible and not too far from the camera
- Check `MIN_FACE_BBOX_AREA` if faces are being rejected as too small

### InsightFace import error

```bash
pip install insightface --upgrade
pip install onnxruntime --upgrade
```

---

## Future Edge Device Migration

This system is designed for easy migration to **Raspberry Pi** or **NVIDIA Jetson** hardware:

| Component | Laptop (Current) | Edge Device (Future) |
|-----------|-------------------|----------------------|
| Camera | `cv2.VideoCapture(0)` — USB webcam | CSI camera / Picamera2 |
| ONNX Provider | `CPUExecutionProvider` | `CUDAExecutionProvider` / TensorRT |
| Model | Buffalo_L (full) | Possibly Buffalo_S for speed |
| Display | OpenCV window | HDMI/LCD or headless |
| Input | Keyboard | Hardware buttons / RFID |
| Sync | Local only | Wi-Fi sync to cloud portal |

### What needs to change:
1. `CAMERA_INDEX` / camera backend in `camera.py`
2. `PROVIDERS` in `config.py`
3. Optional model downsize in `config.py`
4. Add sync module for cloud communication
5. Hardware button input handling
6. Display module for attached LCD

### What stays the same:
- All database logic
- All attendance logic
- Enrollment flow
- Recognition pipeline
- CSV export
- Logging

---

## License

This project is for educational and personal use.

---

## Author

Built as a laptop prototype for a physical face recognition attendance system.
