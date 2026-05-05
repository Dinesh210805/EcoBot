import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

_lock = threading.Lock()
_sessions: dict[str, "SessionMemory"] = {}

MAX_HISTORY = 20  # messages per session
MAX_SESSIONS = 500


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class SessionMemory:
    session_id: str
    history: deque = field(default_factory=lambda: deque(maxlen=MAX_HISTORY))
    last_classification: Optional[dict] = None
    location: Optional[str] = None

    def add_message(self, role: str, content: str):
        self.history.append(Message(role=role, content=content))

    def get_history_for_llm(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.history]


def get_session(session_id: str) -> SessionMemory:
    with _lock:
        if session_id not in _sessions:
            _evict_if_needed()
            _sessions[session_id] = SessionMemory(session_id=session_id)
        return _sessions[session_id]


def update_session_location(session_id: str, location: str):
    session = get_session(session_id)
    with _lock:
        session.location = location


def store_classification(session_id: str, result: dict):
    session = get_session(session_id)
    with _lock:
        session.last_classification = result


def _evict_if_needed():
    """Drop oldest sessions when limit is reached (no lock needed — called under lock)."""
    if len(_sessions) >= MAX_SESSIONS:
        oldest_key = next(iter(_sessions))
        del _sessions[oldest_key]
