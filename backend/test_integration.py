import sys
import os
import json

# Add project root to sys.path so we can run from anywhere
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import database
from backend import nlp_engine

def run_tests():
    print("==================================================")
    print("Starting Integration Tests for Question Finder API")
    print("==================================================")
    
    # 1. Test Database Initialization & Seeding
    print("\n1. Testing DB Initialization and Auto-Seeding...")
    if os.path.exists(database.DATABASE_PATH):
        print(f"Removing old test database at {database.DATABASE_PATH}...")
        os.remove(database.DATABASE_PATH)
        
    database.init_db()
    print("Database initialized successfully.")
    
    # Verify seed questions
    all_questions = database.get_all_questions_for_similarity()
    print(f"Total seeded questions: {len(all_questions)}")
    assert len(all_questions) > 0, "Error: Seeding failed, questions table is empty."
    print("DB Seeding verified successfully.")
    
    # 2. Test User Creation
    print("\n2. Testing User Creation & Retrieval...")
    test_email = "test_student@finder.edu"
    test_hash = "mock_sha256_hashed_password"
    
    user_id = database.create_user(test_email, test_hash)
    print(f"User created with ID: {user_id}")
    assert user_id is not None, "Error: Failed to create user."
    
    # Try creating duplicate user
    dup_id = database.create_user(test_email, test_hash)
    assert dup_id is None, "Error: Duplicate user allowed in DB!"
    print("Duplicate user block verified.")
    
    # Retrieve user
    user = database.get_user_by_email(test_email)
    assert user is not None, "Error: Failed to retrieve user by email."
    assert user["email"] == test_email, "Error: User email mismatch."
    print("User retrieval verified successfully.")
    
    # 3. Test NLP Engine Auto-Tagging
    print("\n3. Testing NLP Engine Auto-Tagging...")
    test_cases = [
        ("What is the derivative of x squared?", "Mathematics"),
        ("Why do leaves look green under daylight?", "Biology"),
        ("Explain how binary search algorithm runs in O(log n) time.", "Computer Science"),
        ("Who fought in the American Civil War?", "History")
    ]
    
    for question, expected_tag in test_cases:
        from sentence_transformers import util
        q_emb = nlp_engine.get_model().encode(question, convert_to_tensor=True)
        scores = {}
        for topic, t_emb in nlp_engine.get_topic_embeddings().items():
            scores[topic] = util.cos_sim(q_emb, t_emb).item()
        print(f"Scores for '{question}':")
        for t, s in scores.items():
            print(f"  - {t}: {s:.4f}")
        tag = nlp_engine.auto_tag_question(question)
        print(f"Question: '{question}' -> Tagged: {tag} (Expected: {expected_tag})")
        assert tag == expected_tag, f"Error: Tag mismatch. Expected {expected_tag}, got {tag}"
    print("Auto-tagging verified successfully.")
    
    # 4. Test Semantic Similarity Matching & Question Saving
    print("\n4. Testing Question Saving & Similarity Matching...")
    user_question = "How does photosynthesis convert sunlight to energy?"
    
    # Compute embedding
    q_emb = nlp_engine.get_embedding(user_question)
    q_tag = nlp_engine.auto_tag_question(user_question)
    print(f"User asked: '{user_question}' -> Tag: {q_tag}")
    
    # Compute similarity against all past questions
    matches = []
    for q in all_questions:
        score = nlp_engine.compute_similarity(q_emb, q["embedding"])
        matches.append((q["id"], q["text"], score))
        
    matches.sort(key=lambda x: x[2], reverse=True)
    
    # Take top 3 similar questions
    top_matches = [m for m in matches if m[2] < 0.99][:3]
    
    print("Top matches found:")
    for mid, mtext, mscore in top_matches:
        print(f" - [{mid}] '{mtext}' (Score: {mscore:.4f})")
        
    # Verify that the best biology-related question matches (photosynthesis seed is in DB)
    best_match_text = top_matches[0][1]
    assert "photosynthesis" in best_match_text.lower() or "sunlight" in best_match_text.lower(), \
        f"Error: Expected biology match, got '{best_match_text}'"
    print("Semantic similarity matching verified successfully.")
    
    # Save the user question
    q_id = database.save_question(user_id, user_question, q_emb, q_tag)
    print(f"User question saved in DB with ID: {q_id}")
    
    # Save similarity records
    for mid, mtext, mscore in top_matches:
        database.save_similarity(q_id, mid, mscore)
    print("Similarity links saved in DB.")
    
    # 5. Test History Retrieval
    print("\n5. Testing User History & Filter Query...")
    history = database.get_user_history(user_id, tag_filter="All")
    print(f"Total history questions: {len(history)}")
    assert len(history) == 1, "Error: User history size mismatch."
    assert history[0]["text"] == user_question, "Error: History question text mismatch."
    assert len(history[0]["similar_questions"]) == 3, "Error: Saved similar questions list mismatch."
    print("General history retrieval verified.")
    
    # Filter by specific tag
    history_bio = database.get_user_history(user_id, tag_filter="Biology")
    assert len(history_bio) == 1, "Error: History tag filter failed to return Biology question."
    
    history_math = database.get_user_history(user_id, tag_filter="Mathematics")
    assert len(history_math) == 0, "Error: History tag filter returned unexpected results."
    print("History tag filtering verified.")
    
    print("\n==================================================")
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
