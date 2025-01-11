from flask import Flask, request, jsonify
import sqlite3
import bcrypt
import jwt
import datetime
from functools import wraps
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32) 
DATABASE_FILE = "core.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS USER (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SESSION (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_token TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES USER (id)
    )
    """)
    conn.commit()
    conn.close()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM USER WHERE id = ?", (data['user_id'],))
            user = cursor.fetchone()
            conn.close()

            if not user:
                return jsonify({'message': 'Invalid token!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(user, *args, **kwargs)

    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not email or not username or not password:
        return jsonify({'message': 'All fields are required!'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO USER (email, username, password_hash) VALUES (?, ?, ?)",
            (email, username, hashed_password)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'User registered successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Email or username already exists!'}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USER WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
        # Generate a new token
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        # Invalidate old tokens (optional: keep only one session per user)
        cursor.execute("DELETE FROM SESSION WHERE user_id = ?", (user['id'],))

        # Store the new token in the SESSION table
        cursor.execute(
            "INSERT INTO SESSION (user_id, session_token) VALUES (?, ?)",
            (user['id'], token)
        )
        conn.commit()
        conn.close()

        return jsonify({'token': token}), 200
    else:
        conn.close()
        return jsonify({'message': 'Invalid username or password!'}), 401

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            conn = get_db_connection()
            cursor = conn.cursor()

            # Validate the token against the SESSION table
            cursor.execute("SELECT * FROM SESSION WHERE session_token = ?", (token,))
            session = cursor.fetchone()

            if not session:
                conn.close()
                return jsonify({'message': 'Invalid or expired token!'}), 401

            # Get the user associated with the token
            cursor.execute("SELECT * FROM USER WHERE id = ?", (data['user_id'],))
            user = cursor.fetchone()
            conn.close()

            if not user:
                return jsonify({'message': 'Invalid token!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(user, *args, **kwargs)

    return decorated


@app.route('/protected', methods=['GET'])
@token_required
def protected(user):
    return jsonify({'message': f'Welcome, {user["username"]}!'}), 200

if __name__ == '__main__':
    create_tables()
    app.run(host="0.0.0.0", port=5001, debug=False)
