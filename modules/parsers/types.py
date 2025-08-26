from typing import List, Optional
from pydantic import BaseModel

class StatusCard(BaseModel):
    slide: int
    area: str
    status: str              # "On Track" | "At Risk" | "Blocked"
    color_hex: Optional[str] = None

class TimelineMilestone(BaseModel):
    slide: int
    title: str
    date: Optional[str]      # ISO YYYY-MM-DD if parsed
    raw_date: Optional[str]  # original label

class TimelineSpan(BaseModel):
    slide: int
    title: str
    start_date: Optional[str]
    end_date: Optional[str]
    raw_range: Optional[str] # original "Jul 24 - Aug 18"
