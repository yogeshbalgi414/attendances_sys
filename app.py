from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from twilio.rest import Client
import time
from sqlalchemy import func  # ← Add this import
from datetime import datetime, timedelta  # ← Add timedelta
from sqlalchemy.orm import relationship
import json
from flask import jsonify






app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ams.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from flask_migrate import Migrate

# Initialize Flask-Migrate
migrate = Migrate(app, db)



# Twilio Config
'''
TWILIO_ACCOUNT_SID= 'ACdfbf8e67a996a3d20cd6ce120e18d987'
TWILIO_AUTH_TOKEN= '8227afb93f20af70ee0e1000cc11f06d'
TWILIO_PHONE_NUMBER='+19382018064'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
'''
'''
TWILIO_ACCOUNT_SID= 'AC0df29079df0648ec3e8d03b5c8ceca09'
TWILIO_AUTH_TOKEN= '4e18d081908636544a8be6f1439ef097'
TWILIO_PHONE_NUMBER='+15158008250'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

TWILIO_ACCOUNT_SID = 'ACdfbf8e67a996a3d20cd6ce120e18d987'
TWILIO_AUTH_TOKEN = '8227afb93f20af70ee0e1000cc11f06d'
TWILIO_PHONE_NUMBER = '+19382018064'
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
'''
# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    role = db.Column(db.String(20))
    rfid = db.Column(db.String(100), unique=True)
    parent_no = db.Column(db.String(20), nullable=True)
    Phno = db.Column(db.String(20), nullable=True)
    passd=db.Column(db.String(20))

    timetables = relationship('Timetable', back_populates='faculty')
    student_attendances = relationship('Attendance', foreign_keys='Attendance.student_id', back_populates='student')
    faculty_attendances = relationship('Attendance', foreign_keys='Attendance.faculty_id', back_populates='instructor')

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(100))
    day = db.Column(db.String(20))  # New field: Monday, Tuesday, etc.
    start_time = db.Column(db.Time)  # Existing start time field
    end_time = db.Column(db.Time)    # Existing end time field
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    faculty = relationship('User', back_populates='timetables')
    slot = relationship('Slot', back_populates='timetables')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(100), default="General")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    day = db.Column(db.String(20))
    student = relationship('User', foreign_keys=[student_id], back_populates='student_attendances')
    instructor = relationship('User', foreign_keys=[faculty_id], back_populates='faculty_attendances')

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timetables = relationship('Timetable', back_populates='slot')

with app.app_context():
    db.create_all()

# Class Session Memory
current_session = {
    "faculty_id": None,
    "faculty_uid": None,
    "subject": None,
    "start_time": None
}

from flask import Flask, request, jsonify, redirect, session
#from models import db, User
from werkzeug.security import check_password_hash  # Optional if passwords are hashed

@app.route('/', methods=['GET'])
def index():
    return render_template('login.html')

@app.route('/', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Look up the user by username
    user = User.query.filter_by(name=username).first()
    
    # Check if user exists and password matches
    if user and user.passd == password:
        # For basic login we don't need sessions
        return jsonify({
            'success': True,
            'message': 'Login successful', 
            'role': user.role,
            'user_id': user.id
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid username or password'
        }), 401

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Check if username already exists
    existing_user = User.query.filter_by(name=username).first()
    if existing_user:
        return jsonify({
            'success': False,
            'message': 'Username already exists'
        }), 400
    
    # Check if email already exists
    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        return jsonify({
            'success': False,
            'message': 'Email already exists'
        }), 400
    
    # Create new student user
    new_user = User(
        name=username,
        email=email,
        passd=password,
        role='student'  # Default role for new signups
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'User registered successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Registration failed: {str(e)}'
        }), 500
    

@app.route('/logout')
def logout():
    return redirect(url_for('index'))

# Route protection middleware


