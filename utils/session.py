"""Sessions de parcours : une session vivante par membre, retrouvée même après un redémarrage.

Modèle de sécurité (inchangé) :
- chaque parcours reçoit un ``session_id`` aléatoire, non devinable ;
- une action n'agit que sur le parcours du membre qui la déclenche : le rattachement se fait par
  l'identifiant Discord, donc un composant ne peut jamais toucher le parcours d'un autre membre ;
- un membre n'a qu'un parcours vivant à la fois : relancer un test remplace l'ancien ;
- une session disparaît à l'expiration du délai d'inactivité ou à la fin du parcours.

Robustesse (2026-10-12, après le signalement « le bot cherche dans le vide, dit que ce n'est plus
possible et il faut tout recommencer ») :
- les parcours EN COURS sont enregistrés dans ``state/sessions.json`` (chemin configurable) :
  un redémarrage du bot ne fait plus perdre un parcours commencé ;
- un parcours TERMINÉ reste quelques minutes EN MÉMOIRE seulement (jamais sur le disque) : un clic
  rejoué par Discord (double appui, interaction réémise) reçoit le même résultat au lieu du message
  « ce parcours n'est plus actif » ;
- l'écriture du fichier est atomique, limitée en fréquence et ne fait JAMAIS échouer un parcours :
  toute erreur d'écriture est journalisée puis ignorée.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from utils.models import BudgetMode, ClawVariant, Grip, Thenar

log = logging.getLogger(__name__)

# Issues possibles de ``SessionStore.lookup`` / ``SessionStore.current``.
LOOKUP_OK = "ok"
LOOKUP_INACTIVE = "inactive"    # inconnue, remplacée, terminée ou expirée
LOOKUP_FORBIDDEN = "forbidden"  # l'identifiant appartient à un autre utilisateur

STATE_VERSION = 1
FINISHED_GRACE_SECONDS = 300.0   # rejeu d'une interaction déjà traitée : 5 minutes
SAVE_INTERVAL_SECONDS = 5.0      # les rafraîchissements d'activité n'écrivent pas à chaque clic


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@dataclass
class FinderSession:
    user_id: int
    session_id: str = field(default_factory=lambda: secrets.token_urlsafe(12))
    grip: Grip | None = None
    # Éminence thénar : collectée et affichée, SANS effet sur le score (règle du propriétaire,
    # MASTER_PROMPT §7.6). Le mécanisme d'ajustement existe mais est en pause, valeurs neutres :
    # THENAR_WIDTH_ADJUSTMENT (utils/matcher.py) vaut 0 / 0 / 0.
    thenar: Thenar | None = None
    # Variante de Claw : demandée seulement pour cette prise, et seulement pour affiner le conseil
    # de bosse (elle n'entre dans aucun calcul). Voir ClawVariant dans utils/models.py.
    claw_variant: ClawVariant | None = None
    hand_length_mm: float | None = None
    hand_width_mm: float | None = None
    budget_mode: BudgetMode | None = None
    max_budget_eur: float | None = None
    last_seen: float = field(default=0.0)
    finished: bool = False          # résultat déjà produit (conservé pour un clic rejoué)
    finished_at: float = 0.0

    # -- progression -------------------------------------------------------
    @property
    def has_measures(self) -> bool:
        return self.hand_length_mm is not None and self.hand_width_mm is not None

    # -- enregistrement ----------------------------------------------------
    def to_state(self, age_seconds: float) -> dict[str, Any]:
        """Représentation minimale enregistrée sur disque : seules les réponses déjà données."""
        state: dict[str, Any] = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "age_seconds": round(max(0.0, age_seconds), 3),
        }
        if self.grip is not None:
            state["grip"] = self.grip.value
        if self.thenar is not None:
            state["thenar"] = self.thenar.value
        if self.claw_variant is not None:
            state["claw_variant"] = self.claw_variant.value
        if self.hand_length_mm is not None:
            state["hand_length_mm"] = self.hand_length_mm
        if self.hand_width_mm is not None:
            state["hand_width_mm"] = self.hand_width_mm
        if self.budget_mode is not None:
            state["budget_mode"] = self.budget_mode.value
        if self.max_budget_eur is not None:
            state["max_budget_eur"] = self.max_budget_eur
        return state

    @classmethod
    def from_state(cls, raw: dict[str, Any], last_seen: float) -> "FinderSession | None":
        """Reconstruit une session enregistrée ; ``None`` si l'enregistrement est inutilisable."""
        try:
            session = cls(user_id=int(raw["user_id"]), session_id=str(raw["session_id"]))
            if raw.get("grip"):
                session.grip = Grip(raw["grip"])
            if raw.get("thenar"):
                session.thenar = Thenar(raw["thenar"])
            if raw.get("claw_variant"):
                session.claw_variant = ClawVariant(raw["claw_variant"])
            if raw.get("budget_mode"):
                session.budget_mode = BudgetMode(raw["budget_mode"])
            session.hand_length_mm = _float_or_none(raw.get("hand_length_mm"))
            session.hand_width_mm = _float_or_none(raw.get("hand_width_mm"))
            session.max_budget_eur = _float_or_none(raw.get("max_budget_eur"))
        except (KeyError, TypeError, ValueError):
            return None
        session.last_seen = last_seen
        return session


