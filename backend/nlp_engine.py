import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

# Global lazy-loaded SentenceTransformer model
_model = None

def get_model():
    global _model
    if _model is None:
        print("Initializing SentenceTransformer model 'all-MiniLM-L6-v2'...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Model initialized successfully.")
    return _model

# Define our fixed list of topic tags and several representative questions for each.
# We will use the centroid (average) embedding of these questions to define each topic.
TOPIC_REPRESENTATIVES = {
    "Mathematics": [
        "How do I solve this equation for x?",
        "What is the formula for calculating the area, volume, or perimeter?",
        "Explain calculus concepts like derivatives, integrals, limits, and tangent lines.",
        "What is the value of pi, square roots, or logarithm calculations?",
        "How do you calculate probability, permutations, or statistical standard deviations?"
    ],
    "Physics": [
        "What is the law of gravity, motion, or electromagnetic forces?",
        "Explain the theory of relativity, quantum mechanics, or string theory.",
        "How does kinetic, potential, thermal, or mechanical energy work?",
        "What is the speed of light, sound frequency, or light wave refraction?",
        "Explain thermodynamics, entropy, and heat transfer equations."
    ],
    "Chemistry": [
        "What is the molecular structure of this compound or organic molecule?",
        "Explain chemical reactions, catalysts, and how chemical equations balance.",
        "How does the periodic table organize chemical elements and their properties?",
        "What is the difference between covalent, ionic, and hydrogen bonds?",
        "How do acids and bases interact, and what does the pH scale represent?"
    ],
    "Biology": [
        "How does photosynthesis convert sunlight and carbon dioxide into chemical energy?",
        "What is the function of eukaryotic cells, mitochondria, DNA, and ribosomes?",
        "Explain genetics, DNA replication, heredity, and natural selection evolution.",
        "Describe the anatomy of the human circulatory system, brain, or heart.",
        "What are the roles of different ecosystems, food webs, and environmental biomes?"
    ],
    "Computer Science": [
        "What is the difference between a list, dictionary, and a tuple in Python?",
        "How does a binary search algorithm run in logarithmic log n time complexity?",
        "Explain how database indexes, primary keys, and SQL queries work.",
        "What is the difference between TCP and UDP protocols in computer networking?",
        "How do I write a recursive function or handle memory allocation in programming?"
    ],
    "History": [
        "What caused the fall of the Western Roman Empire or ancient civilizations?",
        "Who fought in the American Civil War, World War I, or World War II?",
        "What were the primary triggers, events, and results of the French Revolution in 1789?",
        "Describe the reign of ancient kings, emperors, queens, and dynasties.",
        "What was the significance of the industrial revolution and colonization?"
    ],
    "Literature": [
        "What is the theme of fate, tragedy, or love in Shakespeare's Romeo and Juliet?",
        "Who wrote the play Hamlet, and what is its main character plot?",
        "Explain literary terms like metaphor, simile, irony, and symbolism.",
        "What is the grammar rule, sentence structure, or part of speech in English?",
        "Describe the main character's arc, narrative conflict, or setting in the novel."
    ],
    "Economics": [
        "Explain the laws of supply and demand, price elasticity, and market equilibrium.",
        "What is inflation, gross domestic product GDP, and how is it measured?",
        "How do interest rates set by central banks affect the economy?",
        "Describe the concepts of microeconomics, macroeconomics, and fiscal policy.",
        "What is trade deficit, currency exchange rates, or stock market shares?"
    ]
}

# Dummy keys so we can reference them
TOPIC_DEFINITIONS = {k: k for k in TOPIC_REPRESENTATIVES.keys()}

# Cached topic centroid embeddings to avoid recalculating on every request
_topic_embeddings = None

def get_topic_embeddings():
    global _topic_embeddings
    if _topic_embeddings is None:
        model = get_model()
        print("Pre-calculating topic centroid embeddings...")
        _topic_embeddings = {}
        
        for topic, sentences in TOPIC_REPRESENTATIVES.items():
            # Encode all representative questions for this topic
            embeddings = model.encode(sentences, convert_to_tensor=True)
            # Compute the centroid (average) vector along dimension 0
            centroid = torch.mean(embeddings, dim=0)
            _topic_embeddings[topic] = centroid
            
        print("Topic centroid embeddings calculated successfully.")
    return _topic_embeddings

def get_embedding(text: str) -> list[float]:
    """Generates a 384-dimensional vector embedding for the input text."""
    model = get_model()
    embedding_tensor = model.encode(text, convert_to_tensor=True)
    return embedding_tensor.cpu().numpy().tolist()

def auto_tag_question(question_text: str) -> str:
    """Classifies a question into a topic using cosine similarity against predefined topic centroids."""
    model = get_model()
    topic_embeddings = get_topic_embeddings()
    
    # Generate question embedding
    q_embedding = model.encode(question_text, convert_to_tensor=True)
    
    best_tag = "General"
    best_score = -1.0
    
    # Compare similarity against each topic centroid
    for topic, centroid_embedding in topic_embeddings.items():
        score = util.cos_sim(q_embedding, centroid_embedding).item()
        if score > best_score:
            best_score = score
            best_tag = topic
            
    # If the highest match is extremely weak, fallback to General
    if best_score < 0.15:
        best_tag = "General"
        
    return best_tag

def compute_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    """Computes the cosine similarity between two float vector embeddings."""
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(dot_product / (norm_a * norm_b))
