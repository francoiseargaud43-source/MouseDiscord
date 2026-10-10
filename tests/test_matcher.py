"""Tests unitaires du moteur de compatibilité morphologique (utils/matcher.py).

Les valeurs de référence (V6 30, Z1 30, A9 Plus 25, X1 20 pour 180×90 Palm) sont celles du
cahier des charges initial : elles servent de non-régression. La largeur du Z1 passe à 0 point
car l'écart 4.2 mm est dans la zone 2–5 mm (seuil d'exclusion à 5 mm, pas de bande +5).
"""
from __future__ import annotations

import dataclasses

import pytest

from config import MOUSE_DB_PATH
from utils.catalog import load_catalog
from utils.matcher import (
    GRIP_WIDTH_ESTIMATE_OFFSET_MM,
    MAX_SCORE,
    STATUS_EXCLUDED,
    STATUS_PENDING,
    STATUS_SCORED,
    WIDTH_MEASUREMENT_OFFSET_MM,
    compatibility_percent,
    compute_target_ranges,
    evaluate_mouse,
    grip_width_for_scoring,
    rank_by_compatibility,
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
        fit_rationale="", dimension_status="verified", fit_status="owner_spec",
    )
    base.update(overrides)
    return Mouse(**base)


HAND = HandMeasure(180, 90)


# ---------------------------------------------------------------------------
# Plages cibles et constantes
# ---------------------------------------------------------------------------
def test_palm_target_ranges_for_180x90():
    r = compute_target_ranges(HandMeasure(180, 90), Grip.PALM)
    assert r.length_min == pytest.approx(71.4 + 180 * 0.2633)          # 118.794
    assert r.length_max == pytest.approx(r.length_min + 5.0)
    assert r.width_min == pytest.approx(48.4 + 90 * 0.08)              # 55.6
    assert r.width_max == pytest.approx(r.width_min + 4.0)             # 59.6


def test_claw_uses_same_ranges_as_palm():
    assert compute_target_ranges(HAND, Grip.CLAW) == compute_target_ranges(HAND, Grip.PALM)


def test_fingertip_has_no_minimum_length_and_other_width_constants():
    r = compute_target_ranges(HAND, Grip.FINGERTIP)
    assert r.length_min == 0.0
    assert r.length_max == pytest.approx(71.4 + 180 * 0.2633 + 5.0)
    assert r.width_min == pytest.approx(47.3 + 90 * 0.08)              # 54.5
    assert r.width_max == pytest.approx(r.width_min + 3.9)


def test_width_offset_constant_is_three_mm():
    assert GRIP_WIDTH_ESTIMATE_OFFSET_MM == 3.0
    assert WIDTH_MEASUREMENT_OFFSET_MM == GRIP_WIDTH_ESTIMATE_OFFSET_MM


def test_max_score_is_sum_of_criteria():
    assert MAX_SCORE == 10 + 10 + 10 + 5 + 5


# ---------------------------------------------------------------------------
# Scénario de référence : main 180x90 mm, Palm (non-régression)
# ---------------------------------------------------------------------------
def test_palm_180x90_v6_breakdown(catalog):
    s = evaluate_mouse(catalog["scyrox_v6"], HAND, Grip.PALM)
    assert s.is_scored
    assert (s.breakdown.length_pts, s.breakdown.width_pts) == (10, 10)
    assert s.breakdown.grip_pts == 5 and s.breakdown.hump_pts == 5
    assert s.breakdown.button_pts == 0          # Mid, attendu High
    assert s.total == 30


def test_palm_180x90_a9_plus_breakdown(catalog):
    s = evaluate_mouse(catalog["atk_a9_plus"], HAND, Grip.PALM)
    assert (s.breakdown.length_pts, s.breakdown.width_pts) == (5, 5)
    assert (s.breakdown.grip_pts, s.breakdown.hump_pts, s.breakdown.button_pts) == (10, 5, 0)
    assert s.total == 25


def test_palm_180x90_x1_breakdown(catalog):
    s = evaluate_mouse(catalog["atk_x1_ultra_max"], HAND, Grip.PALM)
    assert (s.breakdown.length_pts, s.breakdown.width_pts) == (0, 5)
    assert s.breakdown.grip_pts == 10
    assert s.total == 20


