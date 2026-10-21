# Automated Attendance System for Rural Schools

Web-based face-recognition attendance (Flask + dlib + SQLite).

## Local chalana (Windows) - sabse aasan
`run.bat` pe double-click karo. Pehli baar packages install honge, phir browser khulega.
Ya manually: `python -m venv .venv` -> `.venv\Scripts\activate` -> `pip install -r requirements.txt` -> `python app.py`
Browser (Chrome/Edge): http://127.0.0.1:5000  (VS Code ke built-in browser mein camera nahi chalta)
Default password: `admin123` (ADMIN_PASSWORD env variable se badlo)

## Folder
    app.py            Flask backend, routes, database
    faces.py          face encoding / matching (dlib)
    templates/        HTML pages (UI)
    requirements.txt  packages
    attendance.db     DATABASE FILE (app chalne par khud banti hai, GitHub pe nahi jati)

## GitHub pe upload
Repo mein sirf code jata hai. `.venv` aur `attendance.db` `.gitignore` ki wajah se apne aap bahar rehte hain.

## Vercel deploy
1. GitHub repo ko Vercel mein Import karo (Framework: Flask/Other, root directory default).
2. Environment Variables set karo: `SECRET_KEY` (lamba random text), `ADMIN_PASSWORD` (apna password).
3. Deploy. Vercel khud requirements.txt se packages install karta hai, venv ki zaroorat nahi.

IMPORTANT: Vercel mein filesystem read-only hai, isliye DB `/tmp` mein banti hai. Ye temporary hai:
restart/naye instance par students aur attendance reset ho sakti hai. Sirf DEMO ke liye theek hai.
Asli use ke liye local setup (run.bat) use karo.
