"""Génère docs/audit/matrice_profils.md : comparaison des souris pour les profils P, C et F.

Usage (depuis la racine du dépôt) :
    python tools/compare_profiles.py

Le script n'introduit aucune donnée : il applique le moteur (utils/matcher.py) et la sélection
(utils/selection.py) au catalogue data/mouse_db.json. Relancer après toute modification du catalogue.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cogs.finder_flow import result_slots  # noqa: E402
from config import MOUSE_DB_PATH  # noqa: E402
from utils.catalog import load_catalog  # noqa: E402
from utils.matcher import MAX_SCORE, compute_target_ranges, distance_outside, evaluate_mouse, grip_width_for_scoring  # noqa: E402
from utils.models import BudgetMode, Grip, HandMeasure  # noqa: E402
from utils.selection import select  # noqa: E402

PROFILES = [
    ("P", "Palm 180 × 90 mm", HandMeasure(180, 90), Grip.PALM),
    ("C", "Claw 150 × 75 mm", HandMeasure(150, 75), Grip.CLAW),
    ("F", "Fingertip 200 × 100 mm", HandMeasure(200, 100), Grip.FINGERTIP),
]
CUSTOM_MAX_EUR = 75.0
MODES = [
    ("Économique", BudgetMode.ECONOMIQUE),
    ("Qualité/Prix", BudgetMode.QUALITE_PRIX),
    ("Haut de gamme", BudgetMode.HAUT_DE_GAMME),
    ("Peu importe le prix", BudgetMode.PEU_IMPORTE_PRIX),
    ("Budget ≤ {cap:g} €", BudgetMode.CUSTOM),   # le plafond est formaté à l'affichage
]


def _fmt_dist(value: float | None, low: float, high: float, grip: Grip) -> str:
    if value is None:
        return "non vérifiée"
    d = distance_outside(value, low, high)
    return "dans la plage" if d == 0 else f"écart {d:.1f} mm"


def _status_cell(s) -> str:
    if s.is_excluded:
        return f"❌ exclue — {s.excluded_reason}"
    if s.is_pending:
        return f"⏳ à vérifier ({s.total}/{s.computable_max} pts partiels)"
    if s.is_partial:
        return f"✅ {s.total}/{MAX_SCORE} (boutons non documentés)"
    return f"✅ {s.total}/{MAX_SCORE}"


def build(custom_max_eur: float = CUSTOM_MAX_EUR) -> str:
    """Construit la matrice complète.

    ``custom_max_eur`` est le plafond du mode « Budget personnalisé ». Il ne doit influencer QUE la
    ligne « Budget » des classements par mode — c'est le sens du contrôle de non-régression
    `tests/test_compare_profiles.py::test_only_the_budget_row_depends_on_the_custom_budget`.
    """
    mice = load_catalog(MOUSE_DB_PATH)
    out: list[str] = []
    out.append("# Matrices de comparaison par profil\n")
    out.append(f"_Généré par `tools/compare_profiles.py` à partir de `data/mouse_db.json` le "
               f"**{date.today().isoformat()}**. Ne pas modifier à la main : relancer le script._\n")
    out.append("**Lecture** : « ✅ » = score final sur 40 ; « ⏳ » = données manquantes, score partiel NON classable ; "
               "« ❌ » = exclusion. Le pourcentage du barème n'est pas une probabilité.\n")
    out.append(f"Budget personnalisé de comparaison : {custom_max_eur:g} € (il ne s'applique QU'À la ligne « Budget » "
               "des classements : les autres modes classent le catalogue entier, comme le bot). "
               "Tolérances de sélection : Économique 5 pts, Qualité/Prix 2 pts, Haut de gamme 2 pts, Budget 2 pts "
               "(provisoires).\n")

    for code, title, hand, grip in PROFILES:
        ranges = compute_target_ranges(hand, grip)
        target_len = (f"≤ {ranges.length_max:.1f} mm" if grip is Grip.FINGERTIP
                      else f"{ranges.length_min:.1f}–{ranges.length_max:.1f} mm")
        out.append(f"\n## Profil {code} — {title}\n")
        out.append(f"Cible longueur : {target_len} · Cible largeur de prise : "
                   f"{ranges.width_min:.1f}–{ranges.width_max:.1f} mm\n")
        out.append("| Modèle | Statut / score | Longueur | Largeur de prise utilisée | Grip | Bosse | Boutons | Confiance | Données manquantes |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        scores = []
        for m in mice:
            s = evaluate_mouse(m, hand, grip, BudgetMode.CUSTOM, custom_max_eur)
            scores.append(s)
            width_used, src = grip_width_for_scoring(m)
            width_txt = f"{width_used:.1f} mm ({'mesurée' if src == 'measured' else 'estimée'}, écart {distance_outside(width_used, ranges.width_min, ranges.width_max):.1f})"
            length_txt = f"{m.length_mm:.1f} mm ({_fmt_dist(m.length_mm, ranges.length_min, ranges.length_max, grip)})" if m.length_mm is not None else "non vérifiée (conflit)"
            fit = m.fit_for(grip)
            hump = "ignorée (Fingertip)" if grip is Grip.FINGERTIP else m.hump_position
            missing = ", ".join(s.missing) if s.missing else ("—" if not s.is_excluded else s.excluded_reason)
            out.append(
                f"| {m.label} | {_status_cell(s)} | {length_txt} | {width_txt} | {fit} | {hump} | {m.button_height} | "
                f"{s.confidence or '—'} | {missing} |"
            )

        out.append(f"\n**Classement par mode (profil {code}, calculé comme dans le bot)**\n")
        out.append("Les deux colonnes sont les deux premières souris que le bot AFFICHE (1er = match idéal ; "
                   "2e = alternative, qui préfère une autre coque et n'élargit qu'une fois à ±5 points) : "
                   "ce n'est pas le 2e brut du classement.\n")
        out.append("| Mode | 1er | 2e | Zone de tolérance | Explication du 1er |")
        out.append("|---|---|---|---|---|")
        # Chaque mode est jugé sur la liste que le bot utilise pour ce mode : le plafond de budget
        # personnalisé ne concerne que le mode « Budget » (avant le 2026-10-12, ce script classait les
        # cinq modes sur la liste plafonnée à 75 € et se trompait de gagnant sur 8 lignes sur 15).
        free_scores = [evaluate_mouse(m, hand, grip) for m in mice]
        for label, mode in MODES:
            pool_scores = scores if mode is BudgetMode.CUSTOM else free_scores
            # Comme le bot : classement complet, puis les deux places affichées (règle de coque incluse).
            sel = select(pool_scores, mode, top_n=len(pool_scores))
            label = label.format(cap=custom_max_eur)
            ideal, alternative, _economy = result_slots(sel)
            first = f"{ideal.mouse.label} ({ideal.total}/{MAX_SCORE})" if ideal else "aucun classable"
            second = f"{alternative.mouse.label} ({alternative.total}/{MAX_SCORE})" if alternative else "—"
            out.append(f"| {label} | {first} | {second} | {sel.pool_size} candidat(s) | {sel.explanation} |")
        out.append("")
    return "\n".join(out) + "\n"


DEFAULT_TARGET = ROOT / "docs" / "audit" / "matrice_profils.md"


def main(argv: list[str] | None = None) -> int:
    """Régénère la matrice des profils (document de traçabilité du moteur).

    ``--help`` et ``--sortie`` ont été ajoutés le 2026-10-12 : sans argument, le script réécrivait
    directement ``docs/audit/matrice_profils.md`` — un fichier versionné — sans confirmation.
    Le comportement par défaut est inchangé.
    """
    parser = argparse.ArgumentParser(
        description="Régénère la matrice des profils (moteur de sélection) et l'écrit dans un fichier.",
    )
    parser.add_argument("--sortie", default=str(DEFAULT_TARGET),
                        help="fichier Markdown à écrire (défaut : docs/audit/matrice_profils.md)")
    parser.add_argument("--budget", type=float, default=CUSTOM_MAX_EUR,
                        help=f"plafond du mode « Budget personnalisé » (défaut : {CUSTOM_MAX_EUR:g} €) ; "
                             "il ne doit modifier que la ligne « Budget »")
    args = parser.parse_args(argv)
    target = Path(args.sortie)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build(args.budget), encoding="utf-8")
    print(f"Écrit : {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
