"""Tests unitaires du moteur de scoring (utils/matcher.py)."""
from __future__ import annotations

import dataclasses

import pytest

from config import MOUSE_DB_PATH
from utils.catalog import load_catalog
from utils.matcher import (
    MAX_SCORE,
    WIDTH_MEASUREMENT_OFFSET_MM,
    compatibility_percent,
    compute_target_ranges,
    evaluate_mouse,
    rank_mice,
    recommend,
)
from utils.models import BudgetMode, Grip, HandMeasure, Mouse


@pytest.fixture(scope="module")
def catalog():
    return {m.id: m for m in load_catalog(MOUSE_DB_PATH)}


def make_mouse(**overrides) -> Mouse:
    base = dict(
        id="test_mouse", brand="Test", model="M", price_eur=60.0, budget_tier="Qualité-Prix",
        length_mm=120.0, width_max_mm=63.0, hump_position="Mid", button_height="Mid",
        palm_grip_fit="Élevé", claw_grip_fit="Élevé", fingertip_grip_fit="Élevé",
        fit_rationale="",
    )
    base.update(overrides)
    return Mouse(**base)


# ---------------------------------------------------------------------------
# Plages cibles
# ---------------------------------------------------------------------------
def test_palm_target_ranges_for_180x90():
    r = compute_target_ranges(HandMeasure(180, 90), Grip.PALM)
    assert r.length_min == pytest.approx(71.4 + 180 * 0.2633)          # 118.794
    assert r.length_max == pytest.approx(r.length_min + 5.0)           # 123.794
    assert r.width_min == pytest.approx(48.4 + 90 * 0.08)              # 55.6
    assert r.width_max == pytest.approx(r.width_min + 4.0)             # 59.6


def test_claw_uses_same_ranges_as_palm():
    assert compute_target_ranges(HandMeasure(180, 90), Grip.CLAW) == compute_target_ranges(
        HandMeasure(180, 90), Grip.PALM
    )


def test_fingertip_has_no_minimum_length_and_other_width_constants():
    r = compute_target_ranges(HandMeasure(180, 90), Grip.FINGERTIP)
    assert r.length_min == 0.0
    assert r.length_max == pytest.approx(71.4 + 180 * 0.2633 + 5.0)
    assert r.width_min == pytest.approx(47.3 + 90 * 0.08)              # 54.5
    assert r.width_max == pytest.approx(r.width_min + 3.9)


def test_width_offset_constant_is_three_mm():
    assert WIDTH_MEASUREMENT_OFFSET_MM == 3.0


# ---------------------------------------------------------------------------
# Scénario de référence : main 180x90 mm, Palm
# ---------------------------------------------------------------------------
def test_palm_180x90_v6_breakdown(catalog):
    s = evaluate_mouse(catalog["scyrox_v6"], HandMeasure(180, 90), Grip.PALM)
    assert not s.is_excluded
    # Longueur 119.0 dans [118.79, 123.79] -> 10 ; largeur évaluée 58.0 dans [55.6, 59.6] -> 10
    # Palm Moyen -> 5 ; bosse Mid -> 5 ; boutons Mid (attendu High) -> 0
    assert s.breakdown.length_pts == 10
    assert s.breakdown.width_pts == 10
    assert s.breakdown.grip_pts == 5
    assert s.breakdown.hump_pts == 5
    assert s.breakdown.button_pts == 0
    assert s.total == 30


def test_palm_180x90_a9_plus_breakdown(catalog):
    s = evaluate_mouse(catalog["atk_a9_plus"], HandMeasure(180, 90), Grip.PALM)
    # Longueur 125.0 : écart 1.21 < 3 -> 5 ; largeur évaluée 60.5 : écart 0.9 < 2 -> 5
    assert (s.breakdown.length_pts, s.breakdown.width_pts) == (5, 5)
    assert s.breakdown.grip_pts == 10   # Élevé
    assert s.breakdown.hump_pts == 5    # Mid
    assert s.breakdown.button_pts == 0  # Mid, attendu High
    assert s.total == 25


def test_palm_180x90_x1_breakdown(catalog):
    s = evaluate_mouse(catalog["atk_x1_ultra_max"], HandMeasure(180, 90), Grip.PALM)
    # Longueur 127.0 : écart 3.21 (>= 3) -> 0 ; largeur évaluée 61.0 : écart 1.4 -> 5
    assert (s.breakdown.length_pts, s.breakdown.width_pts) == (0, 5)
    assert s.breakdown.grip_pts == 10
    assert s.total == 20


def test_palm_180x90_z1_is_kept_with_seuil_5mm(catalog):
    # ATK Z1 : largeur évaluée 63.8, écart 4.2 mm : hors bande +5 (écart < 2) mais sous le seuil d'exclusion 5 mm
    z1 = evaluate_mouse(catalog["atk_z1_ultra"], HandMeasure(180, 90), Grip.PALM)
    assert not z1.is_excluded
    assert z1.breakdown.length_pts == 10   # 122.5 dans [118.79, 123.79]
    assert z1.breakdown.width_pts == 0     # écart 4.2 mm : ni +10, ni +5 (bande < 2 mm)
    assert z1.breakdown.grip_pts == 10     # Palm Élevé
    assert z1.breakdown.hump_pts == 5      # Mid-Front -> Front/Mid
    assert z1.breakdown.button_pts == 5    # High
    assert z1.total == 30


