import os
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import logging
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app with static folder
app = Flask(__name__, static_folder='static')

# Use environment variables for sensitive data
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7496744940:AAHrLANClx8nHcny5tVQKRdv0t_wS_xAzYM')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '5535430478')

# Configure upload folder
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
import secrets

app.secret_key = secrets.token_hex(16)  # Set a strong random secret key for session and flash
db = SQLAlchemy(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    college_name = db.Column(db.String(100), nullable=False)
    id_card = db.Column(db.String(100))
    registration_date = db.Column(db.DateTime, default=db.func.current_timestamp())

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    file_paths = db.Column(db.Text)
    report_date = db.Column(db.DateTime, default=db.func.current_timestamp())

class EmergencyLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/<page>')
def serve_page(page):
    if page.endswith('.html'):
        return render_template(page)
    return render_template(f'{page}.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return jsonify({"success": True, "message": "File uploaded successfully!"}), 200

@app.route('/emergency', methods=['POST'])
def emergency_alert():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not latitude or not longitude:
        return jsonify({"success": False, "message": "Invalid location data"}), 400

    # Format the message
    message = f"🚨 Emergency Alert!\nLocation: https://www.google.com/maps?q={latitude},{longitude}"

    # Send message to Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return jsonify({"success": True, "message": "Notification sent!"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to send notification."}), 500

from sqlalchemy.exc import IntegrityError

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        college_name = request.form.get('college_name')
        id_card = request.files.get('id_card')

        # Save the uploaded ID card
        id_card_filename = None
        if id_card:
            # Save with unique filename to avoid overwriting
            import uuid
            ext = os.path.splitext(id_card.filename)[1]
            id_card_filename = f"{uuid.uuid4().hex}{ext}"
            id_card_path = os.path.join(app.config['UPLOAD_FOLDER'], id_card_filename)
            id_card.save(id_card_path)

        # Save the user to the database
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),  # Hash password for security
            college_name=college_name,
            id_card=id_card_filename
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))

    # Render the registration form for GET requests
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # Successful login
            session['user_id'] = user.id
            logging.info(f"User {email} logged in successfully. Session user_id set to {user.id}")
            print(f"DEBUG: User {email} logged in, session user_id: {session.get('user_id')}")
            return redirect(url_for('profile'))
        else:
            logging.warning(f"Failed login attempt for email: {email}")
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    app.logger.debug(f"profile route accessed, session user_id: {user_id}")
    print(f"DEBUG: profile route accessed, session user_id: {user_id}")
    if not user_id:
        flash('Please log in to access your profile.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)


from flask import session

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
