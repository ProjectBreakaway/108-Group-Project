from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer,   primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role          = db.Column(db.String(20), nullable=False)  # 'admin','teacher','student'

    # relationships
    enrollments    = db.relationship('Enrollment', back_populates='student')
    taught_courses = db.relationship('Course', back_populates='teacher',
                                     foreign_keys='Course.teacher_id')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Course(db.Model):
    __tablename__ = 'courses'
    id         = db.Column(db.Integer,   primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    capacity   = db.Column(db.Integer,    nullable=False)
    teacher_id = db.Column(db.Integer,    db.ForeignKey('users.id'), nullable=False)

    teacher     = db.relationship('User', back_populates='taught_courses')
    enrollments = db.relationship('Enrollment', back_populates='course')

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id  = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    grade      = db.Column(db.Float,   nullable=True)

    student = db.relationship('User',   back_populates='enrollments')
    course  = db.relationship('Course', back_populates='enrollments')
