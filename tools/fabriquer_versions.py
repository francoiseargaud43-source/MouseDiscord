"""Fabrique ``data/versions.json`` depuis le relevé ATK version par version.

Le relevé (``docs/audit/ATK_VERSIONS_2026-11-12.csv``) a été fait sur les fiches officielles ATK, page
France, une ligne par version en vente ; l'autonomie vient du fichier de compléments posé à côté
(``ATK_VERSIONS_COMPLEMENTS_2026-11-12.csv``). Rien n'est converti ni deviné : une case vide reste absente.

Usage :
    python tools/fabriquer_versions.py docs/audit/ATK_VERSIONS_2026-11-12.csv data/versions.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Souris du catalogue -> (modèle du relevé, variante que son bouton d'achat ouvre).
SOURIS = {
    "atk_f1_ultimate": ("F1 V3", "48175399370970"),
    "atk_x1_ultra_max": ("X1 V2", "47058382782682"),
    "atk_z1_ultra": ("Z1 V2", "47222052290778"),
    "atk_u2_v2_ultimate": ("U2 V2", "47201864974554"),
    "atk_u2_v2_mini": ("U2 V2 Mini", "47204034150618"),
    "atk_zero": ("ZERO", "47655307804890"),
    "atk_ghost_ultimate": ("Ghost (carbone)", "47320425595098"),
    "atk_ghost_extreme": ("Ghost (carbone)", "47320425627866"),
    "atk_a9_ultimate": ("A9 Ultimate", "46878654005466"),
    "atk_a9_air": ("A9 Ultimate", "47193565364442"),
    "atk_a9_mini": ("A9 Ultimate Mini", "47852235718874"),
}

LISEZ_MOI = (
    "Versions d'une même souris (même coque, autres composants), affichées sous le résultat "
    "(utils/versions.py). Relevé du 2026-11-12 sur les fiches officielles ATK, page France "
    "(https://www.atk.store/en-fr/products/<handle>?country=FR) : prix en euros tels qu'affichés "
    "par la boutique (elle encaisse en dollars, au taux qu'elle affiche), aucune conversion faite ici. "
    "Autonomie : heures à 1000 Hz du comparateur officiel ATK (« Product Finder & Comparison »). "
    "Une valeur absente de la fiche reste absente. « resultat » marque la version décrite par la "
    "fiche du catalogue. Une version épuisée a « dispo » à false et n'est pas proposée. "
    "Fabriqué par tools/fabriquer_versions.py depuis docs/audit/ATK_VERSIONS_2026-11-12.csv."
)
AFFILIATION = (
    "Programme ATK (GoAffPro) : « When people visit the store using your link, you get commissions "
    "on everything they buy » — la commission vaut quelle que soit la version achetée ; chaque "
    "lien porte quand même ?ref=aze."
)


def _lire(chemin: Path) -> list[dict[str, str]]:
    with chemin.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def fabriquer(releve: Path, complements: Path | None) -> dict:
    lignes = _lire(releve)
    handle = None
    for ligne in lignes:
        if ligne["handle_produit"] != "idem":
            handle = ligne["handle_produit"]
        ligne["handle"] = handle
    autonomie: dict[str, int] = {}
    if complements is not None and complements.exists():
        for ligne in _lire(complements):
            heures = re.search(r"/\s*(\d+)\s*Hours", ligne["batterie"], re.I)
            if heures:
                autonomie[ligne["variant_id"]] = int(heures.group(1))
    donnees: dict = {"_lisez_moi": LISEZ_MOI, "_affiliation": AFFILIATION}
    for ident, (modele, variante) in SOURIS.items():
        versions = []
        for ligne in (x for x in lignes if x["modele"] == modele):
            nom = ligne["version"].replace("U2 V2 ", "") if modele.startswith("U2 V2") else ligne["version"]
            version = {
                "nom": nom,
                "prix_eur": float(ligne["prix_EUR"]),
                "dispo": ligne["stock"] == "oui",
                "lien": (f"https://www.atk.store/en-fr/products/{ligne['handle']}"
                         f"?country=FR&ref=aze&variant={ligne['variant_id']}"),
            }
            if ligne["capteur"].strip() and "(sic)" not in ligne["capteur"]:
                version["capteur"] = ligne["capteur"].strip()
            if re.fullmatch(r"\d+", ligne["polling_hz"]):
                version["hz"] = int(ligne["polling_hz"])
            poids = re.match(r"(\d+(?:\.\d+)?)", ligne["poids_g"])
            if poids:
                version["poids_g"] = float(poids.group(1))
            if ligne["switchs"]:
                version["switchs"] = ligne["switchs"]
            if ligne["mcu"]:
                version["mcu"] = ligne["mcu"]
            if ligne["variant_id"] in autonomie:
                version["autonomie_h"] = autonomie[ligne["variant_id"]]
            if "Magnetic Charging" in ligne["version"]:
                version["en_plus"] = ["base de charge magnétique"]
            if ligne["variant_id"] == variante:
                version["resultat"] = True
            versions.append(version)
        if not any(v.get("resultat") for v in versions):
            raise ValueError(f"{ident} : la variante {variante} n'est pas dans le relevé")
        premiere = next(x for x in lignes if x["modele"] == modele)
        donnees[ident] = {
            "releve": "2026-11-12",
            "page": f"https://www.atk.store/en-fr/products/{premiere['handle']}?country=FR",
            "versions": versions,
        }
    return donnees


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fabrique data/versions.json depuis le relevé ATK.")
    parser.add_argument("releve", type=Path, help="relevé CSV (docs/audit/ATK_VERSIONS_2026-11-12.csv)")
    parser.add_argument("sortie", type=Path, help="fichier JSON à écrire (data/versions.json)")
    args = parser.parse_args(argv)
    if not args.releve.is_file():
        parser.exit(2, f"relevé introuvable : {args.releve}\n")
    if not args.sortie.parent.is_dir():
        parser.exit(2, f"dossier de destination introuvable : {args.sortie.parent}\n")
    complements = args.releve.with_name(args.releve.name.replace("ATK_VERSIONS_", "ATK_VERSIONS_COMPLEMENTS_"))
    donnees = fabriquer(args.releve, complements)
    args.sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Écrit : {args.sortie} ({sum(1 for k in donnees if not k.startswith('_'))} souris)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