def test_palm_180x90_excluded_mice(catalog):
    hand = HandMeasure(180, 90)
    # Scyrox V8 et ATK F1 : compatibilité Palm « Faible » -> exclusion
    assert evaluate_mouse(catalog["scyrox_v8"], hand, Grip.PALM).is_excluded
    assert evaluate_mouse(catalog["atk_f1_ultimate"], hand, Grip.PALM).is_excluded


def test_palm_180x90_ranking_without_budget(catalog):
    ranked = recommend(list(catalog.values()), HandMeasure(180, 90), Grip.PALM, top_n=5)
    # Ex æquo à 30 : Scyrox V6 et ATK Z1 (sans choix de gamme, l'ordre du catalogue départage)
    assert [s.mouse.id for s in ranked] == ["scyrox_v6", "atk_z1_ultra", "atk_a9_plus", "atk_x1_ultra_max"]
    assert [s.total for s in ranked] == [30, 30, 25, 20]


def test_palm_180x90_z1_wins_tie_when_haut_de_gamme(catalog):
    ranked = recommend(list(catalog.values()), HandMeasure(180, 90), Grip.PALM, BudgetMode.HAUT_DE_GAMME)
    assert ranked[0].mouse.id == "atk_z1_ultra" and ranked[0].total == 30
    assert ranked[1].mouse.id == "scyrox_v6"


def test_palm_180x90_v6_wins_tie_when_qualite_prix(catalog):
    ranked = recommend(list(catalog.values()), HandMeasure(180, 90), Grip.PALM, BudgetMode.QUALITE_PRIX)
    assert ranked[0].mouse.id == "scyrox_v6"


def test_compatibility_percent_rounding(catalog):
    from utils.matcher import MouseScore, ScoreBreakdown
    m = catalog["atk_z1_ultra"]
    def pct(total):
        return compatibility_percent(MouseScore(mouse=m, grip=Grip.PALM, breakdown=ScoreBreakdown(length_pts=total)))
    assert pct(40) == 100
    assert pct(35) == 88    # 87.5 -> demi vers le haut
    assert pct(30) == 75
    assert pct(25) == 63    # 62.5 -> 63
    assert pct(0) == 0


def test_max_score_is_sum_of_criteria():
    assert MAX_SCORE == 10 + 10 + 10 + 5 + 5


# ---------------------------------------------------------------------------
# Bornes et seuils
# ---------------------------------------------------------------------------
def test_length_delta_below_3_gives_5_points():
    hand = HandMeasure(180, 90)
    low = compute_target_ranges(hand, Grip.PALM).length_min
    mouse = make_mouse(length_mm=low - 2.9)  # écart 2.9
    s = evaluate_mouse(mouse, hand, Grip.PALM)
    assert s.breakdown.length_pts == 5


def test_length_delta_exactly_3_gives_zero_points():
    hand = HandMeasure(180, 90)
    low = compute_target_ranges(hand, Grip.PALM).length_min
    s = evaluate_mouse(make_mouse(length_mm=low - 3.0), hand, Grip.PALM)
    assert s.breakdown.length_pts == 0 and not s.is_excluded


def test_length_delta_above_8_excludes():
    hand = HandMeasure(180, 90)
    low = compute_target_ranges(hand, Grip.PALM).length_min
    assert evaluate_mouse(make_mouse(length_mm=low - 8.5), hand, Grip.PALM).is_excluded


def test_length_delta_exactly_8_is_not_excluded():
    hand = HandMeasure(180, 90)
    low = compute_target_ranges(hand, Grip.PALM).length_min
    assert not evaluate_mouse(make_mouse(length_mm=low - 8.0), hand, Grip.PALM).is_excluded


def test_width_delta_exactly_2_gives_zero_and_above_5_excludes():
    hand = HandMeasure(180, 90)
    r = compute_target_ranges(hand, Grip.PALM)
    # width_max_mm = largeur évaluée + 3
    at_2 = evaluate_mouse(make_mouse(width_max_mm=r.width_min - 2.0 + 3.0), hand, Grip.PALM)
    assert at_2.breakdown.width_pts == 0 and not at_2.is_excluded
    at_5 = evaluate_mouse(make_mouse(width_max_mm=r.width_max + 5.0 + 3.0), hand, Grip.PALM)
    assert not at_5.is_excluded and at_5.breakdown.width_pts == 0
    over_5 = evaluate_mouse(make_mouse(width_max_mm=r.width_max + 5.5 + 3.0), hand, Grip.PALM)
    assert over_5.is_excluded


