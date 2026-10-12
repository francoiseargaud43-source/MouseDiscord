"""Le comparateur de données (``tools/db_effect.py``) doit prouver ce qu'il annonce.

Deux exigences, dans les deux sens : deux catalogues identiques ne peuvent produire **aucun** écart
(sinon l'outil inventerait des changements), et une modification réelle doit en produire (sinon
l'outil ne prouverait rien). Les deux catalogues de test sont écrits dans un dossier temporaire :
le dépôt n'est jamais modifié.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import db_effect  # noqa: E402
from config import MOUSE_DB_PATH  # noqa: E402


def _catalogue(modifie: bool, dossier: Path) -> Path:
    """Copie du catalogue réel, éventuellement modifiée : le prix de l'ATK ZERO tombe à 1 €."""
    entrees = json.loads(MOUSE_DB_PATH.read_text(encoding="utf-8"))
    if modifie:
        for entree in entrees:
            if entree["id"] == "atk_zero":
                entree["price_eur"] = 1.0
    chemin = dossier / ("catalogue_modifie.json" if modifie else "catalogue_identique.json")
    chemin.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    return chemin


def test_deux_catalogues_identiques_ne_produisent_aucun_ecart(tmp_path):
    """Un outil qui « trouve » des changements entre deux fichiers identiques serait inutilisable."""
    chemin = _catalogue(modifie=False, dossier=tmp_path)
    rapport = db_effect.comparer(chemin, chemin, "mini")
    assert rapport.profils >= 100, f"grille trop petite : {rapport.profils} profils"
    assert rapport.changes == [], rapport.changes[:3]


def test_un_prix_modifie_change_bien_des_profils(tmp_path):
    """Un prix d'entrée de gamme divisé par 70 doit remonter dans le parcours : sinon, rien n'est mesuré."""
    avant = _catalogue(modifie=False, dossier=tmp_path)
    apres = _catalogue(modifie=True, dossier=tmp_path)
    rapport = db_effect.comparer(avant, apres, "mini")
    assert rapport.changes, "aucun changement détecté alors que le prix de l'ATK ZERO a été modifié"
    assert "atk_zero" in " ".join(rapport.changes)
    # Le classement reste dans les trois places : aucune place ne se perd ni ne s'ajoute.
    assert rapport.place_gagnee == 0 and rapport.place_perdue == 0


def test_l_outil_refuse_deux_catalogues_qui_ne_lisent_pas_les_memes_souris(tmp_path):
    """Comparer deux catalogues différents ne veut rien dire : l'outil le dit au lieu de calculer."""
    avant = _catalogue(modifie=False, dossier=tmp_path)
    entrees = json.loads(avant.read_text(encoding="utf-8"))
    entrees = [e for e in entrees if e["id"] != "atk_zero"]
    incomplet = tmp_path / "catalogue_incomplet.json"
    incomplet.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="mêmes souris"):
        db_effect.comparer(avant, incomplet, "mini")
