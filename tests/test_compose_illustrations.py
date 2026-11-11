"""Les deux illustrations dérivées suivent-elles le texte, sans qu'un dessin des originaux soit retouché ?

Demande du propriétaire du 2026-11-11 : « l'ordre des images n'est pas logique suivant l'écriture ».
Deux images du parcours ne suivaient pas le texte placé au-dessus d'elles :

- l'étape 1 énumère **Paume, Griffe, Bout des doigts** (texte et menu), alors que l'original
  ``T09_griffe_paume_doigts.png`` dessine Griffe, Paume, Bout des doigts ;
- l'étape « type de griffe » décrit trois façons de tenir la souris et n'en montrait qu'une.

``tools/compose_illustrations.py`` fabrique donc deux images à partir des originaux de ``ImageUse/``.
Ce fichier remplace la relecture à l'œil par des preuves :

- **l'ordre** des panneaux est celui des lignes du texte et des options du menu, lu dans les mêmes
  tables que le bot (``GRIP_OPTIONS``, ``CLAW_VARIANT_OPTIONS``) ;
- **aucun dessin n'est retouché** : chaque panneau de la nouvelle T09 est comparé au pixel près à
  celui de l'original ;
- **les images du dépôt sont bien celles que l'outil compose** — et la comparaison a des dents : un
  accent oublié sur une pastille, que l'écart moyen de l'image entière laissait passer, est refusé.

Les libellés de T16 demandent la mise en forme « Raqm » de Pillow (crénage de la police). Les tests qui
composent cette image sont sautés, avec la raison, sur une machine qui ne l'a pas ; ceux de T09 — une
recopie de pixels — tournent partout.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from PIL import Image, features

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import compose_illustrations as outil  # noqa: E402
from cogs import finder_flow as flow  # noqa: E402
from utils.models import CLAW_VARIANT_LABELS, GRIP_NAMES, Grip  # noqa: E402

ILLUSTRATIONS = ROOT / "assets" / "illustrations"
IMAGES = json.loads((ROOT / "assets" / "images.json").read_text(encoding="utf-8"))
avec_raqm = pytest.mark.skipif(
    not features.check("raqm"),
    reason="mise en forme « Raqm » de Pillow absente : les libellés de T16 ne peuvent pas être composés ici",
)


def _empreintes(dossier: Path) -> dict[str, str]:
    return {fichier.name: hashlib.sha256(fichier.read_bytes()).hexdigest()
            for fichier in sorted(dossier.iterdir()) if fichier.is_file()}


# --- L'ordre : celui du texte ------------------------------------------------------------------------

def test_l_ordre_des_panneaux_est_celui_des_lignes_du_texte_et_du_menu():
    """Le texte, le menu et l'image énumèrent les prises et les types de griffe dans le même ordre."""
    prises = [grip for grip, _, _ in flow.GRIP_OPTIONS]
    assert prises == [Grip.PALM, Grip.CLAW, Grip.FINGERTIP]
    # Étape 1 : les lignes du texte, les options du menu, puis le nom du fichier (qui décrit ses panneaux).
    etape = flow.grip_step_embed().description
    positions = [etape.index(f"**{GRIP_NAMES[grip]}**") for grip in prises]
    assert positions == sorted(positions)
    assert [option.value for option in flow.GripSelect().options] == [grip.value for grip in prises]
    assert outil.PRISES == IMAGES["step1_grip"] == "T09_paume_griffe_doigts.png"
    mots = [GRIP_NAMES[grip].lower().split()[-1] for grip in prises]          # paume, griffe, doigts
    assert [outil.PRISES.index(mot) for mot in mots] == sorted(outil.PRISES.index(mot) for mot in mots)
    # L'original, lui, garde son nom et sa place : il n'est plus publié, il n'est pas supprimé.
    assert (outil.ORIGINAUX / outil.ORIGINAL_PRISES).is_file()
    assert not (ILLUSTRATIONS / outil.ORIGINAL_PRISES).exists()

    # Étape « type de griffe » : mêmes libellés, mêmes photos, même ordre que le texte et le menu.
    types = [variant for variant, _, _ in flow.CLAW_VARIANT_OPTIONS]
    assert [libelle for _, libelle in outil.PHOTOS_DE_GRIFFE] == [CLAW_VARIANT_LABELS[v] for v in types]
    assert [nom for nom, _ in outil.PHOTOS_DE_GRIFFE] == [IMAGES[flow.CLAW_VARIANT_IMAGES[v]] for v in types]
    assert [option.value for option in flow.ClawVariantSelect().options] == [v.value for v in types]
    etape = flow.claw_variant_step_embed().description
    positions = [etape.index(f"**{CLAW_VARIANT_LABELS[v]}**") for v in types]
    assert positions == sorted(positions)
    assert outil.GRIFFES == IMAGES["step2_claw_variant"] == "T16_griffe_relachee_agressive_pince.png"