@app.route('/api/scan', methods=['POST'])
def handle_scan():
    uid = request.form.get('uid')
    timestamp = request.form.get('timestamp')

    user = User.query.filter_by(rfid=uid).first()
    if not user:
        return "UNKNOWN"

    if user.role == "faculty":
        if current_session["faculty_uid"] == uid:
            # Faculty ending the session
            faculty_id = current_session["faculty_id"]
            subject = current_session["subject"]
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Fetch all students
            students = User.query.filter_by(role="student").all()

            # Get today's attendance for this subject/faculty
            attendance_today = Attendance.query.filter_by(
                faculty_id=faculty_id,
                subject=subject
            ).filter(Attendance.timestamp >= start_of_day).all()

            present_ids = set([a.student_id for a in attendance_today])

            # Send SMS to absent students' parents
            for student in students:
                if student.id not in present_ids and student.parent_no:
                    try:
                        client.messages.create(
                            body=f"Dear Parent, your child {student.name} was ABSENT today for subject: {subject}.",
                            from_=TWILIO_PHONE_NUMBER,
                            to=student.parent_no
                        )
                    except Exception as e:
                        print(f"SMS to {student.name}'s parent failed: {e}")

            # Clear the session
            current_session.update({
                "faculty_id": None,
                "faculty_uid": None,
                "subject": None,
                "start_time": None
            })
            return f"SESSION ENDED:{user.name}"

        elif current_session["faculty_uid"] is None:
            today = datetime.today().strftime('%A')
            timetable_entries = Timetable.query.filter_by(faculty_id=user.id, day=today).all()

            if not timetable_entries:
                return "NO_TIMETABLE"

            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            for entry in timetable_entries:
                existing_attendance = Attendance.query.filter_by(
                    faculty_id=user.id,
                    subject=entry.subject
                ).filter(Attendance.timestamp >= start_of_day).first()

                if existing_attendance:
                    return "ALREADY_TAUGHT"

            subject = timetable_entries[0].subject

            current_session.update({
                "faculty_id": user.id,
                "faculty_uid": uid,
                "subject": subject,
                "start_time": time.time()
            })
            return f"FACULTY:{user.name}"

        else:
            return "CLASS IN PROGRESS"

    elif user.role == "student":
        if current_session["faculty_id"]:
            already_marked = Attendance.query.filter_by(
                student_id=user.id,
                faculty_id=current_session["faculty_id"],
                subject=current_session["subject"]
            ).first()
            if already_marked:
                return "ALREADY_MARKED"

            try:
                attendance = Attendance(
                    student_id=user.id,
                    faculty_id=current_session["faculty_id"],
                    subject=current_session["subject"],
                    timestamp=datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"),
                    day=datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%A")
                )
                db.session.add(attendance)
                db.session.commit()
            except Exception as e:
                return f"ERROR:{str(e)}"

            if user.parent_no:
                try:
                    client.messages.create(
                        body=f"Dear Parent, your child {user.name} has attended the class: {current_session['subject']}.",
                        from_=TWILIO_PHONE_NUMBER,
                        to=user.parent_no
                    )
                except Exception as e:
                    print(f"SMS Error: {e}")

            return f"STUDENT:{user.parent_no or 'N/A'}"
        else:
            return "NOCLASS"

    return "UNKNOWN"


@app.route("/faculty/<int:faculty_id>")
def faculty_dashboard(faculty_id):
    faculty = User.query.get(faculty_id)
    timetable_entries = Timetable.query.all()
    # Get a distinct list of subjects taught by this faculty
    faculty_subjects = list({entry.subject for entry in timetable_entries if entry.faculty_id == faculty.id})