def test_palm_180x90_z1_is_kept_with_seuil_5mm(catalog):
    z1 = evaluate_mouse(catalog["atk_z1_ultra"], HAND, Grip.PALM)
    assert z1.is_scored
    assert z1.breakdown.length_pts == 10     # 122.5 dans [118.79, 123.79]
    assert z1.breakdown.width_pts == 0       # écart 4.2 mm : ni +10 ni +5 (bande < 2 mm)
    assert z1.breakdown.grip_pts == 10
    assert z1.breakdown.hump_pts == 5        # Mid-Front -> Front/Mid
    assert z1.breakdown.button_pts == 5      # High
    assert z1.total == 30


def test_palm_180x90_excluded_mice(catalog):
    assert evaluate_mouse(catalog["scyrox_v8"], HAND, Grip.PALM).is_excluded
    assert evaluate_mouse(catalog["atk_f1_ultimate"], HAND, Grip.PALM).is_excluded


def test_palm_180x90_ranking_by_compatibility(catalog):
    scores = [evaluate_mouse(m, HAND, Grip.PALM) for m in catalog.values()]
    ranked = rank_by_compatibility(scores)
    # Ex æquo à 30 : l'ordre du catalogue départage (V6 avant Z1)
    assert [s.mouse.id for s in ranked][:4] == ["scyrox_v6", "atk_z1_ultra", "atk_a9_plus", "atk_x1_ultra_max"]
    assert [s.total for s in ranked][:4] == [30, 30, 25, 20]


def test_compatibility_percent_rounding(catalog):
    from utils.matcher import MouseScore, ScoreBreakdown

    def pct(total):
        return compatibility_percent(MouseScore(mouse=catalog["atk_z1_ultra"], grip=Grip.PALM,
                                                breakdown=ScoreBreakdown(length_pts=total)))
    assert pct(40) == 100
    assert pct(35) == 88    # 87.5 -> vers le haut
    assert pct(30) == 75
    assert pct(25) == 63    # 62.5 -> 63
    assert pct(0) == 0


# ---------------------------------------------------------------------------
# Largeur de prise : mesurée vs estimée
# ---------------------------------------------------------------------------
def test_estimated_width_is_used_without_measure():
    m = make_mouse(width_max_mm=63.0, grip_width_mm=None)
    assert grip_width_for_scoring(m) == (60.0, "estimated")


def test_measured_grip_width_replaces_estimate():
    m = make_mouse(width_max_mm=63.0, grip_width_mm=59.0)
    assert grip_width_for_scoring(m) == (59.0, "measured")
    s = evaluate_mouse(m, HAND, Grip.PALM)
    assert s.width_source == "measured" and s.width_used_mm == 59.0


def test_confidence_levels():
    assert evaluate_mouse(make_mouse(), HAND, Grip.PALM).confidence == "moyenne"
    assert evaluate_mouse(make_mouse(grip_width_mm=60.0), HAND, Grip.PALM).confidence == "élevée"
    assert evaluate_mouse(make_mouse(dimension_status="single_source"), HAND, Grip.PALM).confidence == "faible"
    assert evaluate_mouse(make_mouse(fit_status="unverified"), HAND, Grip.PALM).confidence == "faible"


# ---------------------------------------------------------------------------
# Statuts : scored / pending / excluded
# ---------------------------------------------------------------------------
def test_unknown_grip_makes_candidate_pending_not_scored():
    s = evaluate_mouse(make_mouse(palm_grip_fit="Inconnu"), HAND, Grip.PALM)
    assert s.status == STATUS_PENDING
    assert s.is_pending and not s.is_scored
    assert s.computable_max == 30  # 10 longueur + 10 largeur + 10 (grip non calculable, exclu du max)
    assert any("Palm" in m for m in s.missing)
    assert s.breakdown.grip_pts == 0


def test_unknown_buttons_make_candidate_pending():
    s = evaluate_mouse(make_mouse(button_height="Inconnu"), HAND, Grip.PALM)
    assert s.status == STATUS_PENDING
    assert "hauteur des boutons non vérifiée" in s.missing


def test_unknown_hump_is_pending_except_in_fingertip():
    assert evaluate_mouse(make_mouse(hump_position="Inconnu"), HAND, Grip.PALM).is_pending
    s = evaluate_mouse(make_mouse(hump_position="Inconnu", button_height="Low"), HAND, Grip.FINGERTIP)
    assert s.is_scored and s.breakdown.hump_pts == 0


