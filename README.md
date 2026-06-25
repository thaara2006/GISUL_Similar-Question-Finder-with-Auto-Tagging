# Similar Question Finder with Auto-Tagging

**Option chosen:** Deploy to Render (free tier).
**Tech stack:**
- Frontend: HTML, vanilla CSS, JavaScript.
- Backend: Flask (Python) with SQLite.
- AI/ML: `sentence-transformers` model `all-MiniLM-L6-v2` for embeddings, zero-shot topic tagging via cosine similarity against predefined topic centroids.

## Running locally

```bash
# clone the repo (replace <PAT> if you need private)
git clone https://github.com/thaara2006/GISUL_Similar-Question-Finder-with-Auto-Tagging.git
cd GISUL_Similar-Question-Finder-with-Auto-Tagging
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.app   # runs on http://127.0.0.1:8000
```

Open `frontend/index.html` in a browser.

## How the AI/ML works

- The backend loads a pre‑trained SentenceTransformer (`all-MiniLM-L6-v2`).
- When a user submits a question, the text is encoded to a 384‑dimensional embedding.
- **Topic tagging:** each topic has a centroid embedding computed from a few representative questions. The question embedding is compared to each centroid (cosine similarity) and the highest‑scoring topic becomes the tag.
- **Similarity search:** the question embedding is compared against embeddings of all previously stored questions; the top 3 most similar (excluding near‑duplicates) are returned.

## Deployment (Render)

The repository contains a `render.yaml` that tells Render how to build and run the service. When you connect the repo to Render, it will automatically install dependencies and start the Flask app on the provided port.
