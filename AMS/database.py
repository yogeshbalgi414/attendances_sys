# database.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))  # student, faculty, hod
    rfid = db.Column(db.String(100), unique=True)

class Timetable(db.Model):
    __tablename__ = 'timetable'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(100))
    day = db.Column(db.String(20))  # Monday, Tuesday...
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
