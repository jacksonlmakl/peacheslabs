import sqlite3

DATABASE_FILE = "core.db"
SQL_SETUP_FILE = "database.sql"

def setup_database():
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Read and execute the SQL setup file
        with open(SQL_SETUP_FILE, "r") as f:
            sql_script = f.read()
        cursor.executescript(sql_script)

        conn.commit()
        print("Database setup completed successfully.")
    except sqlite3.Error as e:
        print("Error setting up the database:", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_database()
