# Semantix - Semantic Academic Search Platform

A semantic search and knowledge graph application for exploring academic papers across software engineering, cloud computing, DevOps, and AI/ML domains. Built with Flask and transformer-based embeddings, Semantix classifies user queries by intent and retrieves relevant papers from OpenAlex, re-ranking results using semantic similarity and visualising paper relationships as an interactive knowledge graph.

## Disclaimer

This project was developed by **Bwalya Kalambo** as a Final Year Project for the Bachelor of Science in Software Engineering programme at **The Zambia University of Technology**. It is shared here for portfolio and demonstration purposes only. All rights to use, distribute, or modify this work are held by The Zambia University of Technology.

## Features

- **Intent-Based Search** — Automatically classifies queries into domains (Software Engineering, Cloud, DevOps, AI/ML)
- **Semantic Re-ranking** — Uses transformer embeddings to re-rank search results for better accuracy
- **Interactive Knowledge Graph** — Cytoscape.js-powered visualisation of paper relationships
- **Self-Learning** — Automatically learns from unknown queries to improve classification over time
- **Manual Training** — Add training examples and retrain the classifier through the UI

## Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy with SQLite
- **ML Models**: sentence-transformers (MiniLM-L6-v2), scikit-learn
- **Vector Search**: FAISS
- **Data Source**: OpenAlex API
- **Frontend**: Vanilla JavaScript, Cytoscape.js

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd SemantixRaw
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env   # Linux/Mac
copy .env.example .env  # Windows
```

Edit `.env` with your settings.

### 5. Run the application

```bash
python app.py
```

The app will be available at `http://localhost:5000`.

## Project Structure

```
SemantixRaw/
├── app.py                     # Main Flask application
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── database/
│   ├── __init__.py
│   └── models.py              # SQLAlchemy models
├── services/
│   ├── __init__.py
│   ├── embedding_service.py   # Transformer embeddings + FAISS
│   ├── classifier_service.py  # Intent classification
│   ├── openalex_service.py    # OpenAlex API integration
│   ├── graph_service.py       # Cytoscape.js graph builder
│   ├── training_service.py    # Manual training management
│   └── learning_service.py    # Self-learning from queries
├── routes/
│   ├── __init__.py
│   ├── auth.py                # Authentication endpoints
│   ├── search.py              # Search endpoints
│   ├── chat.py                # Q&A endpoints
│   ├── graph.py               # Graph visualisation endpoints
│   └── train.py               # Training management endpoints
└── public/
    ├── index.html             # Home page
    ├── search.html            # Search page
    ├── chat.html              # Q&A page
    ├── graph.html             # Graph explorer
    ├── train.html             # Training management
    ├── login.html             # Authentication
    ├── css/                   # Stylesheets
    └── js/                    # JavaScript files
```

## License

All rights reserved by **The Zambia University of Technology**. This repository is for demonstration purposes only.
