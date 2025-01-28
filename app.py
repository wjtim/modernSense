from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from transformers import pipeline
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from markupsafe import Markup
from dotenv import load_dotenv
import pandas as pd
import io
import os
import re

app = Flask(__name__)
CORS(app)
load_dotenv()

#App configs from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Email configuration for SendGrid
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.environ.get('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

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

#Mail setup
mail = Mail(app)

# Token serializer for email verification
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

#User Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

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


# Helper function to send verification email
def send_verification_email(user_email):
    token = s.dumps(user_email, salt='email-confirm')
    verification_url = url_for('verify_email', token=token, _external=True)
    msg = Message("Email Verification", recipients=[user_email])
    msg.html = Markup(f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);">
            <div style="background-color: #22c55e; color: #ffffff; padding: 20px; text-align: center;">
                <h2>Welcome to ModernSense!</h2>
            </div>
            <div style="padding: 30px;">
                <p>Welcome to ModernSense,</p>
                <p>Please confirm your email address to complete your registration.</p>
                <p>Click the button below to verify your email:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" style="background-color: #22c55e; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 4px; font-weight: bold;">Verify Email</a>
                </p>
                <p>If the button doesn't work, you can also verify by clicking this link:</p>
                <p style="text-align: center;"><a href="{verification_url}">{verification_url}</a></p>
                <p>Thank you,<br>The ModernSense Team</p>
            </div>
            <div style="background-color: #f4f4f4; color: #888888; padding: 10px; text-align: center; font-size: 12px;">
                <p>This email was sent to you by ModernSense sentiment analysis. If you did not register, please ignore this message.</p>
            </div>
        </div>
    </body>
    </html>
    """)
    mail.send(msg)

# Helper function to send password reset email
def send_reset_email(user_email):
    token = s.dumps(user_email, salt='password-reset')
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message("Password Reset Request", recipients=[user_email])
    msg.html = Markup(f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);">
            <div style="background-color: #22c55e; color: #ffffff; padding: 20px; text-align: center;">
                <h2>Reset Your Password</h2>
            </div>
            <div style="padding: 30px;">
                <p>You requested a password reset. Click the button below to reset your password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" style="background-color: #22c55e; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 4px; font-weight: bold;">Reset Password</a>
                </p>
                <p>If the button doesn't work, you can also reset your password by clicking this link:</p>
                <p style="text-align: center;"><a href="{reset_url}">{reset_url}</a></p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
            <div style="background-color: #f4f4f4; color: #888888; padding: 10px; text-align: center; font-size: 12px;">
                <p>This email was sent by ModernSense sentiment analysis.</p>
            </div>
        </div>
    </body>
    </html>
    """)
    mail.send(msg)

#CSV Filetype verification method
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

# Route to handle login
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_verified:
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Please verify your email before logging in.", "login")
        else:
            flash("Invalid username or password", "login")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Email regex pattern
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        password_regex = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        if not re.match(email_regex, email):
            flash("Invalid email address", "register")
        elif not re.match(password_regex, password):
            flash("Password must be at least 8 characters long, include at least one letter, one number, and one special character", "register")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists", "register")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered", "register")
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            send_verification_email(email)
            flash("Registered successfully! Please check your email to verify your account.", "login_success")
            return redirect(url_for("login"))
    return render_template("register.html")

# Route to verify email
@app.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)  # Token expires in 1 hour
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_verified = True
            db.session.commit()
            flash("Your email has been verified. You can now log in.", "login_success")
            return redirect(url_for('login'))
    except:
        flash("The verification link is invalid or has expired.", "verify")
        return redirect(url_for('register'))

# Route to request password reset
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_email(email)
            flash("A password reset link has been sent to your email.", "reset")
        else:
            flash("No account found with that email.", "reset")
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)  # Token expires in 1 hour
    except:
        flash("The reset link is invalid or has expired.", "error")
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match", "reset")
        elif not re.match(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', new_password):
            flash("Password must be at least 8 characters long, include a letter, a number, and a special character", "reset")
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                flash("Your password has been updated. You can now log in.", "login_success")
                return redirect(url_for('login'))
            else:
                flash("Internal server error, user not found. Contact Support", "reset")
    return render_template('reset_password.html', token=token)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!")
    return redirect(url_for("home"))

@app.route("/")
def home():
    return render_template("landing.html")

@app.route("/input", methods=["GET", "POST"])
@login_required
def input():
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
    return render_template("input.html", sentiment_results=sentiment_results, user_expected=user_expected)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_file():
    
    #File Upload recieved from Form
    file = request.files.get('file')
    stats = {}

    #Debug print line
    print("Upload route taken")

    #Check file format of upload for CSV
    if file and allowed_file(file.filename):
        print("File received")
        # Read and process CSV file
        file_content = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(file_content))
        # Check for required columns
        if 'review' not in df.columns or 'rating' not in df.columns:
            flash("CSV must contain 'review' and 'rating' columns.", "csv_error")
            return redirect(url_for("input"))
        
        if df.shape[0] > 10:  # More than 10 rows
            print("File has more than 10 rows. Please upload a smaller file.")
            flash("File has more than 10 rows. Please upload a smaller file.", "csv_error")
            return redirect(url_for("input"))
        if df.shape[1] > 2:
            print("Limit your files columns to only Rating and Review.")
            flash("Limit your files columns to only Rating and Review.", "csv_error")
            return redirect(url_for("input"))
        # Process reviews and ratings
        df['expected_rating'] = df['review'].apply(lambda x: scoring_analyzer(x)[0]['label'])
        df['rating_confidence'] = round(df['review'].apply(lambda x: scoring_analyzer(x)[0]['score']*100), 2)
        df['evaluated_sentiment'] = df['review'].apply(lambda x: sentiment_analyzer(x)[0]['label'])
        df['sentiment_confidence'] = round(df['review'].apply(lambda x: sentiment_analyzer(x)[0]['score']*100), 2)
        
        # Convert the DataFrame to a list of lists for rendering in HTML
        columns = df.columns.tolist()  # Extract the column headers
        rows = df.values.tolist()  # Extract the rows of data

        # Calculate statistics
        stats['nlptown_avg_score'] = round(df['rating_confidence'].mean(), 2)
        stats['distilbert_avg_score'] = round(df['sentiment_confidence'].mean(), 2)
        stats['average_rating'] = df['rating'].mean()

        # Convert the DataFrame to CSV for display
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        session['csv_data'] = csv_buffer.getvalue()

        return render_template("input.html", columns=columns, rows=rows, stats=stats)
    
    flash("No file uploaded or file format is incorrect.", "csv_error")
    return redirect(url_for("input"))

@app.route('/download_csv')
@login_required
def download_csv():
    # Check if CSV data is available in session
    csv_data = session.get('csv_data')
    if csv_data:
        # Return the CSV file as a downloadable response
        return send_file(
            io.BytesIO(csv_data.encode()),  # Convert string to bytes
            mimetype='text/csv',
            as_attachment=True,
            download_name='analysed_reviews.csv'
        )
    else:
        print("CSV Data not found")
        flash("No CSV available for download.")
        return redirect(url_for("input"))
    
if __name__ == "__main__":
    app.run(debug=True)