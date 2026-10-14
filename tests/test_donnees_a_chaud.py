"""Lecture à chaud des fichiers de données : jamais de cache, jamais de redémarrage.

Promesse du guide de déploiement (et de la docstring de `compute_selection`) : **remplacer un
fichier de données sur le serveur suffit** — le bot le relit à chaque interaction. Elle n'est vraie
que si *chaque* appel relit le disque : un `lru_cache` ajouté « pour la performance », ou un
catalogue capturé une fois au démarrage, la casserait en silence (le membre verrait l'ancien prix,
l'ancien nom, l'ancienne forme, et personne ne comprendrait pourquoi avant longtemps).

Ces trois tests refusent les trois façons de casser la promesse :

1. un cache dans le chargeur de catalogue ;
2. un cache dans le chargeur des liens commerciaux ;
3. un catalogue lu une seule fois par le moteur (le cas le plus probable : la lecture est faite
   dans `compute_selection`, elle doit rester **dans** la fonction).

Défaut de la même famille trouvé le 2026-10-12 (C61) : le rapport de statistiques « de référence »
était en réalité un rapport de grille resserrée — un artefact figé que plus personne ne relisait.
"""
from __future__ import annotations

import copy
import json

from config import MOUSE_DB_PATH
from utils.catalog import load_catalog, load_commercial_links


def _catalogue_brut() -> list[dict]:
    return json.loads(MOUSE_DB_PATH.read_text(encoding="utf-8"))


def test_le_catalogue_est_relu_a_chaque_appel(tmp_path):
    """Deux appels, deux lectures : une souris ajoutée au fichier doit apparaître aussitôt."""
    copie = tmp_path / "mouse_db.json"
    brut = _catalogue_brut()
    copie.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
    avant = [m.id for m in load_catalog(copie)]

    ajoutee = copy.deepcopy(brut[0])
    ajoutee["id"] = "souris_ajoutee_a_chaud"
    ajoutee["model"] = "Ajoutée à chaud"
    copie.write_text(json.dumps([*brut, ajoutee], ensure_ascii=False), encoding="utf-8")
    apres = [m.id for m in load_catalog(copie)]

    assert apres == [*avant, "souris_ajoutee_a_chaud"], (
        "le catalogue n'a pas été relu : un cache a été ajouté dans load_catalog "
        "(la promesse « aucun redémarrage » du guide de déploiement ne tient plus)"
    )


def test_les_liens_commerciaux_sont_relus_a_chaque_appel(tmp_path):
    """Même règle pour les liens d'achat : remplacer le fichier suffit, sans redémarrer."""
    fichier = tmp_path / "commercial_links.json"
    fichier.write_text(json.dumps({"atk_u2": "https://boutique.test/avant"}), encoding="utf-8")
    assert load_commercial_links(fichier)["atk_u2"] == "https://boutique.test/avant"

    fichier.write_text(json.dumps({"atk_u2": "https://boutique.test/apres"}), encoding="utf-8")
    assert load_commercial_links(fichier)["atk_u2"] == "https://boutique.test/apres", (
        "les liens commerciaux ne sont pas relus : un cache a été ajouté dans load_commercial_links"
    )


def test_le_calcul_relit_le_catalogue_a_chaque_parcours(tmp_path, monkeypatch):
    """`compute_selection` lit le catalogue de chaque parcours : renommer les souris se voit tout de suite.

    Le test renomme **toutes** les souris du fichier (préfixe « MAJ ») et vérifie que le calcul
    suivant renvoie exactement ces noms — c'est la preuve que ni le fichier, ni les objets `Mouse`
    ne sont conservés d'un parcours à l'autre. Le chemin est celui du module (`flux.MOUSE_DB_PATH`),
    comme le fait `tools/db_effect.py` : c'est le branchement que le serveur remplace en pratique.
    """
    from cogs import finder_flow as flux
    from utils.models import BudgetMode, Grip, Thenar
    from utils.session import FinderSession

    copie = tmp_path / "mouse_db.json"
    copie.write_bytes(MOUSE_DB_PATH.read_bytes())
    monkeypatch.setattr(flux, "MOUSE_DB_PATH", copie)

    def noms() -> list[str]:
        session = FinderSession(user_id=1)
        session.grip = Grip.PALM
        session.thenar = Thenar.PETITE
        session.hand_length_mm = 180.0
        session.hand_width_mm = 90.0
        session.budget_mode = BudgetMode.PEU_IMPORTE_PRIX
        return [score.mouse.model for score in flux.result_slots(flux.compute_selection(session))
                if score is not None]

    avant = noms()
    assert avant, "aucune place calculée : le test ne prouverait rien"

    brut = _catalogue_brut()
    for souris in brut:
        souris["model"] = f"MAJ {souris['model']}"
    copie.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")

    apres = noms()
    assert apres == [f"MAJ {nom}" for nom in avant], (
        "le calcul n'a pas relu le catalogue : la lecture a été sortie de compute_selection "
        "(ou mise en cache) — le guide promet qu'aucun redémarrage n'est nécessaire"
    )
