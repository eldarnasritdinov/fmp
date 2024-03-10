from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, DateTimeField, TextAreaField, SelectField
from wtforms.validators import DataRequired, EqualTo, Length
from wtforms.widgets import TextArea
from flask_ckeditor import CKEditorField
from flask_wtf.file import FileField


# Create a search form
class SearchForm(FlaskForm):
    searched = StringField('Searched', validators=[DataRequired()])
    submit = SubmitField('Submit')


# Create Login Form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


# Create a Posts Form
class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    # content = StringField('Content', validators=[DataRequired()], widget=TextArea())
    content = CKEditorField('Content', validators=[DataRequired()])
    slug = StringField('Slug', validators=[DataRequired()])
    submit = SubmitField('Submit')


# Create a Form Class - User
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    sex = StringField("Gender")
    about = TextAreaField("About author")
    profile_pic = FileField('Profile Picture')
    password_hash = PasswordField('Password', validators=[DataRequired(), EqualTo('password_hash2',                                                                   message='Passwords Must Match!')])
    password_hash2 = PasswordField('Confirm Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('regular', 'Regular'), ('organizer', 'Organizer')], validators=[DataRequired()])  # Add role field
    language = SelectField('Language', choices=[('ENG', 'English'), ('RU', 'Русский'), ('KG', 'Кыргызча')], validators=[DataRequired()])  # Added language selection
    submit = SubmitField('Sumbit')


# Create a Form Class - News
class NewsForm(FlaskForm):
    name = StringField('Enter news headline', validators=[DataRequired()])
    description = StringField('Enter news description', validators=[DataRequired()])
    submit = SubmitField('Sumbit')