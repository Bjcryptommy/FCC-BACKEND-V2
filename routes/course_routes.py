# backend/routes/course_routes.py

from flask import Blueprint, request, jsonify
import psycopg2
import os

course_bp = Blueprint('course', __name__)

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )

# ----------------------------------------
# ✅ Add a new course (admin only)
# ----------------------------------------
@course_bp.route('/courses', methods=['POST'])
def add_course():
    data = request.get_json()
    username = data.get('username')
    title = data.get('title')
    description = data.get('description')
    language = data.get('language', 'General')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user or user[0] != 'admin':
        return jsonify({"error": "Only admins can add courses."}), 403

    cursor.execute(
        "INSERT INTO courses (title, description, language) VALUES (%s, %s, %s)",
        (title, description, language)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Course added successfully"}), 201

# ----------------------------------------
# ✅ View all courses
# ----------------------------------------
@course_bp.route('/courses', methods=['GET'])
def get_courses():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses")
    rows = cursor.fetchall()
    conn.close()

    courses = [{
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "language": row[3] if len(row) > 3 else "General"
    } for row in rows]

    return jsonify(courses)

# ----------------------------------------
# ✅ Add lesson to a course
# ----------------------------------------
@course_bp.route('/lessons', methods=['POST'])
def add_lesson():
    data = request.get_json()
    course_id = data.get('course_id')
    title = data.get('title')
    video_url = data.get('video_url')
    lesson_text = data.get('lesson_text')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO lessons (course_id, title, video_url, lesson_text) VALUES (%s, %s, %s, %s)",
        (course_id, title, video_url, lesson_text)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Lesson added successfully"}), 201

# ----------------------------------------
# ✅ View lessons for a course
# ----------------------------------------
@course_bp.route('/courses/<int:course_id>/lessons', methods=['GET'])
def get_lessons(course_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lessons WHERE course_id = %s", (course_id,))
    rows = cursor.fetchall()
    conn.close()

    lessons = [{
        "id": row[0],
        "course_id": row[1],
        "title": row[2],
        "video_url": row[3],
        "lesson_text": row[4]
    } for row in rows]

    return jsonify(lessons)

# ----------------------------------------
# ✅ Delete a course (with cascading deletes)
# ----------------------------------------
@course_bp.route('/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    conn = get_db()
    cursor = conn.cursor()

    # 1. Get all lesson IDs for this course
    cursor.execute("SELECT id FROM lessons WHERE course_id = %s", (course_id,))
    lesson_ids = [row[0] for row in cursor.fetchall()]

    # 2. Delete questions linked to those lessons
    for lesson_id in lesson_ids:
        cursor.execute("DELETE FROM questions WHERE lesson_id = %s", (lesson_id,))
        cursor.execute("DELETE FROM user_progress WHERE lesson_id = %s", (lesson_id,))
        cursor.execute("DELETE FROM user_points WHERE lesson_id = %s", (lesson_id,))
        cursor.execute("DELETE FROM comments WHERE lesson_id = %s", (lesson_id,))

    # 3. Delete lessons
    cursor.execute("DELETE FROM lessons WHERE course_id = %s", (course_id,))

    # 4. Finally, delete the course
    cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": f"Course {course_id} and related data deleted"}), 200


# ----------------------------------------
# ✅ Delete a lesson (and related data)
# ----------------------------------------
@course_bp.route('/lessons/<int:lesson_id>', methods=['DELETE'])
def delete_lesson(lesson_id):
    conn = get_db()
    cursor = conn.cursor()

    # Delete dependent records first (order matters!)
    cursor.execute("DELETE FROM questions WHERE lesson_id = %s", (lesson_id,))
    cursor.execute("DELETE FROM user_progress WHERE lesson_id = %s", (lesson_id,))
    cursor.execute("DELETE FROM user_points WHERE lesson_id = %s", (lesson_id,))
    cursor.execute("DELETE FROM comments WHERE lesson_id = %s", (lesson_id,))

    # Then delete the lesson itself
    cursor.execute("DELETE FROM lessons WHERE id = %s", (lesson_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": f"Lesson {lesson_id} and its related data deleted"}), 200
