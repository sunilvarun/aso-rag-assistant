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
