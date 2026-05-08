from flask import Flask, render_template, request, redirect, session, flash, jsonify
import sqlite3
import datetime
import os
import hashlib
import secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Optional integrations
try:
    import razorpay
except ImportError:
    razorpay = None

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secure random key

# ─────────────────────────── CONFIG ────────────────────────────
RAZORPAY_KEY    = os.getenv("RAZORPAY_KEY", "")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET", "")
TWILIO_SID      = os.getenv("TWILIO_SID", "")
TWILIO_AUTH     = os.getenv("TWILIO_AUTH", "")
TWILIO_NUMBER   = os.getenv("TWILIO_NUMBER", "whatsapp:+14155238886")
DB_PATH         = "hostel.db"

razor = None
if razorpay and RAZORPAY_KEY and RAZORPAY_SECRET:
    try:
        razor = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
    except Exception:
        pass

# ─────────────────────────── DB ────────────────────────────────
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = connect()
    cur  = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT NOT NULL,
        phone     TEXT UNIQUE NOT NULL,
        email     TEXT UNIQUE NOT NULL,
        password  TEXT NOT NULL,
        room      TEXT,
        fee       INTEGER DEFAULT 5000,
        paid      INTEGER DEFAULT 0,
        status    TEXT DEFAULT 'Active',
        join_date TEXT,
        course    TEXT,
        year      TEXT,
        guardian  TEXT,
        guardian_phone TEXT,
        photo_url TEXT
    );

    CREATE TABLE IF NOT EXISTS pending (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT NOT NULL,
        phone     TEXT UNIQUE NOT NULL,
        email     TEXT UNIQUE NOT NULL,
        password  TEXT NOT NULL,
        room_type TEXT,
        date      TEXT,
        course    TEXT,
        year      TEXT,
        guardian  TEXT,
        guardian_phone TEXT
    );

    CREATE TABLE IF NOT EXISTS rooms (
        room_no   TEXT PRIMARY KEY,
        type      TEXT,
        capacity  INTEGER DEFAULT 2,
        occupied  INTEGER DEFAULT 0,
        floor     INTEGER DEFAULT 1,
        amenities TEXT
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_phone TEXT NOT NULL,
        category      TEXT DEFAULT 'General',
        message       TEXT NOT NULL,
        status        TEXT DEFAULT 'Pending',
        admin_reply   TEXT,
        date          TEXT,
        resolved_date TEXT
    );

    CREATE TABLE IF NOT EXISTS parcels (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_phone TEXT NOT NULL,
        parcel_name   TEXT NOT NULL,
        sender        TEXT,
        status        TEXT DEFAULT 'Arrived',
        date          TEXT,
        collected_date TEXT
    );

    CREATE TABLE IF NOT EXISTS entry_log (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_phone TEXT NOT NULL,
        time          TEXT,
        status        TEXT,
        guard_note    TEXT
    );

    CREATE TABLE IF NOT EXISTS payments (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_phone TEXT NOT NULL,
        amount        INTEGER NOT NULL,
        mode          TEXT DEFAULT 'Manual',
        status        TEXT DEFAULT 'Pending',
        razorpay_id   TEXT,
        date          TEXT,
        month         TEXT,
        receipt_no    TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS leaves (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_phone TEXT NOT NULL,
        from_date     TEXT NOT NULL,
        to_date       TEXT NOT NULL,
        reason        TEXT,
        status        TEXT DEFAULT 'Pending',
        admin_note    TEXT,
        applied_date  TEXT
    );

    CREATE TABLE IF NOT EXISTS notices (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        title    TEXT NOT NULL,
        body     TEXT NOT NULL,
        priority TEXT DEFAULT 'Normal',
        date     TEXT,
        author   TEXT DEFAULT 'Admin'
    );

    CREATE TABLE IF NOT EXISTS meals (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        date    TEXT NOT NULL,
        session TEXT NOT NULL,
        menu    TEXT,
        rating_sum INTEGER DEFAULT 0,
        rating_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS meal_feedback (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER,
        student_phone TEXT,
        rating  INTEGER,
        comment TEXT,
        UNIQUE(meal_id, student_phone)
    );

    CREATE TABLE IF NOT EXISTS room_transfers (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_phone TEXT NOT NULL,
        from_room     TEXT,
        to_room_type  TEXT,
        reason        TEXT,
        status        TEXT DEFAULT 'Pending',
        date          TEXT
    );

    CREATE TABLE IF NOT EXISTS admins (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name     TEXT,
        role     TEXT DEFAULT 'admin'
    );
    """)

    # Seed default admin if not exists
    existing = cur.execute("SELECT id FROM admins WHERE username='admin'").fetchone()
    if not existing:
        cur.execute(
            "INSERT INTO admins(username, password, name) VALUES (?,?,?)",
            ('admin', generate_password_hash('admin123'), 'Administrator')
        )

    # Seed sample rooms if empty
    room_count = cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if room_count == 0:
        rooms_data = [
            ('A101','Single',1,0,1,'AC, Attached Bathroom'),
            ('A102','Single',1,0,1,'AC, Attached Bathroom'),
            ('B101','Double',2,0,1,'Fan, Common Bathroom'),
            ('B102','Double',2,0,1,'Fan, Common Bathroom'),
            ('B103','Double',2,0,1,'Fan, Common Bathroom'),
            ('C101','Triple',3,0,2,'Fan, Common Bathroom'),
            ('C102','Triple',3,0,2,'Fan, Common Bathroom'),
        ]
        cur.executemany(
            "INSERT OR IGNORE INTO rooms(room_no,type,capacity,occupied,floor,amenities) VALUES (?,?,?,?,?,?)",
            rooms_data
        )

    conn.commit()
    conn.close()

init_db()

# ─────────────────────────── UTIL ──────────────────────────────
def send_msg(phone, msg):
    if TwilioClient and TWILIO_SID and TWILIO_AUTH:
        try:
            client = TwilioClient(TWILIO_SID, TWILIO_AUTH)
            client.messages.create(body=msg, from_=TWILIO_NUMBER, to=f"whatsapp:+91{phone}")
        except Exception:
            pass

def allocate_room(room_type):
    conn = connect()
    cur  = conn.cursor()
    rooms = cur.execute(
        "SELECT * FROM rooms WHERE type=? AND occupied < capacity ORDER BY room_no",
        (room_type,)
    ).fetchall()
    for r in rooms:
        cur.execute("UPDATE rooms SET occupied=occupied+1 WHERE room_no=?", (r['room_no'],))
        conn.commit()
        conn.close()
        return r['room_no']
    conn.close()
    return "FULL"

def deallocate_room(room_no):
    conn = connect()
    cur  = conn.cursor()
    cur.execute("UPDATE rooms SET occupied=MAX(0, occupied-1) WHERE room_no=?", (room_no,))
    conn.commit()
    conn.close()

def gen_receipt():
    return "RCP-" + secrets.token_hex(5).upper()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("student_phone"):
            return redirect("/student")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

def get_student(phone):
    conn = connect()
    cur  = conn.cursor()
    s = cur.execute("SELECT * FROM students WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return s

# ─────────────────────────── ROOT ──────────────────────────────
@app.route("/")
def index():
    return redirect("/student")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ─────────────────── STUDENT LOGIN / REGISTER ──────────────────
@app.route("/student", methods=["GET","POST"])
def student_login():
    if session.get("student_phone"):
        return redirect("/dashboard")
    error = None
    if request.method == "POST":
        user     = request.form.get("user","").strip()
        password = request.form.get("password","")
        conn = connect()
        cur  = conn.cursor()
        student = cur.execute(
            "SELECT * FROM students WHERE phone=? OR email=?", (user, user)
        ).fetchone()
        pending = cur.execute(
            "SELECT * FROM pending WHERE phone=? OR email=?", (user, user)
        ).fetchone()
        conn.close()
        if student and check_password_hash(student['password'], password):
            if student['status'] == 'Inactive':
                error = "Account is deactivated. Contact admin."
            else:
                session["student_phone"] = student['phone']
                return redirect("/dashboard")
        elif pending:
            error = "Application pending admin approval."
        else:
            error = "Invalid credentials. New student? Apply below."
    return render_template("student_login.html", error=error)

@app.route("/apply", methods=["GET","POST"])
def apply():
    if request.method == "POST":
        name   = request.form.get("name","").strip()
        phone  = request.form.get("phone","").strip()
        email  = request.form.get("email","").strip()
        pw     = request.form.get("password","")
        room   = request.form.get("room","Double")
        course = request.form.get("course","")
        year   = request.form.get("year","")
        guard  = request.form.get("guardian","")
        gphone = request.form.get("guardian_phone","")

        if not all([name, phone, email, pw]):
            return render_template("student_apply.html", error="All fields are required.")

        try:
            conn = connect()
            cur  = conn.cursor()
            cur.execute(
                """INSERT INTO pending(name,phone,email,password,room_type,date,course,year,guardian,guardian_phone)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (name, phone, email, generate_password_hash(pw), room,
                 str(datetime.date.today()), course, year, guard, gphone)
            )
            conn.commit()
            conn.close()
            return render_template("student_apply.html", success=True)
        except sqlite3.IntegrityError:
            return render_template("student_apply.html", error="Phone or Email already registered.")

    return render_template("student_apply.html")

# ─────────────────────────── DASHBOARD ─────────────────────────
@app.route("/dashboard", methods=["GET","POST"])
@login_required
def dashboard():
    phone = session["student_phone"]
    conn  = connect()
    cur   = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "complaint":
            msg      = request.form.get("msg","").strip()
            category = request.form.get("category","General")
            if msg:
                cur.execute(
                    "INSERT INTO complaints(student_phone,category,message,status,date) VALUES (?,?,?,?,?)",
                    (phone, category, msg, "Pending", str(datetime.date.today()))
                )
                conn.commit()
                send_msg(phone, f"✅ Complaint submitted. We'll resolve it soon.")

        elif action == "leave":
            from_d  = request.form.get("from_date")
            to_d    = request.form.get("to_date")
            reason  = request.form.get("reason","")
            if from_d and to_d:
                cur.execute(
                    "INSERT INTO leaves(student_phone,from_date,to_date,reason,status,applied_date) VALUES (?,?,?,?,?,?)",
                    (phone, from_d, to_d, reason, "Pending", str(datetime.date.today()))
                )
                conn.commit()

        elif action == "transfer":
            room_type = request.form.get("room_type")
            reason    = request.form.get("reason","")
            cur.execute(
                "INSERT INTO room_transfers(student_phone,from_room,to_room_type,reason,status,date) VALUES (?,?,?,?,?,?)",
                (phone, None, room_type, reason, "Pending", str(datetime.date.today()))
            )
            conn.commit()

    student    = cur.execute("SELECT * FROM students WHERE phone=?", (phone,)).fetchone()
    complaints = cur.execute("SELECT * FROM complaints WHERE student_phone=? ORDER BY date DESC LIMIT 5", (phone,)).fetchall()
    parcels    = cur.execute("SELECT * FROM parcels WHERE student_phone=? ORDER BY date DESC LIMIT 5", (phone,)).fetchall()
    leaves     = cur.execute("SELECT * FROM leaves WHERE student_phone=? ORDER BY applied_date DESC LIMIT 5", (phone,)).fetchall()
    notices    = cur.execute("SELECT * FROM notices ORDER BY date DESC LIMIT 5").fetchall()
    entry_log  = cur.execute("SELECT * FROM entry_log WHERE student_phone=? ORDER BY time DESC LIMIT 5", (phone,)).fetchall()
    payments   = cur.execute("SELECT * FROM payments WHERE student_phone=? ORDER BY date DESC LIMIT 5", (phone,)).fetchall()
    meals      = cur.execute("SELECT * FROM meals WHERE date=?", (str(datetime.date.today()),)).fetchall()
    transfers  = cur.execute("SELECT * FROM room_transfers WHERE student_phone=? ORDER BY date DESC LIMIT 3", (phone,)).fetchall()

    due = (student['fee'] or 0) - (student['paid'] or 0)
    conn.close()
    return render_template("student_dashboard.html",
        student=student, complaints=complaints, parcels=parcels,
        leaves=leaves, notices=notices, entry_log=entry_log,
        payments=payments, meals=meals, transfers=transfers, due=due
    )

# ─────────────────────────── PAYMENT ───────────────────────────
@app.route("/pay/<phone>", methods=["GET","POST"])
def pay(phone):
    conn = connect()
    cur  = conn.cursor()
    student = cur.execute("SELECT * FROM students WHERE phone=?", (phone,)).fetchone()

    if not student:
        conn.close()
        return "Student not found", 404

    if request.method == "POST":
        amount  = int(request.form.get("amount", 0))
        mode    = request.form.get("mode","Manual")
        month   = request.form.get("month", str(datetime.date.today().strftime("%B %Y")))
        receipt = gen_receipt()
        if amount > 0:
            cur.execute(
                "INSERT INTO payments(student_phone,amount,mode,status,date,month,receipt_no) VALUES (?,?,?,?,?,?,?)",
                (phone, amount, mode, "Paid", str(datetime.date.today()), month, receipt)
            )
            cur.execute("UPDATE students SET paid=paid+? WHERE phone=?", (amount, phone))
            conn.commit()
            send_msg(phone, f"💰 Payment of ₹{amount} received. Receipt: {receipt}")
            conn.close()
            return redirect("/dashboard")

    due = (student['fee'] or 0) - (student['paid'] or 0)
    conn.close()
    return render_template("payment.html", student=student, due=due)

# ─────────────────────────── MEAL FEEDBACK ─────────────────────
@app.route("/meal/rate", methods=["POST"])
@login_required
def meal_rate():
    phone   = session["student_phone"]
    meal_id = request.form.get("meal_id")
    rating  = int(request.form.get("rating", 3))
    comment = request.form.get("comment","")
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO meal_feedback(meal_id,student_phone,rating,comment) VALUES (?,?,?,?)",
            (meal_id, phone, rating, comment)
        )
        cur.execute(
            "UPDATE meals SET rating_sum=rating_sum+?, rating_count=rating_count+1 WHERE id=?",
            (rating, meal_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect("/dashboard")

# ─────────────────────────── ADMIN LOGIN ───────────────────────
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if session.get("admin"):
        return redirect("/admin")
    error = None
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        conn = connect()
        cur  = conn.cursor()
        admin = cur.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password'], password):
            session["admin"]      = admin['username']
            session["admin_name"] = admin['name']
            return redirect("/admin")
        error = "Invalid admin credentials."
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    session.pop("admin_name", None)
    return redirect("/admin/login")

# ─────────────────────────── ADMIN DASHBOARD ───────────────────
@app.route("/admin")
@admin_required
def admin():
    conn = connect()
    cur  = conn.cursor()

    students   = cur.execute("SELECT * FROM students ORDER BY join_date DESC").fetchall()
    pending    = cur.execute("SELECT * FROM pending ORDER BY date DESC").fetchall()
    rooms      = cur.execute("SELECT * FROM rooms ORDER BY room_no").fetchall()
    complaints = cur.execute(
        "SELECT c.*, s.name FROM complaints c LEFT JOIN students s ON c.student_phone=s.phone ORDER BY c.date DESC"
    ).fetchall()
    payments   = cur.execute(
        "SELECT p.*, s.name FROM payments p LEFT JOIN students s ON p.student_phone=s.phone ORDER BY p.date DESC LIMIT 20"
    ).fetchall()
    notices    = cur.execute("SELECT * FROM notices ORDER BY date DESC").fetchall()
    leaves     = cur.execute(
        "SELECT l.*, s.name FROM leaves l LEFT JOIN students s ON l.student_phone=s.phone ORDER BY l.applied_date DESC"
    ).fetchall()
    transfers  = cur.execute(
        "SELECT rt.*, s.name FROM room_transfers rt LEFT JOIN students s ON rt.student_phone=s.phone ORDER BY rt.date DESC"
    ).fetchall()
    parcels    = cur.execute("SELECT * FROM parcels ORDER BY date DESC LIMIT 20").fetchall()

    # Stats
    total_students  = len(students)
    active_students = sum(1 for s in students if s['status']=='Active')
    total_rooms     = len(rooms)
    full_rooms      = sum(1 for r in rooms if r['occupied'] >= r['capacity'])
    total_collected = cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='Paid'").fetchone()[0]
    pending_complaints = sum(1 for c in complaints if c['status']=='Pending')
    pending_leaves  = sum(1 for l in leaves if l['status']=='Pending')

    conn.close()
    return render_template("admin.html",
        students=students, pending=pending, rooms=rooms,
        complaints=complaints, payments=payments, notices=notices,
        leaves=leaves, transfers=transfers, parcels=parcels,
        total_students=total_students, active_students=active_students,
        total_rooms=total_rooms, full_rooms=full_rooms,
        total_collected=total_collected,
        pending_complaints=pending_complaints, pending_leaves=pending_leaves
    )

@app.route("/approve/<int:pid>")
@admin_required
def approve(pid):
    conn = connect()
    cur  = conn.cursor()
    d = cur.execute("SELECT * FROM pending WHERE id=?", (pid,)).fetchone()
    if d:
        room = allocate_room(d['room_type'])
        try:
            cur.execute(
                """INSERT INTO students(name,phone,email,password,room,fee,paid,status,join_date,course,year,guardian,guardian_phone)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d['name'], d['phone'], d['email'], d['password'],
                 room, 5000, 0, 'Active', str(datetime.date.today()),
                 d['course'], d['year'], d['guardian'], d['guardian_phone'])
            )
            cur.execute("DELETE FROM pending WHERE id=?", (pid,))
            conn.commit()
            send_msg(d['phone'], f"✅ Your hostel application is APPROVED! Room: {room}. Welcome!")
        except sqlite3.IntegrityError:
            pass
    conn.close()
    return redirect("/admin")

@app.route("/reject/<int:pid>")
@admin_required
def reject(pid):
    conn = connect()
    cur  = conn.cursor()
    d = cur.execute("SELECT * FROM pending WHERE id=?", (pid,)).fetchone()
    if d:
        send_msg(d['phone'], "❌ Your hostel application was not approved. Contact admin for more info.")
        cur.execute("DELETE FROM pending WHERE id=?", (pid,))
        conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/complaint/reply/<int:cid>", methods=["POST"])
@admin_required
def complaint_reply(cid):
    reply  = request.form.get("reply","")
    status = request.form.get("status","Resolved")
    conn   = connect()
    cur    = conn.cursor()
    c = cur.execute("SELECT * FROM complaints WHERE id=?", (cid,)).fetchone()
    if c:
        cur.execute(
            "UPDATE complaints SET admin_reply=?, status=?, resolved_date=? WHERE id=?",
            (reply, status, str(datetime.date.today()), cid)
        )
        conn.commit()
        if reply:
            send_msg(c['student_phone'], f"📋 Complaint Update: {reply}")
    conn.close()
    return redirect("/admin#complaints")

@app.route("/admin/leave/<int:lid>/<action>")
@admin_required
def leave_action(lid, action):
    status = "Approved" if action=="approve" else "Rejected"
    conn   = connect()
    cur    = conn.cursor()
    l = cur.execute("SELECT * FROM leaves WHERE id=?", (lid,)).fetchone()
    if l:
        cur.execute("UPDATE leaves SET status=? WHERE id=?", (status, lid))
        conn.commit()
        send_msg(l['student_phone'], f"🏠 Leave application {status} ({l['from_date']} to {l['to_date']})")
    conn.close()
    return redirect("/admin#leaves")

@app.route("/admin/transfer/<int:tid>/<action>")
@admin_required
def transfer_action(tid, action):
    conn = connect()
    cur  = conn.cursor()
    t = cur.execute("SELECT * FROM room_transfers WHERE id=?", (tid,)).fetchone()
    if t and action == "approve":
        student = cur.execute("SELECT * FROM students WHERE phone=?", (t['student_phone'],)).fetchone()
        if student and student['room']:
            deallocate_room(student['room'])
        new_room = allocate_room(t['to_room_type'])
        cur.execute("UPDATE students SET room=? WHERE phone=?", (new_room, t['student_phone']))
        cur.execute("UPDATE room_transfers SET status='Approved',from_room=? WHERE id=?", (student['room'] if student else '', tid))
        conn.commit()
        send_msg(t['student_phone'], f"🏠 Room transfer approved! New Room: {new_room}")
    elif t:
        cur.execute("UPDATE room_transfers SET status='Rejected' WHERE id=?", (tid,))
        conn.commit()
    conn.close()
    return redirect("/admin#transfers")

@app.route("/admin/notice/add", methods=["POST"])
@admin_required
def add_notice():
    title    = request.form.get("title","")
    body     = request.form.get("body","")
    priority = request.form.get("priority","Normal")
    if title and body:
        conn = connect()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO notices(title,body,priority,date,author) VALUES (?,?,?,?,?)",
            (title, body, priority, str(datetime.date.today()), session.get("admin_name","Admin"))
        )
        conn.commit()
        conn.close()
    return redirect("/admin#notices")

@app.route("/admin/notice/delete/<int:nid>")
@admin_required
def delete_notice(nid):
    conn = connect()
    cur  = conn.cursor()
    cur.execute("DELETE FROM notices WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    return redirect("/admin#notices")

@app.route("/admin/student/toggle/<phone>")
@admin_required
def toggle_student(phone):
    conn = connect()
    cur  = conn.cursor()
    student = cur.execute("SELECT status FROM students WHERE phone=?", (phone,)).fetchone()
    if student:
        new_status = "Inactive" if student['status']=='Active' else "Active"
        cur.execute("UPDATE students SET status=? WHERE phone=?", (new_status, phone))
        conn.commit()
    conn.close()
    return redirect("/admin#students")

@app.route("/admin/meal/add", methods=["POST"])
@admin_required
def add_meal():
    date    = request.form.get("date", str(datetime.date.today()))
    session_name = request.form.get("session","Lunch")
    menu    = request.form.get("menu","")
    conn    = connect()
    cur     = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO meals(date,session,menu) VALUES (?,?,?)",
        (date, session_name, menu)
    )
    conn.commit()
    conn.close()
    return redirect("/admin#meals")

# ─────────────────────────── GUARD ─────────────────────────────
@app.route("/guard", methods=["GET","POST"])
def guard():
    msg = None
    student_info = None
    if request.method == "POST":
        conn = connect()
        cur  = conn.cursor()
        action = request.form.get("action","entry")
        phone  = request.form.get("phone","").strip()

        student = cur.execute("SELECT * FROM students WHERE phone=?", (phone,)).fetchone()

        if not student:
            msg = ("error","Student not found with this phone number.")
        else:
            student_info = dict(student)
            if action == "parcel":
                parcel = request.form.get("parcel","")
                sender = request.form.get("sender","")
                cur.execute(
                    "INSERT INTO parcels(student_phone,parcel_name,sender,status,date) VALUES (?,?,?,?,?)",
                    (phone, parcel, sender, "Arrived", str(datetime.date.today()))
                )
                conn.commit()
                send_msg(phone, f"📦 Parcel '{parcel}' from '{sender}' has arrived at hostel reception.")
                msg = ("success", f"Parcel logged for {student['name']}.")
            else:
                status = request.form.get("status","IN")
                note   = request.form.get("note","")
                cur.execute(
                    "INSERT INTO entry_log(student_phone,time,status,guard_note) VALUES (?,?,?,?)",
                    (phone, str(datetime.datetime.now()), status, note)
                )
                conn.commit()
                send_msg(phone, f"🚪 Entry recorded: {status} at {datetime.datetime.now().strftime('%I:%M %p')}")
                msg = ("success", f"{student['name']} marked {status}.")

        conn.close()

    conn = connect()
    cur  = conn.cursor()
    recent_entries = cur.execute(
        """SELECT e.*, s.name, s.room FROM entry_log e
           LEFT JOIN students s ON e.student_phone=s.phone
           ORDER BY e.time DESC LIMIT 15"""
    ).fetchall()
    recent_parcels = cur.execute(
        """SELECT p.*, s.name FROM parcels p
           LEFT JOIN students s ON p.student_phone=s.phone
           ORDER BY p.date DESC LIMIT 10"""
    ).fetchall()
    conn.close()
    return render_template("guard.html",
        msg=msg, student_info=student_info,
        recent_entries=recent_entries, recent_parcels=recent_parcels
    )

# ─────────────────────────── REPORT ────────────────────────────
@app.route("/report")
@admin_required
def report():
    conn = connect()
    cur  = conn.cursor()
    payment_data = cur.execute(
        "SELECT date, SUM(amount) as total FROM payments WHERE status='Paid' GROUP BY date ORDER BY date"
    ).fetchall()
    complaint_data = cur.execute(
        "SELECT status, COUNT(*) as cnt FROM complaints GROUP BY status"
    ).fetchall()
    room_data = cur.execute(
        "SELECT type, SUM(capacity) as cap, SUM(occupied) as occ FROM rooms GROUP BY type"
    ).fetchall()
    monthly = cur.execute(
        "SELECT month, SUM(amount) as total FROM payments WHERE status='Paid' GROUP BY month"
    ).fetchall()
    conn.close()

    chart_generated = False
    if HAS_MATPLOTLIB and payment_data:
        try:
            import io, base64
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            fig.patch.set_facecolor('#0f172a')
            for ax in axes:
                ax.set_facecolor('#1e293b')
                ax.tick_params(colors='#94a3b8')
                ax.spines['bottom'].set_color('#334155')
                ax.spines['left'].set_color('#334155')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)

            dates  = [r['date'] for r in payment_data]
            values = [r['total'] for r in payment_data]
            axes[0].bar(dates, values, color='#6366f1')
            axes[0].set_title('Daily Collections', color='#e2e8f0', fontsize=12)
            axes[0].set_xlabel('Date', color='#94a3b8')
            axes[0].set_ylabel('Amount (₹)', color='#94a3b8')
            plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha='right')

            room_types = [r['type'] for r in room_data]
            occ = [r['occ'] for r in room_data]
            cap = [(r['cap'] - r['occ']) for r in room_data]
            x = range(len(room_types))
            axes[1].bar(x, occ, label='Occupied', color='#f43f5e')
            axes[1].bar(x, cap, bottom=occ, label='Vacant', color='#22c55e', alpha=0.7)
            axes[1].set_xticks(x)
            axes[1].set_xticklabels(room_types)
            axes[1].set_title('Room Occupancy', color='#e2e8f0', fontsize=12)
            axes[1].legend(facecolor='#1e293b', labelcolor='#e2e8f0')

            plt.tight_layout()
            os.makedirs("static", exist_ok=True)
            plt.savefig("static/report.png", dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close()
            chart_generated = True
        except Exception as e:
            print(f"Chart error: {e}")

    return render_template("report.html",
        payment_data=payment_data, complaint_data=complaint_data,
        room_data=room_data, monthly=monthly,
        chart_generated=chart_generated
    )

# ─────────────────────────── API (JSON) ────────────────────────
@app.route("/api/student/<phone>")
def api_student(phone):
    s = get_student(phone)
    if not s:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(s))

@app.route("/api/stats")
def api_stats():
    conn = connect()
    cur  = conn.cursor()
    stats = {
        "total_students": cur.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "active_students": cur.execute("SELECT COUNT(*) FROM students WHERE status='Active'").fetchone()[0],
        "total_rooms": cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0],
        "pending_applications": cur.execute("SELECT COUNT(*) FROM pending").fetchone()[0],
        "total_collected": cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='Paid'").fetchone()[0],
        "pending_complaints": cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0],
    }
    conn.close()
    return jsonify(stats)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
