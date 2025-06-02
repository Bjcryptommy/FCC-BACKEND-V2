# backend/models.py

import psycopg2
from psycopg2 import sql

# Render PostgreSQL credentials
DB_NAME = "fcc_clone"
DB_USER = "fcc_clone_user"
DB_PASSWORD = "essfA7Cp2fMoEGtxj4VtZkROg3bSnlW3"
DB_HOST = "dpg-d0umgre3jp1c738irgug-a.oregon-postgres.render.com"
DB_PORT = "5432"

def get_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def create_tables():
    conn = get_db()
    cur = conn.cursor()

    # USERS table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            full_name TEXT,
            password TEXT,
            role TEXT DEFAULT 'student',
            total_points INTEGER DEFAULT 0
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            title TEXT,
            description TEXT,
            language TEXT DEFAULT 'General'
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            course_id INTEGER REFERENCES courses(id),
            title TEXT,
            video_url TEXT,
            lesson_text TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER REFERENCES lessons(id),
            question_text TEXT,
            correct_answer_id INTEGER
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id SERIAL PRIMARY KEY,
            question_id INTEGER REFERENCES questions(id),
            answer_text TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER REFERENCES users(id),
            lesson_id INTEGER REFERENCES lessons(id),
            is_completed BOOLEAN
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_points (
            user_id INTEGER REFERENCES users(id),
            lesson_id INTEGER REFERENCES lessons(id),
            points INTEGER,
            badge TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_attempts (
            user_id INTEGER REFERENCES users(id),
            question_id INTEGER REFERENCES questions(id),
            attempts INTEGER DEFAULT 0,
            is_correct BOOLEAN DEFAULT FALSE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER REFERENCES lessons(id),
            username TEXT,
            text TEXT,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    conn.commit()
    cur.close()
    conn.close()

create_tables()