# --- T09 : une recopie, au pixel près ----------------------------------------------------------------

def test_les_prises_sont_recopiees_de_l_original_sans_un_pixel_de_dessin_retouche():
    """Paume | Griffe | Bout des doigts : chaque panneau est celui de l'original, à sa nouvelle place."""
    original = Image.open(outil.ORIGINAUX / outil.ORIGINAL_PRISES).convert("RGB")
    haut = outil.HAUTEUR
    (filet_1, apres_1), filet_2 = outil.FILET_1, outil.FILET_2[0]
    largeur_paume = filet_2 - apres_1                      # le panneau « Paume » mesure 782 px
    largeur_filet = len(outil.TEINTES_DU_FILET)
    for image in (outil.composer_prises(outil.ORIGINAUX / outil.ORIGINAL_PRISES),
                  Image.open(ILLUSTRATIONS / outil.PRISES).convert("RGB")):
        assert image.size == original.size == (outil.LARGEUR, outil.HAUTEUR)
        assert not outil.identiques(image, original)       # l'ordre a bien changé
        # « Paume » : deuxième panneau de l'original, premier désormais.
        assert outil.identiques(image.crop((0, 0, largeur_paume, haut)),
                                original.crop((apres_1, 0, filet_2, haut)))
        # « Griffe » : premier panneau de l'original, deuxième désormais.
        debut_griffe = largeur_paume + largeur_filet
        assert debut_griffe + filet_1 == filet_2           # les deux panneaux tiennent dans la même place
        assert outil.identiques(image.crop((debut_griffe, 0, filet_2, haut)),
                                original.crop((0, 0, filet_1, haut)))
        # Second filet et « Bout des doigts » : inchangés, au même endroit.
        assert outil.identiques(image.crop((filet_2, 0, outil.LARGEUR, haut)),
                                original.crop((filet_2, 0, outil.LARGEUR, haut)))
        # Le filet entre « Paume » et « Griffe » est retracé uni, aux teintes du filet d'origine.
        for decalage, teinte in enumerate(outil.TEINTES_DU_FILET):
            colonne = image.crop((largeur_paume + decalage, 0, largeur_paume + decalage + 1, haut))
            assert colonne.getcolors() == [(haut, teinte)]
            d_origine = original.crop((filet_1 + decalage, 0, filet_1 + decalage + 1, haut))
            assert max(d_origine.getcolors())[1] == teinte  # la teinte dominante de l'original


def test_un_original_aux_mauvaises_dimensions_est_refuse(tmp_path, capsys):
    """Les cotes sont celles de l'original livré : une autre image ne doit pas être découpée au hasard."""
    for nom, _ in outil.PHOTOS_DE_GRIFFE:
        (tmp_path / nom).write_bytes((outil.ORIGINAUX / nom).read_bytes())
    Image.new("RGB", (1200, 450), outil.ENCRE).save(tmp_path / outil.ORIGINAL_PRISES)
    sortie = tmp_path / "sortie"
    sortie.mkdir()
    with pytest.raises(SystemExit) as fin:
        outil.main(["--originaux", str(tmp_path), "--sortie", str(sortie)])
    assert fin.value.code == 2
    erreur = capsys.readouterr().err
    assert "composition impossible" in erreur and "1200 × 450 px au lieu de 2352 × 882" in erreur
    assert "Traceback" not in erreur
    assert list(sortie.iterdir()) == []                    # rien d'écrit à moitié


