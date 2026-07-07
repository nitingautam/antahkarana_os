import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ItemType(str, Enum):
    TASK = "task"
    IDEA = "idea"
    REFERENCE = "reference"
    WAITING_ON = "waiting-on"
    SOMEDAY = "someday"

    @classmethod
    def from_str(cls, val: str):
        val_clean = val.lower().strip().replace("_", "-")
        for member in cls:
            if member.value == val_clean:
                return member
        return cls.TASK


class Priority(str, Enum):
    HIGH = "high"
    MED = "med"
    LOW = "low"

    @classmethod
    def from_str(cls, val: str):
        val_clean = val.lower().strip()
        if "high" in val_clean or "1" in val_clean or "urgent" in val_clean:
            return cls.HIGH
        elif "low" in val_clean or "3" in val_clean or "minor" in val_clean:
            return cls.LOW
        return cls.MED


class Effort(str, Enum):
    QUICK = "quick"
    FOCUSED = "focused"
    PROJECT = "project"

    @classmethod
    def from_str(cls, val: str):
        val_clean = val.lower().strip()
        if "quick" in val_clean or "min" in val_clean or "short" in val_clean:
            return cls.QUICK
        elif "project" in val_clean or "long" in val_clean or "days" in val_clean or "weeks" in val_clean:
            return cls.PROJECT
        return cls.FOCUSED


class TaskStatus(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"
    STALE = "stale"


class InboxItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    source: str = "cli"


class ClassifiedItem(BaseModel):
    inbox_id: str
    text: str
    timestamp: str
    item_type: str
    category: str  # PARA Project or Area e.g. "Work/AI", "Health", "Finance"
    priority: str
    effort: str
    reasoning: Optional[str] = None


class TaskItem(BaseModel):
    id: str
    text: str
    item_type: str
    category: str
    priority: str
    effort: str
    status: str = "open"
    created_at: str
    updated_at: str
    stale: bool = False


class NoteItem(BaseModel):
    id: str
    text: str
    category: str
    created_at: str
    item_type: str = "reference"


class ArchiveItem(BaseModel):
    id: str
    text: str
    category: str
    created_at: str
    reason: Optional[str] = None


class ReviewDigest(BaseModel):
    timestamp: str
    completed_count: int
    open_count: int
    completion_rate_pct: float
    stale_items: List[TaskItem]
    reflections: List[str]


class EisenhowerQuadrant(str, Enum):
    DO_NOW = "Q1 - Do Now (Urgent & Important)"
    SCHEDULE = "Q2 - Schedule (Important, Not Urgent)"
    DELEGATE = "Q3 - Delegate / Quick Win (Urgent, Not Important)"
    ELIMINATE = "Q4 - Reconsider (Neither)"


class EisenhowerItem(BaseModel):
    task: TaskItem
    quadrant: str
    reason: str


class PlanDigest(BaseModel):
    timestamp: str
    q1_do_now: List[EisenhowerItem]
    q2_schedule: List[EisenhowerItem]
    q3_delegate: List[EisenhowerItem]
    q4_eliminate: List[EisenhowerItem]
    summary: str


class AgentLogEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    agent_name: str
    event_type: str  # "start", "thought", "llm_call", "success", "error"
    message: str
    details: Optional[Dict[str, Any]] = None
