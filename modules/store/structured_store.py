import sqlite3
from typing import Iterable, Dict, List, Tuple

DDL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS statuses(
  slide INTEGER, area TEXT, status TEXT, color_hex TEXT
);
CREATE TABLE IF NOT EXISTS milestones(
  slide INTEGER, title TEXT, date TEXT, raw_date TEXT
);
CREATE TABLE IF NOT EXISTS spans(
  slide INTEGER, title TEXT, start_date TEXT, end_date TEXT, raw_range TEXT
);
"""

class StructuredStore:
    def __init__(self, path: str):
        self.path = path
        # initialize schema on a fresh connection
        with self._connect() as conn:
            conn.executescript(DDL)

    def _connect(self) -> sqlite3.Connection:
        # New connection per call; safe across threads
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # -------- Upserts (append style, hackathon-safe) --------
    def add_statuses(self, rows: Iterable[Dict]):
        rows = list(rows)
        if not rows: return
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO statuses VALUES (:slide,:area,:status,:color_hex)",
                rows,
            )
            conn.commit()

    def add_milestones(self, rows: Iterable[Dict]):
        rows = list(rows)
        if not rows: return
        # normalize keys from parser just in case
        norm = [
            {
                "slide": r.get("slide"),
                "title": r.get("title"),
                "date": r.get("date"),
                "raw_date": r.get("raw_date"),
            }
            for r in rows
        ]
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO milestones VALUES (:slide,:title,:date,:raw_date)",
                norm,
            )
            conn.commit()

    def add_spans(self, rows: Iterable[Dict]):
        rows = list(rows)
        if not rows: return
        norm = [
            {
                "slide": r.get("slide"),
                "title": r.get("title"),
                "start_date": r.get("start_date"),
                "end_date": r.get("end_date"),
                "raw_range": r.get("raw_range")
                           or f"{r.get('raw_left','')}-{r.get('raw_right','')}".strip("-"),
            }
            for r in rows
        ]
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO spans VALUES (:slide,:title,:start_date,:end_date,:raw_range)",
                norm,
            )
            conn.commit()

    # -------- Queries used by the planner --------
    def red_areas(self) -> List[Tuple[int, str]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT slide, area FROM statuses WHERE status='At Risk'")
            return [(row["slide"], row["area"]) for row in cur.fetchall()]

    def status_by_area_like(self, area_q: str) -> List[Tuple[int, str, str]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT slide, area, status FROM statuses WHERE area LIKE ?",
                (f"%{area_q}%",),
            )
            return [(row["slide"], row["area"], row["status"]) for row in cur.fetchall()]

    def get_milestone(self, title_q: str) -> List[Tuple[int, str, str]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT slide, title, COALESCE(date, raw_date) AS when_str "
                "FROM milestones WHERE title LIKE ?",
                (f"%{title_q}%",),
            )
            return [(row["slide"], row["title"], row["when_str"]) for row in cur.fetchall()]

    def get_span(self, title_q: str) -> List[Tuple[int, str, str, str]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT slide, title, COALESCE(start_date, ''), COALESCE(end_date, '') "
                "FROM spans WHERE title LIKE ?",
                (f"%{title_q}%",),
            )
            return [(row[0], row[1], row[2], row[3]) for row in cur.fetchall()]

    # -------- Maintenance --------
    def reset(self):
        with self._connect() as conn:
            conn.executescript(
                "DELETE FROM milestones; DELETE FROM spans; DELETE FROM statuses;"
            )
            conn.commit()
