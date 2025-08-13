# ASO Team AI Chatbot (RAG)

A lightweight, local-first Retrieval-Augmented Generation (RAG) chatbot that indexes a folder of docs and answers questions with sources.

## Features
- Indexes PDF, DOCX, TXT, PPTX, and XLSX (with a special example for a funnel sheet).
- FAISS vector search with sentence-transformers/all-MiniLM-L6-v2.
- Pluggable LLM backend via `interlinked` (default: Gemini 2.0 Flash through `GoogleAIClient`).
- Gradio chat UI with source citations.

## Quick Start

### 1) Create and activate a virtual env (macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

> If your environment can’t install `faiss-cpu`, try `pip install faiss-cpu==1.8.0.post1` or use conda.  
> If `unstructured` pulls optional extras you don’t want, keep as-is for now or remove its loaders in `modules/indexer.py`.

### 3) Configure
Edit `config.yaml` (or set env vars) to point to your documents folder and choose the model/client.
```yaml
data_dir: "/path/to/your/my_corpus"
index_dir: "faiss_index"
embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
k: 3
model:
  provider: "google"           # "google" | "openai" (example) | "mock"
  name: "gemini-2.0-flash"
```

### 4) Run
```bash
python main.py
```
This will build or load the FAISS index and launch a local Gradio app in your browser.

### 5) Re-index (optional)
Delete the `faiss_index/` folder **or** run with the `--reindex` flag:
```bash
python main.py --reindex
```

## GitHub: initialize & push
```bash
git init
git add .
git commit -m "Initial commit: RAG app skeleton"
# create an empty repo on GitHub first, then:
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## Packaging (later)
- Use PyInstaller to build a macOS app. See `pyinstaller.spec.example` for a starting point.

## Notes
- `interlinked` is assumed to be available in your environment. If it’s an internal package, add the correct install instructions.
- For large Excel files, consider refining the conversion logic in `modules/indexer.py` to avoid noisy text.
