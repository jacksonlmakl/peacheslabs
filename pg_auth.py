from flask import Flask, request, jsonify
import psycopg2
import bcrypt
import jwt
import datetime
from functools import wraps
import secrets
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATABASE_CONFIG = {
    "dbname": "coredb",        # Replace with your database name
    "user": "postgres",        # Replace with your PostgreSQL username
    "password": "password123", # Replace with your PostgreSQL password
    "host": "localhost",       # Replace with your PostgreSQL host
    "port": "5432"             # Replace with your PostgreSQL port (default is 5432)
}

def get_db_connection():
    conn = psycopg2.connect(
        dbname=DATABASE_CONFIG["dbname"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"]
    )
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "USER" (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "SESSION" (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        session_token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES "USER" (id)
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
            data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM \"USER\" WHERE id = %s", (data['user_id'],))
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
            "INSERT INTO \"USER\" (email, username, password_hash) VALUES (%s, %s, %s)",
            (email, username, hashed_password)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'User registered successfully!'}), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        return jsonify({'message': 'Email or username already exists!'}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM \"USER\" WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
        # Generate a new token
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.secret_key, algorithm="HS256")

        # Invalidate old tokens (optional: keep only one session per user)
        cursor.execute("DELETE FROM \"SESSION\" WHERE user_id = %s", (user['id'],))

        # Store the new token in the SESSION table
        cursor.execute(
            "INSERT INTO \"SESSION\" (user_id, session_token) VALUES (%s, %s)",
            (user['id'], token)
        )
        conn.commit()
        conn.close()

        return jsonify({'token': token}), 200
    else:
        conn.close()
        return jsonify({'message': 'Invalid username or password!'}), 401

@app.route('/protected', methods=['GET'])
@token_required
def protected(user):
    return jsonify({'message': f'Welcome, {user["username"]}!'}), 200

if __name__ == '__main__':
    create_tables()
    app.run(host="0.0.0.0", port=5001, debug=False)