# Prefer subject from URL, fallback to first faculty subject
    current_subject = request.args.get('subject') or (faculty_subjects[0] if faculty_subjects else "General")

    
    # Timetable Calendar Data
    calendar_data = {
        day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    }
   

    all_slots = Slot.query.all()

    for day in calendar_data:
        for slot in all_slots:
            # Find the timetable for the current slot and day
            timetable = next((t for t in timetable_entries if t.slot_id == slot.id and t.day == day), None)
            calendar_data[day].append({
                "slot": slot,
                "timetable": timetable
            })
    # Attendance Trends
    students = User.query.filter_by(role="student").all()
    attendance_data = []
    for student in students:
        total_classes = Attendance.query.filter_by(
            faculty_id=faculty.id, 
            subject=current_subject
        ).count()
        attended = Attendance.query.filter_by(
            student_id=student.id,
            faculty_id=faculty.id,
            subject=current_subject
        ).count()
        attendance_data.append({
            "student": student,
            "attendance": f"{(attended/total_classes*100) if total_classes > 0 else 0:.1f}%",
            "chart_data": [attended, total_classes-attended]
        })

    # Absentee Alerts (Last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    frequent_absentees = db.session.query(
        User, 
        func.count(Attendance.id).label('absences')
    ).outerjoin(
        Attendance, 
        (User.id == Attendance.student_id) & 
        (Attendance.subject == current_subject) &
        (Attendance.timestamp >= seven_days_ago)
    ).filter(
        User.role == "student",
        Attendance.id == None
    ).group_by(User.id).order_by(db.desc('absences')).limit(5).all()

    latest_attendance = Attendance.query.order_by(Attendance.id.desc()).first()
    return render_template(
        "faculty_dashboard.html",
        faculty=faculty,
        calendar_data=calendar_data,
        current_subject=current_subject,
        attendance_data=attendance_data,
        frequent_absentees=frequent_absentees,
        latest_attendance_id=latest_attendance.id if latest_attendance else 0,
        latest_attendance_name=latest_attendance.student.name if latest_attendance else "",
    )


@app.route("/hod", methods=["GET"])
def hod_dashboard():
    timetable_entries = Timetable.query.all()
    all_slots = Slot.query.all()
    calendar_data = {
        day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    }

    for day in calendar_data:
        for slot in all_slots:
            timetable = next((t for t in timetable_entries if t.slot_id == slot.id and t.day == day), None)
            calendar_data[day].append({
                "slot": slot,
                "timetable": timetable
            })

    students = User.query.filter_by(role='student').all()
    student_id = request.args.get('student_id')
    selected_student = None
    attendance_stats = []

    if student_id:
        selected_student = User.query.get(int(student_id))
        all_subjects = Timetable.query.all()
        for t in all_subjects:
            total = Attendance.query.filter_by(faculty_id=t.faculty_id, subject=t.subject).count()
            attended = Attendance.query.filter_by(student_id=selected_student.id, subject=t.subject).count()
            percentage = (attended / total * 100) if total > 0 else 0
            attendance_stats.append({
                "subject": t.subject,
                "attended": attended,
                "total": total,
                "percentage": round(percentage, 2)
            })

    latest_attendance = Attendance.query.order_by(Attendance.id.desc()).first()

    return render_template("hod.html",
                           calendar_data=calendar_data,
                           students=students,
                           selected_student=selected_student,
                           attendance_stats=attendance_stats,
                           latest_attendance_id=latest_attendance.id if latest_attendance else 0,
                           latest_attendance_name=latest_attendance.student.name if latest_attendance else "")

