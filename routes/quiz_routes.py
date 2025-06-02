# backend/routes/quiz_routes.py

from flask import Blueprint, request, jsonify
import psycopg2
import os

quiz_bp = Blueprint('quiz', __name__)

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )

@quiz_bp.route('/questions', methods=['POST'])
def add_question():
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    question_text = data.get('question_text')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO questions (lesson_id, question_text) VALUES (%s, %s) RETURNING id", (lesson_id, question_text))
    question_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return jsonify({"message": "Question added", "question_id": question_id}), 201

@quiz_bp.route('/answers', methods=['POST'])
def add_answers():
    data = request.get_json()
    question_id = data.get('question_id')
    answers = data.get('answers')

    conn = get_db()
    cursor = conn.cursor()

    correct_answer_id = None

    for answer in answers:
        cursor.execute("INSERT INTO answers (question_id, answer_text) VALUES (%s, %s) RETURNING id", (question_id, answer['text']))
        answer_id = cursor.fetchone()[0]
        if answer.get('is_correct', False):
            correct_answer_id = answer_id

    if correct_answer_id:
        cursor.execute("UPDATE questions SET correct_answer_id = %s WHERE id = %s", (correct_answer_id, question_id))

    conn.commit()
    conn.close()
    return jsonify({"message": "Answers added"}), 201

@quiz_bp.route('/submit-answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    username = data.get('username')
    question_id = data.get('question_id')
    selected_answer_id = data.get('answer_id')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_row = cursor.fetchone()
    if not user_row:
        return jsonify({"error": "User not found"}), 404
    user_id = user_row[0]

    cursor.execute("SELECT correct_answer_id FROM questions WHERE id = %s", (question_id,))
    correct_row = cursor.fetchone()
    if not correct_row:
        return jsonify({"error": "Question not found"}), 404
    correct_answer_id = correct_row[0]

    cursor.execute("SELECT attempts, is_correct FROM user_attempts WHERE user_id = %s AND question_id = %s", (user_id, question_id))
    attempt = cursor.fetchone()

    if attempt and attempt[1]:
        return jsonify({"message": "Already answered correctly"}), 200

    if attempt:
        attempts = attempt[0] + 1
        cursor.execute("UPDATE user_attempts SET attempts = %s WHERE user_id = %s AND question_id = %s", (attempts, user_id, question_id))
    else:
        attempts = 1
        cursor.execute("INSERT INTO user_attempts (user_id, question_id, attempts) VALUES (%s, %s, %s)", (user_id, question_id, attempts))

    if selected_answer_id == correct_answer_id:
        cursor.execute("UPDATE user_attempts SET is_correct = TRUE WHERE user_id = %s AND question_id = %s", (user_id, question_id))
        points = 10 if attempts == 1 else 7 if attempts == 2 else 5 if attempts == 3 else 0
        cursor.execute("UPDATE users SET total_points = total_points + %s WHERE id = %s", (points, user_id))
        conn.commit()
        conn.close()
        return jsonify({"correct": True, "message": "Correct answer!", "points_awarded": points})

    conn.commit()
    conn.close()
    return jsonify({"correct": False, "message": "Incorrect. Try again.", "attempts": attempts})

@quiz_bp.route('/questions/<int:question_id>/answers', methods=['GET'])
def get_answers_for_question(question_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, answer_text FROM answers WHERE question_id = %s", (question_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": row[0], "text": row[1]} for row in rows])

@quiz_bp.route('/quiz/<int:lesson_id>', methods=['GET'])
def get_quiz_by_lesson(lesson_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question_text FROM questions WHERE lesson_id = %s", (lesson_id,))
    questions = cursor.fetchall()
    if not questions:
        conn.close()
        return jsonify([])

    result = []
    for qid, qtext in questions:
        cursor.execute("SELECT id, answer_text FROM answers WHERE question_id = %s", (qid,))
        answers = cursor.fetchall()
        result.append({"id": qid, "question": qtext, "answers": [{"id": a[0], "text": a[1]} for a in answers]})

    conn.close()
    return jsonify(result)

@quiz_bp.route('/user-progress/<username>', methods=['GET'])
def get_user_progress(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify([])
    user_id = user[0]
    cursor.execute("""
        SELECT ua.question_id, ua.attempts, ua.is_correct, l.title
        FROM user_attempts ua
        JOIN questions q ON ua.question_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        WHERE ua.user_id = %s
    """, (user_id,))
    results = cursor.fetchall()
    conn.close()
    return jsonify([{
        "question_id": row[0],
        "attempts": row[1],
        "is_correct": bool(row[2]),
        "lesson_title": row[3]
    } for row in results])

@quiz_bp.route('/questions/<int:question_id>/delete', methods=['DELETE'])
def delete_question(question_id):
    conn = get_db()
    cursor = conn.cursor()

    # First delete answers linked to this question
    cursor.execute("DELETE FROM answers WHERE question_id = %s", (question_id,))
    
    # Then delete any user attempts related to this question
    cursor.execute("DELETE FROM user_attempts WHERE question_id = %s", (question_id,))
    
    # Finally delete the question
    cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))

    conn.commit()
    conn.close()
    return jsonify({"message": "Question deleted successfully!"})
