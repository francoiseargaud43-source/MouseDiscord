"""Tests de l'outil de mesure de la hauteur d'appui des boutons (`tools/measure_button_height.py`).

Les images de test sont **synthétiques** : on connaît la géométrie dessinée, donc on peut vérifier
que la mesure est exacte. Deux propriétés sont verrouillées : la mesure d'une vue orthographique
est juste, et une vue en perspective est **refusée** (aucune valeur produite).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from measure_button_height import CLICK_FRACTION, PERSPECTIVE_TOLERANCE, measure  # noqa: E402

LENGTH_MM, HEIGHT_MM = 118.2, 38.8          # ATK F1 V3 Ultimate (fiche officielle)
WIDTH_PX, HEIGHT_PX = 1182, 388             # 10 px/mm, vue orthographique parfaite


def _profil(click_height_ratio: float, path: Path) -> Path:
    """Le ratio demandé est la hauteur du dessus AU POINT DE MESURE (bord d'attaque des boutons)."""
    """Dessine une souris de profil : avant à gauche, bosse au milieu, hauteur d'appui contrôlée."""
    img = Image.new("RGB", (WIDTH_PX + 200, HEIGHT_PX + 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    top = 100
    base = top + HEIGHT_PX
    peak_x = 100 + int(WIDTH_PX * 0.55)
    click_x = 100 + int(WIDTH_PX * CLICK_FRACTION)
    click_top = base - int(HEIGHT_PX * click_height_ratio)
    points = [(100, base), (100, click_top), (click_x, click_top), (peak_x, top),
              (100 + WIDTH_PX, top + int(HEIGHT_PX * 0.45)), (100 + WIDTH_PX, base)]
    draw.polygon(points, fill=(20, 20, 20))
    img.save(path)
    return path


@pytest.fixture()
def orthographique(tmp_path):
    return _profil(0.40, tmp_path / "profil.png")


def test_mesure_exacte_sur_une_vue_orthographique(orthographique):
    result = measure(orthographique, LENGTH_MM, HEIGHT_MM, front="left")
    assert result.aspect_error < 0.03
    assert result.klass == "Low"
    assert result.click_ratio == pytest.approx(0.40, abs=0.03)
    assert result.click_height_mm == pytest.approx(0.40 * HEIGHT_MM, abs=1.5)


def test_low_et_high_sont_reconnus_et_mid_reste_non_tranche(tmp_path):
    """« Low » et « High » sont étalonnés sur deux souris réelles ; « Mid » reste NON TRANCHÉ.

    Tant qu'aucune souris de référence « boutons moyens » n'a été mesurée, l'outil ne doit jamais
    écrire « Mid » : mieux vaut une classe absente qu'une classe inventée.
    """
    classes = {}
    for nom, ratio in (("bas", 0.40), ("haut", 0.80)):
        result = measure(_profil(ratio, tmp_path / f"{nom}.png"), LENGTH_MM, HEIGHT_MM, front="left")
        classes[nom] = result.klass
        assert result.click_ratio == pytest.approx(ratio, abs=0.02)
    assert classes == {"bas": "Low", "haut": "High"}
    intermediaire = measure(_profil(0.50, tmp_path / "intermediaire.png"), LENGTH_MM, HEIGHT_MM, front="left")
    assert intermediaire.klass is None
    assert "NON TRANCHÉE" in intermediaire.verdict


def test_une_vue_en_perspective_est_refusee_sans_valeur(tmp_path):
    """Vue « plongeante » : silhouette étirée en longueur, rapport hors tolérance → mesure refusée."""
    # Silhouette écrasée (60 % de la hauteur attendue) : le rapport longueur/hauteur s'éloigne.
    img = Image.new("RGB", (WIDTH_PX + 200, HEIGHT_PX + 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    base = 100 + HEIGHT_PX
    thin = int(HEIGHT_PX * 0.6)
    draw.rectangle([100, base - thin, 100 + WIDTH_PX, base], fill=(20, 20, 20))
    path = tmp_path / "perspective.png"
    img.save(path)
    result = measure(path, LENGTH_MM, HEIGHT_MM, front="left")
    assert result.aspect_error > PERSPECTIVE_TOLERANCE
    assert result.klass is None
    assert "refusée" in result.verdict


def test_image_detouree_sur_fond_transparent(tmp_path):
    """Les rendus produits sont souvent détourés (PNG transparent) : la silhouette doit être lue.

    Sans cette lecture, la transparence devient du noir et la mesure est fausse (bug corrigé le
    2026-10-12 sur les rendus Pulsar).
    """
    img = Image.new("RGBA", (WIDTH_PX + 200, HEIGHT_PX + 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    top, base = 100, 100 + HEIGHT_PX
    click_top = base - int(HEIGHT_PX * 0.40)
    draw.polygon([(100, base), (100, click_top), (100 + int(WIDTH_PX * 0.4), click_top),
                  (100 + int(WIDTH_PX * 0.55), top), (100 + WIDTH_PX, top + int(HEIGHT_PX * 0.45)),
                  (100 + WIDTH_PX, base)], fill=(20, 20, 20, 255))
    path = tmp_path / "detouree.png"
    img.save(path)
    result = measure(path, LENGTH_MM, HEIGHT_MM, front="left")
    assert result.aspect_error < 0.03
    assert result.klass == "Low"
