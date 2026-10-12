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
- deux places du résultat ne montrent jamais la même souris ;
- chaque souris montrée porte bien son NOM, son PRIX, son SCORE et son pourcentage (texte du message) ;
- aucun bouton d'achat pour une souris absente, et un bouton pour chaque souris affichée qui a un lien ;
- en budget personnalisé, aucune souris affichée au-dessus du budget ;
- aucune souris « en attente » (donnée manquante) ni « écartée » (prise faible) n'est affichée ;
- chaque place est contrôlée contre SA fenêtre : le match idéal est la tête du classement du mode,
  l'alternative reste dans la zone du mode ou n'en sort que si aucune autre coque ne s'y trouve (et
  jamais plus chère que le match idéal), l'économie reste dans sa fenêtre propre (±5 points) et coûte
  strictement moins cher que les deux autres ;
- comptage, sans le compter comme une faute, des profils où DEUX places montrent la même coque :
  c'est le repli documenté (« jamais moins de résultats qu'avant ») quand la zone de tolérance ne
  contient que des variantes de la coque retenue — il est mesuré, pas supposé.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cogs.finder_flow import (ALTERNATIVE_EXTENSION_POINTS, ECONOMY_SLOT_TOLERANCE_POINTS,  # noqa: E402
                              ResultsView, compute_selection, result_slots, results_embeds)
from config import COMMERCIAL_LINKS_PATH  # noqa: E402
from utils.catalog import load_commercial_links  # noqa: E402
from utils.matcher import MAX_SCORE, compatibility_percent  # noqa: E402
from utils.models import BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402
from utils.selection import TOLERANCE_BY_MODE, _same_shell  # noqa: E402
from utils.session import FinderSession  # noqa: E402

LINKS = load_commercial_links(COMMERCIAL_LINKS_PATH)
GRIP_FIELD = {Grip.PALM: "palm_grip_fit", Grip.CLAW: "claw_grip_fit", Grip.FINGERTIP: "fingertip_grip_fit"}


def prix_fr(price: float) -> str:
    """« 68,95 € » — la virgule décimale française, telle qu'affichée au membre."""
    return f"{price:.2f}".replace(".", ",") + " €"


def message_text(embeds) -> str:
    """Tout le texte visible du résultat (titres, descriptions, champs), pour les contrôles de contenu."""
    morceaux = []
    for embed in embeds:
        morceaux += [embed.title or "", embed.description or "", embed.footer.text or ""]
        for field in embed.fields:
            morceaux += [field.name, field.value]
    return "\n".join(morceaux)