@app.route("/student/<int:student_id>")
def student_dashboard(student_id):
    student = User.query.get(student_id)
    all_subjects = Timetable.query.all()
    attendance_data = []


    # Current date information
    current_date = datetime.now()
    current_month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_end = (current_month_start.replace(month=current_month_start.month % 12 + 1, day=1) - timedelta(days=1)) if current_month_start.month < 12 else current_month_start.replace(year=current_month_start.year + 1, month=1, day=1) - timedelta(days=1)
    
    # Weekly attendance data
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    week_start = current_date - timedelta(days=current_date.weekday())
    week_end = week_start + timedelta(days=6)
    
    weekly_attendance = {day: False for day in days_of_week}
    streak_data = {
        "current_streak": 0,
        "best_streak": 0
    }
    
    # Calculate monthly attendance
    monthly_stats = {
        "total_classes": 0,
        "attended_classes": 0
    }

    attendance_data = []
    unique_subjects = set()
    for t in all_subjects:
        if t.subject not in unique_subjects:
            total = Attendance.query.filter_by(faculty_id=t.faculty_id, subject=t.subject).count()
            attended = Attendance.query.filter_by(student_id=student.id, subject=t.subject).count()
            percentage = (attended / total * 100) if total > 0 else 0
            attendance_data.append({
                "subject": t.subject,
                "attended": attended,
                "total": total,
                "percentage": round(percentage, 2)
            })
            unique_subjects.add(t.subject)
    total_attended = sum(row['attended'] for row in attendance_data)
    total_classes = sum(row['total'] for row in attendance_data)
    student.overall_attendance = round((total_attended / total_classes * 100), 2) if total_classes > 0 else 0

    unique_subjects = [row['subject'] for row in attendance_data]
    percentages = [row['percentage'] for row in attendance_data]



    # Process subject-wise attendance data
    for t in all_subjects:
        total = Attendance.query.filter_by(faculty_id=t.faculty_id, subject=t.subject).count()
        attended = Attendance.query.filter_by(student_id=student.id, subject=t.subject).count()
        percentage = (attended / total * 100) if total > 0 else 0
        
        # Get monthly stats for this subject
        month_total = Attendance.query.filter(
            Attendance.faculty_id == t.faculty_id,
            Attendance.subject == t.subject,
            Attendance.timestamp >= current_month_start,
            Attendance.timestamp <= current_month_end
        ).count()
        
        month_attended = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.subject == t.subject,
            Attendance.timestamp >= current_month_start,
            Attendance.timestamp <= current_month_end
        ).count()
        
        monthly_stats["total_classes"] += month_total
        monthly_stats["attended_classes"] += month_attended
        
        attendance_data.append({
            "subject": t.subject,
            "attended": attended,
            "total": total,
            "percentage": round(percentage, 2)
        })
    
    # Calculate weekly streak info
    for i, day in enumerate(days_of_week):
        day_date = week_start + timedelta(days=i)
        
        # Check if student attended any class on this day
        day_attendance = Attendance.query.filter(
            Attendance.student_id == student.id,
            func.date(Attendance.timestamp) == day_date.date()
        ).first()
        
        if day_attendance:
            weekly_attendance[day] = True
    
    # Calculate streaks (this is simplified - a more complex algorithm would track historical data)
    consecutive_days = 0
    max_streak = 0
    
    for day in days_of_week:
        if weekly_attendance[day]:
            consecutive_days += 1
            max_streak = max(max_streak, consecutive_days)
        else:
            consecutive_days = 0
    
    streak_data["current_streak"] = consecutive_days
    streak_data["best_streak"] = max_streak  # In a real app, this would be from historical data
    
    # Fetch attendance calendar events
    calendar_events = []
    
    # Get all attendance records for this student in the past month
    month_records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.timestamp >= current_date - timedelta(days=30),
        Attendance.timestamp <= current_date
    ).all()
    
    for record in month_records:
        calendar_events.append({
            "title": record.subject,
            "date": record.timestamp.strftime('%Y-%m-%d'),
            "color": "#4ade80"
        })
    
    # Get historical monthly trends (in a real app, would calculate from actual data)
    monthly_trends = [
        {"month": "Jan", "percentage": 65},
        {"month": "Feb", "percentage": 78},
        {"month": "Mar", "percentage": 80},
        {"month": "Apr", "percentage": 74},
        {"month": "May", "percentage": sum(a["percentage"] for a in attendance_data) / len(attendance_data) if attendance_data else 0}
    ]
    monthly_attendance = {
    "attended": monthly_stats["attended_classes"],
    "total": monthly_stats["total_classes"],
    "percentage": (monthly_stats["attended_classes"] / monthly_stats["total_classes"] * 100) if monthly_stats["total_classes"] > 0 else 0
}

    return render_template(
        "student_dashboard.html", 
        student=student, 
        attendance_data=attendance_data,
        weekly_attendance=weekly_attendance,
        streak_data=streak_data,
        monthly_stats=monthly_stats,
        monthly_attendance=monthly_attendance,
        calendar_events=calendar_events,
        monthly_trends=monthly_trends
    )

from flask import Response

@app.route('/updates')
def sse_updates():
    def event_stream():
        while True:
            # Implement your actual update detection logic here
            # This is a simplified example
            latest = Attendance.query.order_by(Attendance.id.desc()).first()
            if latest:
                yield f"data: {json.dumps({
                    'message': f'Attendance marked for {latest.student_rel.name}',
                    'student': latest.student_rel.name,
                    'subject': latest.subject
                })}\n\n"
            time.sleep(1)
    
    return Response(event_stream(), mimetype="text/event-stream")

