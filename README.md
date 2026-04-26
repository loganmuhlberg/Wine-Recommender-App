# Vinny — AI-Powered Wine Recommender

**Domain:** Personalized AI Recommendation Systems, Wine
**Team:** Logan

---

## Overview

Vinny is a personalized wine recommendation web application that combines semantic search over a large wine review corpus with a large language model to deliver tailored, explainable wine recommendations. Users complete a taste profile quiz, submit queries, and receive curated wine selections with rationale, food pairing suggestions, and direct purchase links, with the ability to iteratively refine results through conversational feedback.

---

## Architecture Overview

### Data Flow

```
User (Streamlit Frontend)
        │
        │  HTTP/JSON requests
        ▼
FastAPI Backend (main.py)
        │
        ├──► SQLite (app.db)
        │    └── Users, TasteProfiles, Recommendations, RecommendedWines
        │
        ├──► ChromaDB (wine_db/)
        │    └── 169,000 wine description embeddings
        │    └── Queried via sentence-transformers (all-MiniLM-L6-v2)
        │
        ├──► Google Gemini 2.5 Flash API
        │    └── Reasons over RAG candidates
        │    └── Returns structured JSON recommendations
        │
        └──► Brave Search API
             └── Enriches picks with bottle thumbnails and buy links
```

### Full Recommendation Pipeline

```
1. User submits query + sidebar filters
2. FastAPI loads taste profile from SQLite
3. Embeddings layer:
    - Embeds query text using sentence-transformers
    - Applies metadata filters (price, region, country, varietal)
    - ChromaDB returns top 10 semantically similar wines (MMR optional)
4. Gemini 2.5 Flash:
   - Receives taste profile + query + 10 candidates
   - Selects best 3 and writes rationale, food pairing, serving suggestion
   - Returns structured JSON validated against Pydantic schema
5. Brave Search API:
   - Fires image + web search per selected wine
   - Returns bottle thumbnail URL and retail buy link
6. Results assembled and saved to SQLite
7. RecommendResponse returned to Streamlit frontend
8. User can refine — feedback appended to conversation history
   and pipeline re-runs with updated query + new candidates
```


## Data Sources

Kaggle: Data sourced from https://www.kaggle.com/datasets/zynicide/wine-reviews
- Utilized in creating the ChromaDB database for semantic search and RAG retrieval.

---

## Prerequisites

- Python 3.10+
- Anaconda or virtualenv (recommended)

---

## API Keys Required

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=your_gemini_api_key_here
BRAVE_API_KEY=your_brave_search_api_key_here
```

### Getting API Keys

**Gemini API Key:**
1. Go to https://aistudio.google.com
2. Sign in with a Google account
3. Click "Get API Key" → "Create API key"
4. Copy the key into your `.env` file

**Brave Search API Key:**
1. Go to https://api-dashboard.search.brave.com
2. Create an account and subscribe to the free tier
3. Generate an API key from the dashboard
4. Copy the key into your `.env` file

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/loganmuhlberg/Wine-Recommender-App.git
cd Wine-Recommender-App
```

### 2. Create and activate a virtual environment

```bash
# Using conda
conda create -n vinara python=3.11
conda activate vinara

# Or using venv
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
```

### 5. Build the ChromaDB vector database

This step embeds all wine descriptions and must be run once before starting the app. It takes approximately 15–30 minutes on CPU.

```bash
cd backend
python scripts/ingest_kaggle.py
```

To test with a small subset first:

```bash
python scripts/ingest_kaggle.py --limit 1000
```

### 7. Extract filter options for the frontend

```bash
python scripts/extract_filter_options.py
```

This generates `frontend/filter_options.json` containing the available countries, regions, and varietals for the sidebar dropdowns.

### 8. Start the backend server

Open a terminal and run from the `backend/` directory:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive API docs are at `http://localhost:8000/docs`.

### 9. Start the frontend

Open a second terminal and run from the `frontend/` directory:

```bash
cd frontend
streamlit run app.py
```

The app will be available at `http://localhost:8501`.


## Usage

1. Open `http://localhost:8501` in your browser
2. Create a new account or log in with your Guest ID
3. Complete the taste profile quiz to personalize recommendations
4. Navigate to the Recommendations page
5. Type a natural language query describing what you're looking for
6. Use the sidebar filters to narrow by price, country, region, or varietal
7. View your three recommended wines with rationale and buy links
8. Use the refinement box to adjust the selection based on feedback
9. View past recommendations in the History page
