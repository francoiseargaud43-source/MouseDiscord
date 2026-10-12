"""Mesure la hauteur d'appui des boutons sur une vue de profil officielle.

Méthode (reproductible, sans invention de valeur) :

1. l'image est nettoyée : le fond (couleur des bords) est retiré, la souris reste ;
2. la **boîte englobante** de la souris donne sa longueur et sa hauteur en pixels ;
3. **contrôle qualité** : le rapport longueur/hauteur mesuré est comparé aux cotes officielles
   (fiche du fabricant). Au-delà de la tolérance, la vue est considérée en perspective et la
   mesure est **refusée** (aucune valeur n'est produite) ;
4. l'échelle est déduite de la hauteur officielle, puis on relève la hauteur du dessus de la coque
   à l'aplomb du point d'appui des doigts (à ``CLICK_FRACTION`` de la longueur depuis l'avant) ;
5. la classe est déduite du rapport « hauteur d'appui / hauteur maximale », dont les seuils sont
   calibrés sur les souris dont la hauteur de boutons est déjà connue (référentiel : outils du
   propriétaire). Aucune valeur absolue n'est inventée : seule une **classe** est produite, avec
   l'incertitude affichée.

Les trois références d'étalonnage (bas, moyens, hauts) sont vérifiées le 2026-10-12 : la classe
« moyens » a été obtenue en mesurant l'**ATK A9 Plus** (classe « Mid » du cahier des charges) sur
**deux rendus officiels distincts**, tous deux à 47,3 % — la même méthode qui avait donné les deux
autres références. La frontière entre deux classes est posée à mi-chemin des deux références, et une
mesure à moins d'un point d'une frontière reste **non tranchée**.

Ce que l'outil ne fait pas : il ne décide pas la publication d'une valeur au catalogue. Celle-ci
exige en plus que l'identité du modèle soit prouvée sur l'image et que **deux vues distinctes**
donnent la même classe (règle écrite dans `docs/audit/MESURE_BOUTONS_2026-10-12.md`, §15.3).

L'image doit d'**abord** être identifiée : le nom de fichier ne prouve rien (le même fichier circule
souvent sous plusieurs noms de modèles — voir ``tools/image_corpus_check.py``). L'identité se vérifie
à l'œil sur l'image (nom imprimé sur la coque, logo) ; une image non identifiée ne produit aucune
valeur publiable, quelle que soit la qualité de la mesure.

Usage :
    python tools/measure_button_height.py IMAGE --length-mm 122.5 --height-mm 42.4 [--front left|right]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

# Les mesures réelles du 2026-10-12 (F1 V2 « boutons bas » contre Z1 V2 « boutons hauts », deux
# valeurs connues) montrent que le pouvoir discriminant est MAXIMAL près de l'avant et s'annule au
# tiers de la souris : à 5 % de la longueur, l'écart entre les deux souris est de 11,8 points de
# hauteur ; à 22 %, il ne reste que 3,1 points ; à 40 %, l'ordre s'inverse. Le relevé se fait donc
# au bord d'attaque des boutons, là où le doigt se pose réellement.
CLICK_FRACTION = 0.05
# Tolérance du contrôle qualité sur le rapport longueur/hauteur (vue acceptée si l'écart est faible).
PERSPECTIVE_TOLERANCE = 0.06
# Références mesurées le 2026-10-12 sur des souris dont la hauteur de boutons est CONNUE (valeurs du
# propriétaire). Chaque référence est un rapport « hauteur d'appui / hauteur totale » relevé au bord
# d'attaque des boutons, sur des rendus officiels dont l'identité a été vérifiée :
#   - « bas »   : ATK F1 V2 (43,3 %) — valeur d'étalonnage d'origine, recoupée par l'ATK ZERO
#                 (deux rendus : 43,3 % et 43,7 %) ;
#   - « moyens » : ATK A9 Plus (47,3 %) — deux rendus officiels distincts, tous deux à 47,3 % ;
#   - « hauts » : ATK Z1 V2 (55,1 %), recoupé par le rendu « Z1 ULTIMATE » (55,0 %).
CALIBRATION_REFERENCES = (
    ("ATK F1 V2 (boutons bas)", "Low", 0.433),
    ("ATK A9 Plus (boutons moyens)", "Mid", 0.473),
    ("ATK Z1 V2 (boutons hauts)", "High", 0.551),
)
# Marge d'incertitude : une mesure à moins de cette distance d'une frontière entre deux classes reste
# NON TRANCHÉE. Un point, c'est plus du double du plus grand écart observé entre deux rendus d'une
# même souris de classe connue (0,7 point : l'ATK ZERO mesurée 43,0 %, 43,3 % et 43,7 %).
CALIBRATION_MARGIN = 0.01


@dataclass(frozen=True)
class Measure:
    length_px: float
    height_px: float
    aspect_measured: float
    aspect_reference: float
    aspect_error: float
    scale_mm_per_px: float
    click_height_mm: float
    click_ratio: float
    verdict: str
    klass: str | None


def _background_colour(img: Image.Image) -> tuple[int, int, int]:
    """Couleur de fond = médiane des quatre coins (les vues officielles sont sur fond uni)."""
    w, h = img.size
    corners = []
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)):
        corners.append(img.getpixel((x, y))[:3])
    corners.sort()
    return corners[len(corners) // 2]


def _mask_from_alpha(img: Image.Image, alpha_min: int = 40) -> tuple[dict[int, int], dict[int, int]] | None:
    """Silhouette d'une image détourée (PNG transparent) : le fond est transparent, pas coloré.

    C'est le cas des rendus produits détourés (Pulsar, ATK Store) : sans cette lecture, la
    transparence devient du noir et la silhouette est fausse (erreur corrigée le 2026-10-12).
    """
    if img.mode not in ("RGBA", "LA"):
        return None
    alpha = img.convert("RGBA").getchannel("A")
    w, h = alpha.size
    top: dict[int, int] = {}
    bottom: dict[int, int] = {}
    for x in range(w):
        column = [y for y in range(h) if alpha.getpixel((x, y)) > alpha_min]
        if column:
            top[x] = column[0]
            bottom[x] = column[-1]
    return (top, bottom) if top else None


def _silhouette(img: Image.Image, tolerance: int = 28):
    """Boîte englobante et profil supérieur de la souris.

    ``top[x]`` = première rangée non-fond de la colonne (le dessus de la coque) ;
    ``bottom[x]`` = dernière rangée non-fond (la base). La hauteur de la souris se mesure entre
    le point le plus haut **du dessus** et le point le plus bas **de la base** — et non entre deux
    points du dessus, ce qui sous-estimerait la hauteur (erreur corrigée le 2026-10-12).
    """
    from_alpha = _mask_from_alpha(img)
    if from_alpha is not None:
        top, bottom = from_alpha
    else:
        bg = _background_colour(img)
        w, h = img.size
        pixels = img.load()
        top: dict[int, int] = {}
        bottom: dict[int, int] = {}
        for x in range(w):
            column = [y for y in range(h)
                      if abs(pixels[x, y][0] - bg[0]) + abs(pixels[x, y][1] - bg[1])
                      + abs(pixels[x, y][2] - bg[2]) > tolerance]
            if column:
                top[x] = column[0]
                bottom[x] = column[-1]
    if not top:
        raise ValueError("aucune souris détectée : le fond et la souris se confondent")
    xs = sorted(top)
    x_min, x_max = xs[0], xs[-1]
    # Nettoyage : on ignore les colonnes isolées (bruit, ombre portée) aux extrémités.
    span = x_max - x_min + 1
    edge = max(1, int(span * 0.01))
    x_min, x_max = xs[edge], xs[-edge - 1]
    top = {x: y for x, y in top.items() if x_min <= x <= x_max}
    bottom = {x: y for x, y in bottom.items() if x_min <= x <= x_max}
    y_min = min(top.values())
    y_max = max(bottom.values())
    height_px = y_max - y_min + 1
    return x_min, x_max, y_min, y_max, height_px, top


def measure(path: str | Path, length_mm: float, height_mm: float, front: str = "left") -> Measure:
    img = Image.open(path)
    if img.mode not in ("RGBA", "LA"):
        img = img.convert("RGB")
    x_min, x_max, y_min, y_max, height_px, profile = _silhouette(img)
    length_px = x_max - x_min + 1

    aspect_measured = length_px / height_px
    aspect_reference = length_mm / height_mm
    aspect_error = abs(aspect_measured - aspect_reference) / aspect_reference

    scale = height_mm / height_px
    # Point d'appui des doigts : à CLICK_FRACTION de la longueur depuis l'avant.
    click_x = (x_min + int(length_px * CLICK_FRACTION)) if front == "left" else (x_max - int(length_px * CLICK_FRACTION))
    row = profile.get(click_x)
    if row is None:
        raise ValueError("profil incomplet au point de mesure")
    click_height_mm = (y_max - row) * scale
    ratio = click_height_mm / height_mm

    if aspect_error > PERSPECTIVE_TOLERANCE:
        return Measure(length_px, height_px, aspect_measured, aspect_reference, aspect_error,
                       scale, click_height_mm, ratio,
                       verdict="vue refusée : rapport longueur/hauteur trop éloigné des cotes officielles "
                               "(vue en perspective)", klass=None)

    klass, verdict = _classify(ratio)
    return Measure(length_px, height_px, aspect_measured, aspect_reference, aspect_error,
                   scale, click_height_mm, ratio, verdict=verdict, klass=klass)


def _boundaries() -> list[tuple[tuple[str, str, float], tuple[str, str, float], float]]:
    """Les frontières entre classes : à mi-chemin entre deux références voisines (triées)."""
    refs = sorted(CALIBRATION_REFERENCES, key=lambda r: r[2])
    return [(gauche, droite, (gauche[2] + droite[2]) / 2) for gauche, droite in zip(refs, refs[1:])]


def _classify(ratio: float) -> tuple[str | None, str]:
    """Classe la mesure par la référence la plus proche, ou refuse de trancher.

    Les trois hauteurs de boutons sont ordonnées (bas < moyens < hauts). La frontière entre deux
    classes est posée à mi-chemin de leurs deux références étalonnées ; une mesure à moins de
    ``CALIBRATION_MARGIN`` d'une frontière reste **non tranchée**, car l'incertitude de la mesure ne
    permet pas de la placer d'un côté plutôt que de l'autre. Aucune classe n'est inventée.
    """
    for gauche, droite, frontiere in _boundaries():
        if abs(ratio - frontiere) <= CALIBRATION_MARGIN:
            return None, (f"vue acceptée, mais classe NON TRANCHÉE : la mesure ({ratio * 100:.1f} %) "
                          f"est à {abs(ratio - frontiere) * 100:.1f} point de la frontière "
                          f"« {gauche[1]}/{droite[1]} » ({frontiere * 100:.1f} %), en deçà de la marge "
                          f"de {CALIBRATION_MARGIN * 100:.0f} point")
    ecart, reference = min(((abs(ratio - r[2]), r) for r in CALIBRATION_REFERENCES), key=lambda t: t[0])
    return reference[1], (f"vue acceptée : mesure à {ecart * 100:.1f} point de la référence "
                          f"« {reference[0]} » ({reference[2] * 100:.1f} %) → classe estimée "
                          f"« {reference[1]} »")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hauteur d'appui des boutons sur une vue de profil.")
    parser.add_argument("image")
    parser.add_argument("--length-mm", type=float, required=True)
    parser.add_argument("--height-mm", type=float, required=True)
    parser.add_argument("--front", choices=("left", "right"), default="left",
                        help="côté où se trouve l'avant de la souris sur l'image")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = measure(args.image, args.length_mm, args.height_mm, args.front)
    if args.json:
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0
    print(f"Longueur mesurée : {result.length_px} px · hauteur : {result.height_px} px "
          f"(rapport {result.aspect_measured:.2f} vs {result.aspect_reference:.2f} attendu, "
          f"écart {result.aspect_error * 100:.1f} %)")
    print(f"Échelle : {result.scale_mm_per_px:.4f} mm/px")
    print(f"Hauteur d'appui : {result.click_height_mm:.1f} mm "
          f"({result.click_ratio * 100:.0f} % de la hauteur totale) → classe « {result.klass} »")
    print(result.verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
