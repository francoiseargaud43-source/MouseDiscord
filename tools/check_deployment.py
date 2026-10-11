"""Contrôle de déploiement (à lancer sur l'hébergement, depuis le dossier du projet) :

    python tools/check_deployment.py

Vérifie : version de Python, fichiers obligatoires, présence du token (sans l'afficher),
entiers de configuration, catalogue, liens et images, droit d'écriture de state/.
Code de sortie 1 s'il existe une ERREUR bloquante ; les ATTENTION n'empêchent pas le lancement.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values  # noqa: E402

OK, WARN, ERROR = "OK", "ATTENTION", "ERREUR"
REQUIRED_FILES = (
    "bot.py", "config.py", "requirements.txt",
    "cogs/__init__.py", "cogs/mouse_finder.py", "cogs/finder_flow.py",
    "utils/__init__.py", "utils/assets.py", "utils/catalog.py", "utils/matcher.py",
    "utils/models.py", "utils/selection.py", "utils/session.py", "utils/validation.py",
    "data/mouse_db.json",
)
PLACEHOLDER_HOSTS = ("url.com",)  # domaine d'exemple présent dans les données initiales
MIN_PYTHON = (3, 10)


def check(root: Path, env: Mapping[str, str], python_version: tuple = tuple(sys.version_info[:2])) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []

    if python_version < MIN_PYTHON:
        results.append((ERROR, f"Python {python_version[0]}.{python_version[1]} : version 3.10 minimum requise"))
    else:
        results.append((OK, f"Python {python_version[0]}.{python_version[1]}"))

    missing = [f for f in REQUIRED_FILES if not (root / f).is_file()]
    if missing:
        results.append((ERROR, f"fichiers obligatoires manquants : {', '.join(missing)}"))
    else:
        results.append((OK, "fichiers obligatoires présents"))

    env_file = root / ".env"
    file_values = dotenv_values(env_file) if env_file.is_file() else {}
    if not env_file.is_file():
        results.append((WARN, "fichier .env absent (valable seulement si les variables sont définies ailleurs)"))
    merged = {**file_values, **{k: v for k, v in env.items() if v is not None}}  # l'environnement du processus prime

    if (merged.get("DISCORD_TOKEN") or "").strip():
        results.append((OK, "DISCORD_TOKEN renseigné (valeur non affichée)"))
    else:
        results.append((ERROR, "DISCORD_TOKEN absent ou vide"))

    for name in ("FINDER_CHANNEL_ID", "SESSION_TTL_SECONDS"):
        raw = (merged.get(name) or "").strip()
        if raw and not raw.isdigit():
            results.append((ERROR, f"{name} doit être un nombre entier (valeur actuelle : {raw!r})"))

    catalog_path = root / "data" / "mouse_db.json"
    if catalog_path.is_file():
        try:
            from utils.catalog import load_catalog

            results.append((OK, f"catalogue lisible : {len(load_catalog(catalog_path))} souris"))
        except Exception as exc:  # noqa: BLE001 - diagnostic à afficher tel quel
            results.append((ERROR, f"data/mouse_db.json invalide : {exc}"))

    links_path = root / "data" / "commercial_links.json"
    try:
        raw_links = json.loads(links_path.read_text(encoding="utf-8")) if links_path.is_file() else {}
        real = {k: v for k, v in raw_links.items() if not k.startswith("_")}
        valid = [k for k, v in real.items() if isinstance(v, str) and v.startswith(("https://", "http://"))]
        results.append((OK, f"liens d'achat valides : {len(valid)} (sans lien, le résultat affiche « Liens à venir »)"))
        for key in real:
            if key in valid and any(host in real[key] for host in PLACEHOLDER_HOSTS):
                results.append((WARN, f"lien d'exemple détecté pour « {key} » : remplacez-le ou videz-le avant la mise en ligne"))
    except json.JSONDecodeError as exc:
        results.append((ERROR, f"commercial_links.json invalide (JSON) : {exc}"))

    images_path = root / "assets" / "images.json"
    base_url = (merged.get("IMAGES_BASE_URL") or "").strip()
    if images_path.is_file():
        try:
            images = json.loads(images_path.read_text(encoding="utf-8"))
            entries = {k: v.strip() for k, v in images.items()
                       if not k.startswith("_") and isinstance(v, str) and v.strip()}
            filenames = [v for v in entries.values() if not v.startswith("https://")]
            if base_url and not base_url.startswith("https://"):
                results.append((ERROR, f"IMAGES_BASE_URL doit commencer par https:// (valeur actuelle : {base_url!r})"))
            resolved = len(entries) - len(filenames) + (len(filenames) if base_url.startswith("https://") else 0)
            results.append((OK, f"images configurées : {resolved}/{len(entries)} (vide = pas d'illustration, sans erreur)"))
            if filenames and not base_url:
                results.append((WARN, f"IMAGES_BASE_URL n'est pas renseigné : {len(filenames)} illustration(s) de "
                                      "assets/illustrations/ ne seront pas affichées (voir README, section Personnaliser les images)"))
            missing = [name for name in filenames if not (root / "assets" / "illustrations" / name).is_file()]
            if missing:
                shown = ", ".join(missing[:5]) + ("…" if len(missing) > 5 else "")
                results.append((WARN, f"illustrations absentes de assets/illustrations/ : {shown}"))
        except json.JSONDecodeError as exc:
            results.append((ERROR, f"assets/images.json invalide (JSON) : {exc}"))
    else:
        results.append((WARN, "assets/images.json absent : le bot fonctionne sans illustration"))

    state_dir = root / "state"
    try:
        state_dir.mkdir(exist_ok=True)
        probe = state_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        results.append((OK, "dossier state/ inscriptible"))
    except OSError as exc:
        results.append((ERROR, f"dossier state/ non inscriptible : {exc}"))

    try:
        import discord

        results.append((OK, f"discord.py {discord.__version__} importable"))
    except ImportError:
        results.append((ERROR, "discord.py introuvable : lancez l'installation des dépendances (requirements.txt)"))

    return results


def main() -> int:
    results = check(ROOT, os.environ)
    for level, message in results:
        print(f"[{level:9}] {message}")
    errors = sum(1 for level, _ in results if level == ERROR)
    print(f"\n{errors} erreur(s) bloquante(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
