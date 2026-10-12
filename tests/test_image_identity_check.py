"""Contrôle d'identité par silhouette (tools/image_identity_check.py).

L'outil sert à rattacher une image **sans nom imprimé** à une image **nommée** du même modèle, pour
pouvoir mesurer une deuxième vue (règle « deux images distinctes ») sans jamais se fier au nom de
fichier. Les tests vérifient : la lecture du profil, la mise dans le même sens (paramètre `front`), les
deux verdicts bornés, et le fait que l'outil refuse de trancher entre les deux populations étalonnées.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("iic", RACINE / "tools" / "image_identity_check.py")
iic = importlib.util.module_from_spec(spec)
sys.modules["iic"] = iic
spec.loader.exec_module(iic)

LARGEUR, HAUTEUR = 1200, 400


def _profil_png(chemin: Path, points_cles: list[tuple[float, float]], retournee: bool = False) -> Path:
    """Silhouette fermée dont le dessus suit les points clés (x en fraction, hauteur en fraction)."""
    img = Image.new("RGB", (LARGEUR + 200, HAUTEUR + 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    base = 100 + HAUTEUR
    sommets = []
    for fraction, hauteur in points_cles:
        x = 100 + int(fraction * LARGEUR)
        if retournee:
            x = 100 + LARGEUR - int(fraction * LARGEUR)
        sommets.append((x, base - int(hauteur * HAUTEUR)))
    polygone = [(100, base), *sommets, (100 + LARGEUR, base)]
    draw.polygon(polygone, fill=(25, 25, 25))
    img.save(chemin)
    return chemin


# Profil « type souris » : bosse au milieu, nez bas à l'avant.
PROFIL = [(0.00, 0.30), (0.08, 0.36), (0.25, 0.55), (0.50, 0.95), (0.70, 0.88), (0.90, 0.55), (1.00, 0.32)]
PROFIL_AUTRE = [(0.00, 0.35), (0.10, 0.45), (0.30, 0.80), (0.45, 0.98), (0.75, 0.70), (0.95, 0.40), (1.00, 0.38)]


def test_meme_coque_avec_les_deux_vues_dans_le_bon_sens(tmp_path):
    ref = _profil_png(tmp_path / "ref.png", PROFIL)
    cand = _profil_png(tmp_path / "cand.png", PROFIL)
    resultat = iic.compare(ref, cand)                       # les deux profils identiques
    assert resultat.same_shell
    assert resultat.mean_gap < 0.01
    assert resultat.verdict.startswith("même coque probable")


def test_meme_coque_meme_image_retournee_avec_le_bon_parametre(tmp_path):
    """Une vue retournée (avant de l'autre côté) est correctement remise dans le même sens."""
    ref = _profil_png(tmp_path / "ref.png", PROFIL)
    cand = _profil_png(tmp_path / "cand.png", PROFIL, retournee=True)
    assert iic.compare(ref, cand, "left", "right").same_shell
    # Sans l'information d'orientation, la comparaison échoue : le paramètre est bien décisif.
    assert not iic.compare(ref, cand, "left", "left").same_shell


def test_coques_differentes_sont_signalees(tmp_path):
    ref = _profil_png(tmp_path / "ref.png", PROFIL)
    cand = _profil_png(tmp_path / "cand.png", PROFIL_AUTRE)
    resultat = iic.compare(ref, cand)
    assert not resultat.same_shell
    assert resultat.verdict.startswith("coques différentes")


def test_verdicts_bornees_aux_trois_niveaux():
    """Le verdict est borné : même coque / indéterminé / coques différentes, jamais entre-deux forcé.

    Les seuils sont ceux de l'étalonnage réel (même coque 0,24 % ; coques différentes 4,5-4,8 %) ; la
    fonction de décision est testée directement, ses seuils sont donc vérifiables sans synthétiser deux
    images dont l'écart moyen tomberait exactement dans la bande grise.
    """
    assert iic._verdict(0.0).startswith("même coque probable")
    assert iic._verdict(iic.SAME_SHELL_MAX_MEAN).startswith("même coque probable")     # borne incluse
    assert iic._verdict(0.02).startswith("NON TRANCHÉ")
    assert iic._verdict(iic.DIFFERENT_SHELL_MIN_MEAN).startswith("coques différentes")  # borne incluse
    assert iic._verdict(0.10).startswith("coques différentes")
    assert iic.SAME_SHELL_MAX_MEAN < 0.02 < iic.DIFFERENT_SHELL_MIN_MEAN


def test_silhouette_illisible_refusee(tmp_path):
    """Une image uniforme (aucune silhouette) doit lever une erreur explicite, pas un verdict."""
    vide = tmp_path / "vide.png"
    Image.new("RGB", (400, 200), (255, 255, 255)).save(vide)
    with pytest.raises(ValueError):
        iic.top_profile(vide)


def test_profil_normalise_est_borne_et_ordonne(tmp_path):
    """Le profil normalisé est une fraction de hauteur dans [0, 1], de longueur fixe."""
    ref = _profil_png(tmp_path / "ref.png", PROFIL)
    profil = iic.top_profile(ref)
    assert len(profil) == iic.PROFILE_POINTS
    assert all(0.0 <= h <= 1.0 for h in profil)
    assert max(profil) > 0.9        # la bosse est bien la hauteur maximale