def test_conflicting_dimensions_are_pending_even_when_values_fit():
    s = evaluate_mouse(make_mouse(dimension_status="conflicting"), HAND, Grip.PALM)
    assert s.is_pending
    assert "dimensions en conflit entre sources" in s.missing


def test_missing_length_is_pending_with_width_points_still_reported():
    s = evaluate_mouse(make_mouse(length_mm=None), HAND, Grip.PALM)
    assert s.is_pending and "longueur non vérifiée" in s.missing
    # largeur évaluée 60.0 : écart 0.4 mm à la plage [55.6, 59.6] -> 5 pts
    assert s.breakdown.width_pts == 5 and s.breakdown.length_pts == 0


def test_excluded_wins_over_pending():
    s = evaluate_mouse(make_mouse(palm_grip_fit="Faible", button_height="Inconnu"), HAND, Grip.PALM)
    assert s.status == STATUS_EXCLUDED


def test_excluded_status_has_no_total_and_no_confidence():
    s = evaluate_mouse(make_mouse(palm_grip_fit="Faible"), HAND, Grip.PALM)
    assert s.total == 0 and s.confidence is None and s.excluded_reason


# ---------------------------------------------------------------------------
# Bornes et seuils (stricts, arrondis à 6 décimales)
# ---------------------------------------------------------------------------
def test_length_delta_below_3_gives_5_points():
    low = compute_target_ranges(HAND, Grip.PALM).length_min
    assert evaluate_mouse(make_mouse(length_mm=low - 2.9), HAND, Grip.PALM).breakdown.length_pts == 5


def test_length_delta_exactly_3_gives_zero_points():
    low = compute_target_ranges(HAND, Grip.PALM).length_min
    s = evaluate_mouse(make_mouse(length_mm=low - 3.0), HAND, Grip.PALM)
    assert s.breakdown.length_pts == 0 and not s.is_excluded


def test_length_delta_above_8_excludes():
    low = compute_target_ranges(HAND, Grip.PALM).length_min
    assert evaluate_mouse(make_mouse(length_mm=low - 8.5), HAND, Grip.PALM).is_excluded


def test_length_delta_exactly_8_is_not_excluded():
    low = compute_target_ranges(HAND, Grip.PALM).length_min
    assert not evaluate_mouse(make_mouse(length_mm=low - 8.0), HAND, Grip.PALM).is_excluded


def test_width_exact_boundaries_with_estimate():
    r = compute_target_ranges(HAND, Grip.PALM)
    # largeur évaluée = width_max - 3 ; écart exactement 2 -> 0 pt, pas exclu
    at_2 = evaluate_mouse(make_mouse(width_max_mm=r.width_min - 2.0 + 3.0), HAND, Grip.PALM)
    assert at_2.breakdown.width_pts == 0 and not at_2.is_excluded
    # écart exactement 5 -> non exclu
    at_5 = evaluate_mouse(make_mouse(width_max_mm=r.width_max + 5.0 + 3.0), HAND, Grip.PALM)
    assert not at_5.is_excluded
    # écart 5.5 -> exclu
    assert evaluate_mouse(make_mouse(width_max_mm=r.width_max + 5.5 + 3.0), HAND, Grip.PALM).is_excluded


def test_width_delta_just_under_2_gives_5_points():
    r = compute_target_ranges(HAND, Grip.PALM)
    s = evaluate_mouse(make_mouse(grip_width_mm=r.width_max + 1.9), HAND, Grip.PALM)
    assert s.breakdown.width_pts == 5


def test_width_uses_width_max_minus_three():
    r = compute_target_ranges(HAND, Grip.PALM)
    s = evaluate_mouse(make_mouse(width_max_mm=r.width_max + WIDTH_MEASUREMENT_OFFSET_MM), HAND, Grip.PALM)
    assert s.breakdown.width_pts == 10


def test_fingertip_length_has_no_lower_bound():
    short = make_mouse(length_mm=60.0, fingertip_grip_fit="Élevé", button_height="Low")
    assert evaluate_mouse(short, HAND, Grip.FINGERTIP).breakdown.length_pts == 10


