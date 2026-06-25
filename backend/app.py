import os
import hashlib
import base64
import json
from flask import Flask, request, jsonify

from backend import database
from backend import nlp_engine

# Initialize Flask app
# static_folder points to the frontend directory relative to the backend script
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"),
    static_url_path=""
)

# Initialize database and NLP embeddings once at startup
print("Starting up: initializing database...")
database.init_db()
print("Starting up: loading NLP engine and caching topic embeddings...")
nlp_engine.get_topic_embeddings()
print("Application startup complete.")

# Helper: Hash Password
def hash_password(email: str, password: str) -> str:
    salted = f"{email.lower()}:{password}"
    return hashlib.sha256(salted.encode()).hexdigest()

# Helper: Token Generation & Verification
def generate_token(user_id: int, email: str) -> str:
    session_data = {"user_id": user_id, "email": email}
    session_str = json.dumps(session_data)
    return base64.b64encode(session_str.encode()).decode()

def verify_token(token: str) -> dict:
    try:
        session_str = base64.b64decode(token.encode()).decode()
        return json.loads(session_str)
    except Exception:
        return None

def get_current_user():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    return verify_token(token)

# Static file routing
@app.route("/")
def index():
    return app.send_static_file("index.html")

# API Endpoints
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"detail": "Email and password are required"}), 400
        
    if len(password) < 6:
        return jsonify({"detail": "Password must be at least 6 characters long"}), 400
        
    pw_hash = hash_password(email, password)
    user_id = database.create_user(email, pw_hash)
    
    if user_id is None:
        return jsonify({"detail": "An account with this email already exists"}), 400
        
    token = generate_token(user_id, email)
    return jsonify({"token": token, "email": email})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"detail": "Email and password are required"}), 400
        
    user = database.get_user_by_email(email)
    if not user:
        return jsonify({"detail": "Invalid email or password"}), 401
        
    pw_hash = hash_password(email, password)
    if user["password_hash"] != pw_hash:
        return jsonify({"detail": "Invalid email or password"}), 401
        
    token = generate_token(user["id"], email)
    return jsonify({"token": token, "email": email})

@app.route("/api/questions/ask", methods=["POST"])
def ask_question():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "Access denied. Missing or invalid Authorization header."}), 401
        
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"detail": "Question text cannot be empty"}), 400
    if len(text) > 1000:
        return jsonify({"detail": "Question is too long (max 1000 characters)"}), 400
        
    user_id = current_user["user_id"]
    
    # 1. Get embedding for new question
    embedding = nlp_engine.get_embedding(text)
    
    # 2. Auto-tag the question
    tag = nlp_engine.auto_tag_question(text)
    
    # 3. Find similar past questions
    all_past_questions = database.get_all_questions_for_similarity()
    
    similar_matches = []
    for q in all_past_questions:
        score = nlp_engine.compute_similarity(embedding, q["embedding"])
        similar_matches.append({
            "id": q["id"],
            "text": q["text"],
            "tag": q["tag"],
            "similarity_score": score,
            "created_at": q["created_at"]
        })
        
    # Sort by similarity descending
    similar_matches.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # Take top 3 similar questions. Exclude exact same question matches (score > 0.99)
    filtered_matches = [m for m in similar_matches if m["similarity_score"] < 0.99][:3]
    
    # 4. Save the question to the database
    question_id = database.save_question(user_id, text, embedding, tag)
    
    # 5. Save similarity links
    for match in filtered_matches:
        database.save_similarity(question_id, match["id"], match["similarity_score"])
        
    return jsonify({
        "id": question_id,
        "text": text,
        "tag": tag,
        "similar_questions": filtered_matches
    })

@app.route("/api/questions/history", methods=["GET"])
def get_history():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "Access denied. Missing or invalid Authorization header."}), 401
        
    tag = request.args.get("tag", "All")
    user_id = current_user["user_id"]
    
    history = database.get_user_history(user_id, tag_filter=tag)
    return jsonify(history)

@app.route("/api/tags", methods=["GET"])
def get_tags():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "Access denied. Missing or invalid Authorization header."}), 401
        
    return jsonify(list(nlp_engine.TOPIC_REPRESENTATIVES.keys()))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)