class SessionStore:
    def __init__(
        self,
        ttl_seconds: float = 1800,
        clock: Callable[[], float] = time.monotonic,
        path: Path | str | None = None,
        finished_grace_seconds: float = FINISHED_GRACE_SECONDS,
    ) -> None:
        if ttl_seconds <= 0:
            # Sinon chaque parcours expirerait aussitôt : le membre lirait « ce parcours a expiré »
            # à chaque clic, ce qui ressemble exactement à la panne signalée le 2026-10-12.
            raise ValueError("ttl_seconds doit être supérieur à 0.")
        self._ttl = float(ttl_seconds)
        self._clock = clock
        self._grace = float(finished_grace_seconds)
        self._path = Path(path) if path is not None else None
        self._by_id: dict[str, FinderSession] = {}
        self._active_by_user: dict[int, str] = {}
        self._last_save = float("-inf")
        if self._path is not None:
            self._load()

    # -- cycle de vie ------------------------------------------------------
    def start(self, user_id: int) -> FinderSession:
        """Crée un nouveau parcours pour l'utilisateur ; l'éventuel parcours précédent est supprimé."""
        self.purge_expired()
        self._discard_user(user_id)
        session = FinderSession(user_id=user_id, last_seen=self._clock())
        self._by_id[session.session_id] = session
        self._active_by_user[user_id] = session.session_id
        self._save(force=True)
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
        if self._is_expired(session, now):
            self._remove(session_id)
            self._save(force=True)
            return None, LOOKUP_INACTIVE
        if session.finished:
            # Parcours terminé : encore valable quelques minutes pour un clic rejoué par Discord.
            session.last_seen = now
            return session, LOOKUP_OK
        if self._active_by_user.get(user_id) != session_id:
            return None, LOOKUP_INACTIVE  # parcours remplacé
        session.last_seen = now
        self._save()                      # rafraîchissement d'activité (fréquence limitée)
        return session, LOOKUP_OK

    def current(self, user_id: int) -> tuple[FinderSession | None, str]:
        """Parcours vivant du membre : c'est lui que servent les composants des étapes.

        Les composants d'étapes portent des identifiants FIXES (indispensables pour continuer de
        fonctionner après un redémarrage) : le parcours est donc retrouvé par le membre qui clique,
        jamais par une donnée inscrite dans le message. Aucun accès croisé n'est possible.
        """
        session_id = self._active_by_user.get(user_id)
        if session_id is None:
            return None, LOOKUP_INACTIVE
        return self.lookup(session_id, user_id)

    def get(self, session_id: str | None, user_id: int) -> FinderSession | None:
        return self.lookup(session_id, user_id)[0]

    def finish(self, session_id: str | None) -> None:
        """Marque le parcours comme terminé : gardé en mémoire (rejeu), retiré du disque."""
        session = self._by_id.get(session_id) if session_id else None
        if session is None:
            return
        session.finished = True
        session.finished_at = self._clock()
        self._save(force=True)

    def discard(self, session_id: str | None) -> None:
        """Supprime une session (fin de parcours, fermeture)."""
        if session_id and session_id in self._by_id:
            self._remove(session_id)
            self._save(force=True)

    def discard_user(self, user_id: int) -> None:
        if self._discard_user(user_id):
            self._save(force=True)

    def purge_expired(self) -> int:
        now = self._clock()
        expired = [sid for sid, session in self._by_id.items() if self._is_expired(session, now)]
        for sid in expired:
            self._remove(sid)
        if expired:
            self._save(force=True)
        return len(expired)

    def __len__(self) -> int:
        return len(self._by_id)

    @property
    def storage_path(self) -> Path | None:
        """Fichier d'état des parcours en cours, ou ``None`` si le stockage est désactivé."""
        return self._path

    # -- enregistrement disque ---------------------------------------------
    def save(self, *, force: bool = True) -> None:
        """Enregistre les parcours en cours (jamais les parcours terminés). Ne lève jamais."""
        self._save(force=force)

    def _save(self, *, force: bool = False) -> None:
        if self._path is None:
            return
        now = self._clock()
        if not force and now - self._last_save < SAVE_INTERVAL_SECONDS:
            return
        self._last_save = now
        state = {
            "version": STATE_VERSION,
            "sessions": [
                session.to_state(age_seconds=now - session.last_seen)
                for session in self._by_id.values()
                if not session.finished
            ],
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_name(f"{self._path.name}.tmp")
            temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, self._path)
        except OSError as exc:            # disque plein, droits, dossier absent…
            log.warning("Parcours non enregistrés dans %s : %s", self._path, exc)

    def _load(self) -> None:
        assert self._path is not None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Fichier de sessions illisible (%s) : %s", self._path, exc)
            return
        if not isinstance(raw, dict) or raw.get("version") != STATE_VERSION:
            log.info("Fichier de sessions ignoré (format inconnu) : %s", self._path)
            return
        entries = raw.get("sessions")
        now = self._clock()
        restored = 0
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            age = _float_or_none(entry.get("age_seconds"))
            if age is None or age > self._ttl:
                continue
            session = FinderSession.from_state(entry, last_seen=now - age)
            if session is None or session.session_id in self._by_id:
                continue
            self._by_id[session.session_id] = session
            active = self._active_by_user.get(session.user_id)
            if active is None or self._by_id[active].last_seen < session.last_seen:
                self._active_by_user[session.user_id] = session.session_id
            restored += 1
        if restored:
            log.info("%d parcours en cours restauré(s) depuis %s", restored, self._path)

    # -- interne -----------------------------------------------------------
    def _is_expired(self, session: FinderSession, now: float) -> bool:
        """Un parcours terminé vit le temps du rejeu ; un parcours en cours vit tant qu'on y répond."""
        if session.finished:
            return now - session.finished_at > self._grace
        return now - session.last_seen > self._ttl

    def _discard_user(self, user_id: int) -> bool:
        changed = False
        current = self._active_by_user.pop(user_id, None)
        if current is not None:
            self._by_id.pop(current, None)
            changed = True
        # Les autres parcours du même membre (rejeu, relance) sont retirés aussi : un seul vivant.
        for session_id in [sid for sid, s in self._by_id.items() if s.user_id == user_id]:
            self._by_id.pop(session_id, None)
            changed = True
        return changed

    def _remove(self, session_id: str) -> None:
        session = self._by_id.pop(session_id, None)
        if session is None:
            return
        if self._active_by_user.get(session.user_id) == session_id:
            # Repli sur un autre parcours vivant du même membre, s'il en reste un.
            remaining = [s for s in self._by_id.values() if s.user_id == session.user_id]
            if remaining:
                self._active_by_user[session.user_id] = max(remaining, key=lambda s: s.last_seen).session_id
            else:
                del self._active_by_user[session.user_id]
