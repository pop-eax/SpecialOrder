from flask import Flask, render_template, request, redirect, session, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import *
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import json
from lxml import etree

app = Flask(__name__)
app.secret_key = "sssh"
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db_file/users.db'
db = SQLAlchemy(app)
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
Base = automap_base()
Base.prepare(engine, reflect=True)
metadata = MetaData(engine)
users_map = Base.classes.users
posts_map = Base.classes.posts
settings_map = Base.classes.user_settings
def get_resource_as_string(name, charset='utf-8'):
    with app.open_resource(name) as f:
        return f.read().decode(charset)
app.jinja_env.globals['get_resource_as_string'] = get_resource_as_string


class user_settings(db.Model):
    __tablenamme__ = "userSettings"

    username = db.Column(Text, primary_key=True)
    color = db.Column(Text)
    size = db.Column(db.String(256))

class User(db.Model):
    __tablename__ = "users"

    uuid = db.Column(db.Integer, primary_key=True)
    username = db.Column(Text, unique=True)
    password = db.Column(Text)

    def __repr__(self):
        return "<uuid %r>" % self.username

class Post(db.Model):
    __tablename__ = "posts"

    uuid = db.Column(db.Integer, primary_key=True)
    author = db.Column(Text)
    title = db.Column(db.String(256), index=True)
    body = db.Column(Text)

    def __repr__(self):
        return "<uuid %r>" % self.author

@app.route("/login", methods=["GET", "POST"])
def login_view():
    
    if request.method == "GET" and session.get('logged_in') != True:
        return render_template("login.html")
    
    elif session.get('logged_in') == True:
        return redirect("/")
    
    else:
    
        if request.method == "POST" and request.form['username'] and request.form['pass']:
            username = request.form['username']
            password = request.form['pass']
            user = db.session.query(users_map).filter(or_(users_map.username == username)).first()

            if  user and check_password_hash(user.password, password):
                session['logged_in'] = True
                session['username'] = request.form['username']
                return redirect("/")
            else:
                return redirect("/login")

@app.route("/")
def index_view():
    
    if session.get('logged_in'):
        return render_template("index.html", posts=db.session.query(posts_map).filter(or_(posts_map.author == session['username'])).all())
    else:
        return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register_view():
    
    if request.method == "POST" and request.form['username'] and request.form['pass']:
        username = request.form['username']
        password = request.form['pass']
        password_hash = generate_password_hash(password)
        users_table = Table('users', metadata, autoload=True)

        if db.session.query(users_map).filter(or_(users_map.username == username)).first():
            return "<h1> duplicate username :(</h1>"
        engine.execute(users_table.insert(), username=username, password=password_hash)
        return redirect("/login")
    
    if not session.get('logged_in'):
        return render_template("/register.html")
    else:
        return redirect("/")

@app.route("/post")
def post_view():
    
    if session.get('logged_in'):
        if request.args.get("id"):
            user_post = db.session.query(posts_map).filter_by(uuid=request.args.get("id"), author=session['username']).first()
            return render_template("post.html", post=user_post)
        else:
            return render_template("sample-post.html")
    else:
        return redirect("/login")

@app.route("/create-post", methods=["GET", "POST"])
def CreatePost_view():
    
    if not session.get('logged_in'):
        return redirect("/login")
    if request.method == "GET":
        return render_template("create_post.html")
    else:
        author = session['username']
        title = request.form['title']
        post_body = request.form['post-body']
        posts_table = Table('posts', metadata, autoload=True)
        if author and title and post_body:
            engine.execute(posts_table.insert(), author=author, title=title, body=post_body)
            return redirect("/")
@app.route("/customize", methods=["GET", "POST"])
def customize_view():
    
    if not session.get('logged_in'):
        return redirect("/login")
    if request.method == "GET":
        return render_template("customize.html")
    else:
        settings_table = Table('user_settings', metadata, autoload=True)
        if request.content_type == "application/json":
            data = request.get_json()
            if db.session.query(settings_map).filter_by(username=session['username']).first() and data:
                db.session.query(settings_map).filter_by(username=session['username']).update({"size": data["size"], "color": data["color"]})
                db.session.commit()
                return "DONE :D"
            else:
                engine.execute(settings_table.insert(), username=session['username'], color=data["color"], size=data["size"])
                return "DONE :D"
        elif request.content_type == "application/xml" or request.content_type == "text/xml":
            print(request.data)
            parser = etree.XMLParser()
            k = etree.fromstring(request.data, parser)
            post_color = ""
            post_size = ""
            w = ""
            for i in k.getchildren():
                if i.tag == "color":
                    post_color = i.text
                elif i.tag == "size":
                    post_size = i.text
            if db.session.query(settings_map).filter_by(username=session['username']).first():
                db.session.query(settings_map).filter_by(username=session['username']).update({"size": post_size, "color": post_color})
                db.session.commit()
                return "DONE :D"
            else:
                engine.execute(settings_table.insert(), username=session['username'], color=post_color, size=post_size)
                return "DONE :D"

@app.route("/css/clean-blog.css")
def css_view():
    if not session.get('logged_in'):
        return redirect("/login")
    else:
        settings_table = Table('user_settings', metadata, autoload=True)
        post_color = ""
        post_size = ""
        if db.session.query(settings_map).filter_by(username=session['username']).first():
            post_size = db.session.query(settings_map).filter_by(username=session['username']).first().size
            post_color = db.session.query(settings_map).filter_by(username=session['username']).first().color 

        return Response(render_template("clean-blog.css", color=post_color,size=post_size,w=get_resource_as_string("static/css/clean-blog.css")), mimetype="text/css")

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)