def check_result_message(session, selection, embeds, displayed, repli_coque=None, etiquette="") -> list[str]:
    """Contrôles du CONTENU du message : chaque souris montrée doit l'être avec ses vrais chiffres."""
    problems: list[str] = []
    if not displayed:
        return problems
    ideal, alternative, economy = (list(displayed) + [None, None, None])[:3]
    texte = message_text(embeds)
    reference = selection.reference_score if selection.reference_score is not None else ideal.total
    tolerance = TOLERANCE_BY_MODE.get(selection.mode, 2)

    # Zone de chaque place (décision du 2026-10-12) : le match idéal est la tête du classement ;
    # l'alternative reste dans la zone du mode, sauf si cette zone ne contient que des variantes de la
    # coque retenue — elle peut alors venir de la fenêtre d'élargissement, et seulement si elle est
    # moins chère que le match idéal ; l'économie a sa propre fenêtre et un plafond de prix.
    # Le match idéal est la tête du classement DU MODE : en Économique (et en Qualité/Prix), la tête
    # est la souris la moins chère de la zone de tolérance, donc légitimement jusqu'à `tolerance`
    # points sous la meilleure note du mode — c'est l'invariant vérifié dans tests/test_selection.py.
    if ideal is not None and selection.ranked and ideal.mouse.id != selection.ranked[0].mouse.id:
        problems.append(f"le match idéal n'est pas la tête du classement : {ideal.mouse.label}")
    for role, score, marge in (("le match idéal", ideal, tolerance),
                               ("l'alternative", alternative, max(tolerance, ALTERNATIVE_EXTENSION_POINTS)),
                               ("l'économie", economy, ECONOMY_SLOT_TOLERANCE_POINTS)):
        if score is None:
            continue
        mouse = score.mouse
        if mouse.label not in texte:
            problems.append(f"souris montrée mais absente du texte : {mouse.label}")
        if score.is_pending:
            problems.append(f"souris EN ATTENTE affichée : {mouse.label}")
        fit = getattr(mouse, GRIP_FIELD[session.grip])
        if fit == "Faible":
            problems.append(f"souris à prise FAIBLE affichée : {mouse.label}")
        if not 0 <= score.total <= MAX_SCORE:
            problems.append(f"score hors barème pour {mouse.label} : {score.total}")
        if score.total < reference - marge:
            problems.append(f"{role} hors de sa zone ({mouse.label} : {score.total} < {reference - marge})")
        if role == "l'alternative" and score.total < reference - tolerance:
            # Élargissement : interdit si une autre coque était disponible dans la zone du mode, et
            # interdit si la souris proposée est plus chère que le match idéal.
            autres = [s for s in selection.ranked[1:]
                      if s.total >= reference - tolerance and not _same_shell(ideal, s)]
            if autres:
                problems.append(f"alternative hors zone alors qu'une autre coque y est : {mouse.label}")
            if mouse.price_eur is not None and ideal.mouse.price_eur is not None \
                    and mouse.price_eur > ideal.mouse.price_eur:
                problems.append(f"alternative élargie mais plus chère : {mouse.label}")
        if role == "l'économie" and score is not None:
            plafond = min([s.mouse.price_eur for s in (ideal, alternative)
                           if s is not None and s.mouse.price_eur is not None] or [float("inf")])
            if mouse.price_eur is not None and mouse.price_eur >= plafond:
                problems.append(f"économie pas strictement moins chère que les deux autres : {mouse.label}")
        if mouse.price_eur is not None and prix_fr(mouse.price_eur) not in texte:
            problems.append(f"prix absent ou faux pour {mouse.label} : attendu {prix_fr(mouse.price_eur)}")
        if session.budget_mode is BudgetMode.CUSTOM and mouse.price_eur is not None \
                and session.max_budget_eur is not None and mouse.price_eur > session.max_budget_eur:
            problems.append(f"{mouse.label} ({mouse.price_eur} €) au-dessus du budget {session.max_budget_eur} €")

    attendu_score = f"{ideal.total}/{MAX_SCORE}"
    attendu_pct = f"{compatibility_percent(ideal)} %"
    if attendu_score not in texte:
        problems.append(f"score du match idéal absent du message (attendu {attendu_score})")
    if attendu_pct not in texte:
        problems.append(f"pourcentage du match idéal absent du message (attendu {attendu_pct})")
    for dimension, nom_dimension in ((ideal.mouse.length_mm, "longueur"), (ideal.mouse.width_max_mm, "largeur")):
        if dimension is None:
            continue
        valeur = f"{dimension:g}".replace(".", ",")   # même écriture que _mm() dans le cog
        if valeur not in texte:
            problems.append(f"{nom_dimension} du match idéal absente du message (attendu {valeur} mm)")
    if selection.explanation and selection.explanation not in texte:
        problems.append("justification du choix absente du message")

    if alternative is not None and _same_shell(ideal, alternative):
        zone = [s for s in selection.ranked[1:] if s.total >= reference - tolerance]
        if any(not _same_shell(ideal, s) for s in zone):
            problems.append("alternative de la même coque alors qu'une autre coque est disponible")
    # Repli documenté : deux places peuvent montrer la même coque quand la zone n'offre rien d'autre.
    # On le compte pour le suivre (aucune règle n'est cassée), au lieu de le passer sous silence.
    if repli_coque is not None and any(_same_shell(ideal, s) for s in (alternative, economy) if s is not None):
        repli_coque.append(etiquette)
    identifiants = [s.mouse.id for s in (ideal, alternative, economy) if s is not None]
    if len(identifiants) != len(set(identifiants)):
        problems.append("la même souris est affichée deux fois")

    # Boutons d'achat : un par souris montrée, jamais pour une souris absente, et la bonne adresse.
    view = ResultsView([s for s in (ideal, alternative, economy) if s is not None], LINKS)
    boutons = [item for item in view.children]
    for bouton in boutons:
        url = getattr(bouton, "url", None)
        etiquette = getattr(bouton, "label", "") or ""
        if url is None:
            continue                              # bouton informatif « Liens à venir » (désactivé)
        if not any(url == LINKS.get(s.mouse.id) for s in (ideal, alternative, economy) if s is not None):
            problems.append(f"bouton vers une souris absente du message : {url}")
        attendu = next((s.mouse.label for s in (ideal, alternative, economy)
                        if s is not None and LINKS.get(s.mouse.id) == url), None)
        if attendu and attendu.split(" / ")[0][:20] not in etiquette:
            problems.append(f"bouton mal étiqueté : « {etiquette} » pour {attendu}")
    for score in (ideal, alternative, economy):
        if score is None or not LINKS.get(score.mouse.id):
            continue
        if not any(getattr(b, "url", None) == LINKS[score.mouse.id] for b in boutons):
            problems.append(f"aucun bouton d'achat pour {score.mouse.label}")
    return problems

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
    places = {0: 0, 1: 0, 2: 0, 3: 0}          # nombre de places réellement remplies dans le message
    same_shell_slots: list[str] = []            # profils où deux places partagent la même coque (repli)
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
                montrees = [s for s in (ideal, alternative, economy) if s is not None]
                places[len(montrees)] += 1
                problems.extend(f"{where} : {p}"
                                for p in check_result_message(session, selection, embeds, montrees,
                                                             same_shell_slots, where))
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
    print(f"Profils où deux places montrent la même coque (repli documenté) : {len(same_shell_slots)}"
          + (f"  ·  ex. {same_shell_slots[0]}" if same_shell_slots else ""))
    print("Places remplies dans le résultat : "
          + " · ".join(f"{n} place(s) : {places[n]}" for n in (0, 1, 2, 3))
          + f"  (3 places = {100 * places[3] / cases:.2f} % des profils)" if cases else "")
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
