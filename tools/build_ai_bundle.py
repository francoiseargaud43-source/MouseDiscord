"""Prépare le pack à envoyer à une IA de recherche (voir docs/PROMPT_RECHERCHE_SOURIS_ATK.md).

Usage : python tools/build_ai_bundle.py [chemin_de_sortie.zip]

Le pack contient : le prompt, le catalogue actuel, les documents de référence, le code qui définit
les règles (barème, sélection, vocabulaire, validation) et la liste des identifiants déjà pris.
Il ne contient JAMAIS de secret (`.env`), l'état local (`state/`), les liens d'affiliation ni `.venv/`.
Code de sortie 1 si un fichier attendu est absent du dépôt.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Fichiers fournis à l'IA : documentation + code qui fait foi + données.
BUNDLE_FILES = (
    "docs/PROMPT_RECHERCHE_SOURIS_ATK.md",
    "README.md",
    "data/mouse_db.json",
    "docs/audit/CATALOGUE_ATK.md",
    "docs/audit/matrice_profils.md",
    "utils/matcher.py",
    "utils/selection.py",
    "utils/models.py",
    "utils/catalog.py",
)
DEFAULT_OUTPUT = ROOT / "pack_ia_mousediscord.zip"


def existing_ids(root: Path = ROOT) -> str:
    """Liste lisible des identifiants et libellés déjà présents (l'IA ne doit pas les réutiliser)."""
    with (root / "data" / "mouse_db.json").open(encoding="utf-8") as fh:
        mice = json.load(fh)
    lines = ["# Identifiants déjà utilisés dans data/mouse_db.json (à ne pas réutiliser)", ""]
    for mouse in mice:
        lines.append(f"{mouse['id']}\t{mouse.get('brand', '')} {mouse.get('model', '')}".rstrip())
    return "\n".join(lines) + "\n"


def missing_files(root: Path = ROOT) -> list[str]:
    return [rel for rel in BUNDLE_FILES if not (root / rel).is_file()]


def build_bundle(output: Path = DEFAULT_OUTPUT, root: Path = ROOT) -> Path:
    """Crée l'archive et retourne son chemin. Lève FileNotFoundError si un fichier attendu manque."""
    missing = missing_files(root)
    if missing:
        raise FileNotFoundError("fichiers attendus absents : " + ", ".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in BUNDLE_FILES:
            archive.write(root / rel, arcname=rel)
        archive.writestr("ids_existants.txt", existing_ids(root))
        archive.writestr(
            "LISEZ-MOI.txt",
            "Pack de recherche AzeMouse.\n"
            "1) Joignez cette archive à votre conversation avec l'IA.\n"
            "2) Copiez le prompt du fichier docs/PROMPT_RECHERCHE_SOURIS_ATK.md (§3).\n"
            "3) Ajoutez les liens des vidéos YouTube et vos captures Discord.\n"
            "Aucun secret (token, .env) ne figure dans ce pack.\n",
        )
    return output


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        output = build_bundle(Path(argv[0]) if argv else DEFAULT_OUTPUT)
    except FileNotFoundError as exc:
        print(f"ERREUR : {exc}")
        return 1
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    print(f"Écrit : {output} ({output.stat().st_size // 1024} Ko, {len(names)} fichiers)")
    for name in names:
        print(f"  - {name}")
    print("\nAjoutez à votre message : liens des vidéos YouTube + captures Discord (voir §4 du prompt).")
    print("Aucun secret n'est inclus : ni .env, ni state/, ni liens d'affiliation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
