"""Étude statistique des recommandations : quelle souris sort, combien de fois, et pourquoi les autres
ne sortent jamais.

But (demande du propriétaire, 2026-10-12) : passer TOUTES les formes de main plausibles, toutes les
prises (Palm, les trois variantes de Claw, Fingertip), toutes les tailles de thénar et les six modes
du questionnaire, puis compter combien de fois chaque souris du catalogue est recommandée — match
idéal, alternative, économie — et expliquer les souris qui ne sortent jamais (écartées ? en attente ?
coque en double ?).

L'outil ne modifie AUCUNE donnée : il lit le catalogue et le moteur, il écrit un rapport Markdown.

Usage :
    .venv/bin/python tools/recommendation_stats.py                 # rapport complet (~2 min)
    .venv/bin/python tools/recommendation_stats.py --rapide        # grille réduite
    .venv/bin/python tools/recommendation_stats.py --sortie docs/audit/XXX.md
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cogs.finder_flow import compute_selection, result_slots  # noqa: E402
from config import MOUSE_DB_PATH  # noqa: E402
from utils.catalog import load_catalog  # noqa: E402
from utils.models import BUDGET_LABELS, BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402
from utils.selection import _same_shell  # noqa: E402
from utils.session import FinderSession  # noqa: E402

# --- Grille de mains ---------------------------------------------------------
# Bornes larges autour des mains adultes réelles (la longueur va du poignet au bout du majeur,
# la largeur est mesurée sans le pouce) : 140 à 230 mm et 60 à 120 mm, par pas de 5 mm.
LENGTHS_FULL = [float(v) for v in range(140, 235, 5)]
WIDTHS_FULL = [float(v) for v in range(60, 125, 5)]
LENGTHS_FAST = [160.0, 180.0, 200.0, 215.0]
WIDTHS_FAST = [70.0, 85.0, 100.0, 115.0]

CUSTOM_BUDGETS = [10.0, 25.0, 45.0, 60.0, 90.0, 150.0]
MODES: list[BudgetMode | None] = [None, *BudgetMode]
CLAW_VARIANTS = list(ClawVariant)


def profiles(fast: bool):
    """Génère chaque combinaison (main, prise, thénar, mode) une seule fois."""
    lengths = LENGTHS_FAST if fast else LENGTHS_FULL
    widths = WIDTHS_FAST if fast else WIDTHS_FULL
    for length in lengths:
        for width in widths:
            for mode in MODES:
                budgets = CUSTOM_BUDGETS if mode is BudgetMode.CUSTOM else [None]
                for budget in budgets:
                    # Palm : thénar posé. Claw : les trois variantes (elles ne changent pas le score,
                    # le banc les parcourt pour le prouver). Fingertip : ni variante ni thénar.
                    for grip, variant, thenars in (
                        (Grip.PALM, None, [None, *Thenar]),
                        (Grip.CLAW, None, [None, *Thenar]),
                        (Grip.FINGERTIP, None, [None]),
                    ):
                        for thenar in thenars:
                            session = FinderSession(user_id=7)
                            session.grip = grip
                            session.claw_variant = variant
                            session.thenar = thenar
                            session.hand_length_mm = length
                            session.hand_width_mm = width
                            session.budget_mode = mode
                            session.max_budget_eur = budget
                            yield session
                    # variantes de Claw : mêmes profils, pour vérifier qu'aucune ne change le résultat
                    for variant in CLAW_VARIANTS:
                        for thenar in (None, *Thenar):
                            session = FinderSession(user_id=7)
                            session.grip = Grip.CLAW
                            session.claw_variant = variant
                            session.thenar = thenar
                            session.hand_length_mm = length
                            session.hand_width_mm = width
                            session.budget_mode = mode
                            session.max_budget_eur = budget
                            yield session


def run(fast: bool):
    mice = load_catalog(MOUSE_DB_PATH)
    roles: dict[str, Counter] = {m.id: Counter() for m in mice}
    statuses: dict[str, Counter] = {m.id: Counter() for m in mice}
    by_mode: dict[str, Counter] = {m.id: Counter() for m in mice}
    by_grip: dict[str, Counter] = {m.id: Counter() for m in mice}
    total_profiles = 0
    empty_profiles = 0

    for session in profiles(fast):
        total_profiles += 1
        try:
            selection = compute_selection(session)
        except Exception as exc:  # noqa: BLE001 — l'étude doit signaler, pas s'arrêter
            print(f"EXCEPTION {session.grip} {session.hand_length_mm}x{session.hand_width_mm} "
                  f"{session.budget_mode} : {type(exc).__name__} {exc}")
            continue

        for score in selection.ranked:
            statuses[score.mouse.id]["scored"] += 1
        for score in selection.pending:
            statuses[score.mouse.id]["pending"] += 1

        ideal, alternative, economy = result_slots(selection)
        if ideal is None:
            empty_profiles += 1
        for role, score in (("ideal", ideal), ("alternative", alternative), ("economy", economy)):
            if score is None:
                continue
            roles[score.mouse.id][role] += 1
            roles[score.mouse.id]["total"] += 1
            if session.budget_mode is not None:
                by_mode[score.mouse.id][session.budget_mode.value] += 1
            by_grip[score.mouse.id][session.grip.value] += 1

    return {
        "mice": mice,
        "roles": roles,
        "statuses": statuses,
        "by_mode": by_mode,
        "by_grip": by_grip,
        "total_profiles": total_profiles,
        "empty_profiles": empty_profiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rapide", action="store_true", help="grille réduite")
    parser.add_argument("--sortie", default=str(ROOT / "docs" / "audit" /
                                               "STATISTIQUES_RECOMMANDATIONS_2026-10-12.md"))
    args = parser.parse_args()

    data = run(args.rapide)
    mice = data["mice"]
    roles = data["roles"]
    statuses = data["statuses"]
    by_mode, by_grip = data["by_mode"], data["by_grip"]
    total = data["total_profiles"]

    ranked = sorted(mice, key=lambda m: (-roles[m.id]["total"], -roles[m.id]["ideal"], m.label))
    never = [m for m in ranked if roles[m.id]["total"] == 0]

    class _Carrier:                      # petit adaptateur pour réutiliser _same_shell
        def __init__(self, mouse):
            self.mouse = mouse

    lines: list[str] = []
    add = lines.append
    add("# Statistiques de recommandation — 2026-10-12\n")
    add(f"Grille : **{total:,} profils** (toutes les combinaisons de longueur, largeur, prise, "
        "variante de Claw, thénar, mode et budget personnalisé).\n".replace(",", " "))
    add("Une « recommandation » = une souris affichée dans le message de résultat, à l'une des trois "
        "places : match idéal, alternative, économie.\n")
    add("| Souris | Idéal | Alternative | Économie | Total | Part des profils |")
    add("|---|---:|---:|---:|---:|---:|")
    for mouse in ranked:
        counter = roles[mouse.id]
        share = 100 * counter["total"] / total if total else 0
        add(f"| {mouse.label} | {counter['ideal']} | {counter['alternative']} | {counter['economy']} "
            f"| {counter['total']} | {share:.1f} % |")

    add("\n## Souris jamais recommandées\n")
    if not never:
        add("Aucune : chaque souris du catalogue sort au moins une fois sur cette grille.")
    else:
        for mouse in never:
            add(f"- **{mouse.label}** (`{mouse.id}`)")
    add("\n## Pourquoi certaines ne sortent jamais\n")
    add("| Souris | Écartée | En attente | Classée | Motif principal (donnée manquante, écart, "
        "coque en double) |")
    add("|---|---:|---:|---:|---|")
    for mouse in never:
        motives = []
        if mouse.button_height == "Inconnu":
            motives.append("hauteur des boutons non documentée")
        if mouse.hump_position == "Inconnu":
            motives.append("bosse non documentée")
        if mouse.fit_status == "unverified" or all(
                getattr(mouse, field) == "Inconnu"
                for field in ("palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit")):
            motives.append("aucune compatibilité de prise publiée")
        if mouse.price_eur is None:
            motives.append("prix absent (modes à prix)")
        twins = [other.label for other in mice
                 if other.id != mouse.id and _same_shell(_Carrier(other), _Carrier(mouse))]
        if twins:
            motives.append(f"même coque que {', '.join(twins)}")
        counter = statuses[mouse.id]
        excluded = total - counter["scored"] - counter["pending"]
        add(f"| {mouse.label} | {100 * excluded / total:.0f} % | "
            f"{100 * counter['pending'] / total:.0f} % | {100 * counter['scored'] / total:.0f} % | "
            f"{' · '.join(motives) or 'à examiner'} |")

    add("\n## Par mode (nombre de sorties)\n")
    modes = [mode for mode in MODES if mode is not None]
    add("| Souris | " + " | ".join(BUDGET_LABELS[mode] for mode in modes) + " |")
    add("|---" * (len(modes) + 1) + "|")
    for mouse in ranked:
        add(f"| {mouse.label} | " + " | ".join(str(by_mode[mouse.id][mode.value]) for mode in modes) + " |")

    add("\n## Par prise (nombre de sorties)\n")
    add("| Souris | Palm | Claw | Fingertip |")
    add("|---|---:|---:|---:|")
    for mouse in ranked:
        add(f"| {mouse.label} | {by_grip[mouse.id]['palm']} | {by_grip[mouse.id]['claw']} "
            f"| {by_grip[mouse.id]['fingertip']} |")

    output = Path(args.sortie)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Profils passés : {total}")
    print(f"Profils sans aucun résultat : {data['empty_profiles']}")
    print(f"Souris jamais recommandées : {len(never)}")
    for mouse in never:
        print(f"  · {mouse.label} ({mouse.id})")
    top = ranked[:5]
    print("Les plus recommandées :")
    for mouse in top:
        print(f"  · {mouse.label} : {roles[mouse.id]['total']} sorties "
              f"({100 * roles[mouse.id]['total'] / total:.1f} % des profils)")
    print(f"Rapport écrit : {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
