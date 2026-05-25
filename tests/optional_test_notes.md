# Test Notes

This file contains the manual testing checklist for the Face Recognition Attendance System.

## Prerequisites

- Python 3.10+ virtual environment activated
- All dependencies installed (`pip install -r requirements.txt`)
- Webcam connected and accessible

## Test Checklist

### 1. Application Launch
- [ ] Run `python main.py`
- [ ] Verify banner and menu are displayed
- [ ] Verify `data/`, `exports/`, `logs/` directories are created
- [ ] Verify `data/attendance.db` is created

### 2. Database Initialisation
- [ ] Select option 1 (Initialize Database)
- [ ] Verify "Database initialised" message
- [ ] Re-run — should not error (idempotent)

### 3. Student Enrollment
- [ ] Select option 2 (Add / Enroll Student)
- [ ] Enter: roll_no=TEST001, name=Test User, class=CSE, section=A, samples=5
- [ ] Verify webcam opens
- [ ] Press 'c' to capture 5 samples
- [ ] Verify each capture shows "Captured X/5"
- [ ] Verify images saved under `data/student_images/TEST001/`
- [ ] Verify enrollment summary is printed

### 4. Duplicate Roll Number
- [ ] Try enrolling with roll_no=TEST001 again
- [ ] Verify prompt asking to add more samples or cancel
- [ ] Verify no duplicate student created

### 5. Multiple Face Rejection
- [ ] During enrollment, show 2 faces to camera
- [ ] Press 'c' — should reject with "Multiple faces" message

### 6. Entry Recognition
- [ ] Select option 4 (Start Entry Recognition)
- [ ] Verify embeddings are loaded
- [ ] Stand in front of camera — face should be recognised
- [ ] Verify "[ENTRY] Test User — IN at HH:MM:SS" message
- [ ] Verify green bounding box with name and score

### 7. Duplicate Entry Prevention
- [ ] Stay in front of camera after entry is marked
- [ ] Verify no repeated "[ENTRY]" messages (cooldown active)

### 8. Unknown Face
- [ ] Show an unenrolled face to the camera
- [ ] Verify "UNKNOWN" label with red bounding box
- [ ] Verify no attendance is marked

### 9. Exit Recognition
- [ ] Select option 5 (Start Exit Recognition)
- [ ] Stand in front of camera
- [ ] Verify "[EXIT] Test User — OUT at HH:MM:SS" message with duration

### 10. Exit Before Entry
- [ ] Clear database or test with a student who hasn't entered today
- [ ] Start Exit Recognition
- [ ] Verify "No entry record found" message

### 11. View Students
- [ ] Select option 6
- [ ] Verify table shows TEST001, name, class, section, status, embedding count

### 12. View Today's Attendance
- [ ] Select option 7
- [ ] Verify table shows IN time, OUT time, duration, status

### 13. View Attendance by Date
- [ ] Select option 8
- [ ] Enter today's date
- [ ] Verify same records as option 7

### 14. Export CSV
- [ ] Select option 9
- [ ] Enter today's date
- [ ] Verify file created at `exports/attendance_YYYY-MM-DD.csv`
- [ ] Open CSV and verify columns and data

### 15. Deactivate Student
- [ ] Select option 11
- [ ] Enter roll_no=TEST001
- [ ] Confirm deactivation
- [ ] Verify student status changed to inactive
- [ ] Verify recognition no longer matches this student

### 16. System Info
- [ ] Select option 13
- [ ] Verify database path, model name, camera index, threshold, Python version

### 17. Database Backup
- [ ] Select option 12
- [ ] Verify backup file created with timestamp

### 18. Error Handling
- [ ] Enter invalid menu choices — should not crash
- [ ] Enter empty roll number — should show error
- [ ] Enter invalid date format — should show error
- [ ] Unplug camera during recognition — should show error and exit gracefully

### 19. Logs
- [ ] Check `logs/app.log`
- [ ] Verify entries for: app start, DB init, student add, enrollment, recognition, entry/exit marks, errors
