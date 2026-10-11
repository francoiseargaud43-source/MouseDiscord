"""Mesure la largeur de prise d'une souris sur une image vue de dessus (méthode Oblivity).

Pourquoi ce script : le fabricant (et EloShapes) publient la largeur **maximale**, mesurée au point le
plus large — souvent déformé par l'évasement arrière. Le critère utile est la largeur **au niveau du
capteur**, là où le pouce et l'auriculaire touchent la souris (voir la vidéo Oblivity « The Scientific
Way to Pick A Mouse », 3:19 et 6:35, et `docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md`).

Mode d'emploi (aucune connexion réseau, aucune donnée envoyée) :
  1. faire une capture vue de dessus du contour de la souris (EloShapes par exemple) ;
  2. lancer `python tools/measure_grip_width.py capture.png --length 118.2` ;
  3. reporter la valeur « largeur au capteur » dans `grip_width_mm` du catalogue, avec la source et la date.

L'échelle est déduite de la longueur réelle : le contour doit être entier et cadré (vue de dessus stricte).
Précision typique : ± 0,3 mm sur une capture de 600 px de long (≈ 0,2 mm par pixel).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ALPHA_THRESHOLD = 16          # transparence : en dessous, le pixel est considéré comme vide
BACKGROUND_TOLERANCE = 24     # écart de couleur admis avec le fond (sans transparence)
PROFILE_STEP_PERCENT = 10     # pas du profil affiché (% de la longueur depuis l'avant)


class MeasurementError(ValueError):
    """Image inexploitable (aucun contour détecté, format inattendu…)."""


def _background_color(pixels, size) -> tuple[int, int, int]:
    """Couleur de fond = moyenne des quatre coins."""
    width, height = size
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    samples = [pixels[x, y][:3] for x, y in corners]
    return tuple(sum(channel) // len(samples) for channel in zip(*samples))  # type: ignore[return-value]


def silhouette_rows(image: Image.Image) -> list[tuple[int, int, int]]:
    """Largeur de la silhouette, ligne par ligne : liste de (y, x_min, x_max).

    Une ligne sans pixel « souris » est omise. La transparence sert de masque si elle existe,
    sinon le fond (couleur des coins) est retiré avec une tolérance.
    """
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    has_alpha = any(pixels[x, y][3] < 255 for x in range(0, width, 4) for y in range(0, height, 4))
    background = _background_color(pixels, (width, height))
    rows: list[tuple[int, int, int]] = []
    for y in range(height):
        x_min = x_max = None
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if has_alpha:
                is_shape = alpha > ALPHA_THRESHOLD
            else:
                is_shape = any(abs(channel - back) > BACKGROUND_TOLERANCE
                               for channel, back in zip((red, green, blue), background))
            if is_shape:
                if x_min is None:
                    x_min = x
                x_max = x
        if x_min is not None and x_max is not None:
            rows.append((y, x_min, x_max))
    if not rows:
        raise MeasurementError("aucun contour détecté : vérifiez que la souris se détache du fond")
    return rows


def measure(image_path: Path, length_mm: float, at: float = 0.5) -> dict[str, object]:
    """Mesure la silhouette et retourne les largeurs (mm) à la fraction demandée et au point le plus large."""
    if length_mm <= 0:
        raise MeasurementError("la longueur réelle doit être positive")
    if not 0.0 <= at <= 1.0:
        raise MeasurementError("la fraction de longueur doit être comprise entre 0 et 1")
    rows = silhouette_rows(Image.open(image_path))
    top, bottom = rows[0][0], rows[-1][0]
    height_px = bottom - top + 1
    scale = length_mm / height_px                     # mm par pixel (la hauteur de l'image = la longueur)
    widths = [(y, (x_max - x_min + 1) * scale) for y, x_min, x_max in rows]

    def width_at(fraction: float) -> tuple[float, float]:
        index = min(len(widths) - 1, max(0, round(fraction * (len(widths) - 1))))
        y, value = widths[index]
        return (y - top) / max(1, height_px - 1), value

    at_fraction, at_width = width_at(at)
    max_y, max_width = max(widths, key=lambda item: item[1])
    profile = {f"{percent} %": round(width_at(percent / 100)[1], 2)
               for percent in range(0, 101, PROFILE_STEP_PERCENT)}
    profile["100 %"] = round(widths[-1][1], 2)
    return {
        "image": str(image_path),
        "longueur_reelle_mm": length_mm,
        "hauteur_contour_px": height_px,
        "mm_par_pixel": round(scale, 4),
        "largeur_au_point_demande_mm": round(at_width, 2),
        "fraction_demandee": round(at_fraction, 3),
        "largeur_maximale_mm": round(max_width, 2),
        "fraction_du_maximum": round((max_y - top) / max(1, height_px - 1), 3),
        "profil_mm": profile,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Largeur de prise d'une souris depuis une image vue de dessus.")
    parser.add_argument("image", type=Path, help="contour vu de dessus (PNG ou JPG)")
    parser.add_argument("--length", type=float, required=True, help="longueur réelle de la souris en mm (échelle)")
    parser.add_argument("--at", type=float, default=0.5,
                        help="position de mesure le long de la souris (0 = avant, 0,5 = milieu, 1 = arrière)")
    parser.add_argument("--json", action="store_true", help="sortie JSON (pour un script)")
    args = parser.parse_args(argv)
    if not args.image.is_file():
        print(f"ERREUR : image introuvable : {args.image}")
        return 1
    try:
        result = measure(args.image, args.length, args.at)
    except MeasurementError as exc:
        print(f"ERREUR : {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Image : {result['image']}")
    print(f"Échelle : {result['hauteur_contour_px']} px pour {result['longueur_reelle_mm']} mm "
          f"→ {result['mm_par_pixel']} mm/px")
    print(f"Largeur maximale mesurée : {result['largeur_maximale_mm']} mm "
          f"(à {result['fraction_du_maximum'] * 100:.0f} % de la longueur depuis l'avant)")
    print(f"Largeur à {result['fraction_demandee'] * 100:.0f} % de la longueur : "
          f"**{result['largeur_au_point_demande_mm']} mm**")
    print("Profil de largeur (hausse de l'avant vers l'arrière) :")
    for percent, value in result["profil_mm"].items():
        print(f"  {percent:>5} : {value} mm")
    print("\nReporter la valeur utile dans data/mouse_db.json (champ grip_width_mm) avec sa source et sa date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
