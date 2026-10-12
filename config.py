"""Configuration centralisée du bot (variables d'environnement + chemins).

Lecture du fichier ``.env`` : toujours celui situé À CÔTÉ de ce fichier (ROOT_DIR/.env),
quel que soit le répertoire depuis lequel le bot est lancé. Les variables déjà présentes
dans l'environnement du processus ne sont pas écrasées par ``.env``.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
ENV_FILE = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

MOUSE_DB_PATH = DATA_DIR / "mouse_db.json"
COMMERCIAL_LINKS_PATH = DATA_DIR / "commercial_links.json"
IMAGES_CONFIG_PATH = ASSETS_DIR / "images.json"

load_dotenv(ENV_FILE)  # chemin explicite : ne dépend pas du répertoire courant

# Base publique des illustrations (ex. « https://moncompte.alwaysdata.net/illustrations/ »).
# Elle permet à assets/images.json de ne contenir que des noms de fichiers repris de
# assets/illustrations/ : une seule variable à changer au déploiement. Vide = les noms de
# fichiers ne sont pas résolus (aucune image affichée) ; les URL https:// complètes restent utilisées telles quelles.
IMAGES_BASE_URL = os.getenv("IMAGES_BASE_URL", "").strip()
# Mémoire locale du message publié par !setup_finder (ignorée par Git).
FINDER_STATE_PATH = ROOT_DIR / "state" / "finder_message.json"
# Mémoire locale des parcours EN COURS (ignorée par Git) : elle permet à un questionnaire commencé
# de survivre à un redémarrage du bot. Les réponses d'un parcours terminé n'y sont jamais écrites.
SESSION_STATE_PATH = ROOT_DIR / "state" / "sessions.json"


class ConfigError(ValueError):
    """Variable d'environnement invalide ; le message indique la variable à corriger."""


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "oui"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(
            f"{name} doit être un nombre entier (valeur actuelle : {raw!r}). "
            f"Corrigez-la dans le fichier {ENV_FILE}."
        ) from None


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!").strip() or "!"
# Salon cible de !setup_finder (ID numérique). 0 = salon où la commande est tapée.
FINDER_CHANNEL_ID = _env_int("FINDER_CHANNEL_ID", 0)
# Rend le salon en lecture seule pour @everyone lors du setup.
LOCK_FINDER_CHANNEL = _env_bool("LOCK_FINDER_CHANNEL", True)
# Durée de vie d'une session utilisateur en mémoire (secondes).
SESSION_TTL_SECONDS = _env_int("SESSION_TTL_SECONDS", 1800)
# Conservation des parcours en cours dans state/sessions.json (true par défaut : un redémarrage du
# bot ne fait plus perdre un questionnaire commencé). false = tout en mémoire.
SESSION_PERSIST = _env_bool("SESSION_PERSIST", True)
