"""Tests de la campagne « hauteur des boutons » (`tools/campagne_boutons.py`, 80e passe).

Toutes les images sont SYNTHÉTIQUES : la géométrie dessinée est connue au dixième de millimètre, donc
on vérifie que la mesure la retrouve — quel que soit le rendu (fond transparent, fond uni, simple tracé
sur une grille avec une légende, avant à gauche ou à droite). Les attentes sont écrites en clair : aucun
test ne redemande ses valeurs à l'outil qu'il vérifie.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import campagne_boutons as cb  # noqa: E402

PX_MM = 8.0                       # 8 pixels par millimètre : 0,125 mm par pixel
L_MM, H_MM = 120.0, 40.0
# Dessus de la coque : (distance à la pointe avant en mm, hauteur en mm) — sommet à 70 mm (bosse « Mid »).
DESSUS_BAS = [(0, 14.0), (10, 22.0), (20, 28.0), (30, 32.0), (70, 40.0), (110, 30.0), (120, 12.0)]


def dessiner(chemin: Path, dessus=DESSUS_BAS, *, avant="gauche", fond=(255, 255, 255, 255),
             trace=None, grille=False, legende=False, etirement=1.0) -> Path:
    """Une souris de profil. ``trace`` = couleur du contour seul (sinon silhouette pleine)."""
    marge = 60
    w = int(L_MM * PX_MM) + 2 * marge
    h = int(H_MM * PX_MM * etirement) + 2 * marge
    img = Image.new("RGBA", (w, h), fond)
    draw = ImageDraw.Draw(img)
    if grille:
        for y in range(10, h, 40):
            draw.line([(0, y), (w - 1, y)], fill=(70, 70, 80, 255), width=1)
        for x in range(10, w, 40):
            draw.line([(x, 0), (x, h - 1)], fill=(70, 70, 80, 255), width=1)
    base = h - marge

    def point(d, hauteur):
        x = marge + d * PX_MM if avant == "gauche" else marge + (L_MM - d) * PX_MM
        return (x, base - hauteur * PX_MM * etirement)

    contour = [point(0, 0)] + [point(d, v) for d, v in dessus] + [point(L_MM, 0)]
    if trace is None:
        draw.polygon(contour, fill=(30, 30, 30, 255))
    else:
        draw.line(contour + [contour[0]], fill=trace, width=2)
    if legende:
        draw.rectangle([5, 5, 120, 30], fill=trace or (30, 30, 30, 255))   # un cartouche de texte, isolé
    img.save(chemin)
    return chemin


def mesurer(chemin: Path, avant="gauche", couleur=None) -> cb.Profil:
    img = cb.ouvrir_image(chemin)
    return cb.profil(cb.silhouette(img, couleur), L_MM, H_MM, avant)


# ---------------------------------------------------------------------------
# Le profil est exact, quel que soit le rendu
# ---------------------------------------------------------------------------
def test_profil_exact_sur_une_silhouette_detouree(tmp_path):
    prof = mesurer(dessiner(tmp_path / "s.png", fond=(0, 0, 0, 0)))
    assert prof.ecart_aspect < 0.02
    m = prof.metriques()
    assert m["h_10mm"] == pytest.approx(22.0, abs=0.3)
    assert m["h_20mm"] == pytest.approx(28.0, abs=0.3)
    assert m["h_30mm"] == pytest.approx(32.0, abs=0.3)
    assert m["rapport_20mm"] == pytest.approx(28.0 / 40.0, abs=0.01)
    # 5 % de 120 mm = 6 mm : entre 14 (0 mm) et 22 (10 mm) → 18,8 mm, soit 47 % de 40 mm.
    assert m["rapport_5pct"] == pytest.approx(18.8 / 40.0, abs=0.01)
    assert prof.position_bosse == pytest.approx(70 / 120, abs=0.03)


def test_avant_a_droite_sur_fond_uni_donne_le_meme_profil(tmp_path):
    prof = mesurer(dessiner(tmp_path / "d.png", avant="droite"), avant="droite")
    assert prof.metriques()["h_20mm"] == pytest.approx(28.0, abs=0.3)
    assert prof.position_bosse == pytest.approx(70 / 120, abs=0.03)


def test_un_trace_seul_sur_une_grille_avec_une_legende(tmp_path):
    """Capture d'écran d'un comparateur : contour coloré, lignes de grille d'un bord à l'autre, cartouche
    de texte. Le contour est lu par sa couleur, la grille et le cartouche sont écartés."""
    chemin = dessiner(tmp_path / "g.png", fond=(20, 22, 28, 255), trace=(240, 196, 60, 255),
                      grille=True, legende=True)
    prof = mesurer(chemin, couleur=(240, 196, 60))
    assert prof.ecart_aspect < 0.03
    assert prof.metriques()["h_10mm"] == pytest.approx(22.0, abs=0.4)
    assert prof.metriques()["h_30mm"] == pytest.approx(32.0, abs=0.4)


def test_une_silhouette_pleine_traversee_par_la_grille_reste_d_un_seul_tenant(tmp_path):
    """Sans couleur de tracé, la grille est lue comme « souris » : elle est effacée, mais là où elle
    traverse la silhouette pleine, la souris est rétablie (sinon elle serait découpée en tranches et la
    plus grande tranche seule serait mesurée)."""
    chemin = dessiner(tmp_path / "pleine_grille.png", fond=(250, 250, 250, 255), grille=True)
    prof = mesurer(chemin)
    assert prof.ecart_aspect < 0.02
    assert prof.metriques()["h_10mm"] == pytest.approx(22.0, abs=0.3)
    assert prof.metriques()["h_30mm"] == pytest.approx(32.0, abs=0.3)
    assert prof.position_bosse == pytest.approx(70 / 120, abs=0.03)


def test_une_image_vide_ne_produit_aucune_mesure(tmp_path):
    vide = tmp_path / "vide.png"
    Image.new("RGB", (300, 200), (255, 255, 255)).save(vide)
    with pytest.raises(cb.EntreeInvalide, match="aucune souris détectée"):
        cb.silhouette(cb.ouvrir_image(vide))


# ---------------------------------------------------------------------------
# Étalonnage : les souris connues choisissent la mesure et les seuils
# ---------------------------------------------------------------------------
def test_l_etalonnage_separe_trois_classes_et_se_valide_seul():
    connues = [("a", "Low", 20.0), ("b", "Low", 21.0), ("c", "Low", 22.0),
               ("d", "Mid", 25.0), ("e", "Mid", 26.0), ("f", "Mid", 27.0),
               ("g", "High", 31.0), ("h", "High", 32.0)]
    e = cb.etalonner("h_10mm", connues)
    assert e.erreurs == 0
    assert e.loo_justes == 8 and e.effectif == 8
    assert e.seuil_bas == pytest.approx(23.5) and e.seuil_haut == pytest.approx(29.0)
    assert e.marge == pytest.approx(1.5)


def test_la_mesure_qui_separe_le_mieux_est_retenue():
    bonne = cb.Etalonnage("h_20mm", 1, 2, erreurs=0, loo_justes=8, effectif=8, marge=1.0)
    moins_bonne = cb.Etalonnage("rapport_5pct", 0.4, 0.5, erreurs=2, loo_justes=5, effectif=8, marge=0.02)
    assert cb.choisir([moins_bonne, bonne]) is bonne


# ---------------------------------------------------------------------------
# Campagne de bout en bout : manifeste, refus, alertes, propositions, relecture
# ---------------------------------------------------------------------------
def _dessus(h10: float) -> list[tuple[float, float]]:
    """Variante du profil : seule la hauteur à l'avant change (h à 10 mm donnée)."""
    return [(0, h10 - 6), (10, h10), (20, h10 + 5), (30, h10 + 8), (70, 40.0), (110, 30.0), (120, 12.0)]


