from flask import (
    Flask, render_template, redirect,
    url_for, flash, request
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from wtforms.fields import PasswordField

from models import db, User, Course, Enrollment
from forms import LoginForm

app = Flask(__name__)
app.config.update(
    SECRET_KEY='replace-with-a-secure-key',
    SQLALCHEMY_DATABASE_URI='sqlite:///grades.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
db.init_app(app)

# Flask‑Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'
@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))

# Always send “/” to login
@app.route('/')
def home():
    if current_user.is_authenticated:
        # redirect by role
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        if current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        return redirect('/admin')
    return redirect(url_for('login'))

# Flask‑Admin security
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

# Admin: Users
class UserAdmin(SecureModelView):
    column_list = ['id','username','role']
    form_excluded_columns = ['password_hash','enrollments','taught_courses']
    form_extra_fields = {
        'password': PasswordField('Password')
    }
    def on_model_change(self, form, model, is_created):
        if form.password.data:
            model.set_password(form.password.data)

# Admin: Courses
class CourseAdmin(SecureModelView):
    column_list = ['id','name','capacity','teacher.username']
    form_columns = ['name','capacity','teacher_id']

# Admin: Enrollments
class EnrollmentAdmin(SecureModelView):
    column_list = ['id','student.username','course.name','grade']
    form_columns = ['student_id','course_id','grade']

# Mount admin
admin = Admin(app, name='University Admin', template_mode='bootstrap4')
admin.add_view(UserAdmin(User, db.session))
admin.add_view(CourseAdmin(Course, db.session))
admin.add_view(EnrollmentAdmin(Enrollment, db.session))

# --- Auth routes ---

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(username=form.username.data).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            flash(f'Welcome, {u.username}', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logged_out.html')

# --- Student views ---

@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    return render_template(
        'student_dashboard.html',
        enrolled=current_user.enrollments,
        all_courses=Course.query.all()
    )

@app.route('/student/enroll/<int:cid>')
@login_required
def enroll_course(cid):
    if current_user.role != 'student':
        return redirect(url_for('login'))
    c = Course.query.get_or_404(cid)
    if len(c.enrollments) >= c.capacity:
        flash('Course is full', 'warning')
    else:
        db.session.add(Enrollment(student_id=current_user.id, course_id=cid))
        db.session.commit()
        flash(f'Enrolled in {c.name}', 'success')
    return redirect(url_for('student_dashboard'))

# --- Teacher views ---

@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('login'))
    return render_template(
        'teacher_dashboard.html',
        courses=current_user.taught_courses
    )

@app.route('/teacher/course/<int:cid>', methods=['GET','POST'])
@login_required
def teacher_course(cid):
    if current_user.role != 'teacher':
        return redirect(url_for('login'))
    c = Course.query.get_or_404(cid)
    if c.teacher_id != current_user.id:
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        for e in c.enrollments:
            g = request.form.get(f'grade_{e.id}')
            if g is not None:
                e.grade = float(g)
        db.session.commit()
        flash('Grades updated', 'success')

    return render_template('teacher_course.html', course=c)

# Initialize DB + default admin
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role='admin').first():
            a = User(username='admin', role='admin')
            a.set_password('adminpass')
            db.session.add(a)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
