"""Chargement et validation des données (catalogue + liens commerciaux).

Règles de validation (voir docs/audit/AUDIT.md) :
- identifiants uniques ; valeurs de compatibilité dans FIT_LEVELS (dont « Inconnu ») ;
- une dimension ``None`` doit être justifiée (conflit documenté ou non mesurée) ;
- un conflit de dimension doit lister ses valeurs et ses sources ;
- chaque donnée provenant d'une source web doit citer au moins une source.
"""
from __future__ import annotations

import json
import logging
from dataclasses import fields
from pathlib import Path
from typing import Any, Mapping

from utils.models import (
    BUTTON_HEIGHTS,
    DIMENSION_STATUSES,
    FIT_LEVELS,
    FIT_STATUSES,
    HUMP_POSITIONS,
    PRICE_STATUSES,
    SHAPES,
    UNKNOWN,
    Mouse,
    Source,
)

log = logging.getLogger(__name__)

REQUIRED_KEYS = ("id", "brand", "model", "budget_tier", "width_max_mm", "hump_position",
                 "button_height", "palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit", "fit_rationale")
BUDGET_TIERS = frozenset({"Économique", "Qualité-Prix", "Haut de Gamme"})


class CatalogError(ValueError):
    """Erreur de structure ou de cohérence dans data/mouse_db.json."""


def _positive_or_none(value: Any, name: str, mouse_id: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise CatalogError(f"{mouse_id} : {name} doit être un nombre positif ou null")
    return float(value)


def parse_mouse(raw: Mapping[str, Any], index: int) -> Mouse:
    mouse_id = str(raw.get("id", f"#{index}"))
    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise CatalogError(f"{mouse_id} : champs obligatoires manquants {missing}")

    for name in ("palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit"):
        if raw[name] not in FIT_LEVELS:
            raise CatalogError(f"{mouse_id} : {name} invalide ({raw[name]!r})")
    if raw["button_height"] not in BUTTON_HEIGHTS:
        raise CatalogError(f"{mouse_id} : button_height invalide ({raw['button_height']!r})")
    if raw["hump_position"] not in HUMP_POSITIONS:
        raise CatalogError(f"{mouse_id} : hump_position invalide ({raw['hump_position']!r})")
    shape = raw.get("shape", UNKNOWN)
    if shape not in SHAPES:
        raise CatalogError(f"{mouse_id} : shape invalide ({shape!r})")
    if raw["budget_tier"] not in BUDGET_TIERS:
        raise CatalogError(f"{mouse_id} : budget_tier invalide ({raw['budget_tier']!r})")

    dimension_status = raw.get("dimension_status", "owner_spec_unverified")
    if dimension_status not in DIMENSION_STATUSES:
        raise CatalogError(f"{mouse_id} : dimension_status invalide ({dimension_status!r})")
    price_status = raw.get("price_status", "owner_spec_unverified")
    if price_status not in PRICE_STATUSES:
        raise CatalogError(f"{mouse_id} : price_status invalide ({price_status!r})")
    fit_status = raw.get("fit_status", "owner_spec")
    if fit_status not in FIT_STATUSES:
        raise CatalogError(f"{mouse_id} : fit_status invalide ({fit_status!r})")

    length = _positive_or_none(raw.get("length_mm"), "length_mm", mouse_id)
    conflicts = dict(raw.get("conflicts", {}))
    if length is None and "length_mm" not in conflicts and raw.get("notes", "") == "":
        raise CatalogError(f"{mouse_id} : length_mm null sans conflit documenté ni note")
    for key, conflict in conflicts.items():
        values = conflict.get("values", [])
        if len(values) < 2 or not conflict.get("sources"):
            raise CatalogError(f"{mouse_id} : conflit « {key} » sans au moins 2 valeurs et leurs sources")
    width = _positive_or_none(raw["width_max_mm"], "width_max_mm", mouse_id)
    if width is None:
        raise CatalogError(f"{mouse_id} : width_max_mm est obligatoire")

    sources = tuple(Source.from_dict(s) for s in raw.get("sources", []))
    if dimension_status in {"verified", "single_source"} and not sources:
        raise CatalogError(f"{mouse_id} : dimensions déclarées vérifiées sans source")
    # Une forme renseignée doit citer la source qui l'atteste (jamais de forme devinée).
    if shape != UNKNOWN and not any("shape" in source.fields for source in sources):
        raise CatalogError(f"{mouse_id} : shape renseigné sans source listant « shape »")

    polling = raw.get("polling_hz")
    if polling is not None and (not isinstance(polling, int) or polling <= 0):
        raise CatalogError(f"{mouse_id} : polling_hz invalide")

    values = {f.name: raw.get(f.name) for f in fields(Mouse) if f.name in raw}
    values.update(
        id=mouse_id,
        length_mm=length,
        width_max_mm=width,
        height_mm=_positive_or_none(raw.get("height_mm"), "height_mm", mouse_id),
        grip_width_mm=_positive_or_none(raw.get("grip_width_mm"), "grip_width_mm", mouse_id),
        price_eur=_positive_or_none(raw.get("price_eur"), "price_eur", mouse_id),
        conflicts=conflicts,
        sources=sources,
        category=raw.get("category", "ATK"),
        family=raw.get("family", ""),
        dimension_status=dimension_status,
        price_status=price_status,
        fit_status=fit_status,
        notes=raw.get("notes", ""),
        price_note=raw.get("price_note", ""),
    )
    if values["price_eur"] is None and price_status == "verified":
        raise CatalogError(f"{mouse_id} : price_status 'verified' exige un prix")
    return Mouse(**values)


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
