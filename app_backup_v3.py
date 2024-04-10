from flask import Flask, render_template, flash, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from datetime import date

from webforms import LoginForm, PostForm, UserForm, NewsForm, SearchForm
from flask_ckeditor import CKEditor
from werkzeug.utils import secure_filename
import uuid as uuid
import os
import json

from functools import wraps


app = Flask(__name__)

# Adding rich text editor
ckeditor = CKEditor(app)

# add database
# Old SQLite DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# New MySQL DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:8931172771@localhost/fmp'

# Secret key!
app.config['SECRET_KEY'] = '8931172771'

UPLOAD_FOLDER = 'static/images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize the DataBase
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Flask Login Stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Load translations based on user's selected language
def load_translations(language):
    directory = 'translations'
    filename = f'translations_{language}.json'
    filepath = os.path.join(directory, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except FileNotFoundError:
        # Handle the case where translations file is not found for the given language
        translations = {}
    return translations


# Context processor to add translations to the template context
@app.context_processor
def inject_translations():
    user_language = getattr(request, 'user_language', 'ru')  # Default language is Russian
    translations = load_translations(user_language)
    return dict(translations=translations)


# Decorator to check if the user is an organizer
def organizer_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.role == 'organizer':
            return f(*args, **kwargs)
        else:
            flash("You are not authorized to access this page.")
            return redirect(url_for('dashboard'))  # Redirect to the home page or any other page you prefer
    return decorated_function


# Decorator to check if the user is the poster or an organizer
def can_edit_post(f):
    @wraps(f)
    def decorated_function(id, *args, **kwargs):
        post = Posts.query.get_or_404(id)
        if current_user.is_authenticated and (current_user.id == post.poster_id or current_user.role == 'organizer'):
            return f(id, *args, **kwargs)
        else:
            flash("You are not authorized to edit this post.")
            return redirect(url_for('dashboard'))  # Redirect to the posts page or any other page you prefer
    return decorated_function


# Decorator to check if the user is the poster or an organizer
def can_delete_post(f):
    @wraps(f)
    def decorated_function(id, *args, **kwargs):
        post = Posts.query.get_or_404(id)
        if current_user.is_authenticated and (current_user.id == post.poster_id or current_user.role == 'organizer'):
            return f(id, *args, **kwargs)
        else:
            flash("You are not authorized to delete this post.")
            return redirect(url_for('posts'))  # Redirect to the posts page or any other page you prefer
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# Pass Stuff to Navbar
@app.context_processor
def base():
    form = SearchForm()
    return dict(form=form)


# Create Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            # check the hash
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash('Login Successful')
                return redirect(url_for('dashboard'))
            else:
                flash('Wrong password - try again')
        else:
            flash('That username doesn\'t exist')

    user_language = 'ru'  # Default language is Russian when user is not logged in
    translations = load_translations(user_language)

    return render_template('login.html', form=form, translations=translations)


# Create Logout Page
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You are now logged out')
    return redirect(url_for('login'))


# Create Dashboard Page
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_language = current_user.language  # Assuming you have access to the user's selected language
    translations = load_translations(user_language)
    return render_template('dashboard.html', translations=translations)


@app.route('/posts')
def posts():

    posts = Posts.query.order_by(Posts.date_posted)

    if current_user.is_authenticated:
        user_language = current_user.language  # Assuming you have access to the user's selected language
        translations = load_translations(user_language)

        return render_template('posts.html', posts=posts, translations=translations)

    else:
        user_language = 'ru'  # Default language is Russian when user is not logged in
        translations = load_translations(user_language)

        return render_template('posts.html', posts=posts, translations=translations)


@app.route('/posts/<int:id>')
def post(id):

    if current_user.is_authenticated:
        user_language = current_user.language  # Assuming you have access to the user's selected language
        translations = load_translations(user_language)
        post = Posts.query.get_or_404(id)

        return render_template('post.html', post=post, translations=translations)

    else:
        user_language = 'ru'  # Default language is Russian when user is not logged in
        translations = load_translations(user_language)

        post = Posts.query.get_or_404(id)
        return render_template('post.html', post=post, translations=translations)


@app.route('/posts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@can_edit_post
def edit_post(id):
    post = Posts.query.get_or_404(id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.slug = form.slug.data
        post.content = form.content.data

        # Update Database
        db.session.add(post)
        db.session.commit()

        flash("Post has been updated")
        return redirect(url_for('post', id=post.id))

    if current_user.id == post.poster_id or current_user.id == 20:

        form.title.data = post.title
        form.slug.data = post.slug
        form.content.data = post.content

        user_language = current_user.language  # Assuming you have access to the user's selected language
        translations = load_translations(user_language)

        return render_template('edit_post.html', form=form, translations=translations)
    else:
        flash('You are not allowed to edit other posts')
        posts = Posts.query.order_by(Posts.date_posted)
        return render_template('posts.html', posts=posts)


@app.route('/posts/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@can_delete_post
def delete_post(id):
    post_to_delete = Posts.query.get_or_404(id)
    id = current_user.id
    if id == post_to_delete.poster.id or id == 20:

        try:
            db.session.delete(post_to_delete)
            db.session.commit()

            flash('Blog Post was deleted')

            # Grab and return all the posts from the database
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template('posts.html', posts=posts)

        except:
            flash('A shit, there was a problem deleting the post, try again')

            # Grab and return all the posts from the database
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template('posts.html', posts=posts)

    else:
        flash('You are not allowed to delete other posts')

        # Grab and return all the posts from the database
        posts = Posts.query.order_by(Posts.date_posted)
        return render_template('posts.html', posts=posts)


# add Post Page
@app.route('/add_post', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
@organizer_required  # Ensure the user is an organizer
def add_post():
    form = PostForm()

    user_language = current_user.language  # Assuming you have access to the user's selected language
    translations = load_translations(user_language)

    if form.validate_on_submit():
        poster = current_user.id

        post = Posts(title=form.title.data, content=form.content.data, slug=form.slug.data, poster_id=poster)

        # Clearing the form
        form.title.data = ''
        form.content.data = ''
        form.slug.data = ''

        # Add post data to database
        db.session.add(post)
        db.session.commit()

        flash('Blog Post was submitted successfully')

    # Redirect to the webpage
    return render_template('add_post.html', form=form, translations=translations)


# JSON thing
@app.route('/date')
def get_current_date():
    fav_show = {
        'Eldar': 'Stranger Things',
        'Asyl': 'Naruto',
        'Edil': 'The Walking Dead'
    }
    return fav_show


# Delete Database Record - User
@app.route('/delete/<int:id>')
@login_required
def delete(id):

    if id == current_user.id or current_user.id == 20:

        user_to_delete = Users.query.get_or_404(id)
        name = None
        form = UserForm()

        try:
            db.session.delete(user_to_delete)
            db.session.commit()
            flash('User Deleted Successfully!')

            out_users = Users.query.order_by(Users.date_added)
            return render_template('add_user.html', form=form, name=name, our_users=out_users)

        except:
            flash('Shit! There was a problem deleting user, look at the console error')
            return render_template('add_user.html', form=form, name=name, our_users=out_users)

    else:
        flash('You cannot delete other users')
        return redirect(url_for('dashboard'))


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)

    if request.method == "POST":
        name_to_update.username = request.form['username']
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        name_to_update.sex = request.form['sex']
        name_to_update.about = request.form['about']
        name_to_update.language = request.form['language']

        # Check if a new profile picture is provided
        if 'profile_pic' in request.files:
            profile_pic_file = request.files['profile_pic']
            if profile_pic_file.filename != '':
                pic_filename = secure_filename(profile_pic_file.filename)
                pic_name = str(uuid.uuid1()) + '_' + pic_filename
                name_to_update.profile_pic = pic_name

                try:
                    profile_pic_file.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
                except Exception as e:
                    print(str(e))  # print the error for debugging purposes
                    flash("Error! Failed to save profile picture")
                    return render_template('update.html', form=form, name_to_update=name_to_update, id=id)

        try:
            db.session.commit()
            flash("User Updated Successfully!")
            return render_template('dashboard.html', form=form, name_to_update=name_to_update)
        except Exception as e:
            print(str(e))  # print the error for debugging purposes
            flash("Error! There was a problem updating the user")
            return render_template('update.html', form=form, name_to_update=name_to_update, id=id)

    else:
        return render_template('update.html', form=form, name_to_update=name_to_update, id=id)


@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    name = None
    form = UserForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user is None:
            # Hash the password
            hashed_pw = generate_password_hash(form.password_hash.data, 'pbkdf2')
            user = Users(username=form.username.data, name=form.name.data, email=form.email.data, sex=form.sex.data, password_hash=hashed_pw, role=form.role.data, language=form.language.data)  # Include role information
            db.session.add(user)
            db.session.commit()
        name = form.name.data
        form.username.data = ''
        form.name.data = ''
        form.email.data = ''
        form.sex.data = ''
        form.password_hash = ''
        form.role.data = ''  # Clear role field after submission
        form.language.data = ''  # Clear language field after submission

        flash('User Added Succesfully!')

    user_language = 'ru'  # Default language is Russian when user is not logged in
    translations = load_translations(user_language)

    out_users = Users.query.order_by(Users.date_added)
    return render_template('add_user.html', form=form, name=name, our_users=out_users, translations=translations)


# add News Page
@app.route('/add_news', methods=['GET', 'POST'])
@login_required
@organizer_required  # Ensure the user is an organizer
def add_news():

    user_language = current_user.language  # Assuming you have access to the user's selected language
    translations = load_translations(user_language)
    name = None
    form = NewsForm()

    if form.validate_on_submit():
        news = News.query.filter_by(name=form.name.data).first()
        if news is None:
            news = News(name=form.name.data, description=form.description.data)
            db.session.add(news)
            db.session.commit()
            flash('News Added Successfully!')
            return redirect(url_for('news'))  # Redirect to the news page after adding news
        else:
            flash('News with this name already exists.')
    return render_template('add_news.html', form=form, name=name, translations=translations)


# Create search function
@app.route('/search', methods=['POST'])
def search():
    form = SearchForm()
    posts = Posts.query
    if form.validate_on_submit():

        # Get data from submitted form
        post.searched = form.searched.data

        # Query the database
        posts = posts.filter(Posts.content.like('%' + post.searched + '%'))
        posts = posts.order_by(Posts.title).all()

        return render_template('search.html', form=form, searched=post.searched, posts=posts)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    id = current_user.id
    if id == 20:
        our_users = Users.query.order_by(Users.date_added)
        return render_template('admin.html', our_users=our_users)
    else:
        flash('This page is available only for admins')
        return redirect(url_for('dashboard'))


@app.route('/', methods=['GET', 'POST'])
def index():

    if current_user.is_authenticated:
        user_language = current_user.language  # Assuming you have access to the user's selected language
        translations = load_translations(user_language)
        return render_template('index.html', translations=translations)

    return render_template('index.html')


@app.route('/news', methods=['GET'])
def news():
    news = News.query.order_by(News.date_added)
    if current_user.is_authenticated:
        user_language = current_user.language  # Assuming you have access to the user's selected language
        translations = load_translations(user_language)
        return render_template('news.html', news=news, translations=translations)
    else:
        user_language = 'ru'  # Default language is Russian when user is not logged in
        translations = load_translations(user_language)
        return render_template('news.html', news=news, translations=translations)


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@app.route('/support')
def support():
    if current_user.is_authenticated:
        user_language = current_user.language
    else:
        user_language = 'ru'  # Default language is Russian when user is not logged in
    translations = load_translations(user_language)
    return render_template('support.html', translations=translations)



# Invalid URL
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Internal Sevrer Error
@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500


# Models ---------------------------------------------------------------------------------------------------------------

# Create Model - Blog Posts
class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    slug = db.Column(db.String(255))
    # Foreign key to link users (refer to primary key of the user)
    poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))


# Create Model - Users
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    sex = db.Column(db.String(50))
    language = db.Column(db.String(10))  # Add a column for storing language preference
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    about = db.Column(db.Text(500), nullable=True)
    profile_pic = db.Column(db.String(550), nullable=True)
    # Do some password stuff
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='regular')  # New column for user role
    # user can have many posts
    posts = db.relationship('Posts', backref='poster')

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Crate a string
    def __repr__(self):
        return '<Name %r>' % self.name


# # Create Model - Events
# class Events(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(200), nullable=False)
#     date_added = db.Column(db.DateTime, default=datetime.utcnow)
#     description = db.Column(db.String(1000), nullable=False)
#     # adding event date
#     event_date = db.Column(db.DateTime)
#
#     # Crate a string
#     def __repr__(self):
#         return '<Name %r>' % self.name


# Create Model - News
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Crate a string
    def __repr__(self):
        return '<Name %r>' % self.name

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)