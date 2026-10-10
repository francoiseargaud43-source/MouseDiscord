"""Chargement et validation des données (catalogue + liens commerciaux)."""
from __future__ import annotations

import json
import logging
from dataclasses import fields
from pathlib import Path
from typing import Any, Mapping

from utils.models import Mouse

log = logging.getLogger(__name__)

VALID_FITS = frozenset({"Élevé", "Moyen", "Faible"})
VALID_BUTTON_HEIGHTS = frozenset({"Low", "Mid", "High"})


class CatalogError(ValueError):
    """Erreur de structure dans data/mouse_db.json."""


def parse_mouse(raw: Mapping[str, Any], index: int) -> Mouse:
    names = [f.name for f in fields(Mouse)]
    missing = [name for name in names if name not in raw]
    if missing:
        raise CatalogError(f"Souris #{index} : champs manquants {missing}")
    mouse = Mouse(**{name: raw[name] for name in names})
    for field_name in ("palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit"):
        if getattr(mouse, field_name) not in VALID_FITS:
            raise CatalogError(f"{mouse.id} : {field_name} invalide ({getattr(mouse, field_name)!r})")
    if mouse.button_height not in VALID_BUTTON_HEIGHTS:
        raise CatalogError(f"{mouse.id} : button_height invalide ({mouse.button_height!r})")
    if mouse.price_eur <= 0 or mouse.length_mm <= 0 or mouse.width_max_mm <= 0:
        raise CatalogError(f"{mouse.id} : prix et dimensions doivent être positifs")
    return mouse


def load_catalog(path: Path) -> tuple[Mouse, ...]:
    with Path(path).open(encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise CatalogError("mouse_db.json doit contenir une liste")
    mice = tuple(parse_mouse(item, i) for i, item in enumerate(raw, start=1))
    ids = [m.id for m in mice]
    if len(ids) != len(set(ids)):
        raise CatalogError("Identifiants de souris dupliqués dans mouse_db.json")
    return mice


def load_commercial_links(path: Path) -> dict[str, str]:
    """Retourne {mouse_id: url}. Les entrées invalides sont ignorées avec un avertissement."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        log.warning("Fichier de liens introuvable : %s", path)
        return {}
    links: dict[str, str] = {}
    for mouse_id, url in raw.items():
        if mouse_id.startswith("_"):
            continue
        if isinstance(url, str) and url.startswith(("https://", "http://")):
            links[mouse_id] = url
        else:
            log.warning("Lien ignoré pour %s : URL invalide", mouse_id)
    return links
