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
# propriétaire) : ce sont les deux seuls points d'étalonnage disponibles. Ils encadrent la frontière
# entre « bas » et « haut » ; entre les deux, l'outil REFUSE de trancher (aucune classe inventée).
CALIBRATION_REFERENCES = (
    ("ATK F1 V2 (boutons bas)", "Low", 0.433),
    ("ATK Z1 V2 (boutons hauts)", "High", 0.551),
)
# Marge d'incertitude : une mesure n'est classée que si elle dépasse la référence correspondante
# d'au moins cette marge. Entre les deux, la valeur reste NON TRANCHÉE.
CALIBRATION_MARGIN = 0.02


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


def _silhouette(img: Image.Image, tolerance: int = 28):
    """Boîte englobante et profil supérieur de la souris.

    ``top[x]`` = première rangée non-fond de la colonne (le dessus de la coque) ;
    ``bottom[x]`` = dernière rangée non-fond (la base). La hauteur de la souris se mesure entre
    le point le plus haut **du dessus** et le point le plus bas **de la base** — et non entre deux
    points du dessus, ce qui sous-estimerait la hauteur (erreur corrigée le 2026-10-12).
    """
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
    img = Image.open(path).convert("RGB")
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


def _classify(ratio: float) -> tuple[str | None, str]:
    """Classe la mesure à partir des références étalonnées, ou refuse de trancher.

    Aucune « Mid » n'est produite : la classe moyenne n'est pas étalonnée, donc une valeur
    intermédiaire reste non tranchée. C'est volontaire — une classe inventée serait pire
    qu'une classe absente.
    """
    low = min(r for _, k, r in CALIBRATION_REFERENCES if k == "Low")
    high = max(r for _, k, r in CALIBRATION_REFERENCES if k == "High")
    # Les trois hauteurs de boutons sont ordonnées (bas < moyen < haut) : mesurer au plus la
    # référence « bas » (à la marge près) prouve « bas » ; mesurer au moins la référence « hauts »
    # prouve « hauts ». Entre les deux, la classe moyenne reste indécidable.
    if ratio <= low + CALIBRATION_MARGIN:
        return "Low", ("vue acceptée : mesure au niveau ou sous la référence « boutons bas » "
                       f"({low * 100:.1f} %)")
    if ratio >= high - CALIBRATION_MARGIN:
        return "High", ("vue acceptée : mesure au niveau ou au-dessus de la référence « boutons hauts » "
                        f"({high * 100:.1f} %)")
    return None, (f"vue acceptée, mais classe NON TRANCHÉE : la mesure ({ratio * 100:.1f} %) tombe "
                  f"dans l'intervalle gris {low * 100:.1f}–{high * 100:.1f} % entre les deux "
                  "références ; aucune référence « boutons moyens » n'est disponible")


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