from datetime import datetime

@app.route('/get_attendance_events')
def get_attendance_events():
    start = request.args.get('start')
    end = request.args.get('end')
    
    events = []
    attendances = Attendance.query.filter(
        Attendance.timestamp >= start,
        Attendance.timestamp <= end
    ).all()

    for att in attendances:
        events.append({
            'title': f'{att.student_rel.name} - {att.subject}',
            'start': att.timestamp.isoformat(),
            'color': '#3B82F6' if att.status == 'present' else '#EF4444'
        })
    
    return jsonify(events)

@app.route('/get_attendance_details')
def get_attendance_details():
    date = request.args.get('date')
    details = []
    
    attendances = Attendance.query.filter(
        func.date(Attendance.timestamp) == date
    ).all()

    for att in attendances:
        details.append(f"{att.timestamp.strftime('%H:%M')} - {att.student_rel.name}: {att.subject}")
    
    return jsonify(details)

from datetime import datetime, timedelta

@app.route('/previous_day_attendance')
def previous_day_attendance():
    # Get previous day's date
    previous_day = datetime.utcnow() - timedelta(days=1)
    start_date = previous_day.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    # Get all students
    students = User.query.filter_by(role='student').all()
    
    attendance_data = {
        'students': [],
        'total_present': 0,
        'total_absent': 0
    }

    for student in students:
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.timestamp >= start_date,
            Attendance.timestamp < end_date
        ).count()

        attendance_data['students'].append({
            'name': student.name,
            'present': present,
            'absent': 1 - present  # Assuming one class per day
        })
        
        attendance_data['total_present'] += present
        attendance_data['total_absent'] += (1 - present)

    return jsonify(attendance_data)

@app.route('/api/update_class', methods=['POST'])
def update_class():
    data = request.json
    timetable_id = data.get('timetable_id')
    action = data.get('action')
    new_start_time = data.get('new_start_time')
    new_end_time = data.get('new_end_time')

    timetable_entry = Timetable.query.get(timetable_id)
    if not timetable_entry:
        return jsonify({"status": "error", "message": "Invalid timetable ID"}), 400

    if action == 'shift':
        # Update the start and end time
        timetable_entry.start_time = datetime.strptime(new_start_time, "%H:%M").time()
        timetable_entry.end_time = datetime.strptime(new_end_time, "%H:%M").time()
        timetable_entry.status = 'shifted'
    elif action == 'cancel':
        timetable_entry.status = 'canceled'

    db.session.commit()

    # Send SMS Notifications
    students = User.query.filter_by(role='student').all()
    for student in students:
        try:
            message_body = (
                f"The class for {timetable_entry.subject} on {timetable_entry.day} has been "
                f"{action} to {new_start_time} - {new_end_time}."
                if action == 'shift' else f"The class for {timetable_entry.subject} on {timetable_entry.day} has been canceled."
            )
            client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER_W,
                to=student.parent_no
            )
        except Exception as e:
            print(f"Failed to send SMS to {student.name}: {e}")

    return jsonify({"status": "success", "message": f"Class {action}ed successfully"}), 200


@app.route('/api/update_slot', methods=['POST'])
def update_slot():
    data = request.json
    timetable_id = data.get('timetable_id')
    new_slot_id = data.get('new_slot_id')

    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return jsonify({"status": "error", "message": "Invalid timetable ID"}), 400

    new_slot = Slot.query.get(new_slot_id)
    if not new_slot:
        return jsonify({"status": "error", "message": "Invalid slot ID"}), 400

    # Update the slot
    timetable.slot_id = new_slot_id
    db.session.commit()

    # Notify stakeholders
    students = User.query.filter_by(role='student').all()
    for student in students:
        try:
            client.messages.create(
                body=f"The class for {timetable.subject} on {timetable.day} has been moved to "
                     f"{new_slot.start_time.strftime('%H:%M')} - {new_slot.end_time.strftime('%H:%M')}.",
                from_=TWILIO_PHONE_NUMBER_W,
                to=student.parent_no
            )
        except Exception as e:
            print(f"SMS to {student.name} failed: {e}")

    return jsonify({"status": "success", "message": "Slot updated successfully"}), 200


