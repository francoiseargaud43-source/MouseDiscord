"""Contrôle d'identité d'un corpus d'images avant toute mesure.

Pourquoi cet outil existe : la campagne de mesure de la hauteur des boutons s'appuie sur des images
récupérées par recherche (« le nom de fichier ne prouve rien »). Or un moteur de recherche renvoie
souvent la **même** photo pour des requêtes portant sur des modèles différents : les octets sont
identiques, seul le nom du fichier change. Une image qui porte plusieurs noms de modèles ne peut donc
être attribuée à aucun d'eux — l'utiliser pour une mesure reviendrait à mesurer une souris inconnue.

Cet outil regroupe les fichiers par **empreinte SHA-256** et signale :

- les **groupes de doublons** (mêmes octets, plusieurs noms) : images inexploitables pour une mesure
  attribuée à un modèle ;
- les images **uniques** (un seul nom) : seules candidates, et uniquement après vérification visuelle
  de ce que l'image montre réellement (nom imprimé sur la coque, logo, forme).

Aucune conclusion n'est tirée du nom de fichier : la décision reste humaine et visuelle. L'outil ne
produit que des faits vérifiables (des empreintes).

Usage :
    python tools/image_corpus_check.py [DOSSIER] [--json] [--uniques]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"})
_CHUNK = 1 << 20


def fingerprint(path: Path) -> str:
    """Empreinte SHA-256 du fichier (lecture par blocs, les images peuvent être volumineuses)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def images_of(directory: Path) -> list[Path]:
    """Fichiers image du dossier (récursif), triés par nom — sans dépendre de la casse du suffixe."""
    return sorted(p for p in directory.rglob("*")
                  if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def groups_by_identity(directory: Path) -> tuple[list[list[str]], list[str]]:
    """Renvoie (groupes de doublons, images uniques), chaque élément listant des noms de fichiers.

    Un « groupe de doublons » rassemble les fichiers qui ont exactement les mêmes octets : c'est la
    preuve qu'une seule et même photo circule sous plusieurs noms. Les noms sont triés, et les
    groupes sont triés du plus gros au plus petit puis par premier nom, pour un affichage stable.
    """
    by_hash: dict[str, list[str]] = defaultdict(list)
    for path in images_of(directory):
        by_hash[fingerprint(path)].append(path.name)
    duplicated = sorted((sorted(names) for names in by_hash.values() if len(names) > 1),
                        key=lambda names: (-len(names), names[0]))
    unique = sorted(names[0] for names in by_hash.values() if len(names) == 1)
    return duplicated, unique


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Doublons d'un corpus d'images (identité vérifiable).")
    parser.add_argument("dossier", nargs="?", default="image-search")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--uniques", action="store_true",
                        help="lister aussi les images uniques (candidates à une mesure attribuée)")
    args = parser.parse_args(argv)

    directory = Path(args.dossier)
    if not directory.is_dir():
        parser.error(f"dossier introuvable : {directory}")

    duplicated, unique = groups_by_identity(directory)
    total = sum(len(names) for names in duplicated) + len(unique)
    if args.json:
        print(json.dumps({"fichiers": total,
                          "images_distinctes": len(duplicated) + len(unique),
                          "doublons": duplicated, "uniques": unique}, ensure_ascii=False, indent=2))
        return 0

    print(f"Corpus : {directory} — {total} fichiers, {len(duplicated) + len(unique)} images distinctes, "
          f"{len(duplicated)} groupe(s) de doublons")
    for index, names in enumerate(duplicated, start=1):
        print(f"\nGroupe {index} ({len(names)} noms pour une seule image) :")
        for name in names:
            print(f"  - {name}")
    print(f"\nImages uniques : {len(unique)}")
    if args.uniques:
        for name in unique:
            print(f"  - {name}")
    if duplicated:
        print("\nRègle : une image qui porte plusieurs noms de modèles ne peut être attribuée à aucun\n"
              "d'eux — elle est écartée des mesures. L'identité d'une image unique se vérifie ensuite\n"
              "visuellement (nom imprimé sur la coque, logo, forme), jamais par son nom de fichier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
