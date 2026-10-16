"""Les trois places du résultat : quelles souris montrer, et sous quel titre (calcul pur, sans Discord).

Le moteur (``utils/matcher.py``) note chaque souris sur 40 ; la sélection (``utils/selection.py``) les
classe selon le mode commercial. Ce module choisit, DANS ce classement et sans jamais recalculer un
score, les trois souris que le membre verra :

1. **Le match idéal** — la tête du classement du mode.
2. **L'alternative** — un vrai autre choix : une autre coque, de préférence moins chère, dans la zone du
   mode (``TOLERANCE_BY_MODE``). Si la zone ne contient que des variantes de la coque déjà montrée, la
   recherche s'élargit UNE fois (``ALTERNATIVE_EXTENSION_POINTS``) vers une souris qui ne coûte pas plus
   cher ; à défaut, la variante est gardée.
3. **La troisième place** — la moins chère de sa propre fenêtre (``ECONOMY_SLOT_TOLERANCE_POINTS``) qui
   soit strictement moins chère que les deux autres (« l'économie ») ; sinon l'option la moins chère
   restante de cette fenêtre (« l'autre option ») ; sinon la meilleure souris restante (« autre piste »).

Trois règles valent pour toutes les places (décisions du propriétaire, 2026-10-12 et 2026-10-13) :

- **jamais deux fois la même coque**, tant qu'une autre coque est disponible pour la place ;
- **jamais de trou** : une place reste remplie dès qu'une souris est montrable — si plus rien d'autre
  n'existe, la règle de coque cède (repli « même coque », compté par le banc d'essai) ;
- **l'ordre des pourcentages est garanti** : une place n'est jamais mieux notée que celle du dessus
  (« plafond »). Le seul cas où il cède est celui où aucune souris ne passe sous le plafond ; la place
  reste alors remplie et le banc compte ces profils (« ordre non garanti »).

Le titre de chaque place redit la règle qui l'a choisie (``alternative_slot_title``,
``third_slot_title``) : une « autre piste » n'est jamais présentée comme une alternative comparable.
L'historique chiffré de chacune de ces décisions est tenu dans ``docs/audit/AUDIT.md``.
"""
from __future__ import annotations

from typing import Sequence

from utils.matcher import MouseScore
from utils.models import BudgetMode
from utils.selection import QUALITE_PRIX_TOLERANCE_POINTS, TOLERANCE_BY_MODE, Selection, _same_shell

ALTERNATIVE_EXTENSION_POINTS = 5      # élargissement unique de la zone de l'alternative
ECONOMY_SLOT_TOLERANCE_POINTS = 5     # fenêtre propre de la troisième place

ALTERNATIVE_TITLE = "🥈 L'alternative"
ECONOMY_TITLE = "💸 L'économie"
OTHER_OPTION_TITLE = "➕ L'autre option"
PISTE_TITLE = "🔎 Autre piste"


def mode_tolerance(mode: BudgetMode | None) -> int:
    """Tolérance du mode (la zone dans laquelle une souris reste « comparable » au match idéal)."""
    return TOLERANCE_BY_MODE.get(mode, QUALITE_PRIX_TOLERANCE_POINTS)


def _price_or_inf(score: MouseScore) -> float:
    return score.mouse.price_eur if score.mouse.price_eur is not None else float("inf")


def _best(candidates: Sequence[MouseScore]) -> MouseScore | None:
    """Le meilleur score ; à égalité, la moins chère ; à égalité encore, l'ordre du classement."""
    return max(candidates, key=lambda score: (score.total, -_price_or_inf(score))) if candidates else None


def _under(candidates: Sequence[MouseScore], ceiling: int) -> list[MouseScore]:
    """Candidats jamais mieux notés que la place du dessus : l'ordre des pourcentages est garanti."""
    return [score for score in candidates if score.total <= ceiling]


def _first(*groups: Sequence[MouseScore]) -> MouseScore:
    """Le premier élément du premier groupe non vide (préférences décroissantes ; le dernier est plein)."""
    return next(group[0] for group in groups if group)


def _alternative(ideal: MouseScore, rest: list[MouseScore], reference: int, tolerance: int) -> MouseScore | None:
    def other_shell(score: MouseScore) -> bool:
        return not _same_shell(ideal, score)

    ideal_price = _price_or_inf(ideal)
    zone = _under([score for score in rest if score.total >= reference - tolerance], ideal.total)
    distinct = [score for score in zone if other_shell(score)]
    if distinct:
        # Cas normal : une autre coque est dans la zone. La moins chère d'abord, sinon la mieux notée.
        alternative = _best([score for score in distinct if _price_or_inf(score) < ideal_price]) or _best(distinct)
    else:
        # La zone ne contient que des variantes de la coque montrée : élargissement unique, jamais vers
        # une souris à la fois moins bien notée ET plus chère ; à défaut, la variante est gardée.
        extension = _under([score for score in rest
                            if score.total >= reference - ALTERNATIVE_EXTENSION_POINTS and other_shell(score)],
                           ideal.total)
        alternative = _best([score for score in extension if _price_or_inf(score) <= ideal_price]) or _best(zone)
    if alternative is not None:
        return alternative
    # Dernier palier (« autre piste ») : la meilleure souris restante. Sous le plafond d'abord avec une
    # autre coque, puis sous le plafond quelle que soit la coque, et seulement ensuite au-dessus.
    others = [score for score in rest if other_shell(score)]
    return _best(_under(others, ideal.total)) or _best(_under(rest, ideal.total)) or _best(others)


