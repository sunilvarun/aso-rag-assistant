Got it 👍 — here’s the **single large Markdown file** (`README.md`) that you can copy-paste into GitHub directly:

````markdown
# 📊 ASO Team AI Chatbot (Visual-Aware RAG)

A **lightweight, local-first Retrieval-Augmented Generation (RAG) system** that can parse and index **documents and presentations**, including **timeline-style slides** with shapes, circles, and text boxes.  
Built from scratch with **LangChain-style components, FAISS**, and a pluggable **LLM backend** (default: Google Gemini 2.0 Flash via `interlinked`).

---

## ✨ Features
- Indexes **PDF, DOCX, TXT, XLSX, PPTX/Keynote** files.  
- Special parser for **PowerPoint/Keynote timelines**:
  - Extracts **dates, milestones, spans** even when text is spread across shapes.
  - Handles cases like *“Dates above, milestones below”* or *overlapping text blocks*.  
- Embeddings: **sentence-transformers/all-MiniLM-L6-v2** stored in **FAISS**.  
- Pluggable **LLM backend**:
  - Default: Gemini 2.0 Flash via `GoogleAIClient`.  
  - Supports OpenAI or mocks.  
- **Structured SQLite store** for milestones/spans (queryable by area, title, etc.).  
- **Gradio UI** with:
  - Chat-style Q&A with citations.
  - Re-index button.
  - Inspect sources.  

---

## 🚀 Quick Start

### 1. Create and activate a virtual env (macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> Troubleshooting:
>
> * If `faiss-cpu` fails:
>
>   ```bash
>   pip install faiss-cpu==1.8.0.post1
>   ```
>
>   or use conda.
> * If `unstructured` pulls in extra dependencies you don’t need, disable those loaders in `modules/indexer.py`.

### 3. Configure

Edit `config.yaml`:

```yaml
data_dir: "/path/to/my_corpus"
index_dir: "faiss_index"
embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
k: 3
model:
  provider: "google"           # "google" | "openai" | "mock"
  name: "gemini-2.0-flash"

structured_store:
  path: "structured.db"
```

### 4. Run

```bash
python main.py
```

* First run builds FAISS index & parses slides into milestones/spans.
* Opens a **Gradio app** in your browser.

### 5. Re-index (optional)

```bash
python main.py --reindex
```

or click the **Re-index** button in the UI.

---

## 🖼 Example

Given a timeline slide:

```
May 17 → Design Complete
Jun 20 → Marcom Review
Jul 25 → DE&M Signoff
```

The system parses it into structured data:

```json
{
  "title": "Design Complete",
  "date": "2025-05-17",
  "raw_date": "May 17"
}
```

And lets you query naturally:

```
Q: When is the DE&M Signoff for Project Sun?
A: July 25, 2025  (source: Timeline - Simple but overlapping text.pptx)
```

---

## 📦 GitHub: initialize & push

```bash
git init
git add .
git commit -m "Initial commit: Visual-aware RAG system"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

---

## 🔮 Next Steps

* Generalize beyond timelines (e.g., org charts, funnel diagrams).
* Improve **OCR fallback** for embedded images.
* Package into a **desktop app (PyInstaller)**.
* Extend structured queries (`longest phase`, `critical path`, etc.).

---

## 🏗 Architecture (High-level)

```text
┌──────────────┐    ┌─────────────────┐    ┌───────────────┐
│  Documents   │ →  │   Indexer       │ →  │   FAISS Index  │
│ (PDF, PPTX)  │    │ (Chunk + Parse) │    │ (Embeddings)  │
└──────────────┘    └─────────────────┘    └───────────────┘
                          │
                          ▼
                   ┌───────────────┐
                   │ Structured DB │  (milestones, spans)
                   └───────────────┘
                          │
                          ▼
                   ┌───────────────┐
                   │    LLM (RAG)  │  via interlinked
                   └───────────────┘
                          │
                          ▼
                   ┌───────────────┐
                   │ Gradio UI Chat│
                   └───────────────┘
```