def test_decimal_boundary_is_not_misclassified_by_float_noise():
    """Un écart exactement égal à 3.0 mm reste à 0 point (seuil strict), même avec un bruit flottant."""
    low = compute_target_ranges(HAND, Grip.PALM).length_min
    exact = evaluate_mouse(make_mouse(length_mm=low - 3.0), HAND, Grip.PALM)
    noisy = evaluate_mouse(make_mouse(length_mm=low - 3.0 + 1e-12), HAND, Grip.PALM)
    assert exact.breakdown.length_pts == 0 and noisy.breakdown.length_pts == 0


# ---------------------------------------------------------------------------
# Grip, bosse et boutons (règles centralisées)
# ---------------------------------------------------------------------------
def test_grip_moyen_gives_5_and_faible_excludes():
    assert evaluate_mouse(make_mouse(palm_grip_fit="Moyen"), HAND, Grip.PALM).breakdown.grip_pts == 5
    assert evaluate_mouse(make_mouse(palm_grip_fit="Faible"), HAND, Grip.PALM).is_excluded


def test_palm_hump_and_buttons_points():
    s = evaluate_mouse(make_mouse(hump_position="Front", button_height="High"), HAND, Grip.PALM)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (5, 5)
    s = evaluate_mouse(make_mouse(hump_position="Rear", button_height="Low"), HAND, Grip.PALM)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (0, 0)


def test_claw_hump_and_buttons_points():
    for hump in ("Mid", "Rear"):
        for buttons in ("Low", "Mid"):
            s = evaluate_mouse(make_mouse(hump_position=hump, button_height=buttons), HAND, Grip.CLAW)
            assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (5, 5)
    s = evaluate_mouse(make_mouse(hump_position="Front", button_height="High"), HAND, Grip.CLAW)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (0, 0)


def test_fingertip_ignores_hump_and_rewards_low_buttons():
    s = evaluate_mouse(make_mouse(hump_position="Front", button_height="Low"), HAND, Grip.FINGERTIP)
    assert (s.breakdown.hump_pts, s.breakdown.button_pts) == (0, 10)
    s = evaluate_mouse(make_mouse(hump_position="Rear", button_height="Mid"), HAND, Grip.FINGERTIP)
    assert s.breakdown.button_pts == 0


def test_hump_compound_label_matches_any_ideal_token():
    # « Mid-Front » contient « Front » et « Mid » : adapté en Palm, pas en Fingertip (ignoré)
    assert evaluate_mouse(make_mouse(hump_position="Mid-Front"), HAND, Grip.PALM).breakdown.hump_pts == 5
    assert evaluate_mouse(make_mouse(hump_position="Mid-Rear"), HAND, Grip.PALM).breakdown.hump_pts == 5


# ---------------------------------------------------------------------------
# Budget personnalisé (filtre éliminatoire)
# ---------------------------------------------------------------------------
def test_custom_budget_excludes_mice_above_max():
    s = evaluate_mouse(make_mouse(price_eur=80.0), HAND, Grip.PALM, BudgetMode.CUSTOM, 75.0)
    assert s.is_excluded and "budget" in s.excluded_reason
    assert not evaluate_mouse(make_mouse(price_eur=75.0), HAND, Grip.PALM, BudgetMode.CUSTOM, 75.0).is_excluded


def test_custom_budget_requires_amount():
    with pytest.raises(ValueError):
        evaluate_mouse(make_mouse(), HAND, Grip.PALM, BudgetMode.CUSTOM, None)


def test_custom_budget_unknown_price_is_not_excluded_by_matcher():
    # Un prix inconnu n'est pas une exclusion morphologique : la sélection le place à vérifier.
    s = evaluate_mouse(make_mouse(price_eur=None), HAND, Grip.PALM, BudgetMode.CUSTOM, 75.0)
    assert not s.is_excluded


def test_non_custom_budget_does_not_filter_price():
    assert not evaluate_mouse(make_mouse(price_eur=500.0), HAND, Grip.PALM, BudgetMode.ECONOMIQUE, 10.0).is_excluded


def test_invalid_hand_measure_is_rejected():
    with pytest.raises(ValueError):
        HandMeasure(0, 90)


def test_catalog_mouse_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_mouse().price_eur = 1.0  # type: ignore[misc]


def test_status_constants():
    assert {STATUS_SCORED, STATUS_PENDING, STATUS_EXCLUDED} == {"scored", "pending", "excluded"}
