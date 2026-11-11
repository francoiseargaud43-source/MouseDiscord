"""Résume ce qui diffère entre un fichier JSON du serveur et celui du dépôt.

Appelé par ``deploiement/executer.sh`` (action ``etat``) :
``python3 comparer_donnees.py <nom affiché> <fichier du serveur> <fichier du dépôt>``.
Sert à repérer une retouche faite directement sur le serveur avant qu'un déploiement ne l'écrase.
"""
from __future__ import annotations

import json
import sys


def charger(chemin: str):
    with open(chemin, encoding="utf-8") as fichier:
        return json.load(fichier)


def par_cle(donnees) -> dict:
    """``mouse_db.json`` est une liste de fiches (clé ``id``) ; les autres fichiers sont des dictionnaires."""
    if isinstance(donnees, list):
        return {str(fiche.get("id", rang)): fiche for rang, fiche in enumerate(donnees)}
    return donnees


def court(valeur, limite: int = 140) -> str:
    texte = json.dumps(valeur, ensure_ascii=False)
    return texte if len(texte) <= limite else texte[: limite - 1] + "…"


def main(arguments: list[str]) -> int:
    nom, chemin_serveur, chemin_depot = arguments[1:4]
    try:
        serveur = par_cle(charger(chemin_serveur))
    except (OSError, ValueError) as erreur:
        print(f"{nom} : illisible sur le serveur ({erreur})")
        return 0
    depot = par_cle(charger(chemin_depot))

    nouvelles = sorted(set(depot) - set(serveur))
    seulement_serveur = sorted(set(serveur) - set(depot))
    modifiees = sorted(cle for cle in set(serveur) & set(depot) if serveur[cle] != depot[cle])
    print(f"{nom} : {len(nouvelles)} entrée(s) nouvelle(s) dans le dépôt, "
          f"{len(seulement_serveur)} seulement sur le serveur, {len(modifiees)} modifiée(s)")
    for cle in nouvelles:
        print(f"  + {cle}")
    for cle in seulement_serveur:
        print(f"  ? {cle} (seulement sur le serveur) : {court(serveur[cle])}")
    for cle in modifiees:
        avant, apres = serveur[cle], depot[cle]
        if isinstance(avant, dict) and isinstance(apres, dict):
            champs = sorted(champ for champ in set(avant) | set(apres) if avant.get(champ) != apres.get(champ))
            print(f"  ~ {cle} : {', '.join(champs)}")
        else:
            print(f"  ~ {cle} : serveur = {court(avant)} | dépôt = {court(apres)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
