"""Stratégie de sélection par mode (utils/selection.py).

Invariant commun : un mode ne change jamais le score morphologique ; il ne choisit que parmi les
candidats « scored » dans la zone de tolérance du mode, et ne classe jamais un candidat « pending ».
"""
from __future__ import annotations

import pytest

from utils.matcher import evaluate_mouse
from utils.models import BudgetMode, Grip, HandMeasure, Mouse
from utils.selection import (
    ECONOMIQUE_TOLERANCE_POINTS,
    HAUT_DE_GAMME_TOLERANCE_POINTS,
    QUALITE_PRIX_TOLERANCE_POINTS,
    TOLERANCE_BY_MODE,
    performance_index,
    select,
)

HAND = HandMeasure(180, 90)


def mouse(mid: str, price, **kw) -> Mouse:
    base = dict(
        id=mid, brand="T", model=mid, price_eur=price, budget_tier="Qualité-Prix",
        length_mm=120.0, width_max_mm=63.0, hump_position="Mid", button_height="Mid",
        palm_grip_fit="Élevé", claw_grip_fit="Élevé", fingertip_grip_fit="Élevé",
        fit_rationale="", dimension_status="verified", fit_status="owner_spec",
    )
    base.update(kw)
    return Mouse(**base)


def scored(m: Mouse, budget=None, max_budget=None):
    return evaluate_mouse(m, HAND, Grip.PALM, budget, max_budget)


def test_tolerances_are_documented_constants():
    assert TOLERANCE_BY_MODE[BudgetMode.ECONOMIQUE] == ECONOMIQUE_TOLERANCE_POINTS == 5
    assert TOLERANCE_BY_MODE[BudgetMode.QUALITE_PRIX] == QUALITE_PRIX_TOLERANCE_POINTS == 2
    assert TOLERANCE_BY_MODE[BudgetMode.HAUT_DE_GAMME] == HAUT_DE_GAMME_TOLERANCE_POINTS == 2


def test_no_mode_is_pure_compatibility_ranking():
    best = mouse("best", 90.0, hump_position="Front", button_height="High")   # 30 pts
    cheap = mouse("cheap", 20.0, hump_position="Rear", button_height="Low")   # 20 pts
    scores = [scored(best), scored(cheap)]
    sel = select(scores, None)
    assert [s.mouse.id for s in sel.ranked] == ["best", "cheap"]


def test_economique_picks_cheapest_within_5_points():
    best = mouse("best", 90.0, hump_position="Front", button_height="High")    # 30
    close = mouse("close", 45.0, hump_position="Front", button_height="Mid")   # 25 (écart 5, inclus)
    far = mouse("far", 10.0, hump_position="Rear", button_height="Low")        # 20 (hors zone)
    sel = select([scored(best), scored(close), scored(far)], BudgetMode.ECONOMIQUE)
    assert sel.ranked[0].mouse.id == "close"
    assert sel.pool_size == 2
    assert [s.mouse.id for s in sel.ranked] == ["close", "best"]


def test_economique_boundary_is_inclusive_at_tolerance():
    best = mouse("best", 90.0, hump_position="Front", button_height="High")    # 30
    edge = mouse("edge", 45.0, hump_position="Front", button_height="Mid")     # exactement 25
    just_out = mouse("out", 10.0, hump_position="Rear", button_height="Low")   # 20 : 10 pts de moins
    sel = select([scored(best), scored(edge), scored(just_out)], BudgetMode.ECONOMIQUE)
    assert sel.ranked[0].mouse.id == "edge"


def test_qualite_prix_keeps_only_candidates_within_2_points():
    a = mouse("a", 100.0, hump_position="Front", button_height="High")        # 30 pts
    b = mouse("b", 60.0, hump_position="Front", button_height="Mid")          # 25 pts : hors zone (écart 5)
    sel = select([scored(a), scored(b)], BudgetMode.QUALITE_PRIX)
    assert sel.pool_size == 1 and sel.ranked[0].mouse.id == "a"


def test_qualite_prix_uses_ratio_when_several_in_zone():
    a = mouse("a", 100.0, hump_position="Front", button_height="High")        # 30 pts, 0.30/€
    b = mouse("b", 50.0, hump_position="Front", button_height="High",
              palm_grip_fit="Élevé", length_mm=119.0)                         # 30 pts, 0.60/€
    sel = select([scored(a), scored(b)], BudgetMode.QUALITE_PRIX)
    assert sel.ranked[0].mouse.id == "b"


def test_haut_de_gamme_ignores_price_and_uses_documented_performance():
    cheap_fast = mouse("cheap_fast", 30.0, hump_position="Front", button_height="High",
                       polling_hz=8000, sensor="PAW3950 Ultra")               # 30 pts, index 2
    pricey_slow = mouse("pricey_slow", 150.0, hump_position="Front", button_height="High")  # 30, index 0
    sel = select([scored(pricey_slow), scored(cheap_fast)], BudgetMode.HAUT_DE_GAMME)
    assert sel.ranked[0].mouse.id == "cheap_fast"


