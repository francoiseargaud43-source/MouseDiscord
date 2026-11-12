"""Compose les deux illustrations DÉRIVÉES des originaux livrés (``ImageUse/``).

Demande du propriétaire (2026-11-11) : « l'ordre des images n'est pas logique suivant l'écriture ».
Deux images du parcours ne suivaient pas le texte placé au-dessus d'elles :

- l'étape 1 présente les prises dans l'ordre **Paume, Griffe, Bout des doigts** (texte et menu), mais
  l'original ``T09_griffe_paume_doigts.png`` les dessine dans l'ordre Griffe, Paume, Bout des doigts ;
- l'étape « type de griffe » décrit **trois** façons de tenir la souris, mais ne montrait qu'une seule
  des trois photos (``T04``).

Cet outil fabrique donc, sans jamais toucher aux originaux :

- ``T09_paume_griffe_doigts.png`` — l'original T09 dont les deux premiers panneaux sont échangés.
  **Aucun pixel des dessins n'est redessiné** : les trois panneaux, leurs pastilles et le second filet
  sont recopiés tels quels (vérifié par ``tests/test_compose_illustrations.py``). Seul le filet qui
  sépare désormais « Paume » de « Griffe » est retracé, uni, aux quatre teintes du filet d'origine :
  celui de l'original portait le bout des traits de l'avant-bras « Paume », qui se serait retrouvé
  seul au milieu du filet, à côté d'un autre dessin ;
- ``T16_griffe_relachee_agressive_pince.png`` — les photos ``T04``, ``T05`` et ``T06`` côte à côte,
  même cadrage, avec les pastilles de T09 : mêmes dimensions, même bordeaux, même police.

Les cotes ci-dessous ont été relevées sur l'original T09 (2352 × 882 px). La police des pastilles est
**Syne ExtraBold** (celle de la charte, ``docs/REPORTE_DESIGN.md``) ; elle est fournie dans
``tools/polices/`` avec sa licence (SIL Open Font License 1.1).

``--verifier`` n'écrit rien et recompose les deux images pour les comparer à celles du dépôt :

- T09 doit être **identique au pixel près** (c'est une recopie : aucune bibliothèque ne peut la faire
  varier) ;
- T16 est comparée **cellule par cellule** (carrés de ``CELLULE`` px). Une seule cellule qui s'écarte de
  plus de ``ECART_MOYEN_TOLERE`` rend l'image « DIFFÉRENTE ». Une moyenne sur l'image entière laissait
  passer un libellé de pastille faux (0,7 d'écart moyen) et un accent oublié (0,01) ; par cellule, ces
  deux défauts dépassent 20.

Les libellés de T16 sont composés avec le crénage de la police, comme ceux des originaux : il faut pour
cela la mise en forme « Raqm » de Pillow (``python -m PIL.features`` l'indique). Sans elle, l'outil
refuse de composer plutôt que d'écrire des libellés plus larges de 12 px que ceux de la charte.

Usage :
    python tools/compose_illustrations.py                 # écrit les deux images dans assets/illustrations/
    python tools/compose_illustrations.py --verifier      # n'écrit rien : compare aux images du dépôt
    python tools/compose_illustrations.py --originaux DOSSIER --sortie DOSSIER --police FICHIER.ttf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat, features

ROOT = Path(__file__).resolve().parents[1]
ORIGINAUX = ROOT / "ImageUse"
SORTIE = ROOT / "assets" / "illustrations"
POLICE = Path(__file__).resolve().parent / "polices" / "Syne-ExtraBold.ttf"

ORIGINAL_PRISES = "T09_griffe_paume_doigts.png"
PRISES = "T09_paume_griffe_doigts.png"
GRIFFES = "T16_griffe_relachee_agressive_pince.png"
# Les trois photos de griffe, dans l'ordre du texte de l'étape, avec le libellé de leur pastille
# (repris à la lettre des originaux T04, T05 et T06).
PHOTOS_DE_GRIFFE = (
    ("T04_griffe_relachee.png", "Griffe relâchée"),
    ("T05_griffe_agressive.png", "Griffe agressive"),
    ("T06_griffe_pince.png", "Griffe pince"),
)

# --- Cotes relevées sur l'original T09 -------------------------------------------------------------
LARGEUR, HAUTEUR = 2352, 882
ENCRE = (7, 11, 20)                                   # fond des illustrations (#070B14)
BORDEAUX = (138, 35, 66)                              # pastilles (#8A2342)
CREME = (246, 241, 234)                               # texte des pastilles (#F6F1EA)
FILET_1, FILET_2 = (781, 785), (1567, 1571)           # colonnes des deux filets (4 px chacun)
TEINTES_DU_FILET = ((25, 35, 53), (44, 61, 86), (44, 61, 86), (25, 35, 53))
PANNEAUX = ((0, FILET_1[0]), (FILET_1[1], FILET_2[0]), (FILET_2[1], LARGEUR))
PASTILLE_HAUT, PASTILLE_BAS = 685, 783                # 99 px de haut
PASTILLE_RAYON = 18
PASTILLE_MARGE = 45                                   # de chaque côté du texte
TAILLE_POLICE = 45
LIGNE_DE_BASE = 751

# --- Cadrage des photos T04–T06 (2400 × 1200 px) : la main et la souris, sans la pastille d'origine ---
CADRE_PHOTO = (320, 50, 1460, 950)
FONDU = 150                                           # hauteur du fondu vers le fond, sous la photo
# --verifier, image T16 : l'image est découpée en carrés de CELLULE px ; ECART_MOYEN_TOLERE est l'écart
# moyen par canal (sur 255) admis dans CHAQUE carré. Sur une même machine l'écart est nul ; la marge
# couvre le lissage des lettres et des photos d'une version de Pillow ou de FreeType à l'autre.
CELLULE = 16
ECART_MOYEN_TOLERE = 4.0


def _filet(dessin: ImageDraw.ImageDraw, debut: int) -> None:
    """Un filet vertical de T09 : quatre colonnes unies, aux teintes relevées sur l'original."""
    for decalage, teinte in enumerate(TEINTES_DU_FILET):
        dessin.line((debut + decalage, 0, debut + decalage, HAUTEUR - 1), fill=teinte)


