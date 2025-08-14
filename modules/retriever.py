from typing import List
from langchain.schema import Document

class Retriever:
    def __init__(self, cfg, db):
        self.cfg = cfg
        self.db = db

    def search(self, query: str) -> List[Document]:
        if self.db is None:
            return []
        k = int(self.cfg.get("k", 3))
        adaptive = bool(self.cfg.get("adaptive_topk", False))
        max_k = int(self.cfg.get("adaptive_max_k", 6))

        # Try with k; if too few docs and adaptive enabled, grow.
        docs = self.db.similarity_search(query, k=k)
        cur_k = k
        while adaptive and len(docs) < k and cur_k < max_k:
            cur_k += 1
            docs = self.db.similarity_search(query, k=cur_k)
        return docs