def test_campagne_de_bout_en_bout(tmp_path):
    catalogue = []
    lignes = []
    cas = [  # identifiant, classe au catalogue, hauteur à 10 mm dessinée
        ("bas1", "Low", 18.0), ("bas2", "Low", 19.0), ("moy1", "Mid", 24.0), ("moy2", "Mid", 25.0),
        ("haut1", "High", 31.0), ("haut2", "High", 32.0),
        ("inconnue_basse", "Inconnu", 18.5), ("inconnue_haute", "Inconnu", 31.5),
        ("contredite", "High", 18.2),                       # le catalogue dit « hauts », la mesure dit « bas »
    ]
    for ident, classe, h10 in cas:
        catalogue.append({"id": ident, "brand": "Test", "model": ident, "length_mm": L_MM, "height_mm": H_MM,
                          "hump_position": "Mid", "button_height": classe})
        dessiner(tmp_path / f"{ident}.png", _dessus(h10))
        lignes.append({"id": ident, "image": f"{ident}.png", "avant": "gauche",
                       "source": f"https://www.eloshapes.com/mouse/{ident}", "date": "2026-10-15"})
    # Une vue de biais (écrasée) et une image retournée : refus pour l'une, alerte pour l'autre.
    catalogue.append({"id": "biais", "brand": "Test", "model": "biais", "length_mm": L_MM, "height_mm": H_MM,
                      "hump_position": "Mid", "button_height": "Inconnu"})
    dessiner(tmp_path / "biais.png", _dessus(24.0), etirement=0.8)
    lignes.append({"id": "biais", "image": "biais.png", "avant": "gauche", "source": "", "date": ""})
    catalogue.append({"id": "retournee", "brand": "Test", "model": "retournee", "length_mm": L_MM,
                      "height_mm": H_MM, "hump_position": "Front", "button_height": "Inconnu"})
    dessiner(tmp_path / "retournee.png", _dessus(24.0))
    lignes.append({"id": "retournee", "image": "retournee.png", "avant": "gauche", "source": "", "date": ""})

    (tmp_path / "catalogue.json").write_text(json.dumps(catalogue), encoding="utf-8")
    with (tmp_path / "manifeste.csv").open("w", encoding="utf-8", newline="") as fh:
        ecrivain = csv.DictWriter(fh, fieldnames=["id", "image", "avant", "source", "date"])
        ecrivain.writeheader()
        ecrivain.writerows(lignes)

    code = cb.main(["campagne", str(tmp_path / "manifeste.csv"), "--catalogue", str(tmp_path / "catalogue.json"),
                    "--rapport", str(tmp_path / "rapport.md"), "--json", str(tmp_path / "releve.json")])
    assert code == 0
    releve = json.loads((tmp_path / "releve.json").read_text(encoding="utf-8"))
    par_id = {r["id"]: r for r in releve["releves"]}

    assert par_id["inconnue_basse"]["classe_proposee"] == "Low"
    assert par_id["inconnue_haute"]["classe_proposee"] == "High"
    assert par_id["contredite"]["verdict"].startswith("À REVOIR")
    assert par_id["biais"]["refus"].startswith("vue refusée")
    assert par_id["biais"]["classe_proposee"] is None
    assert any("vérifier le côté avant" in a for a in par_id["retournee"]["alertes"])
    assert len(par_id["bas1"]["sha256"]) == 64
    rapport = (tmp_path / "rapport.md").read_text(encoding="utf-8")
    assert "Mesure retenue par les données" in rapport
    assert "| `inconnue_basse` |" in rapport