def composer_prises(original: Path) -> Image.Image:
    """T09 dans l'ordre du texte : Paume | Griffe | Bout des doigts (panneaux recopiés tels quels)."""
    image = Image.open(original).convert("RGB")
    if image.size != (LARGEUR, HAUTEUR):
        raise ValueError(f"{original.name} : {image.size[0]} × {image.size[1]} px au lieu de "
                         f"{LARGEUR} × {HAUTEUR}")
    griffe = image.crop((0, 0, FILET_1[0], HAUTEUR))
    paume = image.crop((FILET_1[1], 0, FILET_2[0], HAUTEUR))
    reste = image.crop((FILET_2[0], 0, LARGEUR, HAUTEUR))          # second filet + « Bout des doigts »
    largeur_filet = len(TEINTES_DU_FILET)
    resultat = Image.new("RGB", (LARGEUR, HAUTEUR), ENCRE)
    resultat.paste(paume, (0, 0))
    # Filet retracé uni : celui de l'original porte le bout des traits de « Paume » (voir l'en-tête).
    _filet(ImageDraw.Draw(resultat), paume.width)
    resultat.paste(griffe, (paume.width + largeur_filet, 0))
    resultat.paste(reste, (FILET_2[0], 0))
    return resultat


def _pastille(dessin: ImageDraw.ImageDraw, police: ImageFont.FreeTypeFont, texte: str, centre: int) -> None:
    largeur = int(round(police.getlength(texte)))
    gauche = centre - largeur // 2 - PASTILLE_MARGE
    droite = centre + (largeur - largeur // 2) + PASTILLE_MARGE
    dessin.rounded_rectangle((gauche, PASTILLE_HAUT, droite, PASTILLE_BAS), radius=PASTILLE_RAYON, fill=BORDEAUX)
    dessin.text((centre - largeur // 2, LIGNE_DE_BASE), texte, font=police, fill=CREME, anchor="ls")


def composer_griffes(originaux: Path, police: Path) -> Image.Image:
    """Les trois photos de griffe côte à côte, pastilles et filets dans le style de T09."""
    if not features.check("raqm"):
        raise ValueError("la mise en forme « Raqm » de Pillow est absente : sans elle, les libellés "
                         "perdent le crénage de la police et ne sont plus ceux de la charte")
    fonte = ImageFont.truetype(str(police), TAILLE_POLICE, layout_engine=ImageFont.Layout.RAQM)
    resultat = Image.new("RGB", (LARGEUR, HAUTEUR), ENCRE)
    dessin = ImageDraw.Draw(resultat)
    for (nom, libelle), (gauche, droite) in zip(PHOTOS_DE_GRIFFE, PANNEAUX):
        largeur = droite - gauche
        photo = Image.open(originaux / nom).convert("RGB").crop(CADRE_PHOTO)
        hauteur = round(photo.height * largeur / photo.width)
        photo = photo.resize((largeur, hauteur), Image.LANCZOS)
        resultat.paste(photo, (gauche, 0))
        # Sous la photo : son dernier rang (le bureau, sombre et uni) est prolongé puis fondu vers le
        # fond, pour qu'aucun bord franc ne passe derrière la pastille.
        rang = photo.crop((0, hauteur - 8, largeur, hauteur)).resize((largeur, 1), Image.BOX)
        rang = rang.resize((largeur, FONDU), Image.NEAREST).filter(ImageFilter.GaussianBlur(12))
        fond = Image.new("RGB", (largeur, FONDU), ENCRE)
        masque = Image.linear_gradient("L").resize((largeur, FONDU)).point(lambda v: 255 - v)
        resultat.paste(Image.composite(rang, fond, masque), (gauche, hauteur))
        # La jonction photo / prolongement est adoucie sur quelques rangs : aucun trait horizontal.
        bande = (gauche, hauteur - 9, droite, hauteur + 9)
        resultat.paste(resultat.crop(bande).filter(ImageFilter.GaussianBlur(4)), bande[:2])
        _pastille(dessin, fonte, libelle, gauche + largeur // 2)
    for debut, _fin in (FILET_1, FILET_2):
        _filet(dessin, debut)
    return resultat


def ecart_moyen(premiere: Image.Image, seconde: Image.Image) -> float:
    """Écart moyen par canal entre deux images (0 = identiques au pixel près, 255 = opposées)."""
    if premiere.size != seconde.size:
        return 255.0
    difference = ImageChops.difference(premiere.convert("RGB"), seconde.convert("RGB"))
    return sum(ImageStat.Stat(difference).mean) / 3


def ecart_maximal(premiere: Image.Image, seconde: Image.Image) -> float:
    """Le plus grand écart moyen relevé sur un carré de CELLULE px (0 = identiques ; 255 = tailles différentes).

    Une moyenne sur l'image entière dilue un défaut local : un accent oublié sur une pastille n'y pèse
    que 0,01. Carré par carré, le même accent dépasse 20.
    """
    if premiere.size != seconde.size:
        return 255.0
    difference = ImageChops.difference(premiere.convert("RGB"), seconde.convert("RGB"))
    # reduce() rend la moyenne de chaque carré, canal par canal (les carrés du bord sont plus petits) ;
    # les octets sortent dans l'ordre R, V, B de chaque carré.
    octets = difference.reduce(CELLULE).tobytes()
    return max(sum(octets[rang:rang + 3]) for rang in range(0, len(octets), 3)) / 3


def identiques(premiere: Image.Image, seconde: Image.Image) -> bool:
    """Vrai si les deux images ont la même taille et pas un pixel de différence."""
    if premiere.size != seconde.size:
        return False
    return ImageChops.difference(premiere.convert("RGB"), seconde.convert("RGB")).getbbox() is None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose les illustrations dérivées des originaux : T09 dans l'ordre du texte, "
                    "et le triptyque des trois griffes (T16).")
    parser.add_argument("--originaux", default=str(ORIGINAUX), help="dossier des originaux (défaut : ImageUse/)")
    parser.add_argument("--sortie", default=str(SORTIE), help="dossier d'écriture (défaut : assets/illustrations/)")
    parser.add_argument("--police", default=str(POLICE), help="police des pastilles (défaut : Syne ExtraBold fournie)")
    parser.add_argument("--verifier", action="store_true",
                        help="n'écrit rien : compare les images composées à celles du dossier de sortie")
    args = parser.parse_args(argv)

    originaux, sortie, police = Path(args.originaux), Path(args.sortie), Path(args.police)
    if not originaux.is_dir():
        parser.error(f"dossier introuvable (originaux) : {originaux}")
    if not sortie.is_dir():
        parser.error(f"dossier introuvable (sortie) : {sortie}")
    if not police.is_file():
        parser.error(f"police introuvable : {police}")
    manquants = [nom for nom in (ORIGINAL_PRISES, *(nom for nom, _ in PHOTOS_DE_GRIFFE))
                 if not (originaux / nom).is_file()]
    if manquants:
        parser.error(f"original introuvable dans {originaux} : {', '.join(manquants)}")
    try:
        images = {PRISES: composer_prises(originaux / ORIGINAL_PRISES),
                  GRIFFES: composer_griffes(originaux, police)}
    except (OSError, ValueError) as exc:
        parser.error(f"composition impossible : {exc}")

    if not args.verifier:
        for nom, image in images.items():
            image.save(sortie / nom, optimize=True)
            print(f"Écrit : {sortie / nom} ({image.width} × {image.height} px)")
        return 0
    conformes = True
    for nom, image in images.items():
        if not (sortie / nom).is_file():
            print(f"{nom} : ABSENTE de {sortie}")
            conformes = False
            continue
        try:
            with Image.open(sortie / nom) as publiee:
                publiee.load()
                if nom == PRISES:
                    # Une recopie de pixels : la moindre différence est un défaut, pas une tolérance.
                    conforme = identiques(image, publiee)
                    detail = "identique au pixel près" if conforme else "au moins un pixel diffère de la recopie"
                else:
                    ecart = ecart_maximal(image, publiee)
                    conforme = ecart <= ECART_MOYEN_TOLERE
                    detail = (f"écart maximal {ecart:.2f} sur 255 par carré de {CELLULE} px, "
                              f"toléré {ECART_MOYEN_TOLERE:g}")
        except OSError as exc:
            conforme, detail = False, f"illisible : {exc}"
        conformes = conformes and conforme
        print(f"{nom} : {'conforme' if conforme else 'DIFFÉRENTE'} ({detail})")
    return 0 if conformes else 1


if __name__ == "__main__":
    sys.exit(main())
