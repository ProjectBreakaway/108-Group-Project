from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id            = db.Column(db.Integer,   primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role          = db.Column(db.String(10), nullable=False)

    # if a User is deleted, also delete their enrollments & taught courses
    enrollments     = db.relationship(
        "Enrollment",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    taught_courses  = db.relationship(
        "Course",
        back_populates="teacher",
        cascade="all, delete-orphan"
    )

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Course(db.Model):
    __tablename__ = "courses"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    capacity    = db.Column(db.Integer, nullable=False)
    teacher_id  = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    teacher      = db.relationship("User", back_populates="taught_courses")
    enrollments  = db.relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan"
    )


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    course_id   = db.Column(
        db.Integer,
        db.ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    grade       = db.Column(db.Float)

    student     = db.relationship("User",   back_populates="enrollments")
    course      = db.relationship("Course", back_populates="enrollments")
