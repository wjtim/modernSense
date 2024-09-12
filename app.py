from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from transformers import pipeline
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import pandas as pd
import io
import os

app = Flask(__name__)
CORS(app)
load_dotenv()
#App configs from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

#SQLAlchemy setup
db = SQLAlchemy(app)

# Initialize sentiment analysis pipeline
scoring_model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
sentiment_model_name = "distilbert-base-uncased-finetuned-sst-2-english"
scoring_analyzer = pipeline("sentiment-analysis", model=scoring_model_name)
sentiment_analyzer = pipeline("sentiment-analysis", model=sentiment_model_name)

#Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

#User Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
#Initialize db models
with app.app_context():
    db.create_all()

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#CSV Filetype verification method
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

# Route to handle login
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
def upload_file():
    file = request.files.get('file')
    sentiment_results = []
    stats = {}
    print("Upload route taken")
    if file and allowed_file(file.filename):
        print("File received")
        # Read and process CSV file
        file_content = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(file_content))
        
        # Check for required columns
        if 'review' not in df.columns or 'rating' not in df.columns:
            print("CSV must contain 'review' and 'rating' columns.")
            return redirect(url_for("index"))
        
        # Process reviews and ratings
        df['nlptown_label'] = df['review'].apply(lambda x: scoring_analyzer(x)[0]['label'])
        df['nlptown_score'] = df['review'].apply(lambda x: scoring_analyzer(x)[0]['score'])
        df['distilbert_label'] = df['review'].apply(lambda x: sentiment_analyzer(x)[0]['label'])
        df['distilbert_score'] = df['review'].apply(lambda x: sentiment_analyzer(x)[0]['score'])
        
        # Map sentiment score to star rating (assuming score is normalized between 0 and 1)
        df['nlptown_star_rating'] = df['nlptown_score'].apply(lambda x: round(x * 4) + 1)
        
        # Calculate statistics
        stats['nlptown_avg_score'] = df['nlptown_score'].mean()
        stats['distilbert_avg_score'] = df['distilbert_score'].mean()
        stats['average_rating'] = df['rating'].mean()
        stats['average_nlptown_star_rating'] = df['nlptown_star_rating'].mean()
        stats['rating_vs_nlptown'] = ((df['rating'] - df['nlptown_star_rating']).abs().mean())

        # Convert the DataFrame to CSV for display
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        csv_data = csv_buffer.getvalue()
        
        return render_template("index.html", csv_data=csv_data, stats=stats)
    
    print("No file uploaded or file format is incorrect.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)