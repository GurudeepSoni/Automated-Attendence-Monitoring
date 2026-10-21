import base64, io, json, sqlite3, csv, os
from datetime import date, datetime
import numpy as np
from faces import face_encodings, face_distance
from PIL import Image
from flask import Flask, render_template, request, jsonify, g, Response, session, redirect, url_for
from openpyxl import Workbook
from openpyxl.styles import Font

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
_default_db = "/tmp/attendance.db" if os.environ.get("VERCEL") else os.path.join(BASE, "attendance.db")
DB = os.environ.get("DB_PATH", _default_db)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
TOLERANCE = 0.5  # lower = stricter matching, higher = more lenient

@app.before_request
def need_login():
    if request.endpoint in ("login", "static") or session.get("auth"):
        return
    if request.path.startswith("/api/"):
        return jsonify(ok=False, msg="Please log in."), 401
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["auth"] = True
            return redirect(url_for("index"))
        err = "Incorrect password."
    return render_template("login.html", err=err)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY, name TEXT, roll TEXT UNIQUE,
        class_name TEXT, encodings TEXT);
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY, student_id INTEGER, day TEXT, time TEXT,
        UNIQUE(student_id, day));
    """)
    c.commit(); c.close()

def to12(t):
    """'15:42:09' -> '3:42:09 PM'"""
    if not t: return ""
    return datetime.strptime(t, "%H:%M:%S").strftime("%I:%M:%S %p").lstrip("0")

def to_image(data_url):
    raw = base64.b64decode(data_url.split(",")[1])
    return np.array(Image.open(io.BytesIO(raw)).convert("RGB"))

def report_rows(day):
    rows = db().execute("""
        SELECT s.name, s.roll, s.class_name, a.time FROM students s
        LEFT JOIN attendance a ON a.student_id=s.id AND a.day=?
        ORDER BY s.class_name, s.roll""", (day,)).fetchall()
    return [dict(name=r["name"], roll=r["roll"], class_name=r["class_name"],
                 present=bool(r["time"]), time=to12(r["time"])) for r in rows]

@app.route("/")
def index():
    total = db().execute("SELECT COUNT(*) FROM students").fetchone()[0]
    present = db().execute("SELECT COUNT(*) FROM attendance WHERE day=?",
                           (str(date.today()),)).fetchone()[0]
    return render_template("index.html", total=total, present=present,
                           absent=max(total - present, 0),
                           pct=round(present * 100 / total) if total else 0)

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/api/register", methods=["POST"])
def api_register():
    d = request.json
    encs = []
    for img in d["images"]:
        found = face_encodings(to_image(img))
        if len(found) == 1:          # only use photos that contain exactly one face
            encs.append(found[0].tolist())
    if not encs:
        return jsonify(ok=False, msg="No face detected. Try again in good light, looking straight at the camera.")
    try:
        db().execute("INSERT INTO students(name,roll,class_name,encodings) VALUES(?,?,?,?)",
                     (d["name"], d["roll"], d["class_name"], json.dumps(encs)))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(ok=False, msg="This roll number is already registered.")
    return jsonify(ok=True, msg=f"{d['name']} has been registered ({len(encs)} photos used).")

@app.route("/attendance")
def attendance_page():
    return render_template("attendance.html")

@app.route("/api/mark", methods=["POST"])
def api_mark():
    img = to_image(request.json["image"])
    students = db().execute("SELECT * FROM students").fetchall()
    known, owners = [], []
    for s in students:
        for e in json.loads(s["encodings"]):
            known.append(np.array(e)); owners.append(s)
    if not known:
        return jsonify(ok=False, msg="Please register students first.")
    encs = face_encodings(img)
    marked, already, unknown = [], [], 0
    for enc in encs:
        dist = face_distance(known, enc)
        i = int(np.argmin(dist))
        if dist[i] <= TOLERANCE:
            s = owners[i]
            now = datetime.now().strftime("%H:%M:%S")
            try:
                db().execute("INSERT INTO attendance(student_id,day,time) VALUES(?,?,?)",
                             (s["id"], str(date.today()), now))
                db().commit()
                marked.append(dict(name=s["name"], roll=s["roll"], time=to12(now)))
            except sqlite3.IntegrityError:
                already.append(s["name"])
        else:
            unknown += 1
    return jsonify(ok=True, faces=len(encs), marked=marked, already=already, unknown=unknown)

@app.route("/report")
def report():
    day = request.args.get("day", str(date.today()))
    rows = report_rows(day)
    classes = sorted({r["class_name"] for r in rows})
    return render_template("report.html", rows=rows, day=day, classes=classes)

@app.route("/report/download")
def report_download():
    day = request.args.get("day", str(date.today()))
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Name", "Roll No", "Class", "Date", "Status", "Time (12 hr)"])
    for r in report_rows(day):
        w.writerow([r["name"], r["roll"], r["class_name"], day,
                    "Present" if r["present"] else "Absent", r["time"]])
    # utf-8-sig: lets Excel display non-English names correctly
    data = "\ufeff" + out.getvalue()
    return Response(data, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=attendance_{day}.csv"})

@app.route("/report/download.xlsx")
def report_xlsx():
    day = request.args.get("day", str(date.today()))
    wb = Workbook(); ws = wb.active; ws.title = "Attendance"
    ws.append(["Name", "Roll No", "Class", "Date", "Status", "Time (12 hr)"])
    for c in ws[1]: c.font = Font(bold=True)
    for r in report_rows(day):
        ws.append([r["name"], r["roll"], r["class_name"], day,
                   "Present" if r["present"] else "Absent", r["time"]])
    for col, w in zip("ABCDEF", (24, 12, 12, 14, 12, 16)):
        ws.column_dimensions[col].width = w   # prevents ###### in Excel
    buf = io.BytesIO(); wb.save(buf)
    return Response(buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=attendance_{day}.xlsx"})

init_db()   # create tables on startup (also needed when run by a server like Vercel)

if __name__ == "__main__":
    app.run(debug=True)
