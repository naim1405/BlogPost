from flask import Flask, render_template, redirect, url_for, flash, request, g, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentFom
from flask_gravatar import Gravatar
from functools import wraps
import psycopg2
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://blog_bcao_user:DTNJ7djyi4vi40jpytPNbslPUqfRn36K@dpg-cmprhgfqd2ns738t7aj0-a.oregon-postgres.render.com/blog_bcao'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship("Comment", backref = "post")
    
    

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    name = db.Column(db.String(250), nullable = False)
    password = db.Column(db.String(250), nullable=False)
    posts = db.relationship("BlogPost", backref="user")
    comments = db.relationship("Comment", backref = "commentor")
    

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key = True)
    text = db.Column(db.String, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    

with app.app_context():
    db.create_all()

# Login Manager

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(email):    
    user =  db.session.query(User).filter_by(email=email).first()
    if user:
        return user
    else:
        return None

# admin only decorator
def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        g.user = current_user
        admin = db.session.query(User).filter_by(id = 1).first()
        if g.user.is_authenticated:
            if g.user.email != admin.email:
                abort(403)
        else:
            abort(403)
        return func(*args, **kwargs)
    return decorated_function

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    register_form = RegisterForm()
    if request.method =="POST":
        user = User(
            name = request.form["name"],
            email = request.form["email"],
            password = generate_password_hash(password=request.form["password"],method="pbkdf2:sha256", salt_length=8)
        )
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            flash("You are already signed up with that email. Log in instead.")
            return redirect(url_for("login"))
        return redirect("/login")
    return render_template("register.html", form=register_form)


@app.route('/login', methods= ["POST", "GET"])
def login():
    login_form = LoginForm()
    if request.method == "POST":
        email = request.form["email"]
        input_password = request.form["password"]
        user = db.session.query(User).filter_by(email=email).first()
        if user:
            if check_password_hash(pwhash=user.password, password=input_password) == True:
                user.id = email
                login_user(user)
                return redirect("/")
            else:
                flash("Incorrect Password.")
                return redirect(url_for("login"))

        else:
            flash("Email doesn't exist. Please try again.")
            return redirect(url_for("login"))
            
    return render_template("login.html", form = login_form)

@app.route("/secret")
@login_required
def secret():
    return "SECRETS"

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentFom()
    comments = Comment.query.filter_by(post_id=post_id).all()
    print(requested_post.id)
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            comment  = Comment(
                text = comment_form.comment.data,
                commentor = current_user,
                post = requested_post
                
            )
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id = post_id))
        else:
            flash("You need to log in to register a comment.")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, form = comment_form, comments = comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        # post_author = User.query.filter_by(name= current_user.name).first()
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y"),
            user = current_user
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)