@app.route('/api/allocate_slot', methods=['POST'])
def allocate_slot():
    data = request.json
    faculty_id = data.get('faculty_id')
    slot_id = data.get('slot_id')
    subject = data.get('subject') or "New Subject"
    day = data.get('day') or datetime.today().strftime('%A')

    slot = Slot.query.get(slot_id)
    if not slot:
        return jsonify({"status": "error", "message": "Invalid slot ID"}), 400

    timetable_entry = Timetable.query.filter_by(faculty_id=faculty_id, subject=subject, day=day).first()

    if timetable_entry:
        if timetable_entry.slot_id != slot_id:
            conflict_entry = Timetable.query.filter_by(slot_id=slot_id, day=day).first()
            if conflict_entry and conflict_entry.id != timetable_entry.id:
                return jsonify({"status": "error", "message": "That slot is already occupied by another class."}), 400
            timetable_entry.slot_id = slot_id
            timetable_entry.start_time = slot.start_time
            timetable_entry.end_time = slot.end_time
            db.session.commit()
            return jsonify({"status": "success", "message": "Slot updated successfully!"}), 200
        return jsonify({"status": "info", "message": "Subject already scheduled in this slot."}), 200

    conflict_entry = Timetable.query.filter_by(slot_id=slot_id, day=day).first()
    if conflict_entry:
        return jsonify({"status": "error", "message": "That slot is already occupied by another class."}), 400

    new_entry = Timetable(
        faculty_id=faculty_id,
        slot_id=slot_id,
        day=day,
        subject=subject,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status="scheduled"
    )
    db.session.add(new_entry)
    db.session.commit()

    faculty = User.query.get(faculty_id)
    message_body = (
        f"\u2709 New Class Scheduled:\nSubject: {subject}\nDay: {day}\nTime: {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}\nBy: {faculty.name}"
    )

    recipients = User.query.filter(User.id != faculty_id, User.role.in_(['faculty', 'student'])).all()
    for user in recipients:
        if user.Phno:
            try:
                client.messages.create(
                    body=message_body,
                    from_=TWILIO_PHONE_NUMBER,
                    to=user.Phno
                )
            except Exception as e:
                print(f"SMS to {user.name} failed: {e}")

    return jsonify({"status": "success", "message": "Slot allocated successfully!"}), 200


@app.route('/cancel_slot', methods=['POST'])
def cancel_slot():
    data = request.json
    slot_id = data.get('slot_id')
    day = data.get('day')
    faculty_id = data.get('faculty_id')

    timetable_entry = Timetable.query.filter_by(slot_id=slot_id, day=day, faculty_id=faculty_id).first()
    if timetable_entry:
        subject = timetable_entry.subject
        faculty = User.query.get(faculty_id)

        db.session.delete(timetable_entry)
        db.session.commit()

        message_body = (
            f"\u274C Class Canceled:\nSubject: {subject}\nDay: {day}\nPreviously by: {faculty.name}"
        )

        recipients = User.query.filter(User.id != faculty_id, User.role.in_(['faculty', 'student'])).all()
        for user in recipients:
            if user.Phno:
                try:
                    client.messages.create(
                        body=message_body,
                        from_=TWILIO_PHONE_NUMBER,
                        to=user.Phno
                    )
                except Exception as e:
                    print(f"SMS to {user.name} failed: {e}")

        return jsonify({'success': True, 'message': 'Slot cancelled successfully'})

    return jsonify({'success': False, 'message': 'Timetable entry not found'})



