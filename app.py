from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from transformers import pipeline
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from fileinput import filename
import pandas as pd
import numpy
import os



print(numpy.__version__)
app = Flask(__name__)

# Initialize sentiment analysis pipeline
scoring_model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
sentiment_model_name = "distilbert-base-uncased-finetuned-sst-2-english"
scoring_analyzer = pipeline("sentiment-analysis", model=scoring_model_name)
sentiment_analyzer = pipeline("sentiment-analysis", model=sentiment_model_name)

UPLOAD_FOLDER = os.path.join('staticFiles', 'uploads')
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config['SECRET_KEY'] = 'thisisasecretkey'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.secret_key = 'Super secret Flask key'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registered successfully! Please log in.")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!")
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    sentiment_results = {}
    user_expected = {}
    if request.method == "POST":
        
        user_input = request.form["user_input"]
        user_rating = request.form["user_rating"]
        
        scoring_result = scoring_analyzer(user_input)[0]
        sentiment_results['scoring'] = {
            "label": scoring_result["label"],
            "score": round(scoring_result["score"], 4)
        }
        distilbert_result = sentiment_analyzer(user_input)[0]
        sentiment_results['sentiment'] = {
            "label": distilbert_result["label"],
            "score": round(distilbert_result["score"], 4)
        }
        user_expected = {
            "score": user_rating + " stars"
        }
        print(user_input)
    return render_template("index.html", sentiment_results=sentiment_results, user_expected=user_expected)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def uploadFile():
    if request.method == 'POST':
      # upload file flask
        f = request.files.get('file')
 
        # Extracting uploaded file name
        data_filename = secure_filename(f.filename)
 
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],
                            data_filename))
 
        session['uploaded_data_file_path'] = os.path.join(app.config['UPLOAD_FOLDER'], data_filename)
        return render_template('uploadSuccess.html')
    return render_template("upload.html")

@app.route('/show_data')
@login_required
def showData():
    # Uploaded File Path
    data_file_path = session.get('uploaded_data_file_path', None)
    # read csv
    uploaded_df = pd.read_csv(data_file_path,
                              encoding='unicode_escape')
    # Converting to html Table
    uploaded_df_html = uploaded_df.to_html()
    return render_template('displayCSV.html',
                           data_var=uploaded_df_html)

if __name__ == "__main__":
    app.run(debug=True)