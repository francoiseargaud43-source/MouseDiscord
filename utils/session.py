"""Sessions de parcours en mémoire, isolées par identifiant unique.

Modèle de sécurité :
- chaque parcours reçoit un ``session_id`` aléatoire (non devinable) ;
- chaque vue / modal du parcours porte ce ``session_id`` ;
- chaque action vérifie à la fois l'identifiant ET le propriétaire (``user_id``) ;
- un utilisateur n'a qu'un parcours actif : relancer un test REMPLACE l'ancien
  (les anciens menus deviennent inactifs et ne peuvent plus rien modifier) ;
- une session est supprimée dès que le résultat est produit, fermé, expiré ou remplacé.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Callable

from utils.models import BudgetMode, Grip, Thenar

# Issues possibles de ``SessionStore.lookup``.
LOOKUP_OK = "ok"
LOOKUP_INACTIVE = "inactive"    # inconnue, remplacée, terminée ou expirée
LOOKUP_FORBIDDEN = "forbidden"  # l'identifiant appartient à un autre utilisateur


@dataclass
class FinderSession:
    user_id: int
    session_id: str = field(default_factory=lambda: secrets.token_urlsafe(12))
    grip: Grip | None = None
    # Éminence thénar : stockée et affichée à titre informatif, JAMAIS utilisée dans un calcul.
    thenar: Thenar | None = None
    hand_length_mm: float | None = None
    hand_width_mm: float | None = None
    budget_mode: BudgetMode | None = None
    max_budget_eur: float | None = None
    last_seen: float = field(default=0.0)


class SessionStore:
    def __init__(self, ttl_seconds: float = 1800, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._by_id: dict[str, FinderSession] = {}
        self._active_by_user: dict[int, str] = {}

    # -- cycle de vie ------------------------------------------------------
    def start(self, user_id: int) -> FinderSession:
        """Crée un nouveau parcours pour l'utilisateur ; l'éventuel parcours précédent est supprimé."""
        self.purge_expired()
        self.discard_user(user_id)
        session = FinderSession(user_id=user_id, last_seen=self._clock())
        self._by_id[session.session_id] = session
        self._active_by_user[user_id] = session.session_id
        return session

    def lookup(self, session_id: str | None, user_id: int) -> tuple[FinderSession | None, str]:
        """Retourne (session, statut). Ne modifie jamais une session appartenant à un autre utilisateur."""
        if not session_id:
            return None, LOOKUP_INACTIVE
        session = self._by_id.get(session_id)
        if session is None:
            return None, LOOKUP_INACTIVE
        if session.user_id != user_id:
            return None, LOOKUP_FORBIDDEN
        now = self._clock()
        if now - session.last_seen > self._ttl:
            self._remove(session_id)
            return None, LOOKUP_INACTIVE
        if self._active_by_user.get(user_id) != session_id:
            return None, LOOKUP_INACTIVE  # parcours remplacé
        session.last_seen = now
        return session, LOOKUP_OK

    def get(self, session_id: str | None, user_id: int) -> FinderSession | None:
        return self.lookup(session_id, user_id)[0]

    def discard(self, session_id: str | None) -> None:
        """Supprime une session (fin de parcours, fermeture)."""
        if session_id and session_id in self._by_id:
            self._remove(session_id)

    def discard_user(self, user_id: int) -> None:
        current = self._active_by_user.pop(user_id, None)
        if current is not None:
            self._by_id.pop(current, None)

    def purge_expired(self) -> int:
        now = self._clock()
        expired = [sid for sid, s in self._by_id.items() if now - s.last_seen > self._ttl]
        for sid in expired:
            self._remove(sid)
        return len(expired)

    def _remove(self, session_id: str) -> None:
        session = self._by_id.pop(session_id, None)
        if session is not None and self._active_by_user.get(session.user_id) == session_id:
            del self._active_by_user[session.user_id]

    def __len__(self) -> int:
        return len(self._by_id)