def test_width_uses_width_max_minus_three():
    hand = HandMeasure(180, 90)
    r = compute_target_ranges(hand, Grip.PALM)
    # Largeur max brute 62.6 -> évaluée 59.6 (borne haute exacte) -> 10 pts
    s = evaluate_mouse(make_mouse(width_max_mm=r.width_max + WIDTH_MEASUREMENT_OFFSET_MM), hand, Grip.PALM)
    assert s.breakdown.width_pts == 10


def test_fingertip_length_has_no_lower_bound():
    hand = HandMeasure(180, 90)
    short = make_mouse(length_mm=60.0, fingertip_grip_fit="Élevé", button_height="Low")
    s = evaluate_mouse(short, hand, Grip.FINGERTIP)
    assert s.breakdown.length_pts == 10


# ---------------------------------------------------------------------------
# Grip, bosse et boutons
# ---------------------------------------------------------------------------
def test_grip_moyen_gives_5_and_faible_excludes():
    hand = HandMeasure(180, 90)
    assert evaluate_mouse(make_mouse(palm_grip_fit="Moyen"), hand, Grip.PALM).breakdown.grip_pts == 5
    assert evaluate_mouse(make_mouse(palm_grip_fit="Faible"), hand, Grip.PALM).is_excluded


def test_palm_hump_and_buttons_points():
    hand = HandMeasure(180, 90)
    s = evaluate_mouse(make_mouse(hump_position="Front", button_height="High"), hand, Grip.PALM)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (5, 5)
    s = evaluate_mouse(make_mouse(hump_position="Rear", button_height="Low"), hand, Grip.PALM)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (0, 0)


def test_claw_hump_and_buttons_points():
    hand = HandMeasure(180, 90)
    for hump in ("Mid", "Rear"):
        for buttons in ("Low", "Mid"):
            s = evaluate_mouse(make_mouse(hump_position=hump, button_height=buttons), hand, Grip.CLAW)
            assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (5, 5)
    s = evaluate_mouse(make_mouse(hump_position="Front", button_height="High"), hand, Grip.CLAW)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (0, 0)


def test_fingertip_ignores_hump_and_rewards_low_buttons():
    hand = HandMeasure(180, 90)
    s = evaluate_mouse(make_mouse(hump_position="Front", button_height="Low"), hand, Grip.FINGERTIP)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (0, 10)
    s = evaluate_mouse(make_mouse(hump_position="Rear", button_height="Mid"), hand, Grip.FINGERTIP)
    assert s.breakdown.button_pts == 0


# ---------------------------------------------------------------------------
# Budget et tri
# ---------------------------------------------------------------------------
def test_custom_budget_excludes_mice_above_max():
    hand = HandMeasure(180, 90)
    s = evaluate_mouse(make_mouse(price_eur=80.0), hand, Grip.PALM, BudgetMode.CUSTOM, 75.0)
    assert s.is_excluded and "budget" in s.excluded_reason
    ok = evaluate_mouse(make_mouse(price_eur=75.0), hand, Grip.PALM, BudgetMode.CUSTOM, 75.0)
    assert not ok.is_excluded


def test_custom_budget_requires_amount():
    with pytest.raises(ValueError):
        evaluate_mouse(make_mouse(), HandMeasure(180, 90), Grip.PALM, BudgetMode.CUSTOM, None)


def test_non_custom_budget_does_not_filter_price():
    hand = HandMeasure(180, 90)
    s = evaluate_mouse(make_mouse(price_eur=500.0), hand, Grip.PALM, BudgetMode.ECONOMIQUE, 10.0)
    assert not s.is_excluded


def test_tie_is_broken_by_budget_tier_match():
    hand = HandMeasure(180, 90)
    a = evaluate_mouse(make_mouse(id="a", budget_tier="Économique"), hand, Grip.PALM)
    b = evaluate_mouse(make_mouse(id="b", budget_tier="Qualité-Prix"), hand, Grip.PALM)
    assert a.total == b.total
    assert [s.mouse.id for s in rank_mice([a, b], BudgetMode.QUALITE_PRIX)] == ["b", "a"]
    assert [s.mouse.id for s in rank_mice([a, b], BudgetMode.ECONOMIQUE)] == ["a", "b"]


def test_higher_score_beats_tier_match():
    hand = HandMeasure(180, 90)
    high = evaluate_mouse(make_mouse(id="high", budget_tier="Économique", hump_position="Mid", button_height="High"), hand, Grip.PALM)
    low = evaluate_mouse(make_mouse(id="low", budget_tier="Haut de Gamme", button_height="Mid"), hand, Grip.PALM)
    ranked = rank_mice([low, high], BudgetMode.HAUT_DE_GAMME)
    assert ranked[0].mouse.id == "high"


def test_recommend_returns_empty_when_everything_excluded():
    hand = HandMeasure(180, 90)
    assert recommend([make_mouse(palm_grip_fit="Faible")], hand, Grip.PALM) == []


def test_invalid_hand_measure_is_rejected():
    with pytest.raises(ValueError):
        HandMeasure(0, 90)


def test_catalog_mouse_is_frozen():
    m = make_mouse()
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.price_eur = 1.0  # type: ignore[misc]
