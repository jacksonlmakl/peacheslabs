from flask import Flask, request, jsonify
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
import os

app = Flask(__name__)
app.secret_key = 'test'

DATABASE_CONFIG = {
    "dbname": "account",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
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

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get("token")
        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            decoded_data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM \"USER\" WHERE id = %s", (decoded_data['user_id'],))
            user = cursor.fetchone()
            conn.close()

            if not user:
                return jsonify({"message": "Invalid token!"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"message": "Token is invalid!", "error": str(e)}), 401

        return f(user, *args, **kwargs)
    return decorated

@app.route('/upload', methods=['POST'])
@token_required
def upload_file(user):
    if 'file' not in request.files:
        return jsonify({"message": "No file provided!"}), 400

    uploaded_file = request.files['file']
    file_name = uploaded_file.filename
    file_type = uploaded_file.content_type
    allowed_types = ["application/pdf", "text/plain", "text/csv"]

    if file_type not in allowed_types:
        return jsonify({"message": f"Invalid file type! Only .pdf, .txt, and .csv are allowed."}), 400

    # Read the file content
    file_data = uploaded_file.read()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO files (user_id, file_name, file_type, file_data)
            VALUES (%s, %s, %s, %s)
        """, (user['id'], file_name, file_type, psycopg2.Binary(file_data)))
        conn.commit()
        conn.close()
        return jsonify({"message": f"File '{file_name}' uploaded successfully!"}), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"message": "Failed to upload file.", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)
