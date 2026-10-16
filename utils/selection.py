"""Stratégie de sélection par mode commercial (étape 3 du moteur).

Séparation en trois opérations (spécification du propriétaire, non versionnée dans ce dépôt ; voir docs/audit/AUDIT.md §2 et §5) :
1. compatibilité morphologique  -> utils/matcher.py (points sur 40, inchangés par le mode) ;
2. éligibilité                  -> statut « scored » / « pending » / « excluded » ;
3. stratégie de sélection       -> ce module : le mode choisit parmi les candidats
                                   suffisamment compatibles, jamais en modifiant le score.

Chaque mode définit :
- une TOLÉRANCE (points d'écart au meilleur score) : règle de classement PROVISOIRE, pas un seuil
  biomécanique validé ; elle est centralisée ici et couverte par tests/test_selection.py ;
- un critère de classement à l'intérieur de cette zone.

Le mode « Peu importe le prix » (2026-10-11, demande du propriétaire) renverse la logique : la forme
d'abord, sans contrainte budgétaire. Le score morphologique reste seul juge du premier rang ; à score
égal, les composants DOCUMENTÉS les plus actuels (même indice que le haut de gamme : polling ≥ 8000 Hz,
capteur haut de gamme) départagent, puis le prix le plus bas. Aucun prix connu n'est exigé.

Les pondérations de performance ne retiennent que des caractéristiques DOCUMENTÉES.
Une donnée absente compte pour zéro : cela ne signifie pas une performance inférieure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from utils.matcher import MouseScore, rank_by_compatibility
from utils.models import BudgetMode, Mouse

# Tolérances de classement (points sur 40), provisoires et configurables.
ECONOMIQUE_TOLERANCE_POINTS = 5   # plus large : on accepte une légère baisse de compatibilité pour le prix
QUALITE_PRIX_TOLERANCE_POINTS = 2
HAUT_DE_GAMME_TOLERANCE_POINTS = 2
PEU_IMPORTE_PRIX_TOLERANCE_POINTS = 2
CUSTOM_TOLERANCE_POINTS = 2

TOLERANCE_BY_MODE = {
    BudgetMode.ECONOMIQUE: ECONOMIQUE_TOLERANCE_POINTS,
    BudgetMode.QUALITE_PRIX: QUALITE_PRIX_TOLERANCE_POINTS,
    BudgetMode.HAUT_DE_GAMME: HAUT_DE_GAMME_TOLERANCE_POINTS,
    BudgetMode.PEU_IMPORTE_PRIX: PEU_IMPORTE_PRIX_TOLERANCE_POINTS,
    BudgetMode.CUSTOM: CUSTOM_TOLERANCE_POINTS,
}

# Caractéristiques de performance DOCUMENTÉES retenues pour le mode haut de gamme.
PERFORMANCE_POLLING_HZ = 8000
PERFORMANCE_SENSORS = frozenset({"PAW3950", "PAW3950 Ultra", "PAW3955", "PAW3955 Master"})
MAX_PERFORMANCE_INDEX = 2


# Classement des COMPOSANTS documentés (2026-10-11, demande du propriétaire) : il sert au
# départage du mode « Peu importe le prix », jamais à modifier un score morphologique. Les rangs
# suivent les générations annoncées par les fabricants ; les valeurs viennent du catalogue, qui
# cite la source de chacune. Une donnée absente vaut 0 : elle n'est jamais devinée.
SENSOR_TIERS = {
    "PAW3955 Master Plus": 5,
    "PAW3955 Master": 5,
    "PAW3955": 5,
    "PAW3950 Ultra": 4,
    "PAW3950": 3,
    # Capteur maison Pulsar (2026-10-12) : ses caractéristiques PUBLIÉES (32 000 dpi, 750 IPS, 50 g)
    # sont celles de la classe PAW3950 — rang aligné, aucune valeur inventée. Le classement reste un
    # départage de composants DOCUMENTÉS, jamais un score morphologique.
    "Pulsar XS-1": 3,
    "PAW3395 Ultra": 2,
    "PAW3395": 1,
}
MCU_TIERS = {
    "Nordic 54H20": 3, "Nordic nRF54H20": 3,
    "Nordic 54L15": 2, "Nordic nRF54L15": 2,
    "Nordic 54LM20": 2, "Nordic nRF54LM20": 2,
    "Nordic nRF52840": 1, "Nordic 52840": 1,
}
# MCU documentés mais non classés (puce maison ou chinoise, sans référentiel comparable publié) :
# NearLink/HiSilicon (A9 Plus), BK Custom Esports (A9 NB), Broadcom CX52850SE (VXE X3). Rang 0.
SWITCH_OPTICAL, SWITCH_MECHANICAL = 2, 1


def _switch_tier(switches: str) -> int:
    """2 = optique documenté, 1 = mécanique documenté, 0 = non renseigné (jamais deviné)."""
    text = (switches or "").lower()
    if "optique" in text or "optical" in text:
        return SWITCH_OPTICAL
    if "mécanique" in text or "mechanical" in text or "lightblade" in text or "huano" in text:
        return SWITCH_MECHANICAL
    return 0


def components_index(mouse: Mouse) -> tuple[int, int, int, int]:
    """Classement des composants documentés : capteur, MCU, switchs, fréquence (chacun 0 à 5).

    Plus le tuple est grand, plus les composants sont récents et performants — comparaison
    lexicographique : le capteur d'abord (génération), puis le MCU, puis les switchs, puis la
    fréquence. À ne pas confondre avec ``performance_index`` (mode haut de gamme, inchangé).
    """
    return (
        SENSOR_TIERS.get((mouse.sensor or "").strip(), 0),
        MCU_TIERS.get((mouse.mcu or "").strip(), 0),
        _switch_tier(mouse.switches),
        1 if mouse.polling_hz is not None and mouse.polling_hz >= PERFORMANCE_POLLING_HZ else 0,
    )


def performance_index(mouse: Mouse) -> int:
    """0 à 2 : +1 si polling ≥ 8000 Hz documenté, +1 si capteur haut de gamme documenté."""
    index = 0
    if mouse.polling_hz is not None and mouse.polling_hz >= PERFORMANCE_POLLING_HZ:
        index += 1
    if mouse.sensor in PERFORMANCE_SENSORS:
        index += 1
    return index


@dataclass(frozen=True)
class Selection:
    mode: BudgetMode | None
    ranked: tuple[MouseScore, ...]     # top N, dans l'ordre du mode
    pending: tuple[MouseScore, ...]    # candidats à vérifier (non classés)
    explanation: str                   # justification du premier choix
    pool_size: int                     # nombre de candidats dans la zone de tolérance
    reference_score: int | None        # meilleur score de référence du mode


def _same_shell(first: MouseScore, second: MouseScore) -> bool:
    """Deux souris de la même coque (mêmes variantes de couleur, de capteur ou de finition)."""
    a, b = first.mouse, second.mouse
    if a.id == b.id:
        return True
    return bool(a.shell_id) and a.shell_id == b.shell_id


def _price_key(score: MouseScore) -> float:
    return score.mouse.price_eur if score.mouse.price_eur is not None else float("inf")


def _order_for_mode(mode: BudgetMode, pool: list[MouseScore], rest: list[MouseScore], catalog_index: dict[str, int]):
    def idx(s: MouseScore) -> int:
        return catalog_index[s.mouse.id]

    if mode is BudgetMode.ECONOMIQUE:
        key = lambda s: (_price_key(s), -s.total, idx(s))
    elif mode is BudgetMode.QUALITE_PRIX:
        key = lambda s: (-(s.total / s.mouse.price_eur), -s.total, idx(s))
    elif mode is BudgetMode.HAUT_DE_GAMME:
        key = lambda s: (-performance_index(s.mouse), -s.total, idx(s))
    elif mode is BudgetMode.PEU_IMPORTE_PRIX:
        # Forme d'abord : le score reste maître ; à score égal, les composants documentés les plus
        # récents (capteur, MCU, switchs, fréquence), puis la moins chère. Le prix n'est jamais un
        # critère de premier rang.
        key = lambda s: (-s.total, tuple(-v for v in components_index(s.mouse)), _price_key(s), idx(s))
    else:  # CUSTOM : à score égal, le moins cher (ne pas dépenser le budget par défaut)
        key = lambda s: (-s.total, _price_key(s), idx(s))
    return sorted(pool, key=key) + sorted(rest, key=lambda s: (-s.total, _price_key(s), idx(s)))


def _explanation(mode: BudgetMode, top: MouseScore, pool: list[MouseScore], reference: int) -> str:
    n = len(pool)
    tol = TOLERANCE_BY_MODE[mode]
    # Fragment inséré après le critère : « … parmi les 2 souris à 2 pts ou moins du meilleur score (30/40) »
    # ou « …, seule souris dans la zone de tolérance » (phrases lisibles ; aucune règle de tri modifiée).
    zone = (
        f" parmi les {n} souris à {tol} pts ou moins du meilleur score ({reference}/40)"
        if n > 1
        else ", seule souris dans la zone de tolérance"
    )
    if mode is BudgetMode.ECONOMIQUE:
        return f"Économique : {top.mouse.label} est la moins chère{zone}."
    if mode is BudgetMode.QUALITE_PRIX:
        return (f"Rapport qualité/prix : meilleur rapport points/€{zone}. "
                "Indicateur provisoire, pas un score qualité-prix validé.")
    if mode is BudgetMode.HAUT_DE_GAMME:
        return (f"Haut de gamme : performances documentées les plus élevées ({performance_index(top.mouse)}/{MAX_PERFORMANCE_INDEX})"
                f"{zone}. Le prix n'entre pas dans le classement.")
    if mode is BudgetMode.PEU_IMPORTE_PRIX:
        return (f"Forme d'abord : {top.mouse.label} est la souris dont la forme colle le mieux à votre main{zone}. "
                "À score égal, les composants documentés les plus récents décident (capteur, MCU, switchs, fréquence), "
                "puis le prix le plus bas. "
                "Le budget ne limite jamais le choix.")
    return (f"Budget personnalisé : meilleur score conforme au budget{zone} ; "
            "à score égal, la moins chère.")


def select(
    scores: Sequence[MouseScore],
    mode: BudgetMode | None,
    top_n: int = 2,
) -> Selection:
    """Applique le mode aux candidats éligibles. Les exclus n'apparaissent nulle part."""
    catalog_index = {s.mouse.id: i for i, s in enumerate(scores)}
    pending = [s for s in scores if s.is_pending]
    eligible = [s for s in scores if s.is_scored]

    if mode is None:
        ranked = rank_by_compatibility(eligible)[:top_n]
        expl = ("Classement morphologique seul (aucun mode commercial choisi)." if ranked else "Aucune souris éligible.")
        return Selection(None, tuple(ranked), tuple(pending), expl, len(ranked), ranked[0].total if ranked else None)

    # Les modes à prix exigent un prix connu ; sinon le candidat passe en « à vérifier ».
    price_required = mode in {BudgetMode.ECONOMIQUE, BudgetMode.QUALITE_PRIX, BudgetMode.CUSTOM}
    if price_required:
        priced = [s for s in eligible if s.mouse.price_eur is not None]
        unpriced = [s for s in eligible if s.mouse.price_eur is None]
        pending = pending + unpriced
        eligible = priced

    if not eligible:
        return Selection(mode, (), tuple(pending), "Aucune souris éligible pour ce mode.", 0, None)

    reference = max(s.total for s in eligible)
    tolerance = TOLERANCE_BY_MODE[mode]
    pool = [s for s in eligible if s.total >= reference - tolerance]
    rest = [s for s in eligible if s.total < reference - tolerance]
    ordered = _order_for_mode(mode, pool, rest, catalog_index)
    ranked = tuple(ordered[:top_n])
    return Selection(
        mode=mode,
        ranked=ranked,
        pending=tuple(pending),
        explanation=_explanation(mode, ranked[0], pool, reference),
        pool_size=len(pool),
        reference_score=reference,
    )
