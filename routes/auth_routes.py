# backend/routes/auth_routes.py

from flask import Blueprint, request, jsonify
import psycopg2
from models import get_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'student')

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        """, (username, password, role))
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Username already exists"}), 409
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "❌ Username does not exist."}), 404

    if row[0] != password:
        return jsonify({"error": "❌ Incorrect password."}), 401

    return jsonify({"message": "Login successful!"}), 200


@auth_bp.route('/all-users', methods=['GET'])
def all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, total_points FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{"username": u[0], "role": u[1], "total_points": u[2] or 0} for u in users])


@auth_bp.route('/role/<username>', methods=['GET'])
def get_user_role(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return jsonify({"role": row[0]})
    return jsonify({"error": "User not found"}), 404


@auth_bp.route('/points/<username>')
def get_user_points(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT total_points FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return jsonify({"total_points": row[0] if row else 0})


@auth_bp.route('/user-attempts/<username>')
def get_user_attempts(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify([])

    user_id = user[0]
    cursor.execute("SELECT question_id, attempts, is_correct FROM user_attempts WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    result = [{"question_id": row[0], "attempts": row[1], "is_correct": bool(row[2])} for row in rows]
    return jsonify(result)


@auth_bp.route('/user/<username>', methods=['GET'])
def get_user_profile(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, full_name FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return jsonify({"username": row[0], "full_name": row[1] or ""})
    return jsonify({"error": "User not found"}), 404


@auth_bp.route('/update-profile', methods=['PUT'])
def update_profile():
    data = request.get_json()
    current_username = data.get('current_username')
    new_username = data.get('new_username')
    full_name = data.get('full_name')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = %s", (current_username,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if new_username and new_username != current_username:
        cursor.execute("SELECT id FROM users WHERE username = %s", (new_username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "New username is already taken"}), 409

    cursor.execute("""
        UPDATE users SET username = %s, full_name = %s WHERE username = %s
    """, (new_username or current_username, full_name, current_username))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Profile updated!"}), 200


@auth_bp.route('/change-password', methods=['PUT'])
def change_password():
    data = request.get_json()
    username = data.get('username')
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if row[0] != old_password:
        cursor.close()
        conn.close()
        return jsonify({"error": "Old password is incorrect"}), 403

    cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Password changed successfully!"}), 200


@auth_bp.route('/debug/users')
def debug_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)


@auth_bp.route('/leaderboard', methods=['GET'])
def leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, total_points FROM users ORDER BY total_points DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{"username": row[0], "total_points": row[1] or 0} for row in rows])


@auth_bp.route('/delete-user/<target_username>', methods=['DELETE'])
def delete_user(target_username):
    data = request.get_json()
    requesting_username = data.get("requesting_username")

    if not requesting_username:
        return jsonify({"error": "Requesting user not provided"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE username = %s", (requesting_username,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        return jsonify({"error": "Requesting user not found"}), 404

    if row[0] != "admin":
        cursor.close()
        conn.close()
        return jsonify({"error": "Only admins can delete users"}), 403

    if requesting_username == target_username:
        cursor.close()
        conn.close()
        return jsonify({"error": "You cannot delete yourself"}), 403

    cursor.execute("DELETE FROM users WHERE username = %s", (target_username,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": f"User '{target_username}' has been deleted."}), 200
