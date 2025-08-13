from typing import List
from langchain.schema import Document

class Retriever:
    def __init__(self, cfg, db):
        self.k = int(cfg.get("k", 3))
        self.db = db

    def search(self, query: str) -> List[Document]:
        if self.db is None:
            return []
        return self.db.similarity_search(query, k=self.k)
