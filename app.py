import os
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import logging
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

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
serializer = URLSafeTimedSerializer(app.secret_key)

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
    status = db.Column(db.String(20), default='pending')  # Added status column
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

from flask import session

@app.route('/emergency', methods=['POST'])
def emergency_alert():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not latitude or not longitude:
        return jsonify({"success": False, "message": "Invalid location data"}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    college_name = user.college_name

    # Format the message with college name
    message = f"🚨 Emergency Alert!\nCollege: {college_name}\nLocation: https://www.google.com/maps?q={latitude},{longitude}"

    # Send message to Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, json=payload)
        app.logger.info(f"Telegram API response status: {response.status_code}, response text: {response.text}")
    except Exception as e:
        app.logger.error(f"Error sending message to Telegram: {e}")
        return jsonify({"success": False, "message": "Failed to send notification due to exception."}), 500

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
        try:
            email = request.form.get('email')
            password = request.form.get('password')

            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                # Successful login
                session['user_id'] = user.id
                logging.info(f"User {email} logged in successfully. Session user_id set to {user.id}")
                print(f"DEBUG: User {email} logged in, session user_id: {session.get('user_id')}")
                redirect_url = url_for('profile')
                print(f"DEBUG: Redirecting to {redirect_url}")
                return redirect(redirect_url)
            else:
                logging.warning(f"Failed login attempt for email: {email}")
                flash('Invalid email or password. Please try again.', 'danger')
                return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Exception during login: {e}")
            flash('An error occurred during login. Please try again later.', 'danger')
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
    
    # Query stats for the user
    total_reports = Incident.query.filter_by(user_id=user_id).count()
    pending_reports = Incident.query.filter_by(user_id=user_id, status='pending').count()
    resolved_reports = Incident.query.filter_by(user_id=user_id, status='resolved').count()
    stats = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'resolved_reports': resolved_reports
    }
    # Query incidents for the user
    incidents = Incident.query.filter_by(user_id=user_id).order_by(Incident.report_date.desc()).all()
    
    return render_template('profile.html', user=user, stats=stats, incidents=incidents)


from flask import session

from flask import flash

@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/report_incident', methods=['GET', 'POST'])
def report_incident():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to report an incident.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        description = request.form.get('description')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        file = request.files.get('files')

        if not description or not latitude or not longitude or not file:
            flash('All fields are required.', 'danger')
            return redirect(url_for('report_incident'))

        # Save the uploaded file with a unique filename
        import uuid
        ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else ''
        filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Save incident to database
        new_incident = Incident(
            user_id=user_id,
            description=description,
            file_paths=filename
        )
        db.session.add(new_incident)
        db.session.commit()

        flash('Report submitted successfully!', 'success')
        return redirect(url_for('report_incident'))

    return render_template('report.html')

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_via_mailtrap(to_email, subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email
    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
            app.logger.info("Email sent successfully via Gmail SMTP.")
    except Exception as e:
        app.logger.error(f"Error sending email via Gmail SMTP: {e}")
        raise

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate token valid for 1 hour (3600 seconds)
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            app.logger.info(f"DEBUG: Reset URL: {reset_url}")

            # Compose email HTML content
            html = f"""
            <p>Hello,</p>
            <p>You requested a password reset. Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>If you did not request this, please ignore this email.</p>
            """
            app.logger.info(f"DEBUG: Email content: {html}")

            try:
                send_email_via_mailtrap(email, "Password Reset Request", html)
                app.logger.info("Password reset email sent successfully via Gmail SMTP.")
                flash('A password reset link has been sent to your email.', 'info')
            except Exception as e:
                app.logger.error(f"Failed to send password reset email via Gmail SMTP: {e}", exc_info=True)
                flash('Failed to send password reset email. Please try again later.', 'danger')
        else:
            # Do not reveal if email is not registered
            flash('A password reset link has been sent to your email.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The password reset link has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Invalid password reset link.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not password or not confirm_password:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('reset_password', token=token))
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('reset_password', token=token))

        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(password)
            db.session.commit()
            flash('Your password has been updated. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('forgot_password'))

    return render_template('reset_password.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to edit your profile.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        college_name = request.form.get('college_name')
        id_card = request.files.get('id_card')

        if not name or not college_name:
            flash('Name and College Name are required.', 'danger')
            return redirect(url_for('edit_profile'))

        user.name = name
        user.college_name = college_name

        if id_card:
            import uuid
            ext = os.path.splitext(id_card.filename)[1]
            id_card_filename = f"{uuid.uuid4().hex}{ext}"
            id_card_path = os.path.join(app.config['UPLOAD_FOLDER'], id_card_filename)
            id_card.save(id_card_path)
            user.id_card = id_card_filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)

@app.route('/api/incident/<int:incident_id>')
def get_incident(incident_id):
    incident = Incident.query.get(incident_id)
    if not incident:
        return jsonify({'error': 'Incident not found'}), 404
    return jsonify({
        'id': incident.id,
        'description': incident.description,
        'status': incident.status,
        'report_date': incident.report_date.strftime('%Y-%m-%d %H:%M:%S'),
        'file_paths': incident.file_paths
    })

SMTP_SERVER = 'smtp.gmail.com'  # Gmail SMTP server
SMTP_PORT = 587  # Gmail SMTP port
EMAIL_SENDER = 'christinrimal@gmail.com'  # Your Gmail address
EMAIL_PASSWORD = 'dtzr nfaa vrcw zduq'  # Replace with your app password or Gmail password

def send_test_email():
    message = MIMEMultipart('alternative')
    message['Subject'] = 'Test Email'
    message['From'] = EMAIL_SENDER
    message['To'] = 'recipient@example.com'  # Replace with your email
    message.attach(MIMEText('<p>This is a test email.</p>', 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, 'recipient@example.com', message.as_string())
            print("Test email sent successfully.")
    except Exception as e:
        print(f"Error sending test email: {e}")

# send_test_email()

if __name__ == '__main__':
    app.run(debug=True)
