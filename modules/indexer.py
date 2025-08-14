import os
import logging
import pandas as pd
import nltk
from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    TextLoader,
    UnstructuredPowerPointLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from .index_manifest import IndexManifest

log = logging.getLogger("indexer")

# Ensure punkt
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class IndexBuilder:
    """Builds or loads FAISS index. Supports incremental rebuilds via file mtimes."""
    SUPPORTED_EXTS = ('.pdf', '.docx', '.txt', '.pptx', '.xlsx')

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.data_dir = cfg["data_dir"]
        self.index_dir = cfg["index_dir"]
        self.manifest = IndexManifest(cfg.get("manifest_path", ".index_manifest.json"))
        self.embedding_model = HuggingFaceEmbeddings(model_name=cfg["embedding_model"])
        self.db = None

        self.chunk_size = int(cfg.get("chunk_size", 500))
        self.chunk_overlap = int(cfg.get("chunk_overlap", 50))

    # ----- public entry -----
    def build_index(self, force_rebuild: bool = False):
        if self.cfg.get("reindex_on_start"):
            force_rebuild = True

        if not force_rebuild:
            try:
                self.db = FAISS.load_local(
                    self.index_dir, self.embedding_model,
                    allow_dangerous_deserialization=True
                )
                log.info("Loaded existing FAISS index.")
                if self.cfg.get("incremental_index", True):
                    changed, _ = self._scan_changed()
                    if changed:
                        log.info(f"Detected {len(changed)} changed/new files; rebuilding.")
                        return self._full_rebuild()
                return
            except Exception:
                log.info("No existing index found or incompatible. Building anew.")

        return self._full_rebuild()

    # ----- helpers -----
    def _gather_files(self) -> List[str]:
        files = []
        for f in os.listdir(self.data_dir):
            if f.startswith('.'):
                continue
            if f.lower().endswith(self.SUPPORTED_EXTS):
                files.append(os.path.join(self.data_dir, f))
        return sorted(files)

    def _scan_changed(self):
        files = self._gather_files()
        changed, unchanged = self.manifest.diff(files)
        log.info(f"Scanned {len(files)} files | changed/new: {len(changed)}, unchanged: {len(unchanged)}")
        return changed, unchanged

    def _load_documents(self, files: List[str]) -> List[Document]:
        docs: List[Document] = []
        for file in files:
            try:
                ext = file.lower().rsplit('.', 1)[-1]
                if ext == 'pptx':
                    chunks = UnstructuredPowerPointLoader(file).load()
                    for d in chunks:
                        d.metadata["source"] = file
                    docs.extend(chunks)

                elif ext == 'pdf':
                    pdf_docs = PyPDFLoader(file).load()
                    for d in pdf_docs:
                        d.metadata["source"] = file
                        if "page" not in d.metadata and "page_number" in d.metadata:
                            d.metadata["page"] = d.metadata["page_number"]
                    docs.extend(pdf_docs)

                elif ext == 'docx':
                    chunks = UnstructuredWordDocumentLoader(file).load()
                    for d in chunks:
                        d.metadata["source"] = file
                    docs.extend(chunks)

                elif ext == 'txt':
                    chunks = TextLoader(file).load()
                    for d in chunks:
                        d.metadata["source"] = file
                    docs.extend(chunks)

                elif ext == 'xlsx':
                    self._load_xlsx(file, docs)

            except Exception as e:
                log.exception(f"Error loading {file}: {e}")
        return docs

    def _load_xlsx(self, file: str, out: List[Document]):
        try:
            if "Personalization_Funnel.xlsx" in file:
                log.info(f"Special handling for {file}")
                df = pd.read_excel(file, header=None, engine='openpyxl')
                lines = []
                for r in range(4, df.shape[0]):
                    platform = str(df.iloc[r, 0]).strip()
                    step = str(df.iloc[r, 1]).strip()
                    for c in range(2, df.shape[1]):
                        date = str(df.iloc[0, c]).strip()
                        val = str(df.iloc[r, c]).strip()
                        lines.append(f"Platform: {platform} | Step: {step} | Date: {date} | Value: {val}")
                out.append(Document(page_content="\n".join(lines), metadata={"source": file}))
                return

            # Generic path: render each sheet row-wise, cap massive sheets
            sheets = pd.read_excel(file, sheet_name=None, engine='openpyxl')
            MAX_ROWS = 2000
            parts = []
            for name, sdf in sheets.items():
                rows = min(sdf.shape[0], MAX_ROWS)
                for i in range(rows):
                    row = [str(sdf.iloc[i, j]).strip() for j in range(sdf.shape[1])]
                    parts.append(f"[{name}] " + " | ".join(row))
            out.append(Document(page_content="\n".join(parts), metadata={"source": file}))
        except Exception as e:
            log.warning(f"Skipping XLSX file {file}: {e}")

    def _full_rebuild(self):
        files = self._gather_files()
        raw_docs = self._load_documents(files)
        log.info(f"Loaded {len(raw_docs)} documents. Splitting size={self.chunk_size}, overlap={self.chunk_overlap}...")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(raw_docs)
        log.info(f"Split into {len(chunks)} chunks. Building FAISS...")

        self.db = FAISS.from_documents(chunks, self.embedding_model)
        self.db.save_local(self.index_dir)
        self.manifest.update(files)
        self.manifest.save()
        log.info("Built and saved FAISS index.")