# --- T16 : les trois griffes, dans le style de T09 ---------------------------------------------------

@avec_raqm
def test_le_triptyque_des_griffes_reprend_les_cotes_de_t09():
    image = outil.composer_griffes(outil.ORIGINAUX, outil.POLICE)
    assert image.size == (outil.LARGEUR, outil.HAUTEUR) == (2352, 882)
    haut = outil.HAUTEUR
    for debut, _fin in (outil.FILET_1, outil.FILET_2):     # les deux filets, aux colonnes de T09
        for decalage, teinte in enumerate(outil.TEINTES_DU_FILET):
            colonne = image.crop((debut + decalage, 0, debut + decalage + 1, haut))
            assert colonne.getcolors() == [(haut, teinte)]
    pixels = image.load()
    for gauche, droite in outil.PANNEAUX:
        # La pastille : bordeaux de la charte, 99 px de haut (685 à 783), centrée dans son panneau.
        colonnes = [x for x in range(gauche, droite) if pixels[x, outil.PASTILLE_HAUT + 40] == outil.BORDEAUX]
        rangs = [y for y in range(600, haut) if pixels[colonnes[0] + 30, y] == outil.BORDEAUX]
        assert (min(rangs), max(rangs)) == (outil.PASTILLE_HAUT, outil.PASTILLE_BAS)
        assert abs((min(colonnes) + max(colonnes)) / 2 - (gauche + droite - 1) / 2) <= 1
        # Le libellé est écrit en crème sur la pastille.
        bande = image.crop((min(colonnes), outil.PASTILLE_HAUT, max(colonnes) + 1, outil.PASTILLE_BAS + 1))
        assert outil.CREME in [couleur for _, couleur in bande.getcolors(maxcolors=100_000)]
        # Au-dessus : une photo (du clair et du sombre), et non un aplat.
        mini, maxi = image.crop((gauche, 0, droite, 600)).convert("L").getextrema()
        assert mini < 20 and maxi > 200
        # Tout en bas : le fond des illustrations, sans bord de photo.
        assert pixels[gauche + 10, haut - 1] == outil.ENCRE


@avec_raqm
def test_les_deux_images_du_depot_sont_celles_que_l_outil_compose(capsys):
    """``--verifier`` sur le dépôt : T09 identique au pixel près, T16 conforme carré par carré."""
    avant = _empreintes(ILLUSTRATIONS)
    assert outil.main(["--verifier"]) == 0
    sortie = capsys.readouterr().out
    assert f"{outil.PRISES} : conforme (identique au pixel près)" in sortie
    assert f"{outil.GRIFFES} : conforme" in sortie
    assert _empreintes(ILLUSTRATIONS) == avant             # la vérification n'écrit rien


@avec_raqm
def test_la_comparaison_par_carre_voit_un_accent_oublie_que_la_moyenne_laissait_passer(monkeypatch):
    """La première version de ``--verifier`` comparait l'écart moyen de l'image entière (toléré : 2).

    Mesuré le 2026-11-11 : un libellé entièrement faux n'y pesait que 0,7 et un accent oublié 0,01 —
    les deux passaient. Carré par carré, le même accent dépasse 20 pour une tolérance de 4.
    """
    reference = outil.composer_griffes(outil.ORIGINAUX, outil.POLICE)
    (photo_1, _), deuxieme, troisieme = outil.PHOTOS_DE_GRIFFE
    for faux_libelle in ("Griffe relachée", "Griffe agressive"):
        monkeypatch.setattr(outil, "PHOTOS_DE_GRIFFE", ((photo_1, faux_libelle), deuxieme, troisieme))
        fausse = outil.composer_griffes(outil.ORIGINAUX, outil.POLICE)
        assert outil.ecart_moyen(reference, fausse) < 2.0, faux_libelle           # l'ancien contrôle : muet
        assert outil.ecart_maximal(reference, fausse) > 5 * outil.ECART_MOYEN_TOLERE, faux_libelle
    # À l'inverse, un bruit de rendu uniforme (trois niveaux sur 255, invisible) reste toléré.
    assert outil.ecart_maximal(reference, reference.point(lambda v: min(255, v + 3))) <= outil.ECART_MOYEN_TOLERE
    assert outil.ecart_maximal(reference, reference) == 0.0
    assert outil.ecart_maximal(reference, reference.crop((0, 0, 100, 100))) == 255.0   # tailles différentes


