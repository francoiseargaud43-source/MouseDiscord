"""Cache de session en mémoire : une session par utilisateur (session_id = user_id)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from utils.models import BudgetMode, Grip


@dataclass
class FinderSession:
    user_id: int
    grip: Grip | None = None
    hand_length_mm: float | None = None
    hand_width_mm: float | None = None
    budget_mode: BudgetMode | None = None
    max_budget_eur: float | None = None
    last_seen: float = field(default=0.0)


class SessionStore:
    def __init__(self, ttl_seconds: float = 1800, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._sessions: dict[int, FinderSession] = {}

    def start(self, user_id: int) -> FinderSession:
        """Crée (ou remplace) la session de l'utilisateur."""
        session = FinderSession(user_id=user_id, last_seen=self._clock())
        self._sessions[user_id] = session
        return session

    def get(self, user_id: int) -> FinderSession | None:
        """Retourne la session active ou None (expirée / inexistante). Rafraîchit l'activité."""
        session = self._sessions.get(user_id)
        if session is None:
            return None
        now = self._clock()
        if now - session.last_seen > self._ttl:
            del self._sessions[user_id]
            return None
        session.last_seen = now
        return session

    def discard(self, user_id: int) -> None:
        self._sessions.pop(user_id, None)

    def purge_expired(self) -> int:
        now = self._clock()
        expired = [uid for uid, s in self._sessions.items() if now - s.last_seen > self._ttl]
        for uid in expired:
            del self._sessions[uid]
        return len(expired)

    def __len__(self) -> int:
        return len(self._sessions)
