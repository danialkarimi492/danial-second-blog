from flask import Flask, render_template, request, redirect, url_for, abort, flash
from flask_bootstrap import Bootstrap
from forms import RegisterForm, LoginForm, CreatePostForm, CommentForm
from flask_sqlalchemy import SQLAlchemy
import smtplib
import requests
from flask_ckeditor import CKEditor
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from functools import wraps
from flask_gravatar import Gravatar
import os

themealdb_endpoint = "https://www.themealdb.com/api/json/v1/1/search.php"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False,
                    force_lower=False, use_ssl=False, base_url=None)


# Connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///foods-collection.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    posts = relationship('BlogPost', back_populates='author')
    comments = relationship('Comment', back_populates='comment_author')


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship('User', back_populates='posts')

    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = relationship('Comment', back_populates='parent_post')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment_author = relationship('User', back_populates='comments')

    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    parent_post = relationship('BlogPost', back_populates='comments')


db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    return render_template('contact.html', msg=False)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        name_of_meal = request.form['mealName']
        parameter = {
            "s": name_of_meal
        }
        response = requests.get(url=themealdb_endpoint, params=parameter)
        try:
            meal = response.json()['meals'][0]
        except TypeError:
            pass
        else:
            print(meal['strMealThumb'])
            return render_template('search.html', meal=meal, found=True)
    return render_template('search.html', found=False)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            flash("You've already signed up. Login instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hash_and_salted_password
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('all_posts'))
    return render_template('register.html', current_user=current_user, form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("That email doesn't exist. Please try again.")
            return redirect(url_for('login'))
        if not check_password_hash(user.password, password):
            flash("Password incorrect. Please try again.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('all_posts'))
    return render_template('login.html', current_user=current_user, form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('all_posts'))


@app.route('/posts')
def all_posts():
    posts = BlogPost.query.all()
    return render_template('posts.html', posts=posts, current_user=current_user)


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    requested_post_comments = Comment.query.filter_by(post_id=post_id).all()
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for('login'))
        comment_text = form.comment.data
        new_comment = Comment(
            text=comment_text,
            comment_author=current_user,
            parent_post=requested_post
        )

        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))

    return render_template('post.html', post=requested_post,comments=requested_post_comments,
                           form=form, current_user=current_user)


@app.route('/new-post', methods=['GET', 'POST'])
@admin_only
def add_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            img_url=form.img_url.data,
            body=form.body.data,
            date=date.today().strftime('%B %d, %Y'),
            author_id=current_user.id
        )

        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('all_posts'))
    return render_template('make-post.html', current_user=current_user,
                           form=form, is_edit=False)


@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CreatePostForm(
        title=requested_post.title,
        subtitle=requested_post.subtitle,
        body=requested_post.body,
        img_url=requested_post.img_url,
    )
    if form.validate_on_submit():
        requested_post.title = form.title.data
        requested_post.subtitle = form.subtitle.data
        requested_post.img_url = form.img_url.data
        requested_post.body = form.body.data

        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template('make-post.html', current_user=current_user,
                           form=form, is_edit=True)


@app.route('/delete/<int:post_id>')
@admin_only
def delete(post_id):
    requested_post = BlogPost.query.get(post_id)
    db.session.delete(requested_post)
    db.session.commit()
    return redirect(url_for('all_posts'))


@app.route('/about-me')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