def test_sans_les_trois_classes_connues_rien_n_est_propose(tmp_path):
    releves = [cb.Releve("a", "a.png", "", "", "gauche", classe_catalogue="Low", metriques=dict.fromkeys(cb.METRIQUES, 1.0)),
               cb.Releve("b", "b.png", "", "", "gauche", classe_catalogue="Inconnu", metriques=dict.fromkeys(cb.METRIQUES, 2.0))]
    retenu, _ = cb.conclure(releves)
    assert retenu is None
    assert all(r.classe_proposee is None for r in releves)
    assert "étalonnage impossible" in releves[1].verdict


def test_une_souris_inconnue_du_catalogue_est_refusee_sans_mesure(tmp_path):
    releve = cb.mesurer_ligne({"id": "fantome", "image": "x.png", "avant": "gauche"}, tmp_path, {})
    assert releve.refus == "souris inconnue du catalogue : « fantome »"
    assert releve.metriques == {}


def test_la_commande_mesurer_sur_une_vraie_fiche_du_catalogue(tmp_path, capsys):
    """Échelle prise dans le VRAI catalogue (ATK ZERO : 120,1 × 38,1 mm) : rapport accepté."""
    chemin = tmp_path / "zero.png"
    img = Image.new("RGBA", (1100, 420), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon([(50, 380), (50, 330), (500, 76), (1010, 300), (1010, 380)], fill=(0, 0, 0, 255))
    img.save(chemin)
    assert cb.main(["mesurer", str(chemin), "--id", "atk_zero", "--avant", "gauche"]) == 0
    sortie = capsys.readouterr().out
    assert "ATK" in sortie and "accepté" in sortie


def test_le_manifeste_de_la_campagne_couvre_exactement_le_catalogue():
    """Le manifeste livré (``docs/campagne_boutons/manifeste.csv``) est la feuille de route de l'agent qui
    a accès à EloShapes : une ligne par souris du catalogue, ni plus ni moins, et une adresse EloShapes
    seulement quand le catalogue cite déjà la page de CETTE souris (jamais une page de comparaison)."""
    catalogue = json.loads((ROOT / "data" / "mouse_db.json").read_text(encoding="utf-8"))
    with (ROOT / "docs" / "campagne_boutons" / "manifeste.csv").open(encoding="utf-8", newline="") as fh:
        lignes = list(csv.DictReader(fh))
    assert sorted(ligne["id"] for ligne in lignes) == sorted(m["id"] for m in catalogue)
    assert {"id", "image", "avant", "source", "date"} <= set(lignes[0])
    for ligne in lignes:
        assert ligne["image"] == f"{ligne['id']}.png"
        assert "-vs.-" not in ligne["source"]
        assert ligne["source"] == "" or ligne["source"].startswith("https://www.eloshapes.com/")
