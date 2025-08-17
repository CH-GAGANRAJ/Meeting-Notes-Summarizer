import os
from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
from dotenv import load_dotenv
import groq

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration checks
required_vars = ['GROQ_API_KEY', 'MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

# Configure Flask-Mail
app.config.update(
    MAIL_SERVER=os.getenv('MAIL_SERVER'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't'),
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key')
)

mail = Mail(app)

# Initialize Groq client
try:
    api=os.getenv("GROQ_API_KEY")
    groq_client = groq.Client(api_key=api)
except Exception as e:
    raise RuntimeError(f"Failed to initialize Groq client: {str(e)}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/summarize', methods=['POST'])
def summarize():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    transcript = data.get('transcript')
    instructions = data.get('instructions')

    if not transcript:
        return jsonify({"error": "Transcript is required"}), 400

    try:
        # Call Groq API for summarization
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes meeting notes according to user instructions."
                },
                {
                    "role": "user",
                    "content": f"Meeting transcript:\n{transcript}\n\nInstructions: {instructions or 'Provide a concise summary'}"
                }
            ],
            model="llama-3.3-70b-versatile",
        )

        summary = response.choices[0].message.content
        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"error": f"Summarization failed: {str(e)}"}), 500


@app.route('/share', methods=['POST'])
def share():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    summary = data.get('summary')
    recipients = data.get('recipients')

    if not summary or not recipients:
        return jsonify({"error": "Summary and recipients are required"}), 400

    try:
        msg = Message(
            subject="Meeting Notes Summary",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email.strip() for email in recipients.split(',')],
            body=summary
        )
        mail.send(msg)
        return jsonify({"status": "Email sent successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG', 'False') == 'True')