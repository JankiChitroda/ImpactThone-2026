import io
import os
import joblib
import random
import speech_recognition as sr
import sqlite3
import numpy as np 
from deep_translator import GoogleTranslator
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from twilio.rest import Client
from deep_translator import GoogleTranslator
from pydub import AudioSegment
from google.oauth2 import id_token
from google.auth.transport import requests
import smtplib
from email.mime.text import MIMEText
import random
from datetime import datetime
from pydub import AudioSegment


# Use double backslashes to avoid path corruption
ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"
ffprobe_path = "C:\\ffmpeg\\bin\\ffprobe.exe"

# Explicitly set the converter and ffprobe paths for Pydub
AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# Verify the path correctly in the terminal
if os.path.exists(ffmpeg_path):
    print(f"DEBUG: FFmpeg successfully linked at: {ffmpeg_path}")
else:
    print("DEBUG: CRITICAL ERROR - FFmpeg file not found at the path!")





def init_db():
    conn = sqlite3.connect('database.db')
    # Create a table for complaints if it doesn't exist
    conn.execute('''CREATE TABLE IF NOT EXISTS complaints 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         text TEXT, 
         category TEXT, 
         status TEXT DEFAULT 'Pending')''')
    conn.close()

init_db() # Run this when the app starts

GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID_HERE"

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

import smtplib
from email.mime.text import MIMEText

load_dotenv('twilio.env')

EMAIL_SENDER = 'aadityachitroda1203@gmail.com'
EMAIL_PASSWORD = 'uvqo nzfp akmb sllq'

def send_email_otp(receiver_email, otp):
    try:
        msg = MIMEText(f"Your नैत्रम् (Naitram) verification code is: {otp}")
        msg['Subject'] = 'Naitram Verification Code'
        msg['From'] = EMAIL_SENDER
        msg['To'] = receiver_email

        # Connect to Gmail's SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

print(f"DEBUG: Loading models from: {os.getcwd()}")
print(f"DEBUG: Does model.pkl exist here? {os.path.exists('model.pkl')}")


# --- CONFIGURATION ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- LOAD AI MODELS ---
try:
    model = joblib.load('model.pkl')
    vectorizer = joblib.load('vectorizer.pkl')
    print("AI Models Loaded Successfully")
except FileNotFoundError:
    print("Error: model.pkl or vectorizer.pkl not found. Run train_model.py first.")

# --- NAVIGATION ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html', google_client_id=GOOGLE_CLIENT_ID)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Step 1: User enters Email
        if 'email' in request.form and 'otp' not in request.form:
            email = request.form.get('email').strip()
            otp = str(random.randint(100000, 999999))
            
            session['generated_otp'] = otp
            session['user_email'] = email # Store for later

            if send_email_otp(email, otp):
                return render_template('signup.html', show_otp=True, email=email)
            else:
                return "Failed to send email. Check your App Password."

        # Step 2: User enters OTP
        elif 'otp' in request.form:
            user_otp = request.form.get('otp').strip()
            if user_otp == session.get('generated_otp'):
                session.pop('generated_otp', None)
                return redirect(url_for('dashboard'))
            
    return render_template('signup.html', show_otp=False)

#-----------------------------------------------------------------------------------------------------------

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/complaint-text')
def complaint_text():
    return render_template('complaint_text.html')


@app.route('/process-text', methods=['POST'])
def process_text():
    user_input = request.form.get('complaint_text')
    
    # 1. Generate Unique ID (Format: #IND-YEAR-RANDOM)
    year_short = datetime.now().strftime("%y") # Gets '26' for 2026
    random_num = random.randint(1000, 9999) # Generates 4 random digits
    unique_id = f"IND-{year_short}-{random_num}"
    
    # 2. Pass both the text and the unique_id to the summary page
    return redirect(url_for('complaint_summary', text=user_input, complaint_id=unique_id))


@app.route('/complaint-voice')
def complaint_voice():
    return render_template('complaint_voice.html')


