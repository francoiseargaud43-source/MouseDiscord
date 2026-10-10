"""Configuration centralisée du bot (variables d'environnement + chemins)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

MOUSE_DB_PATH = DATA_DIR / "mouse_db.json"
COMMERCIAL_LINKS_PATH = DATA_DIR / "commercial_links.json"
IMAGES_CONFIG_PATH = ASSETS_DIR / "images.json"
# Mémoire locale du message publié par !setup_finder (ignorée par Git).
FINDER_STATE_PATH = ROOT_DIR / "state" / "finder_message.json"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "oui"}


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!").strip() or "!"
# Salon cible de !setup_finder (ID numérique). Vide = salon où la commande est tapée.
FINDER_CHANNEL_ID = int(os.getenv("FINDER_CHANNEL_ID", "0").strip() or 0)
# Rend le salon en lecture seule pour @everyone lors du setup.
LOCK_FINDER_CHANNEL = _env_bool("LOCK_FINDER_CHANNEL", True)
# Durée de vie d'une session utilisateur en mémoire (secondes).
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))
