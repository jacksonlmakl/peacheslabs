import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Database configuration
DATABASE_CONFIG = {
    "dbname": "account",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}


# Local directory to save the files
DOWNLOAD_FOLDER = "downloaded_files"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DATABASE_CONFIG["dbname"],
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            host=DATABASE_CONFIG["host"],
            port=DATABASE_CONFIG["port"]
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

def download_files():
    """Downloads files from the `files` table and saves them locally."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query to fetch file data
        cursor.execute("SELECT id, file_name, file_type, file_data FROM files;")
        files = cursor.fetchall()

        if not files:
            print("No files found in the table.")
            return

        for file in files:
            file_path = os.path.join(DOWNLOAD_FOLDER, file["file_name"])
            with open(file_path, "wb") as f:
                f.write(file["file_data"])
            print(f"Downloaded: {file['file_name']} to {file_path}")

    except Exception as e:
        print(f"Error fetching files: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    download_files()
