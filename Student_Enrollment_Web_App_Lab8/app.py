import os
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for,
    flash, request, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_admin import Admin
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView

from forms import LoginForm, AdminUserForm
from models import db, User, Course, Enrollment

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "devkey"),
    SQLALCHEMY_DATABASE_URI="sqlite:///grades.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db.init_app(app)

# ─── Flask‑Login setup ─────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


def admin_required(f):
    """Decorator: abort(404) unless current_user is admin."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(404)
        return f(*args, **kwargs)
    return wrapped


# ─── Flask‑Admin for Course & Enrollment ───────────────────────────────────────
class SecureModelView(ModelView):
    def is_accessible(self):
        return (
            current_user.is_authenticated and
            current_user.role == "admin"
        )


class CourseAdmin(SecureModelView):
    column_list  = ["id", "name", "capacity", "teacher.username"]
    form_columns = ["name", "capacity", "teacher_id"]


class EnrollmentAdmin(SecureModelView):
    column_list  = ["id", "student.username", "course.name", "grade"]
    form_columns = ["student_id", "course_id", "grade"]


admin = Admin(app, name="University Admin", template_mode="bootstrap4")
admin.add_view(CourseAdmin(Course, db.session))
admin.add_view(EnrollmentAdmin(Enrollment, db.session))

# New “Users” link in the sidebar
admin.add_link(MenuLink(name="Users", url="/admin/users"))
# Logout link
admin.add_link(MenuLink(name="Logout", url="/logout"))


# ─── Authentication routes ────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Welcome, {user.username}", "success")
            return redirect(url_for("home"))
        flash("Invalid username or password", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return render_template("logged_out.html")


@app.route("/")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if current_user.role == "admin":
        return redirect("/admin")
    if current_user.role == "teacher":
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("student_dashboard"))


# ─── Custom Admin User CRUD ───────────────────────────────────────────────────
@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.id).all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def admin_create_user():
    form = AdminUserForm()
    if form.validate_on_submit():
        u = User(username=form.username.data, role=form.role.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("admin_users"))
    return render_template("admin_user_form.html", form=form, action="Create")


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_user(user_id):
    u = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=u)
    if form.validate_on_submit():
        u.username = form.username.data
        u.role = form.role.data
        if form.password.data:
            u.set_password(form.password.data)
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin_users"))
    return render_template("admin_user_form.html", form=form, action="Edit")


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id):
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin_users"))


# ─── Student routes ───────────────────────────────────────────────────────────
@app.route("/student")
@login_required
def student_dashboard():
    if current_user.role != "student":
        return redirect(url_for("home"))
    return render_template(
        "student_dashboard.html",
        enrolled=current_user.enrollments,
        all_courses=Course.query.all()
    )


@app.route("/student/enroll/<int:course_id>")
@login_required
def student_enroll(course_id):
    if current_user.role != "student":
        return redirect(url_for("home"))
    course = Course.query.get_or_404(course_id)
    if len(course.enrollments) >= course.capacity:
        flash("Class full.", "warning")
    else:
        db.session.add(Enrollment(
            student_id=current_user.id,
            course_id=course.id
        ))
        db.session.commit()
        flash(f"Enrolled in {course.name}", "success")
    return redirect(url_for("student_dashboard"))


# ─── Teacher routes ───────────────────────────────────────────────────────────
@app.route("/teacher")
@login_required
def teacher_dashboard():
    if current_user.role != "teacher":
        return redirect(url_for("home"))
    return render_template(
        "teacher_dashboard.html",
        courses=current_user.taught_courses
    )


@app.route("/teacher/course/<int:course_id>", methods=["GET", "POST"])
@login_required
def teacher_course(course_id):
    if current_user.role != "teacher":
        return redirect(url_for("home"))
    course = Course.query.get_or_404(course_id)
    if course.teacher_id != current_user.id:
        flash("Not your class.", "danger")
        return redirect(url_for("teacher_dashboard"))

    if request.method == "POST":
        for enr in course.enrollments:
            g = request.form.get(f"grade_{enr.id}")
            if g is not None:
                enr.grade = float(g)
        db.session.commit()
        flash("Grades updated.", "success")

    return render_template("teacher_course.html", course=course)


# ─── Database setup helper ────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="admin").first():
            a = User(username="admin", role="admin")
            a.set_password("adminpass")
            db.session.add(a)
            db.session.commit()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
