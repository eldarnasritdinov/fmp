from flask import Flask, render_template, flash, request, redirect, url_for, session
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

import smtplib
import ssl


from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from dotenv import load_dotenv
# config = dotenv_values('.env')

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)

# Adding rich text editor
ckeditor = CKEditor(app)

# add database
# Old SQLite DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# New MySQL DB

# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:8931172771@localhost/fmp'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")

# Secret key!
# app.config['SECRET_KEY'] = '8931172771'
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

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
    directory = './static/translations/'
    filename = f'translations_{language}.json'
    filepath = os.path.join(directory, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except FileNotFoundError:
        flash(f"Translations file not found for language '{language}' File path = {filepath}.", 'error')
        # Return an empty dictionary
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


@app.route('/posts', methods=['GET'])
def posts():
    page = request.args.get('page', 1, type=int)
    per_page = 15  # Number of posts per page

    posts = Posts.query.order_by(Posts.date_posted).paginate(page=page, per_page=per_page)

    if current_user.is_authenticated:
        user_language = current_user.language  # Assuming you have access to the user's selected language
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
    if post_to_delete.poster:
        if id == post_to_delete.poster.id or id == 20:
            try:
                db.session.delete(post_to_delete)
                db.session.commit()

                flash('Blog Post was deleted')
                # Redirect to the posts route to display remaining posts
                return redirect(url_for('posts'))

            except Exception as e:
                flash('There was a problem deleting the post: {}'.format(str(e)))
        else:
            flash('You are not allowed to delete posts created by other users')
    else:
        flash('This post cannot be deleted because it has no associated user')

    # Redirect to the posts route in any case
    return redirect(url_for('posts'))


def remove_posts_without_authors():
    # Query posts with no associated user authors
    posts_without_authors = Posts.query.filter_by(poster_id=None).all()

    # Delete posts without authors
    for post in posts_without_authors:
        db.session.delete(post)

    # Commit the changes
    db.session.commit()




# # Add Post Page
# @app.route('/add_post', methods=['GET', 'POST'])
# @login_required  # Ensure the user is logged in
# @organizer_required  # Ensure the user is an organizer
# def add_post():
#     form = PostForm()
#
#     user_language = current_user.language  # Assuming you have access to the user's selected language
#     translations = load_translations(user_language)
#
#     included_users = []  # Initialize included_users as an empty list
#
#     if request.method == 'POST':  # Check if the request method is POST
#
#         if 'searched' in request.form:  # Check if it's a search form submission
#             searched_username = request.form['searched']
#             users = Users.query.filter(Users.username.like('%' + searched_username + '%')).order_by(Users.username).all()
#             return render_template('add_post.html', form=form, translations=translations, users=users)
#
#         elif form.validate_on_submit():  # Otherwise, it's a post form submission
#             poster = current_user.id
#
#             post = Posts(title=form.title.data, content=form.content.data, slug=form.slug.data, poster_id=poster)
#
#             # Clearing the form
#             form.title.data = ''
#             form.content.data = ''
#             form.slug.data = ''
#
#             # Add post data to database
#             db.session.add(post)
#             db.session.commit()
#
#             # Process included users
#             for user_id in form.included_users.data:
#                 user = Users.query.get(user_id)
#                 if user:
#                     post.included_users.append(user)
#                     included_users.append(user.username)  # Add included user's username to the list
#             db.session.commit()
#
#             flash('Blog Post was submitted successfully')
#
#     # Render the template with the form, translations, and included users list
#     return render_template('add_post.html', form=form, translations=translations, included_users=included_users)


# Add Post Page
@app.route('/add_post', methods=['GET', 'POST'])
@login_required
@organizer_required
def add_post():
    form = PostForm()

    user_language = current_user.language
    translations = load_translations(user_language)

    if form.validate_on_submit():
        poster = current_user.id
        image_filename = None

        if form.image.data:
            image_file = form.image.data
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        # Extract latitude and longitude from the request
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # Ensure latitude and longitude are not empty strings
        if not latitude:
            latitude = None
        if not longitude:
            longitude = None

        post = Posts(
            title=form.title.data,
            content=form.content.data,
            slug=form.slug.data,
            poster_id=poster,
            image=image_filename,
            latitude=latitude,
            longitude=longitude
        )

        db.session.add(post)
        db.session.commit()

        flash('Blog Post was submitted successfully. Invite some people!')
        return redirect(url_for('add_users_to_post', post_id=post.id))

    return render_template('add_post.html', form=form, translations=translations)


# New view for adding users to a post
@app.route('/add_users_to_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
@organizer_required
def add_users_to_post(post_id):

    post = Posts.query.get_or_404(post_id)
    form = SearchForm()  # Create this form for searching users

    user_language = current_user.language
    translations = load_translations(user_language)

    if form.validate_on_submit():
        print('TESTSTAKJHFLKSHDFLKHSJDKJSHLDFKJHSLKDJHLKSDJF')
        # Logic to search for users and invite them to the post
        # This logic depends on how you implement the search functionality
        pass

    return render_template('add_users_to_post.html', post=post, form=form, translations=translations)



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
        # Check if email is already taken
        existing_user_email = Users.query.filter_by(email=form.email.data).first()
        if existing_user_email:
            flash('Email address is already taken. Please choose a different one.', 'error')
        else:
            # Check if username is already taken
            existing_user_username = Users.query.filter_by(username=form.username.data).first()
            if existing_user_username:
                flash('Username is already taken. Please choose a different one.', 'error')
            else:
                # Hash the password
                hashed_pw = generate_password_hash(form.password_hash.data, 'pbkdf2')
                user = Users(username=form.username.data, name=form.name.data, email=form.email.data, sex=form.sex.data, password_hash=hashed_pw, role=form.role.data, language=form.language.data)
                db.session.add(user)
                db.session.commit()
                flash('Account created successfully!', 'success')

                # Clear form fields after successful submission
                form.username.data = ''
                form.name.data = ''
                form.email.data = ''
                form.sex.data = ''
                form.password_hash = ''
                form.role.data = ''
                form.language.data = ''

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


# Search Users Function
@app.route('/search/users', methods=['POST'])
def search_user():
    form = SearchForm()
    users = Users.query
    if form.validate_on_submit():
        user.searched = form.searched.data
        users = users.filter(Users.username.like('%' + user.searched + '%'))
        users = users.order_by(Users.username).all()
        return render_template('admin.html', form=form, searched=user.searched, users=users)

    # If form validation fails, render the admin.html template with the form
    # and no search results
    return render_template('admin.html', form=form, message='No such user')




















@app.route('/add_users_to_post/<int:post_id>/search/users', methods=['GET','POST'])
def search_user_to_post(post_id):
    form = SearchForm()
    post = Posts.query.get_or_404(post_id)  # Retrieve the post

    if form.validate_on_submit():
        user.searched = form.searched.data
        users = Users.query.filter(Users.username.like('%' + user.searched + '%')).order_by(Users.username).all()
        return render_template('add_users_to_post.html', post=post, form=form, searched=user.searched, users=users)

    # If form validation fails, render the template with the form and no search results
    return render_template('add_users_to_post.html', post=post, form=form, message='No such user')


# smtp_port = 587
# smtp_server = "smtp@gmail.com"
# email_from = 'eventm.kgz@gmail.com'
# email_to = ''
# pswd = 'fcgr rpef ujty rjuh'
# message = "You have been invited to an event!"
# simple_email_context = ssl.create_default_context()
#
# try:
#     print('Connecting to server...')
#     TIE_server = smtplib.SMTP(smtp_server, smtp_port)
#     TIE_server.starttls(context=simple_email_context)
#     TIE_server.login(email_from, pswd)
#     print('Connected to server')
#     TIE_server.sendmail(email_from, email_to)
#     print(f'Email send to {email_to}')
#
# except Exception as e:
#     print(e)
#
# finally:
#     TIE_server.quit()


@app.route('/invite_user_to_post/<int:post_id>/<int:user_id>', methods=['GET', 'POST'])
def invite_user_to_post(post_id, user_id):

    post = Posts.query.get_or_404(post_id)
    user = Users.query.get_or_404(user_id)

    # Add the user to the post
    post.included_users.append(user)
    db.session.commit()

    # Email sending logic
    smtp_port = 587
    smtp_server = "smtp.gmail.com"
    email_from = 'eventm.kgz@gmail.com'
    pswd = os.getenv("APP_PASSWORD")

    # Create a secure SSL context
    simple_email_context = ssl.create_default_context()

    try:
        # Construct the email message
        message = MIMEMultipart()
        message["From"] = email_from
        message["To"] = user.email
        message["Subject"] = "Invitation to an event"
        body = f"Hi {user.username},\n\nYou have been invited to an event: {post.title}."
        message.attach(MIMEText(body, "plain"))
        text = message.as_string()

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=simple_email_context)
            server.login(email_from, pswd)
            server.sendmail(email_from, user.email, text)

        flash(f'User {user.username} has been invited to the post "{post.title}"')
    except Exception as e:
        flash('Failed to send invitation email.')
        print(e)

    return redirect(url_for('add_users_to_post', post_id=post_id))


@app.route('/invited_events')
@login_required
def invited_events():
    user_language = current_user.language  # Assuming you have access to the user's selected language
    translations = load_translations(user_language)

    invited_events = current_user.included_in_posts
    return render_template('invited_events.html', invited_events=invited_events, translations=translations)




















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

from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

# Create an association table for posts and users
post_users_association = Table('post_users_association', db.Model.metadata,
    Column('post_id', Integer, ForeignKey('posts.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

# Update Posts model
class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    image = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    slug = db.Column(db.String(255))
    poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    # Many-to-many relationship with users
    included_users = db.relationship('Users', secondary=post_users_association, backref='included_in_posts')



# Create Model - Users
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    sex = db.Column(db.String(50))
    language = db.Column(db.String(10))  # Add a column for storing language preference
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    about = db.Column(db.Text, nullable=True)
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
