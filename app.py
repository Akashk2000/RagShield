import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

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

@app.route('/register')
def register():
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)