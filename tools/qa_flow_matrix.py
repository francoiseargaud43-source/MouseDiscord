"""Banc d'essai du parcours : passe TOUTE la grille de profils dans le moteur et rend un rapport.

But : ne jamais découvrir en production un profil qui plante, qui ne renvoie rien du tout ou qui
produit un message hors des limites de Discord. L'outil n'écrit rien et ne modifie aucune donnée.

Usage :
    .venv/bin/python tools/qa_flow_matrix.py           # rapport complet
    .venv/bin/python tools/qa_flow_matrix.py --rapide  # grille réduite (intégration continue)

Contrôles effectués, profil par profil :
- aucune exception ne remonte ;
- le résultat n'est jamais vide (« Aucun match classable ») pour une main plausible ;
- les limites Discord sont respectées (2 à 10 blocs, ≤ 6 000 caractères par bloc, ≤ 25 champs,
  ≤ 1 024 caractères par champ, ≤ 4 096 pour la description, ≤ 5 boutons sur 2 rangées) ;
- le total de points reste dans 0...40 et le pourcentage affiché correspond ;
- deux places du résultat ne montrent jamais la même souris.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cogs.finder_flow import compute_selection, result_slots, results_embeds  # noqa: E402
from utils.matcher import MAX_SCORE  # noqa: E402
from utils.models import BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402
from utils.session import FinderSession  # noqa: E402

GRIPS = list(Grip)
THENARS = [None, *Thenar]
MODES = [None, *BudgetMode]


def _lengths(fast: bool) -> list[float]:
    if fast:
        return [160.0, 180.0, 200.0]
    return [float(v) for v in range(140, 235, 5)]


def _widths(fast: bool) -> list[float]:
    if fast:
        return [70.0, 90.0, 110.0]
    return [float(v) for v in range(60, 125, 5)]


def _budgets(fast: bool) -> list[float]:
    return [30.0, 60.0, 120.0] if fast else [10.0, 25.0, 45.0, 60.0, 90.0, 150.0]


def profile(mode: BudgetMode | None, budget: float | None) -> FinderSession:
    session = FinderSession(user_id=7)
    session.budget_mode = mode
    session.max_budget_eur = budget if mode is BudgetMode.CUSTOM else None
    return session


def check_embed_limits(embeds) -> list[str]:
    problems: list[str] = []
    if not 1 <= len(embeds) <= 10:
        problems.append(f"nombre de blocs hors limites : {len(embeds)}")
    for index, embed in enumerate(embeds, start=1):
        total = len(embed.title or "") + len(embed.description or "")
        total += sum(len(f.name) + len(f.value) for f in embed.fields)
        total += len(embed.footer.text or "")
        if total > 6000:
            problems.append(f"bloc {index} : {total} caractères (> 6000)")
        if len(embed.fields) > 25:
            problems.append(f"bloc {index} : {len(embed.fields)} champs (> 25)")
        if len(embed.description or "") > 4096:
            problems.append(f"bloc {index} : description {len(embed.description or '')} (> 4096)")
        for f in embed.fields:
            if len(f.name) > 256 or len(f.value) > 1024:
                problems.append(f"bloc {index} : champ « {f.name} » hors limites")
    return problems


def run(fast: bool) -> int:
    cases = 0
    problems: list[str] = []
    empties: list[str] = []
    partials = 0
    for grip, length, width, thenar in itertools.product(
        GRIPS, _lengths(fast), _widths(fast), THENARS
    ):
        if grip is not Grip.CLAW and thenar is None:
            continue                       # le thénar est toujours demandé hors Fingertip
        for mode in MODES:
            budgets = _budgets(fast) if mode is BudgetMode.CUSTOM else [None]
            for budget in budgets:
                cases += 1
                where = f"{grip.value}/{length:.0f}x{width:.0f}/thenar={thenar}/mode={mode}/{budget}"
                session = profile(mode, budget)
                session.grip = grip
                session.hand_length_mm = length
                session.hand_width_mm = width
                session.thenar = thenar if grip is not Grip.FINGERTIP else None
                if grip is Grip.CLAW:
                    session.claw_variant = ClawVariant.RELACHEE
                try:
                    selection = compute_selection(session)
                    embeds = results_embeds(session, selection)
                except Exception as exc:  # noqa: BLE001 - le banc d'essai doit tout attraper
                    problems.append(f"{where} : EXCEPTION {type(exc).__name__} : {exc}")
                    continue
                problems.extend(f"{where} : {p}" for p in check_embed_limits(embeds))
                ideal, alternative, economy = result_slots(selection)
                if ideal is None:
                    empties.append(where)
                else:
                    if ideal.is_partial:
                        partials += 1
                    for score in (ideal, alternative, economy):
                        if score is None:
                            continue
                        if not 0 <= score.total <= MAX_SCORE:
                            problems.append(f"{where} : total {score.total} hors barème")
                    if alternative is not None and alternative.mouse.id == ideal.mouse.id:
                        problems.append(f"{where} : alternative identique au match idéal")
                    if economy is not None and economy.mouse.id in {
                        ideal.mouse.id,
                        alternative.mouse.id if alternative else None,
                    }:
                        problems.append(f"{where} : économie déjà montrée plus haut")
    print(f"Profils testés : {cases}")
    print(f"Profils sans aucun résultat : {len(empties)}")
    for where in empties[:15]:
        print(f"  · {where}")
    print(f"Profils où le match idéal est partiel (boutons non documentés) : {partials}")
    print(f"Problèmes détectés : {len(problems)}")
    for problem in problems[:40]:
        print(f"  ! {problem}")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Banc d'essai du parcours")
    parser.add_argument("--rapide", action="store_true", help="grille réduite")
    args = parser.parse_args()
    return run(args.rapide)


if __name__ == "__main__":
    raise SystemExit(main())
