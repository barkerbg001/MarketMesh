"""In-process registry of running chat turns, for cancellation.

MarketMesh runs as a single process (see README: SQLite and one Gunicorn
worker), so an in-memory registry is sufficient.
"""

import threading
import uuid
from dataclasses import dataclass, field


@dataclass
class RunHandle:
    run_id: str
    conversation_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)


class RunRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, RunHandle] = {}
        self._by_conversation: dict[str, str] = {}

    def start(self, conversation_id: str) -> RunHandle | None:
        """Register a run, or return None if the conversation already has one."""
        with self._lock:
            if conversation_id in self._by_conversation:
                return None
            handle = RunHandle(run_id=uuid.uuid4().hex, conversation_id=conversation_id)
            self._runs[handle.run_id] = handle
            self._by_conversation[conversation_id] = handle.run_id
            return handle

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            handle = self._runs.get(run_id)
        if handle is None:
            return False
        handle.cancel_event.set()
        return True

    def finish(self, run_id: str) -> None:
        with self._lock:
            handle = self._runs.pop(run_id, None)
            if handle and self._by_conversation.get(handle.conversation_id) == run_id:
                del self._by_conversation[handle.conversation_id]

    def is_active(self, conversation_id: str) -> bool:
        with self._lock:
            return conversation_id in self._by_conversation

    def any_active(self) -> bool:
        with self._lock:
            return bool(self._runs)


registry = RunRegistry()
