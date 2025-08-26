from typing import List, Dict, Optional, Tuple
import os
import re
from modules.model_client import ask_llm
from modules.store.structured_store import StructuredStore

def os_path_tail(path: str) -> str:
    try:
        return os.path.basename(path)
    except Exception:
        return path

# --- lightweight intent detection for timeline facts ---
_MILESTONE_Q = re.compile(
    r"(?:when\s+(?:is|was|will)\s+(?P<what1>.+?)\??$)|"
    r"(?:date\s+(?:of|for)\s+(?P<what2>.+?)\??$)|"
    r"(?:what\s+date\s+is\s+(?P<what3>.+?)\??$)|"
    r"(?:(?P<what4>.+?)\s+date\??$)",
    re.I
)

def _extract_milestone_query(q: str) -> Optional[str]:
    q = q.strip()
    m = _MILESTONE_Q.search(q)
    if not m:
        return None
    for k in ("what1", "what2", "what3", "what4"):
        s = m.group(k)
        if s:
            # trim generic words like "the", "milestone", etc.
            s = re.sub(r"\b(the|milestone|task|event)\b", "", s, flags=re.I).strip()
            return s
    return None

class ChatEngine:
    def __init__(self, cfg, retriever):
        self.cfg = cfg
        self.retriever = retriever
        self.history: List[Dict[str, str]] = []
        # open the same SQLite DB used by the indexer
        db_path = cfg.get("structured_db_path", ".structured.sqlite")
        self.store = StructuredStore(db_path)

    def _format_history(self) -> str:
        buf = []
        for turn in self.history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if "📂 **Sources:**" in content:
                content = content.split("📂 **Sources:**")[0].strip()
            buf.append(f"{role.capitalize()}: {content}")
        return "\n".join(buf)

    # --- helpers for RAG context formatting ---
    def _format_context_and_sources(self, docs) -> Tuple[str, str]:
        parts = []
        src_lines = []
        uniq = set()
        for d in docs:
            src = os_path_tail(d.metadata.get("source", "Unknown"))
            page = d.metadata.get("page") or d.metadata.get("page_number") or d.metadata.get("slide")
            header = f"[Source: {src}" + (f", page {page}]" if page not in (None, "", 0) else "]")
            parts.append(f"{header}\n{d.page_content}")
            line = f"{src} (page {page})" if page not in ("", None, 0) else src
            if line not in uniq:
                uniq.add(line)
                src_lines.append(f"- {line}")
        context = "\n\n---\n\n".join(parts) if parts else ""
        sources_text = "\n".join(src_lines) if src_lines else "- (no matched documents)"
        return context, sources_text

    # --- structured-first planner ---
    def _answer_from_structure(self, user_q: str) -> Optional[str]:
        """
        Try to answer with exact facts from SQLite (no hallucinations).
        Returns a formatted final answer (with sources) or None to fall back to RAG.
        """
        topic = _extract_milestone_query(user_q)
        if not topic:
            return None

        # 1) milestones (exact dates)
        hits = self.store.get_milestone(topic)
        if hits:
            # choose the best match (first is fine; they’re substring LIKE)
            slide, title, date_str = hits[0]

            # pull a bit of RAG context near that title so the answer has color
            support_query = f"{title} {date_str}"
            docs = self.retriever.search(support_query)
            context, sources_text = self._format_context_and_sources(docs)

            # short grounded answer
            fact_line = f"**{title}** is scheduled on **{date_str}**."
            if not docs:
                # return fact-only if no RAG docs
                return f"{fact_line}\n\n📂 **Sources:**\n- Slide {slide}"

            # ask the LLM to write a one-liner explanation *only using* the context
            history_text = self._format_history()
            prompt = f"""You are a grounded assistant. Use ONLY the provided context to write one concise sentence that restates the date and gives brief context.

Conversation so far:
{history_text}

Context:
{context}

Instruction:
Write one short sentence explaining what the milestone is and confirm the date if present. Do not add new facts.
"""
            reply = ask_llm(
                provider=self.cfg["model"]["provider"],
                model_name=self.cfg["model"]["name"],
                prompt=prompt
            )

            final = f"{fact_line}\n\n{reply}\n\n📂 **Sources:**\n- Slide {slide}\n{sources_text}"
            return final

        # 2) spans (if user asked e.g., “What’s the window for X?”)
        # very simple trigger; you can expand later
        if re.search(r"\b(range|window|between|start|end)\b", user_q, re.I):
            span_hits = self.store.get_span(topic)
            if span_hits:
                slide, title, start, end = span_hits[0]
                docs = self.retriever.search(title)
                context, sources_text = self._format_context_and_sources(docs)
                fact = f"**{title}** runs **{start or 'N/A'} → {end or 'N/A'}**."
                if not docs:
                    return f"{fact}\n\n📂 **Sources:**\n- Slide {slide}"
                history_text = self._format_history()
                prompt = f"""Use ONLY the provided context to briefly confirm the date range for the item below.

Conversation so far:
{history_text}

Item: {title}
Context:
{context}

Answer in one short sentence:
"""
                reply = ask_llm(
                    provider=self.cfg["model"]["provider"],
                    model_name=self.cfg["model"]["name"],
                    prompt=prompt
                )
                return f"{fact}\n\n{reply}\n\n📂 **Sources:**\n- Slide {slide}\n{sources_text}"

        return None

    # --- main chat ---
    def chat(self, message: str) -> str:
        # 1) Try structured first
        structured = self._answer_from_structure(message)
        if structured:
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": structured})
            return structured

        # 2) Fall back to straight RAG
        results = self.retriever.search(message)
        context, sources_text = self._format_context_and_sources(results)

        history_text = self._format_history()
        prompt = f"""You are a grounded assistant. Use ONLY the provided context. If the answer is not present, say you don't know.

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
