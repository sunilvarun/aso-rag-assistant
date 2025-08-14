from typing import List, Dict
from modules.model_client import ask_llm
import os

def os_path_tail(path: str) -> str:
    try:
        return os.path.basename(path)
    except Exception:
        return path

class ChatEngine:
    def __init__(self, cfg, retriever):
        self.cfg = cfg
        self.retriever = retriever
        self.history: List[Dict[str, str]] = []

    def _format_history(self) -> str:
        buf = []
        for turn in self.history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if "📂 **Sources:**" in content:
                content = content.split("📂 **Sources:**")[0].strip()
            buf.append(f"{role.capitalize()}: {content}")
        return "\n".join(buf)

    def chat(self, message: str) -> str:
        results = self.retriever.search(message)

        # Build a clean, separated context for the LLM
        parts = []
        for d in results:
            src = os_path_tail(d.metadata.get("source", "Unknown"))
            page = d.metadata.get("page") or d.metadata.get("page_number")
            header = f"[Source: {src}" + (f", page {page}]" if page not in (None, "", 0) else "]")
            parts.append(f"{header}\n{d.page_content}")
        context = "\n\n---\n\n".join(parts) if parts else ""

        # Sources list for the UI
        def src_line(d):
            src = os_path_tail(d.metadata.get("source", "Unknown"))
            page = d.metadata.get("page") or d.metadata.get("page_number")
            return f"{src} (page {page})" if page not in ("", None, 0) else src
        sources = sorted(set(src_line(d) for d in results))
        sources_text = "\n".join(f"- {s}" for s in sources) if sources else "- (no matched documents)"

        history_text = self._format_history()
        prompt = f"""You are a grounded assistant. Use ONLY the provided context. If the answer is not present in the context, say you don't know.

Conversation so far:
{history_text}

Context:
{context}

Latest question:
{message}

Answer (concise, cite facts from the context when possible):
"""

        reply = ask_llm(
            provider=self.cfg["model"]["provider"],
            model_name=self.cfg["model"]["name"],
            prompt=prompt
        )
        final = f"{reply}\n\n📂 **Sources:**\n{sources_text}"

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": final})
        return final
