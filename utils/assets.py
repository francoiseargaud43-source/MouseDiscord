"""Lecture de assets/images.json : URL des images affichées à chaque étape et à chaque résultat.

Deux façons de renseigner une image (les deux peuvent cohabiter dans le même fichier) :
- un **nom de fichier** repris de ``assets/illustrations/`` (ex. ``T08_azemouse_banniere.png``) :
  il est résolu avec ``IMAGES_BASE_URL`` (fichier ``.env``), qui désigne le dossier public où les
  illustrations ont été publiées — une seule variable à changer au déploiement ;
- une **URL complète** commençant par ``https://`` (hébergement externe) : utilisée telle quelle.

Une valeur vide, un nom de fichier sans ``IMAGES_BASE_URL``, un schéma non https ou un nom de
fichier invalide n'affichent aucune image : le parcours reste utilisable (aucune exception).

Chartes d'affichage rappelées ici (voir ``docs/REPORTE_DESIGN.md``) : fond Nuit (#0B1220),
identité Bordeaux (#8A2342) en couleur latérale d'embed, jaune Étincelle (#F0C43C) en highlight
uniquement dans les images. Discord n'accepte qu'une image par embed et n'autorise pas de police
personnalisée dans le texte natif : les typographies Syne/Fraunces/JetBrains vivent dans les
images, la hiérarchie du texte est rendue par le Markdown natif.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

# Clés d'image par étape et par illustration de résultat.
# Repère des étapes du parcours (4 étapes) : step1_grip (1/4), step2_thenar (2/4),
# step2_measure (3/4), step3_budget (4/4, facultatif). Les noms « step2_measure » et
# « step3_budget » sont conservés pour ne pas casser un assets/images.json déjà renseigné.
IMAGE_KEYS = (
    "banner",
    "step1_grip",
    "step2_thenar",
    "step2_measure",
    "step3_budget",
    "illustration_mouse_dimensions",
    "illustration_rear_narrow",
    "illustration_hump_mid",
    "illustration_hump_front",
    "illustration_hump_rear",
    "illustration_buttons_high",
    "illustration_buttons_low",
    "illustration_buttons_mid",
    "illustration_grip_relaxed",
    "illustration_grip_aggressive",
    "illustration_grip_pincer",
)
# Anciennes clés acceptées en repli pour ne pas perdre une URL déjà renseignée.
LEGACY_KEYS = {"step3_budget": "step4_budget"}

# Nom de fichier simple (pas de schéma, pas de chemin relatif, pas de « .. »).
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.(?:png|jpe?g|webp|gif)$")
# URL https complète utilisable telle quelle : ni espace, ni saut de ligne, ni caractère de contrôle
# (trouvé le 2026-10-13, même famille que les liens d'achat : une adresse qui en contient n'est pas
# une URL — Discord refuse alors l'image, voire l'embed entier. Ici : pas d'image, jamais d'erreur.)
_URL_HTTPS_UTILISABLE = re.compile(r"^https://[^\s\x00-\x1f\x7f]+$")


def default_base_url() -> str:
    """``IMAGES_BASE_URL`` du fichier ``.env`` (chaîne vide si non renseignée)."""
    try:
        from config import IMAGES_BASE_URL
    except ImportError:  # module utilisé hors du projet (tests isolés)
        return ""
    return IMAGES_BASE_URL or ""


def build_image_url(value: object, base_url: str | None = None) -> str | None:
    """Résout une entrée de ``images.json`` en URL https, ou ``None`` si rien ne doit être affiché."""
    if not isinstance(value, str):
        return None
    entry = value.strip()
    if not entry:
        return None
    if entry.startswith("https://"):
        if _URL_HTTPS_UTILISABLE.match(entry):
            return entry
        log.warning("URL d'image ignorée (espace ou caractère de contrôle) : %r", entry[:120])
        return None
    base = (default_base_url() if base_url is None else base_url) or ""
    base = base.strip()
    if not base or not _FILENAME_RE.match(entry):
        return None
    if not base.startswith("https://"):
        log.warning("IMAGES_BASE_URL doit commencer par https:// (valeur actuelle : %r).", base)
        return None
    return f"{base.rstrip('/')}/{entry}"


def load_image_urls(path: Path, base_url: str | None = None) -> dict[str, str | None]:
    """Retourne {clé: url} ; ``None`` si l'URL est vide ou invalide (pas d'image affichée)."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        log.warning("Configuration d'images introuvable : %s", path)
        raw = {}
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Configuration d'images illisible (%s) : %s", path, exc)
        raw = {}
    if not isinstance(raw, dict):
        log.warning("Configuration d'images illisible (objet attendu) : %s", path)
        raw = {}
    resolver = base_url if base_url is not None else default_base_url()
    urls: dict[str, str | None] = {}
    for key in IMAGE_KEYS:
        value = raw.get(key)
        if value in (None, "") and key in LEGACY_KEYS:
            value = raw.get(LEGACY_KEYS[key])
        urls[key] = build_image_url(value, resolver)
    return urls
