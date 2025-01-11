from flask import Flask, request, render_template, redirect, url_for, flash
import sqlite3
import bcrypt
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secure secret key for session and flash messages

DATABASE_FILE = "core.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Generate a secure random session token
def generate_session_token():
    return secrets.token_urlsafe(32)

@app.route("/")
def index():
    session_token = request.args.get("token")
    if session_token:
        # Validate the session token
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username
            FROM USER u
            JOIN SESSION s ON u.id = s.user_id
            WHERE s.session_token = ?
        """, (session_token,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return f"Welcome, {user['username']}! <a href='/logout?token={session_token}'>Logout</a>"
        flash("Invalid session token.", "danger")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        try:
            # Insert the new user into the database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO USER (email, username, password_hash) VALUES (?, ?, ?)",
                (email, username, hashed_password),
            )
            conn.commit()
            conn.close()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email or username already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Retrieve the user's password hash
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM USER WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
            # Generate a secure session token
            session_token = generate_session_token()

            # Store the token in the SESSION table
            cursor.execute(
                "INSERT INTO SESSION (user_id, session_token) VALUES (?, ?)",
                (user["id"], session_token)
            )
            conn.commit()
            conn.close()

            # Redirect to the home page with the token in the URL
            flash("Login successful!", "success")
            return redirect(url_for("index", token=session_token))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session_token = request.args.get("token")
    if session_token:
        # Invalidate the session token
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM SESSION WHERE session_token = ?", (session_token,))
        conn.commit()
        conn.close()
        flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host=0.0.0.0, debug=True)