@app.route('/api/extra_class', methods=['POST'])
def add_extra_class():
    data = request.json
    faculty_id = data.get('faculty_id')
    slot_id = data.get('slot_id')
    subject = data.get('subject')
    day = data.get('day')

    slot = Slot.query.get(slot_id)
    if not slot:
        return jsonify({"status": "error", "message": "Invalid slot ID"}), 400

    # Check if there's already a class in that slot and day
    existing = Timetable.query.filter_by(slot_id=slot_id, day=day).first()
    if existing:
        return jsonify({"status": "error", "message": "Slot is already occupied."}), 400

    # Add the extra class
    new_class = Timetable(
        faculty_id=faculty_id,
        slot_id=slot_id,
        subject=subject,
        day=day,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status='extra'
    )
    db.session.add(new_class)
    db.session.commit()

    return jsonify({"status": "success", "message": "Extra class scheduled successfully."}), 200

from flask import jsonify, send_file
import pandas as pd
from io import BytesIO

@app.route('/api/faculty_attendance_summary')
def faculty_attendance_summary():
    # Get faculty_id from URL parameter instead of JSON body
    faculty_id = request.args.get('faculty_id')
    
    # If no faculty_id is provided, return sample data for demonstration
    if not faculty_id:
        return jsonify({
            "Programming": 24,
            "Data Structures": 18,
            "Algorithms": 15,
            "Web Development": 21
        })
        
    records = Attendance.query.filter_by(faculty_id=faculty_id).all()

    # Group by subject
    summary = {}
    for record in records:
        subj = record.subject
        summary[subj] = summary.get(subj, 0) + 1

    return jsonify(summary)

@app.route('/api/faculty_attendance_report/download')
def download_attendance_report():
    # Get faculty_id from URL parameter instead of JSON body
    faculty_id = request.args.get('faculty_id')
    
    # If no faculty_id provided, use the one from the session or a default
    if not faculty_id and 'faculty_id' in request.cookies:
        faculty_id = request.cookies.get('faculty_id')
    
    # Include proper error handling
    if not faculty_id:
        # For demo, create sample data if no faculty ID
        data = [
            {"Student Name": "John Doe", "Subject": "Programming", "Date": "2025-05-01", "Time": "10:30:00", "Day": "Monday"},
            {"Student Name": "Jane Smith", "Subject": "Data Structures", "Date": "2025-05-02", "Time": "11:45:00", "Day": "Tuesday"},
            {"Student Name": "Alex Johnson", "Subject": "Algorithms", "Date": "2025-05-03", "Time": "09:15:00", "Day": "Wednesday"},
        ]
    else:
        try:
            records = Attendance.query.filter_by(faculty_id=faculty_id).all()
            data = [{
                "Student Name": record.student.name,
                "Subject": record.subject,
                "Date": record.timestamp.strftime("%Y-%m-%d"),
                "Time": record.timestamp.strftime("%H:%M:%S"),
                "Day": record.day
            } for record in records]
        except Exception as e:
            # Log the error for debugging
            print(f"Error generating report: {e}")
            return jsonify({"error": "Failed to generate report"}), 500

    # Generate the Excel file
    try:
        df = pd.DataFrame(data)
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(output, 
                        download_name="faculty_attendance_report.xlsx", 
                        as_attachment=True,
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        print(f"Error creating Excel file: {e}")
        return jsonify({"error": "Failed to create Excel file"}), 500
''' 

def send_eod_summary():
    # Get all students
    students = User.query.filter_by(role="student").all()

    # Get today's date
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Attendance summary
    for student in students:
        total_classes = Attendance.query.filter(
            Attendance.timestamp >= today_start,
            Attendance.timestamp < today_end
        ).count()
        attended_classes = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.timestamp >= today_start,
            Attendance.timestamp < today_end
        ).count()

        if student.parent_no:
            attendance_percentage = (attended_classes / total_classes * 100) if total_classes > 0 else 0
            try:
                message_body = (
                    f"Dear Parent, here is today's summary for your child {student.name}:\n"
                    f"- Total Classes: {total_classes}\n"
                    f"- Classes Attended: {attended_classes}\n"
                    f"- Attendance: {attendance_percentage:.2f}%"
                )
                client.messages.create(
                    body=message_body,
                    from_=TWILIO_PHONE_NUMBER,
                    to=student.parent_no
                )
            except Exception as e:
                print(f"Failed to send EOD summary to {student.name}'s parent: {e}")

'''


if __name__ == '__main__':
    app.run()
