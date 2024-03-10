from flask import Flask, render_template, flash, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError
from wtforms.validators import DataRequired, EqualTo, Length
from wtforms.widgets import TextArea
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from datetime import date

#lol
app = Flask(__name__)

# add database
# Old SQLite DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

# New MySQL DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:8931172771@localhost/fmp'

# Secret key!
app.config['SECRET_KEY'] = '8931172771'
# Initialize the DataBase
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Flask Login Stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# Create Login Form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


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

    return render_template('login.html', form=form)


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
    return render_template('dashboard.html')


# Create a Blog Post model
class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    slug = db.Column(db.String(255))


# Create a Posts Form
class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = StringField('Content', validators=[DataRequired()], widget=TextArea())
    author = StringField('Author', validators=[DataRequired()])
    slug = StringField('Slug', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/posts')
def posts():
    posts = Posts.query.order_by(Posts.date_posted)
    return render_template('posts.html', posts=posts)


@app.route('/posts/<int:id>')
def post(id):
    post = Posts.query.get_or_404(id)
    return render_template('post.html', post=post)


@app.route('/posts/edit/<int:id>', methods=['GET', 'POST'])
def edit_post(id):
    post = Posts.query.get_or_404(id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.author = form.author.data
        post.slug = form.slug.data
        post.content = form.content.data

        # Update Database
        db.session.add(post)
        db.session.commit()

        flash("Post has been updated")
        return redirect(url_for('post', id=post.id))

    form.title.data = post.title
    form.author.data = post.author
    form.slug.data = post.slug
    # here i think he made an error: content was data
    form.content.data = post.content

    return render_template('edit_post.html', form=form)


@app.route('/posts/delete/<int:id>', methods=['GET', 'POST'])
def delete_post(id):
    post_to_delete = Posts.query.get_or_404(id)

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


# add Post Page
@app.route('/add_post', methods=['GET', 'POST'])
def add_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Posts(title=form.title.data, content=form.content.data, author=form.author.data, slug=form.slug.data)

        # Clearing the form
        form.title.data = ''
        form.content.data = ''
        form.author.data = ''
        form.slug.data = ''

        # Add post data to database
        db.session.add(post)
        db.session.commit()

        flash('Blog Post was submitted successfully')

    # Redirect to the webpage
    return render_template('add_post.html', form=form)


# JSON thing
@app.route('/date')
def get_current_date():
    fav_show = {
        'Eldar': 'Stranger Things',
        'Asyl': 'Naruto',
        'Edil': 'The Walking Dead'
    }
    return fav_show


# Create Model - Users
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    sex = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Do some password stuff
    password_hash = db.Column(db.String(128))

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


# Create Model - Events
class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(1000), nullable=False)

    # Crate a string
    def __repr__(self):
        return '<Name %r>' % self.name


# Create Model - Events
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Crate a string
    def __repr__(self):
        return '<Name %r>' % self.name


# Create a Form Class - Test Name
class NamerForm(FlaskForm):
    name = StringField('Enter your name', validators=[DataRequired()])
    submit = SubmitField('Sumbit')


# Create a Form Class - User
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    sex = StringField("Gender")
    password_hash = PasswordField('Password', validators=[DataRequired(), EqualTo('password_hash2', message='Passwords Must Match!')])
    password_hash2 = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Sumbit')


# Delete Database Record - User
@app.route('/delete/<int:id>')
def delete(id):
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


# Update Database Record - User
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)
    if request.method == "POST":
        name_to_update.username = request.form['username']
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        name_to_update.sex = request.form['sex']
        try:
            db.session.commit()
            flash("User Updated Successfully!")
            return render_template('update.html', form=form, name_to_update=name_to_update)
        except:
            flash("Error! There was a problem bro")
            return render_template('update.html', form=form, name_to_update=name_to_update, id=id)
    else:
        print(id)
        return render_template('update.html', form=form, name_to_update=name_to_update, id=id)


# Create a Form Class - Event
class EventForm(FlaskForm):
    name = StringField('Enter event name', validators=[DataRequired()])
    description = StringField('Enter description of your event', validators=[DataRequired()])
    submit = SubmitField('Sumbit')


# Create a Form Class - Password Test
class PasswordForm(FlaskForm):
    email = StringField('Enter your email', validators=[DataRequired()])
    password_hash = PasswordField('Enter you password', validators=[DataRequired()])
    submit = SubmitField('Sumbit')


# Create a Form Class - News
class NewsForm(FlaskForm):
    name = StringField('Enter news headline', validators=[DataRequired()])
    description = StringField('Enter news description', validators=[DataRequired()])
    submit = SubmitField('Sumbit')


@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    name = None
    form = UserForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user is None:
            # Hash the password
            hashed_pw = generate_password_hash(form.password_hash.data, 'pbkdf2')
            user = Users(username=form.username.data, name=form.name.data, email=form.email.data, sex=form.sex.data, password_hash=hashed_pw)
            db.session.add(user)
            db.session.commit()
        name = form.name.data
        form.username.data = ''
        form.name.data = ''
        form.email.data = ''
        form.sex.data = ''
        form.password_hash = ''

        flash('User Added Succesfully!')

    out_users = Users.query.order_by(Users.date_added)
    return render_template('add_user.html', form=form, name=name, our_users=out_users)


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    name = None
    form = EventForm()
    if form.validate_on_submit():
        event = Events.query.filter_by(name=form.name.data).first()
        if event is None:
            event = Events(name=form.name.data, description=form.description.data)
            db.session.add(event)
            db.session.commit()
        name = form.name.data
        form.name.data = ''
        form.description.data = ''
        flash('Event Added Succesfully!')

    return render_template('add_event.html', form=form, name=name)


@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    name = None
    form = NewsForm()
    if form.validate_on_submit():
        news = News.query.filter_by(name=form.name.data).first()
        if news is None:
            news = News(name=form.name.data, description=form.description.data)
            db.session.add(news)
            db.session.commit()
        name = form.name.data
        form.name.data = ''
        form.description.data = ''
        flash('News Added Succesfully!')

    return render_template('add_news.html', form=form, name=name)


# Create password test page
@app.route('/test_pw', methods=['GET', 'POST'])
def test_pw():
    email = None
    password = None
    pw_to_check = None
    passed = None
    form = PasswordForm()

    # Validate Form
    if form.validate_on_submit():
        email = form.email.data
        password = form.password_hash.data

        # Clearing the form
        form.email.data = ''
        form.password_hash.data = ''

        # Lookup used by email address
        pw_to_check = Users.query.filter_by(email=email).first()

        # Check Hashed Password
        passed = check_password_hash(pw_to_check.password_hash, password)

        # flash("Form Submitted Successfully")

    return render_template('test_pw.html', email=email, password=password, pw_to_check=pw_to_check, passed=passed, form=form)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/events', methods=['GET'])
def events():
    events = Events.query.order_by(Events.date_added)
    return render_template('events.html', events=events)


@app.route('/news', methods=['GET'])
def news():
    news = News.query.order_by(News.date_added)
    return render_template('news.html', news=news)


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


# Invalid URL
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Internal Sevrer Error
@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)