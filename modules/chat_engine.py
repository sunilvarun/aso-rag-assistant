from typing import List, Dict, Any
from modules.model_client import ask_llm

class ChatEngine:
    def __init__(self, cfg, retriever):
        self.cfg = cfg
        self.retriever = retriever
        self.history: List[Dict[str, str]] = []

    def _format_history(self) -> str:
        buf = []
        for turn in self.history[-6:]:  # keep last 6 turns for prompt brevity
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if "📂 **Sources:**" in content:
                content = content.split("📂 **Sources:**")[0].strip()
            buf.append(f"{role.capitalize()}: {content}")
        return "\n".join(buf)

    def chat(self, message: str) -> str:
        # Retrieve context
        results = self.retriever.search(message)
        context = "\n\n".join([doc.page_content for doc in results])

        # Build sources text
        def src_line(d):
            src = d.metadata.get("source", "Unknown")
            page = d.metadata.get("page", d.metadata.get("page_number", ""))
            if page not in ("", None):
                return f"{src} (page {page})"
            return src
        sources = sorted(set(src_line(d) for d in results))
        sources_text = "\n".join(f"- {s}" for s in sources) if sources else "- (no matched documents)"

        history_text = self._format_history()

        prompt = f"""You are a grounded assistant. Use ONLY the context to answer. If the answer is not present in the context, say you don't know.

Conversation so far:
{history_text}

Context (from retrieved documents):
{context}

Latest question:
{message}

Answer (concise, cite specific facts from the context when possible):
"""

        reply = ask_llm(
            provider=self.cfg["model"]["provider"],
            model_name=self.cfg["model"]["name"],
            prompt=prompt
        )

        final_answer = f"{reply}\n\n📂 **Sources:**\n{sources_text}"

        # Update history
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": final_answer})

        return final_answer
