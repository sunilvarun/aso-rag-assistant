# modules/query_planner.py

import re
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, List, Set, Dict
from modules.store.structured_store import StructuredStore

# ---- intent patterns ----
RED_Q  = re.compile(r"\b(red|at risk|blocked)\b", re.I)
WHEN_Q = re.compile(r"\bwhen\b|\bdate\b|\bdeadline\b|\brange\b|\bfrom\b.*\bto\b", re.I)

# ---- month helpers ----
MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12
}
SHORT = {m[:3]: i for m, i in MONTHS.items()}

def _parse_month(s: str) -> Optional[int]:
    s = s.strip().lower().replace(".", "")
    return MONTHS.get(s) or SHORT.get(s)

def _parse_dateish(s: str, default_year: int) -> Optional[date]:
    s = s.strip().replace(".", "")
    parts = s.split()
    if len(parts) == 2 and _parse_month(parts[0]):
        m = _parse_month(parts[0])
        d = int(re.sub(r"\D", "", parts[1]) or "1")
        return date(default_year, m, d)
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _extract_range(question: str, default_year: int) -> Optional[Tuple[date, date]]:
    q = question.lower()

    # next N days
    m = re.search(r"next\s+(\d{1,3})\s+days", q)
    if m:
        n = int(m.group(1))
        start = date.today()
        end = start + timedelta(days=n)
        return start, end

    # in <Month>
    m = re.search(r"\bin\s+([A-Za-z]{3,9})\b", q)
    if m and _parse_month(m.group(1)):
        month = _parse_month(m.group(1))
        start = date(default_year, month, 1)
        # end of month
        if month == 12:
            end = date(default_year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(default_year, month + 1, 1) - timedelta(days=1)
        return start, end

    # between X and Y / from X to Y
    m = re.search(
        r"(?:between|from)\s+([A-Za-z]{3,9}\.?\s+\d{1,2}|\d{4}-\d{2}-\d{2})\s+(?:and|to)\s+([A-Za-z]{3,9}\.?\s+\d{1,2}|\d{4}-\d{2}-\d{2})",
        q,
    )
    if m:
        s = _parse_dateish(m.group(1), default_year)
        e = _parse_dateish(m.group(2), default_year)
        if s and e:
            return s, e

    return None

# ---- formatting helpers ----
def _fmt_milestones(rows: List[Tuple[int, str, str]]) -> str:
    """
    rows: [(slide, title, date_or_raw)]
    """
    seen: Set[Tuple[int, str, str]] = set()
    bullets: List[str] = []
    for slide, title, d in rows:
        key = (slide, title or "", d or "")
        if key in seen:
            continue
        seen.add(key)
        if title and d:
            bullets.append(f"- Slide {slide}: **{title}** — {d}")
        elif title:
            bullets.append(f"- Slide {slide}: **{title}**")
        elif d:
            bullets.append(f"- Slide {slide}: {d}")
    return "\n".join(bullets)

def _fmt_spans(rows: List[Tuple[int, str, str, str]]) -> str:
    """
    rows: [(slide, title, start, end)]
    """
    seen: Set[Tuple[int, str, str, str]] = set()
    bullets: List[str] = []
    for slide, title, start, end in rows:
        key = (slide, title or "", start or "", end or "")
        if key in seen:
            continue
        seen.add(key)
        if title and start and end:
            bullets.append(f"- Slide {slide}: **{title}** — {start} → {end}")
        elif title:
            bullets.append(f"- Slide {slide}: **{title}**")
    return "\n".join(bullets)

# ---- main entry ----
def try_structured_first(cfg: dict, question: str) -> str | None:
    """Return a formatted markdown answer if we can satisfy from structured data, else None."""
    store_path = cfg.get("structured_store", {}).get("path") if isinstance(cfg.get("structured_store"), dict) else "structured.db"
    store = StructuredStore(store_path)
    default_year = datetime.now().year

    # 1) Status queries (At Risk / red / blocked)
    if RED_Q.search(question):
        rows = store.red_areas()
        if rows:
            bullets = "\n".join(f"- Slide {s}: {a}" for (s, a) in rows)
            return f"Teams/areas marked **At Risk**:\n{bullets}"
        return "I didn't find any areas marked **At Risk**."

    # 2) Date-range style queries (in August / next 30 days / between X and Y)
    rng = _extract_range(question, default_year)
    if rng:
        s, e = rng

        # milestones strictly inside [s, e]
        ms = list(
            store.conn.execute(
                """
                SELECT slide, title, COALESCE(date, raw_date)
                FROM milestones
                WHERE date IS NOT NULL AND date >= ? AND date <= ?
                ORDER BY date ASC
                """,
                (s.isoformat(), e.isoformat()),
            )
        )

        # spans that overlap [s, e]
        sp = list(
            store.conn.execute(
                """
                SELECT slide, title, COALESCE(start_date,''), COALESCE(end_date,'')
                FROM spans
                WHERE start_date IS NOT NULL AND end_date IS NOT NULL
                  AND NOT(end_date < ? OR start_date > ?)
                ORDER BY start_date ASC
                """,
                (s.isoformat(), e.isoformat()),
            )
        )

        parts: List[str] = []
        if ms:
            parts.append("**Milestones:**")
            parts.append(_fmt_milestones(ms))
        if sp:
            parts.append("**Spans:**")
            parts.append(_fmt_spans(sp))

        return "\n".join(parts) if parts else "I didn’t find milestones or spans in that time window."

    # 3) Simple WHEN lookups (e.g., “When is Production Cutover?”)
    if WHEN_Q.search(question):
        ms = store.get_milestone(question)  # [(slide, title, date_or_raw)]
        sp = store.get_span(question)       # [(slide, title, start, end)]
        parts: List[str] = []
        if ms:
            parts.append("**Milestones:**")
            parts.append(_fmt_milestones(ms))
        if sp:
            parts.append("**Spans:**")
            parts.append(_fmt_spans(sp))
        if parts:
            return "\n".join(parts)

    # No structured hit → let RAG handle it
    return None
