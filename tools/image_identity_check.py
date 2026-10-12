"""Contrôle d'identité d'une image SANS nom par comparaison de silhouette à une image AVEC nom.

Pourquoi cet outil existe : deux règles se heurtaient.

1. « le nom de fichier ne prouve rien » (`tools/image_corpus_check.py`) : une image n'est attribuable à
   un modèle que si ce modèle est identifié **sur l'image** (nom imprimé sur la coque) ;
2. la mesure de la hauteur des boutons exige **deux images distinctes** du même modèle
   (`tools/measure_button_height.py`, règle du 2026-10-12).

Or les fabricants publient souvent, pour un même modèle, **plusieurs rendus** dont un seul porte le nom
imprimé (l'autre flanc montre le logo de la marque). Cet outil permet de rattacher le rendu anonyme au
rendu nommé — non pas par son nom de fichier, mais par la **géométrie** : le profil supérieur de la
silhouette, normalisé en fraction de hauteur le long de la longueur, puis mis dans le même sens.

Ce que l'outil mesure : l'écart moyen, maximal et au 95e centile entre les deux profils, en pourcentage
de la hauteur de la souris. Étalonnage sur le corpus du 2026-10-12 :

- **même coque** (les deux rendus ATK ZERO, l'un nommé « ZERO », l'autre au logo « ATK ») : écart moyen
  **0,24 %**, 95e centile 0,56 % ;
- **coques différentes** (ZERO contre A9, ZERO contre un rendu noir anonyme) : écart moyen **4,5 %** et
  **4,8 %**, maximum ~10-12 %.

Les seuils par défaut (1 % = même coque, 3 % = coque différente) sont donc posés dans une zone vide,
loin des deux populations mesurées. Entre les deux, l'outil refuse de trancher.

Limite assumée : deux coques très proches (mêmes dimensions au millimètre) ne peuvent pas être
distinguées par cette méthode — c'est précisément pourquoi le catalogue enregistre les coques partagées
(`shell_id`) et pourquoi la décision finale reste visuelle.

Usage :
    python tools/image_identity_check.py --reference IMG [--ref-front right] \\
                                         --candidate IMG [--cand-front left] [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

# Seuils d'étalonnage (voir l'en-tête) : mesurés sur le corpus réel du 2026-10-12.
SAME_SHELL_MAX_MEAN = 0.01          # ≤ 1 % en moyenne : même coque
DIFFERENT_SHELL_MIN_MEAN = 0.03     # ≥ 3 % en moyenne : coques différentes entre les deux : indéterminé
PROFILE_POINTS = 200

_MODULE_MESURE = Path(__file__).with_name("measure_button_height.py")


def _loader_mesure():
    """Charge `measure_button_height` (réutilise la lecture de silhouette déjà testée)."""
    spec = importlib.util.spec_from_file_location("_mbh_st", _MODULE_MESURE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_mbh_st"] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Comparison:
    points_reference: int
    points_candidate: int
    mean_gap: float
    max_gap: float
    p95_gap: float
    verdict: str

    @property
    def same_shell(self) -> bool:
        return self.mean_gap <= SAME_SHELL_MAX_MEAN


def top_profile(path: str | Path, front: str = "left", points: int = PROFILE_POINTS) -> list[float]:
    """Profil supérieur normalisé de la silhouette (0 = sol, 1 = point le plus haut), avant en tête."""
    mbh = _loader_mesure()
    img = Image.open(path)
    if img.mode not in ("RGBA", "LA"):
        img = img.convert("RGB")
    x_min, x_max, _y_min, y_max, height_px, top = mbh._silhouette(img)
    if len(top) < 2:
        raise ValueError("silhouette illisible : trop peu de colonnes")
    xs = sorted(top)
    hauteurs = [(x, (y_max - top[x]) / height_px) for x in xs]
    if front == "right":
        hauteurs = [(x_min + x_max - x, h) for x, h in reversed(hauteurs)]
    pas = (len(hauteurs) - 1) / (points - 1)
    return [hauteurs[round(i * pas)][1] for i in range(points)]


def _profil_et_taille(path: Path, front: str) -> tuple[list[float], int]:
    """Profil normalisé + nombre de colonnes de silhouette (une seule lecture d'image)."""
    mbh = _loader_mesure()
    img = Image.open(path)
    if img.mode not in ("RGBA", "LA"):
        img = img.convert("RGB")
    x_min, x_max, _y_min, y_max, height_px, top = mbh._silhouette(img)
    if len(top) < 2:
        raise ValueError("silhouette illisible : trop peu de colonnes")
    xs = sorted(top)
    hauteurs = [(x, (y_max - top[x]) / height_px) for x in xs]
    if front == "right":
        hauteurs = [(x_min + x_max - x, h) for x, h in reversed(hauteurs)]
    pas = (len(hauteurs) - 1) / (PROFILE_POINTS - 1)
    return [hauteurs[round(i * pas)][1] for i in range(PROFILE_POINTS)], len(hauteurs)


def compare(reference: Path, candidate: Path, ref_front: str = "left",
            cand_front: str = "left") -> Comparison:
    """Compare deux profils de silhouette et rend un verdict borné (jamais de conclusion forcée)."""
    profil_ref, points_ref = _profil_et_taille(reference, ref_front)
    profil_cand, points_cand = _profil_et_taille(candidate, cand_front)
    ecarts = sorted(abs(a - b) for a, b in zip(profil_ref, profil_cand))
    moyenne = sum(ecarts) / len(ecarts)
    p95 = ecarts[min(len(ecarts) - 1, int(0.95 * len(ecarts)))]
    return Comparison(points_ref, points_cand, moyenne, ecarts[-1], p95, _verdict(moyenne))


def _verdict(mean_gap: float) -> str:
    """Verdict borné : les seuils sont posés entre les deux populations étalonnées (voir l'en-tête)."""
    if mean_gap <= SAME_SHELL_MAX_MEAN:
        return (f"même coque probable : écart moyen {mean_gap * 100:.2f} % (≤ "
                f"{SAME_SHELL_MAX_MEAN * 100:.0f} %, étalonnage « même coque » = 0,24 %)")
    if mean_gap >= DIFFERENT_SHELL_MIN_MEAN:
        return (f"coques différentes : écart moyen {mean_gap * 100:.2f} % (≥ "
                f"{DIFFERENT_SHELL_MIN_MEAN * 100:.0f} %, étalonnage « coques différentes » = 4,5-4,8 %)")
    return (f"NON TRANCHÉ : écart moyen {mean_gap * 100:.2f} %, entre les deux populations "
            "étalonnées — aucune conclusion")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Identité d'une image sans nom, par comparaison de silhouette à une image nommée.")
    parser.add_argument("--reference", required=True, help="image dont le modèle est identifié visuellement")
    parser.add_argument("--candidate", required=True, help="image à rattacher")
    parser.add_argument("--ref-front", choices=("left", "right"), default="left")
    parser.add_argument("--cand-front", choices=("left", "right"), default="left")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    resultat = compare(Path(args.reference), Path(args.candidate), args.ref_front, args.cand_front)
    if args.json:
        print(json.dumps(resultat.__dict__, ensure_ascii=False, indent=2))
        return 0
    print(f"Référence : {args.reference} (avant à {args.ref_front}) — {resultat.points_reference} colonnes")
    print(f"Candidate : {args.candidate} (avant à {args.cand_front}) — {resultat.points_candidate} colonnes")
    print(f"Écart moyen : {resultat.mean_gap * 100:.2f} % de la hauteur | maximum : "
          f"{resultat.max_gap * 100:.2f} % | 95e centile : {resultat.p95_gap * 100:.2f} %")
    print(f"Verdict : {resultat.verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