def test_haut_de_gamme_missing_performance_counts_zero_not_negative():
    assert performance_index(mouse("x", 10.0)) == 0
    assert performance_index(mouse("y", 10.0, polling_hz=8000, sensor="PAW3950")) == 2
    assert performance_index(mouse("z", 10.0, polling_hz=1000, sensor="PAW3395")) == 0


def test_custom_budget_picks_best_score_then_cheapest():
    a = scored(mouse("a", 70.0, hump_position="Front", button_height="High"), BudgetMode.CUSTOM, 75.0)  # 30
    b = scored(mouse("b", 40.0, hump_position="Front", button_height="High"), BudgetMode.CUSTOM, 75.0)  # 30
    sel = select([a, b], BudgetMode.CUSTOM)
    assert sel.ranked[0].mouse.id == "b"  # même score : la moins chère


def test_unknown_price_never_recommended_in_price_modes():
    priced = mouse("priced", 50.0, hump_position="Mid", button_height="Mid")
    unpriced = mouse("unpriced", None, hump_position="Front", button_height="High")  # meilleur score
    for mode in (BudgetMode.ECONOMIQUE, BudgetMode.QUALITE_PRIX, BudgetMode.CUSTOM):
        sel = select([scored(priced, mode, 100.0), scored(unpriced, mode, 100.0)], mode)
        assert all(s.mouse.id != "unpriced" for s in sel.ranked)
        assert "unpriced" in [s.mouse.id for s in sel.pending]


def test_unknown_price_is_allowed_for_haut_de_gamme():
    unpriced = mouse("unpriced", None, hump_position="Front", button_height="High", polling_hz=8000)
    sel = select([scored(unpriced)], BudgetMode.HAUT_DE_GAMME)
    assert sel.ranked and sel.ranked[0].mouse.id == "unpriced"


def test_pending_candidates_are_never_ranked_in_any_mode():
    pend = mouse("pend", 10.0, palm_grip_fit="Inconnu", hump_position="Front", button_height="High")
    ok = mouse("ok", 60.0, hump_position="Mid", button_height="Mid")
    scores = [scored(pend), scored(ok)]
    for mode in (None, BudgetMode.ECONOMIQUE, BudgetMode.QUALITE_PRIX, BudgetMode.HAUT_DE_GAMME):
        sel = select(scores, mode)
        assert "pend" not in [s.mouse.id for s in sel.ranked]
        assert "pend" in [s.mouse.id for s in sel.pending]


def test_excluded_candidates_are_not_listed_anywhere():
    bad = mouse("bad", 10.0, palm_grip_fit="Faible")
    sel = select([scored(bad), scored(mouse("ok", 60.0))], BudgetMode.ECONOMIQUE)
    assert "bad" not in [s.mouse.id for s in sel.ranked + sel.pending]


def test_modes_can_disagree_on_top_choice():
    best = mouse("best", 100.0, hump_position="Front", button_height="High")     # 30, 0.30/€
    cheap = mouse("cheap", 35.0, hump_position="Front", button_height="Mid")     # 25 : dans la zone économique
    scores = [scored(best), scored(cheap)]
    assert select(scores, BudgetMode.ECONOMIQUE).ranked[0].mouse.id == "cheap"
    assert select(scores, BudgetMode.QUALITE_PRIX).ranked[0].mouse.id == "best"


def test_no_eligible_candidate_returns_empty_selection():
    sel = select([scored(mouse("bad", 10.0, palm_grip_fit="Faible"))], BudgetMode.ECONOMIQUE)
    assert sel.ranked == () and sel.explanation


def test_explanation_mentions_mode_and_tolerance():
    sel = select([scored(mouse("a", 40.0)), scored(mouse("b", 50.0))], BudgetMode.ECONOMIQUE)
    assert "moins chère" in sel.explanation and "5 pts" in sel.explanation


@pytest.mark.parametrize("mode", list(BudgetMode))
def test_top_choice_is_always_within_tolerance_of_reference(mode):
    scores = [
        scored(mouse("best", 100.0, hump_position="Front", button_height="High", polling_hz=8000)),
        scored(mouse("mid", 40.0, hump_position="Front", button_height="Mid")),
        scored(mouse("low", 5.0, hump_position="Rear", button_height="Low")),
    ]
    budget = 200.0 if mode is BudgetMode.CUSTOM else None
    if mode is BudgetMode.CUSTOM:
        scores = [scored(s.mouse, mode, budget) for s in scores]
    sel = select(scores, mode)
    assert sel.ranked
    assert sel.ranked[0].total >= sel.reference_score - TOLERANCE_BY_MODE[mode]
