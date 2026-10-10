"""Lecture de assets/images.json : URL des images affichées à chaque étape."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Clés d'image par étape. Le parcours compte 3 étapes après le retrait de l'étape thénar.
IMAGE_KEYS = ("banner", "step1_grip", "step2_measure", "step3_budget")
# Ancienne clé « step4_budget » acceptée en repli pour ne pas perdre une URL déjà renseignée.
LEGACY_KEYS = {"step3_budget": "step4_budget"}


def load_image_urls(path: Path) -> dict[str, str | None]:
    """Retourne {clé: url} ; None si l'URL est vide ou invalide (pas d'image affichée)."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        log.warning("Configuration d'images introuvable : %s", path)
        raw = {}
    urls: dict[str, str | None] = {}
    for key in IMAGE_KEYS:
        value = raw.get(key)
        if value in (None, "") and key in LEGACY_KEYS:
            value = raw.get(LEGACY_KEYS[key])
        if isinstance(value, str) and value.startswith("https://"):
            urls[key] = value
        else:
            urls[key] = None
    return urls
