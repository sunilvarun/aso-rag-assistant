import os
import logging
import pandas as pd
import nltk
from langchain.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, TextLoader, UnstructuredPowerPointLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

log = logging.getLogger("indexer")

# Ensure punkt (needed by some loaders/splitters)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class IndexBuilder:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.data_dir = cfg["data_dir"]
        self.index_dir = cfg["index_dir"]
        self.embedding_model = HuggingFaceEmbeddings(model_name=cfg["embedding_model"])
        self.db = None

    def _gather_files(self):
        files = []
        for f in os.listdir(self.data_dir):
            if f.startswith('.'): 
                continue
            if f.lower().endswith(('.pdf', '.docx', '.txt', '.pptx', '.xlsx')):
                files.append(os.path.join(self.data_dir, f))
        return files

    def _load_documents(self, files):
        documents = []
        for file in files:
            try:
                if file.endswith('.pptx'):
                    docs = UnstructuredPowerPointLoader(file).load()
                    # add slide number if present in metadata
                    for d in docs:
                        d.metadata["source"] = file
                    documents.extend(docs)
                elif file.endswith('.pdf'):
                    pdf_docs = PyPDFLoader(file).load()
                    # Attach page numbers
                    for d in pdf_docs:
                        d.metadata["source"] = file
                    documents.extend(pdf_docs)
                elif file.endswith('.docx'):
                    docs = UnstructuredWordDocumentLoader(file).load()
                    for d in docs:
                        d.metadata["source"] = file
                    documents.extend(docs)
                elif file.endswith('.txt'):
                    docs = TextLoader(file).load()
                    for d in docs:
                        d.metadata["source"] = file
                    documents.extend(docs)
                elif file.endswith('.xlsx'):
                    try:
                        if "Personalization_Funnel.xlsx" in file:
                            log.info(f"Special handling for {file}")
                            df = pd.read_excel(file, header=None, engine='openpyxl')
                            text_lines = []
                            for row_idx in range(4, df.shape[0]):
                                platform = str(df.iloc[row_idx, 0]).strip()
                                step = str(df.iloc[row_idx, 1]).strip()
                                for col_idx in range(2, df.shape[1]):
                                    date = str(df.iloc[0, col_idx]).strip()
                                    value = str(df.iloc[row_idx, col_idx]).strip()
                                    text_lines.append(f"Platform: {platform}, Step: {step}, Date: {date}, Value: {value}")
                            text = "\n".join(text_lines)
                            documents.append(Document(page_content=text, metadata={"source": file}))
                        else:
                            df = pd.read_excel(file, engine='openpyxl')
                            text = df.to_string()
                            documents.append(Document(page_content=text, metadata={"source": file}))
                    except Exception as e:
                        log.warning(f"Skipping file {file}: {e}")
                else:
                    log.info(f"Unsupported file type skipped: {file}")
            except Exception as e:
                log.exception(f"Error loading {file}: {e}")
        return documents

    def build_index(self, force_rebuild: bool=False):
        if not force_rebuild:
            try:
                self.db = FAISS.load_local(self.index_dir, self.embedding_model, allow_dangerous_deserialization=True)
                log.info("Loaded existing FAISS index.")
                return
            except Exception:
                log.info("No existing index found or incompatible. Will build anew.")

        files = self._gather_files()
        log.info(f"Found {len(files)} files in {self.data_dir}")
        docs = self._load_documents(files)
        log.info(f"Loaded {len(docs)} documents. Splitting...")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)
        log.info(f"Split into {len(chunks)} chunks. Building FAISS index...")

        self.db = FAISS.from_documents(chunks, self.embedding_model)
        self.db.save_local(self.index_dir)
        log.info("Built and saved FAISS index.")