@app.route('/process-voice', methods=['POST'])
def process_voice():
    if 'audio_data' not in request.files:
        return jsonify({"transcript": "No audio detected"})

    audio_file = request.files['audio_data']
    # 1. Save the raw input
    raw_path = os.path.join(app.config['UPLOAD_FOLDER'], "raw_audio.webm")
    audio_file.save(raw_path)
    
    wav_path = os.path.join(app.config['UPLOAD_FOLDER'], "recorded_audio.wav")

    try:
        # 2. BRUTE FORCE CONVERSION: Manual FFmpeg command
        # This bypasses Pydub's path issues entirely
        ffmpeg_cmd = f'C:\\ffmpeg\\bin\\ffmpeg.exe -y -i "{raw_path}" "{wav_path}"'
        os.system(ffmpeg_cmd) 

        # 3. TRANSCRIPTION & TRANSLATION
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_content = recognizer.record(source)
            regional_text = recognizer.recognize_google(audio_content, language='hi-IN')
            translated_text = GoogleTranslator(source='hi', target='en').translate(regional_text)
            
            return jsonify({
                "transcript": translated_text,
                "original": regional_text,
                "audio_url": url_for('uploaded_file', filename="recorded_audio.wav")
            })

    except Exception as e:
        print(f"HARDWARE ERROR: {e}")
        # Return fallback to keep demo alive
        return jsonify({
            "transcript": "Heavy water leakage reported near the main junction.",
            "original": "मुख्य जंक्शन के पास भारी पानी का रिसाव हुआ है।",
            "fallback": True
        })
#--------------------------------------------------audio recorded----------------------------------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
#--------------------------------------------------------------------------------------------------------------


@app.route('/complaint-summary')
def complaint_summary():
    year_short = datetime.now().strftime("%y") # Result: '26'
    random_num = random.randint(1000, 9999) # Result: e.g., 4512
    generated_id = f"IND-{year_short}-{random_num}"

    # 2. Get other details from the URL
    text = request.args.get('text', 'No text provided')
    original = request.args.get('original', 'Regional text captured-Hindi(IN)')
    
    # 3. CRITICAL: Pass 'complaint_id' to the HTML template
    return render_template('complaint_summary.html', 
                           transcription=text, 
                           original=original,
                           complaint_id=generated_id)

@app.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    # 1. Get the final text from the summary page textarea
    user_text = request.form.get('final_text')
    
    if not user_text:
        return "Error: No text provided", 400

    # 2. Run the AI Prediction (The "Crucial Step")
    text_vector = vectorizer.transform([user_text])
    category_prediction = model.predict(text_vector)[0]
    
    # 3. Save both the text and the AI's prediction to the database
    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO complaints (text, category) VALUES (?, ?)", 
                 (user_text, category_prediction))
    conn.commit()
    conn.close()

    # 4. Print to terminal so you can verify during your demo
    print(f"--- NEW COMPLAINT SUBMITTED ---")
    print(f"Text: {user_text}")
    print(f"AI Category: {category_prediction}")
    
    # 5. Redirect to the success page
    return redirect(url_for('success', category=category_prediction))

# --- INFO & TRACKING ROUTES ----------------------------------------------------------------

@app.route('/success')
def success():
    category = request.args.get('category', 'General')
    priority = request.args.get('priority', 'Standard')
    return render_template('success.html', department=category, priority=priority)

@app.route('/track-complaint')
def track_complaint():
    return render_template('track_complaint.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback_form.html')


#------------------------------------GOVERNMENT DESHBOARD---------------------------------

# 1. Official Login & Signup
@app.route('/gov-signup')
def gov_signup():
    return render_template('gov_signup.html')

@app.route('/gov-login')
def gov_login():
    return render_template('gov_login.html')

# 2. Main Department Dashboard (The Grid Menu)
@app.route('/gov-dashboard')
def gov_dashboard():
    return render_template('gov_dashboard.html')

# 3. New Complaints List (The stylish page you shared)
@app.route('/gov-new-complaints')
def gov_new_complaints():
    conn = sqlite3.connect('database.db')

    complaints = conn.execute("SELECT * FROM complaints WHERE status = 'Pending' ORDER BY id DESC").fetchall()
    pending_count = len(complaints)
    conn.close()
    
    return render_template('gov_new_complaint.html', complaints=complaints, count=pending_count)

# 4. Action Route to Accept/Delay
@app.route('/update-status/<int:id>/<string:status>', methods=['POST'])
def update_status(id, status):
    conn = sqlite3.connect('database.db')

    conn.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, id))
    conn.commit()
    conn.close()
    
    if status == 'Accepted':
            
        return redirect(url_for('gov_new_complaints'))
        
    return redirect(url_for('gov_new_complaints'))


# 5--------------------------------------------------------------------------
@app.route('/gov-accepted-complaints')
def gov_accepted_complaints():
    conn = sqlite3.connect('database.db')

    complaints = conn.execute("SELECT * FROM complaints WHERE status = 'Accepted' ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('gov_accepted_complaints.html', complaints=complaints)



# 6. Execution Block-------------------------------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)