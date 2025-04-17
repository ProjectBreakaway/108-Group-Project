# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField(
        "Username", 
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    password = PasswordField(
        "Password", 
        validators=[DataRequired(), Length(min=6)]
    )
    submit = SubmitField("Sign In")


class AdminUserForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    role = SelectField(
        "Role",
        choices=[
            ("student", "Student"),
            ("teacher", "Teacher"),
            ("admin", "Admin")
        ],
        validators=[DataRequired()]
    )
    # For create/edit: on edit you may leave blank to keep existing
    password = PasswordField(
        "Password",
        description="(leave blank to keep current password)"
    )
    submit = SubmitField("Save")
    