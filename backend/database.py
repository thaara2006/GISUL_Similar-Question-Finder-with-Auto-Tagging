import sqlite3
import json
import os
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding_json TEXT NOT NULL,
        tag TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    # Create similarities table (stores links between asked questions and found past questions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS similarities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        similar_question_id INTEGER NOT NULL,
        similarity_score REAL NOT NULL,
        FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
        FOREIGN KEY (similar_question_id) REFERENCES questions (id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()
    
    # Perform seed check
    seed_database_if_empty()

def seed_database_if_empty():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM questions")
    count = cursor.fetchone()["count"]
    
    if count > 0:
        conn.close()
        return
        
    print("Database is empty. Seeding initial questions for semantic similarity finder...")
    
    # We need to import nlp_engine to generate embeddings and tags for seed questions
    from backend import nlp_engine
    
    # We will create a default system user for seed questions
    cursor.execute("SELECT id FROM users WHERE email = 'system@finder.edu'")
    system_user = cursor.fetchone()
    
    if system_user:
        system_user_id = system_user["id"]
    else:
        # Create system user
        # Standard dummy hash since this is a system utility account
        dummy_hash = "system_dummy_password_hash"
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)", 
            ("system@finder.edu", dummy_hash)
        )
        system_user_id = cursor.lastrowid
        
    seed_questions = [
        # Biology
        "How do plants convert sunlight into chemical energy?",
        "What are the main functions of mitochondria in a eukaryotic cell?",
        "What is the role of ribosomes in protein synthesis?",
        "What is the function of red blood cells in the circulatory system?",
        # Physics
        "What is the speed of light in a vacuum and how does it affect time?",
        "Describe the atomic model proposed by Niels Bohr.",
        "Explain Newton's three laws of motion with real-world examples.",
        "What is the theory of general relativity and who formulated it?",
        # Chemistry
        "How does the periodic table organize chemical elements?",
        "What is a covalent bond in chemistry and how does it share electrons?",
        "Explain the difference between acids and bases using pH scale.",
        # Mathematics
        "What is the formula for the area of a circle and how is it derived?",
        "Solve for x in the linear equation: 2x + 5 = 15.",
        "What is the quadratic formula used for and what are its terms?",
        # Computer Science
        "What is the difference between a list and a tuple in Python?",
        "Explain what an IP address is and how it works in computer networking.",
        "What is a database index and why does it speed up queries?",
        # History
        "Who was the first emperor of Rome and when did he rule?",
        "What caused the fall of the Western Roman Empire?",
        "What were the primary triggers of the French Revolution in 1789?",
        # Literature
        "What is the theme of fate in Shakespeare's Romeo and Juliet?",
        "Who wrote the famous play Hamlet and what is its main plot?",
        # Economics
        "Explain the laws of supply and demand and market equilibrium.",
        "What is inflation and how is it measured by governments?"
    ]
    
    for q_text in seed_questions:
        print(f"Processing seed question: '{q_text}'...")
        embedding = nlp_engine.get_embedding(q_text)
        tag = nlp_engine.auto_tag_question(q_text)
        
        cursor.execute(
            "INSERT INTO questions (user_id, text, embedding_json, tag) VALUES (?, ?, ?, ?)",
            (system_user_id, q_text, json.dumps(embedding), tag)
        )
        
    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

def create_user(email, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def save_question(user_id, text, embedding, tag):
    conn = get_db_connection()
    cursor = conn.cursor()
    embedding_json = json.dumps(embedding)
    cursor.execute(
        "INSERT INTO questions (user_id, text, embedding_json, tag) VALUES (?, ?, ?, ?)",
        (user_id, text, embedding_json, tag)
    )
    conn.commit()
    question_id = cursor.lastrowid
    conn.close()
    return question_id

def save_similarity(question_id, similar_question_id, similarity_score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO similarities (question_id, similar_question_id, similarity_score) VALUES (?, ?, ?)",
        (question_id, similar_question_id, similarity_score)
    )
    conn.commit()
    conn.close()

def get_all_questions_for_similarity():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch questions to run similarity comparisons against.
    # Exclude system-user filter if we compare against ALL questions (system + user)
    cursor.execute("SELECT id, text, embedding_json, tag, created_at FROM questions")
    rows = cursor.fetchall()
    conn.close()
    
    questions = []
    for r in rows:
        questions.append({
            "id": r["id"],
            "text": r["text"],
            "embedding": json.loads(r["embedding_json"]),
            "tag": r["tag"],
            "created_at": r["created_at"]
        })
    return questions

def get_user_history(user_id, tag_filter=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to fetch all questions asked by this specific user
    if tag_filter and tag_filter != "All":
        cursor.execute(
            "SELECT id, text, tag, created_at FROM questions WHERE user_id = ? AND tag = ? ORDER BY created_at DESC",
            (user_id, tag_filter)
        )
    else:
        cursor.execute(
            "SELECT id, text, tag, created_at FROM questions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        
    question_rows = cursor.fetchall()
    
    history = []
    for q_row in question_rows:
        q_id = q_row["id"]
        
        # For each question, query the similarities table to find links to similar questions shown
        cursor.execute("""
            SELECT q.id, q.text, q.tag, s.similarity_score, q.created_at
            FROM similarities s
            JOIN questions q ON s.similar_question_id = q.id
            WHERE s.question_id = ?
            ORDER BY s.similarity_score DESC
        """, (q_id,))
        
        similar_rows = cursor.fetchall()
        sim_list = []
        for s_row in similar_rows:
            sim_list.append({
                "id": s_row["id"],
                "text": s_row["text"],
                "tag": s_row["tag"],
                "similarity_score": s_row["similarity_score"],
                "created_at": s_row["created_at"]
            })
            
        history.append({
            "id": q_row["id"],
            "text": q_row["text"],
            "tag": q_row["tag"],
            "created_at": q_row["created_at"],
            "similar_questions": sim_list
        })
        
    conn.close()
    return history
