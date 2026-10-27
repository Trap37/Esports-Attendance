from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class StudentRegistrationForm(FlaskForm):
    full_name = StringField(
        'Full Name',
        description='John Doe',
        validators=[DataRequired(), Length(max=128)],
    )
    csu_id = StringField(
        'CSU ID',
        description='12345678',
        validators=[DataRequired(), Length(max=8)],
    )
    scan_id = StringField(
        'Scan ID',
        description='5 Digit number on the back of ID',
        validators=[DataRequired(), Length(max=8)],
    )
    major = StringField(
        'Major',
        description='Computer Science',
        validators=[DataRequired(), Length(max=64)],
    )
    grade_level = SelectField(
        'Year',
        description='Freshman, Sophomore, etc.',
        choices=[
            # ('', '-- Select year (optional) --'),
            ('Freshman', 'Freshman'),
            ('Sophomore', 'Sophomore'),
            ('Junior', 'Junior'),
            ('Senior', 'Senior'),
            ('Graduate', 'Graduate'),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField('Register')
