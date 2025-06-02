from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os


# Load environment variables from .env
load_dotenv()

# Import after .env is loaded
from models import create_tables
from routes.auth_routes import auth_bp
from routes.course_routes import course_bp
from routes.quiz_routes import quiz_bp
from routes.comment_routes import comment_bp

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secret123')  # fallback if not set
CORS(app)

# Create tables (currently for SQLite, update when PostgreSQL is wired)
create_tables()

# Register blueprints
app.register_blueprint(comment_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(course_bp)
app.register_blueprint(quiz_bp)

@app.route('/')
def home():
    return "FCC Clone Backend Running!"

if __name__ == '__main__':
    app.run(debug=True)