@avec_raqm
def test_verifier_refuse_une_image_qui_ne_suit_plus_l_ordre_ou_qui_manque(tmp_path, capsys):
    for nom in (outil.PRISES, outil.GRIFFES):
        (tmp_path / nom).write_bytes((ILLUSTRATIONS / nom).read_bytes())
    assert outil.main(["--sortie", str(tmp_path), "--verifier"]) == 0
    capsys.readouterr()

    # L'original (Griffe, Paume, Bout des doigts) glissé sous le nouveau nom : l'ordre n'est plus celui du texte.
    (tmp_path / outil.PRISES).write_bytes((outil.ORIGINAUX / outil.ORIGINAL_PRISES).read_bytes())
    assert outil.main(["--sortie", str(tmp_path), "--verifier"]) == 1
    sortie = capsys.readouterr().out
    assert f"{outil.PRISES} : DIFFÉRENTE" in sortie
    assert f"{outil.GRIFFES} : conforme" in sortie

    # Une image absente, une image illisible : dites, et jamais comptées conformes.
    (tmp_path / outil.PRISES).unlink()
    (tmp_path / outil.GRIFFES).write_bytes(b"pas une image")
    avant = _empreintes(tmp_path)
    assert outil.main(["--sortie", str(tmp_path), "--verifier"]) == 1
    sortie = capsys.readouterr().out
    assert f"{outil.PRISES} : ABSENTE" in sortie
    assert f"{outil.GRIFFES} : DIFFÉRENTE (illisible" in sortie
    assert _empreintes(tmp_path) == avant                  # la vérification n'a rien écrit ni réparé


@avec_raqm
def test_l_outil_ecrit_les_deux_images_sans_toucher_aux_originaux(tmp_path, capsys):
    originaux_avant = _empreintes(outil.ORIGINAUX)
    assert outil.main(["--sortie", str(tmp_path)]) == 0
    assert sorted(fichier.name for fichier in tmp_path.iterdir()) == sorted([outil.PRISES, outil.GRIFFES])
    assert _empreintes(outil.ORIGINAUX) == originaux_avant
    capsys.readouterr()
    assert outil.main(["--sortie", str(tmp_path), "--verifier"]) == 0   # ce qu'il écrit, il le reconnaît
    # Et ce qu'il écrit est ce que le dépôt publie.
    for nom in (outil.PRISES, outil.GRIFFES):
        with Image.open(tmp_path / nom) as ecrite, Image.open(ILLUSTRATIONS / nom) as publiee:
            assert outil.ecart_maximal(ecrite, publiee) <= outil.ECART_MOYEN_TOLERE, nom


def test_sans_raqm_l_outil_refuse_de_composer_des_libelles_sans_crenage(tmp_path, monkeypatch, capsys):
    """Sans « Raqm », Pillow écrit les libellés sans crénage : 12 px plus larges que ceux de la charte.

    L'outil le dit en une phrase et n'écrit rien, plutôt que de remplacer l'image par une autre.
    """
    monkeypatch.setattr(outil.features, "check", lambda nom: False)
    with pytest.raises(SystemExit) as fin:
        outil.main(["--sortie", str(tmp_path)])
    assert fin.value.code == 2
    erreur = capsys.readouterr().err
    assert "composition impossible" in erreur and "Raqm" in erreur
    assert "Traceback" not in erreur
    assert list(tmp_path.iterdir()) == []


def test_la_police_des_pastilles_est_fournie_avec_sa_licence():
    """Syne ExtraBold est sous SIL Open Font License : elle se redistribue avec le texte de sa licence."""
    assert outil.POLICE.is_file() and outil.POLICE.name == "Syne-ExtraBold.ttf"
    licence = (outil.POLICE.parent / "LICENCE_OFL_Syne.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in licence.upper()
    assert "Syne" in licence
