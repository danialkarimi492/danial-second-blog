from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


class RegisterForm(FlaskForm):
    name = StringField(label='Name', validators=[DataRequired()])
    email = StringField(label='Email', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField(label='Email', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class CreatePostForm(FlaskForm):
    title = StringField(label='Title', validators=[DataRequired()])
    subtitle = StringField(label='subtitle', validators=[DataRequired()])
    img_url = StringField(label='Image URL', validators=[DataRequired(), URL()])
    body = CKEditorField(label='Blog content', validators=[DataRequired()])
    submit = SubmitField('Submit Post')


class CommentForm(FlaskForm):
    comment = CKEditorField(label='Comment', validators=[DataRequired()])
    submit = SubmitField('Comment')


