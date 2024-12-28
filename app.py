from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail
import json
import os
from werkzeug.utils import secure_filename
from flask import flash
import math

with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server = True

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL='True',
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)

mail = Mail(app)

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


class contact(db.Model):
    serial_no = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    message = db.Column(db.String(100), nullable=False)


class Posts(db.Model):
    serial_no = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    slug = db.Column(db.String(21), nullable=False, unique=True)
    img_file = db.Column(db.String(12), nullable=True)
    tagline = db.Column(db.String(15), nullable=True)

@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
    if page==1:
        prev = "#"
        next = "/?page="+ str(page+1)
    elif page==last:
        prev = "/?page="+ str(page-1)
        next = "#"
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)
    
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/post/<string:post_slug>", methods=['GET'])
@app.route("/post/", methods=['GET'])
def post_route(post_slug=None):
    if post_slug:
        post = Posts.query.filter_by(slug=post_slug).first()
        return render_template('post.html', params=params, post=post)
    else:
        return render_template('all_post.html', params=params)


@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if "user" in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("pass")
        if username == params['admin_user'] and userpass == params['admin_password']:
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)

    return render_template('login.html', params=params)



@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    posts = Posts.query.all()
    return render_template("dashboard.html", params=params, posts=posts)


@app.route("/contact", methods=['GET', 'POST'])
def contact_form():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = contact(name=name, email=email, phone=phone, message=message)
        db.session.add(entry)
        db.session.commit()
        # mail.send_message('New message from ' + name, sender=email, recipients=[params['gmail-user']],
        #                   body=message + "\n" + phone)
        flash("Thanks for submitting your details. We will be back to you","success")
    return render_template('contact.html', params=params)


@app.route("/edit/<string:serial_no>", methods=['GET', 'POST'])
def edit(serial_no):
    if "user" in session and session['user'] == params['admin_user']:
        if request.method == "POST":
            box_title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            created_at = datetime.now()

            if serial_no == '0':
                post = Posts(title=box_title, slug=slug, content=content, tagline=tagline, img_file=img_file,
                             created_at=created_at)
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(serial_no=serial_no).first()
                post.title = box_title
                post.tagline = tagline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.created_at = created_at
                db.session.commit()
                return redirect('/edit/' + serial_no)

    post = Posts.query.filter_by(serial_no=serial_no).first()
    return render_template('edit.html', params=params, post=post, serial_no=serial_no)


@app.route("/delete/<string:serial_no>", methods=['GET', 'POST'])
def delete(serial_no):
    if "user" in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(serial_no=serial_no).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user'] == params['admin_user']:
        if request.method == "POST":
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        return "Uploaded Successfully.!"


@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user')
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)
