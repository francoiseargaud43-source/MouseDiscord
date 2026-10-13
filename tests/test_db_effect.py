"""Le comparateur de données (``tools/db_effect.py``) doit prouver ce qu'il annonce.

Trois exigences, dans les deux sens : deux catalogues identiques ne peuvent produire **aucun** écart
(sinon l'outil inventerait des changements), une modification réelle doit en produire (sinon
l'outil ne prouverait rien), et une simulation de retrait (option ``retrait=True``) doit peser les
souris sorties **sans** accepter pour autant un catalogue enrichi. Les catalogues de test sont
écrits dans un dossier temporaire : le dépôt n'est jamais modifié.
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


def test_un_retrait_se_mesure_avec_le_mode_retrait(tmp_path):
    """Retirer une souris : l'option ``retrait`` pèse les places qu'elle occupait au lieu de refuser."""
    avant = _catalogue(modifie=False, dossier=tmp_path)
    entrees = json.loads(avant.read_text(encoding="utf-8"))
    gardees = [entree for entree in entrees if entree["id"] != "vxe_mad_r"]
    reduit = tmp_path / "catalogue_reduit.json"
    reduit.write_text(json.dumps(gardees, ensure_ascii=False, indent=2), encoding="utf-8")

    rapport = db_effect.comparer(avant, reduit, "mini", retrait=True)
    assert rapport.retirees == ["vxe_mad_r"]
    assert rapport.changes, "aucun changement détecté alors que la VXE MAD R a été retirée"
    assert rapport.places_retirees > 0, "la souris retirée n'occupait aucune place : rien n'est mesuré"
    assert rapport.par_souris_retiree.get("vxe_mad_r") == rapport.places_retirees
    # Retirer une souris ne peut pas ajouter de place : la liste ne s'allonge jamais.
    assert rapport.place_gagnee == 0


def test_le_mode_retrait_refuse_un_catalogue_enrichi(tmp_path):
    """``retrait`` ne sert qu'à retirer : un catalogue qui ajoute une souris reste refusé."""
    avant = _catalogue(modifie=False, dossier=tmp_path)
    entrees = json.loads(avant.read_text(encoding="utf-8"))
    copie = dict(entrees[0])
    copie["id"] = "copie_de_test"
    entrees.append(copie)
    enrichi = tmp_path / "catalogue_enrichi.json"
    enrichi.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="mêmes souris"):
        db_effect.comparer(avant, enrichi, "mini", retrait=True)


def test_l_outil_refuse_deux_catalogues_qui_ne_lisent_pas_les_memes_souris(tmp_path):
    """Comparer deux catalogues différents ne veut rien dire : l'outil le dit au lieu de calculer."""
    avant = _catalogue(modifie=False, dossier=tmp_path)
    entrees = json.loads(avant.read_text(encoding="utf-8"))
    entrees = [e for e in entrees if e["id"] != "atk_zero"]
    incomplet = tmp_path / "catalogue_incomplet.json"
    incomplet.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="mêmes souris"):
        db_effect.comparer(avant, incomplet, "mini")

# --- Chasse aux micro-bugs du 2026-10-13 : un mauvais chemin doit se dire en une ligne ---
def test_un_catalogue_absent_est_signale_sans_trace(tmp_path, monkeypatch, capsys):
    """Avant : `FileNotFoundError` brut. Après : message lisible, code de sortie 2 (erreur d'usage)."""
    monkeypatch.setattr(sys, "argv", ["db_effect.py", "--avant", str(tmp_path / "absent.json"),
                                      "--grille", "mini"])
    with pytest.raises(SystemExit) as sortie:
        db_effect.main()
    assert sortie.value.code == 2
    assert "catalogue introuvable (AVANT)" in capsys.readouterr().err


def test_un_catalogue_illisible_est_signale_sans_trace(tmp_path, monkeypatch, capsys):
    """Un fichier qui n'est pas du JSON ne doit pas remonter `JSONDecodeError` brut non plus."""
    faux = tmp_path / "pas_du_json.json"
    faux.write_text("ceci n'est pas un catalogue", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["db_effect.py", "--avant", str(faux), "--grille", "mini"])
    with pytest.raises(SystemExit) as sortie:
        db_effect.main()
    assert sortie.value.code == 2
    assert "illisible ou incohérent" in capsys.readouterr().err
