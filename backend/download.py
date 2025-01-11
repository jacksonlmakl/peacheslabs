import psycopg2
from psycopg2.extras import RealDictCursor
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd
from bs4 import BeautifulSoup
import json
import csv
from transformers import AutoTokenizer, AutoModel
import torch
import io

# Database configuration
DATABASE_CONFIG = {
    "dbname": "account",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}

# Embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)
model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME)

# Database connection
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

# Ensure embeddings table exists
def ensure_embeddings_table(conn):
    """Creates the embeddings table if it doesn't exist."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR(768) NOT NULL
            );
        """)
        conn.commit()
        cursor.close()
        print("Embeddings table ensured.")
    except Exception as e:
        print(f"Error ensuring embeddings table: {e}")

# Detect content type and extract text
def extract_text(file_type, file_data):
    """Extracts text from various file types."""
    try:
        if file_type == "text/plain":
            return file_data.decode("utf-8")
        elif file_type == "application/pdf":
            reader = PdfReader(io.BytesIO(file_data))
            return "\n".join([page.extract_text() for page in reader.pages])
        elif file_type == "application/json":
            data = json.loads(file_data.decode("utf-8"))
            return json.dumps(data, indent=2)
        elif file_type in ["text/csv", "application/vnd.ms-excel"]:
            df = pd.read_csv(io.BytesIO(file_data))
            return df.to_csv(index=False)
        elif file_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            df = pd.read_excel(io.BytesIO(file_data))
            return df.to_csv(index=False)
        elif file_type == "text/html":
            soup = BeautifulSoup(file_data.decode("utf-8"), "html.parser")
            return soup.get_text(separator="\n").strip()
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(io.BytesIO(file_data))
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    except Exception as e:
        print(f"Error extracting text from file type {file_type}: {e}")
        return None

# Generate text embeddings
def generate_embeddings(text):
    """Generates embeddings for a given text using a transformer model."""
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).numpy()
    return embeddings[0]

# Process each row and insert embeddings
def process_files():
    """Processes files table row by row and inserts embeddings into the embeddings table."""
    conn = get_db_connection()
    if not conn:
        return

    ensure_embeddings_table(conn)

    try:
        cursor = conn.cursor(name="file_cursor", cursor_factory=RealDictCursor)

        # Query to fetch file data row by row
        cursor.execute("SELECT id, user_id, file_name, file_type, file_data FROM files;")

        for file in cursor:
            print(f"Processing File: {file['file_name']} (Type: {file['file_type']})")
            try:
                # Extract text
                content = extract_text(file["file_type"], bytes(file["file_data"]))
                if not content:
                    print(f"Skipping file {file['file_name']}: Unable to extract content.")
                    continue

                # Generate embeddings
                embedding = generate_embeddings(content)

                # Insert into embeddings table
                insert_cursor = conn.cursor()
                insert_cursor.execute("""
                    INSERT INTO embeddings (user_id, file_name, content, embedding)
                    VALUES (%s, %s, %s, %s)
                """, (file["user_id"], file["file_name"], content, embedding.tolist()))
                conn.commit()
                insert_cursor.close()

                print(f"File {file['file_name']} processed and inserted into embeddings table.")
            except Exception as e:
                print(f"Error processing file {file['file_name']}: {e}")

        cursor.close()
    except Exception as e:
        print(f"Error fetching files: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    process_files()