def _third(ideal: MouseScore, alternative: MouseScore | None, rest: list[MouseScore],
           reference: int) -> MouseScore | None:
    shown = {ideal.mouse.id} | ({alternative.mouse.id} if alternative is not None else set())
    ceiling = alternative.total if alternative is not None else ideal.total

    def other_shell(score: MouseScore) -> bool:
        """Aucune des places déjà affichées ne partage sa coque avec cette souris."""
        return not _same_shell(ideal, score) and (alternative is None or not _same_shell(alternative, score))

    window = [score for score in rest if score.total >= reference - ECONOMY_SLOT_TOLERANCE_POINTS]
    # Du moins cher au plus cher (puis du mieux noté au moins bien noté), sous le plafond de la 2e place.
    candidates = _under([score for score in sorted(window, key=lambda s: (_price_or_inf(s), -s.total))
                         if score.mouse.id not in shown], ceiling)
    if candidates:
        # « L'économie » : strictement moins chère que tout ce qui est déjà à l'écran, d'une autre coque si
        # possible. Sinon « l'autre option » : la moins chère de la fenêtre, d'une autre coque si possible.
        price_ceiling = min(_price_or_inf(ideal),
                            _price_or_inf(alternative) if alternative is not None else _price_or_inf(ideal))
        cheaper = [score for score in candidates if _price_or_inf(score) < price_ceiling]
        return _first([score for score in cheaper if other_shell(score)], cheaper,
                      [score for score in candidates if other_shell(score)], candidates)
    # Dernier palier (« autre piste ») : la fenêtre est vide (budget serré, souris suivante très loin).
    remaining = [score for score in rest if score.mouse.id not in shown]
    under_ceiling = _under(remaining, ceiling)
    return _best([score for score in under_ceiling if other_shell(score)] or under_ceiling) or _best(remaining)


def result_slots(selection: Selection) -> tuple[MouseScore | None, MouseScore | None, MouseScore | None]:
    """(match idéal, alternative, troisième place), tirés du classement du mode sans le recalculer."""
    ordered = list(selection.ranked)
    if not ordered:
        return None, None, None
    ideal, rest = ordered[0], ordered[1:]
    reference = selection.reference_score if selection.reference_score is not None else ideal.total
    alternative = _alternative(ideal, rest, reference, mode_tolerance(selection.mode))
    return ideal, alternative, _third(ideal, alternative, rest, reference)


def alternative_slot_title(alternative: MouseScore, ideal: MouseScore,
                           reference: int | None = None, tolerance: int | None = None) -> str:
    """Titre de la deuxième place : « L'alternative » si elle est comparable, sinon « Autre piste ».

    Comparable = dans la zone du mode (``tolerance``), ou dans l'élargissement unique sans coûter plus
    cher que le match idéal. Sans ``reference`` ni ``tolerance`` (appel direct d'un test ou d'un outil),
    le titre reste celui de la place.
    """
    if reference is None or tolerance is None:
        return ALTERNATIVE_TITLE
    if alternative.total >= reference - tolerance:
        return ALTERNATIVE_TITLE
    if alternative.total >= reference - ALTERNATIVE_EXTENSION_POINTS \
            and _price_or_inf(alternative) <= _price_or_inf(ideal):
        return ALTERNATIVE_TITLE
    return PISTE_TITLE


def third_slot_title(economy: MouseScore, ideal: MouseScore,
                     alternative: MouseScore | None = None,
                     reference: int | None = None) -> str:
    """Titre de la troisième place : son rôle réel, dans cet ordre.

    1. « L'économie » — strictement moins chère que tout ce qui est affiché (un fait sur le prix) ;
    2. « Autre piste » — pas moins chère ET hors de sa fenêtre (plus de
       ``ECONOMY_SLOT_TOLERANCE_POINTS`` sous le meilleur score du mode) ;
    3. « L'autre option » — dans sa fenêtre, mais pas moins chère.

    Sans ``reference`` (appel direct d'un test ou d'un outil), la distinction « piste » n'est pas faite.
    """
    ceiling = _price_or_inf(ideal)
    if alternative is not None:
        ceiling = min(ceiling, _price_or_inf(alternative))
    if _price_or_inf(economy) < ceiling:
        return ECONOMY_TITLE
    if reference is not None and economy.total < reference - ECONOMY_SLOT_TOLERANCE_POINTS:
        return PISTE_TITLE
    return OTHER_OPTION_TITLE
