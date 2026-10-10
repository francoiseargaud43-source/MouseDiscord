"""Moteur de recommandation Mouse Shape Finder.

Pour une main de longueur L et de largeur W (mm) et un grip donné, on calcule
des plages cibles, puis on attribue des points sur 40 (cf. README, section Scoring).
Aucune dépendance Discord ici : module pur, entièrement testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from utils.models import BudgetMode, Grip, HandMeasure, Mouse

# ---------------------------------------------------------------------------
# A. Équations de base (plages idéales)
# ---------------------------------------------------------------------------
LENGTH_BASE_MM = 71.4
LENGTH_SLOPE = 0.2633
LENGTH_SPAN_MM = 5.0  # Cible_Longueur_Max = Cible_Longueur_Min + 5 (Palm/Claw) ; +5 au-dessus du min (Fingertip)

WIDTH_BASE_PALM_CLAW_MM = 48.4
WIDTH_BASE_FINGERTIP_MM = 47.3
WIDTH_SLOPE = 0.08
WIDTH_SPAN_PALM_CLAW_MM = 4.0
WIDTH_SPAN_FINGERTIP_MM = 3.9

# ---------------------------------------------------------------------------
# B. Ajustement technique de la largeur
# ---------------------------------------------------------------------------
WIDTH_MEASUREMENT_OFFSET_MM = 3.0  # largeur_evaluee = width_max_mm - 3.0

# ---------------------------------------------------------------------------
# C. Scoring
# ---------------------------------------------------------------------------
MAX_SCORE = 40

LENGTH_PTS_IN_RANGE = 10
LENGTH_PTS_NEAR = 5
LENGTH_NEAR_DELTA_MM = 3.0      # delta < 3 mm -> +5
LENGTH_EXCLUDE_DELTA_MM = 8.0   # delta > 8 mm -> exclusion

WIDTH_PTS_IN_RANGE = 10
WIDTH_PTS_NEAR = 5
WIDTH_NEAR_DELTA_MM = 2.0       # delta < 2 mm -> +5
WIDTH_EXCLUDE_DELTA_MM = 4.0    # delta > 4 mm -> exclusion

GRIP_POINTS = {"Élevé": 10, "Moyen": 5}  # "Faible" -> exclusion
GRIP_EXCLUDED_FIT = "Faible"

HUMP_POINTS = 5
HUMP_IDEAL = {
    Grip.PALM: frozenset({"Front", "Mid"}),
    Grip.CLAW: frozenset({"Mid", "Rear"}),
}  # Fingertip : bosse ignorée

BUTTON_POINTS = {Grip.PALM: 5, Grip.CLAW: 5, Grip.FINGERTIP: 10}
BUTTON_IDEAL = {
    Grip.PALM: frozenset({"High"}),
    Grip.CLAW: frozenset({"Low", "Mid"}),
    Grip.FINGERTIP: frozenset({"Low"}),
}


@dataclass(frozen=True)
class TargetRanges:
    length_min: float
    length_max: float
    width_min: float
    width_max: float


@dataclass(frozen=True)
class ScoreBreakdown:
    length_pts: int = 0
    width_pts: int = 0
    grip_pts: int = 0
    hump_pts: int = 0
    button_pts: int = 0

    @property
    def total(self) -> int:
        return self.length_pts + self.width_pts + self.grip_pts + self.hump_pts + self.button_pts


@dataclass(frozen=True)
class MouseScore:
    mouse: Mouse
    grip: Grip
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    details: tuple[str, ...] = ()
    excluded_reason: str | None = None

    @property
    def is_excluded(self) -> bool:
        return self.excluded_reason is not None

    @property
    def total(self) -> int:
        return 0 if self.is_excluded else self.breakdown.total


def compute_target_ranges(hand: HandMeasure, grip: Grip) -> TargetRanges:
    length_min_base = LENGTH_BASE_MM + hand.length_mm * LENGTH_SLOPE
    length_max = length_min_base + LENGTH_SPAN_MM
    if grip is Grip.FINGERTIP:
        length_min = 0.0  # pas de minimum en Fingertip
        width_min = WIDTH_BASE_FINGERTIP_MM + hand.width_mm * WIDTH_SLOPE
        width_span = WIDTH_SPAN_FINGERTIP_MM
    else:
        length_min = length_min_base
        width_min = WIDTH_BASE_PALM_CLAW_MM + hand.width_mm * WIDTH_SLOPE
        width_span = WIDTH_SPAN_PALM_CLAW_MM
    return TargetRanges(length_min, length_max, width_min, width_min + width_span)


def _distance_outside(value: float, low: float, high: float) -> float:
    """0 si value est dans [low, high], sinon l'écart à la plage."""
    if value < low:
        return low - value
    if value > high:
        return value - high
    return 0.0


def _proximity_points(delta: float, in_pts: int, near_pts: int, near_threshold: float) -> int:
    if delta == 0.0:
        return in_pts
    if delta < near_threshold:
        return near_pts
    return 0


def _ecart_text(delta: float) -> str:
    return "dans la plage" if delta == 0.0 else f"écart {delta:.1f} mm"


def _excluded(mouse: Mouse, grip: Grip, reason: str) -> MouseScore:
    return MouseScore(mouse=mouse, grip=grip, excluded_reason=reason)


def evaluate_mouse(
    mouse: Mouse,
    hand: HandMeasure,
    grip: Grip,
    budget_mode: BudgetMode | None = None,
    max_budget_eur: float | None = None,
) -> MouseScore:
    """Score une souris sur 40 points, ou la marque comme exclue (score 0)."""
    # Filtre éliminatoire budget
    if budget_mode is BudgetMode.CUSTOM:
        if max_budget_eur is None:
            raise ValueError("max_budget_eur est requis pour le mode Budget Personnalisé.")
        if mouse.price_eur > max_budget_eur:
            return _excluded(
                mouse, grip,
                f"Prix {mouse.price_eur:.2f} € au-dessus du budget maximal {max_budget_eur:.2f} €",
            )

    ranges = compute_target_ranges(hand, grip)
    details: list[str] = []

    # --- Longueur -----------------------------------------------------------
    len_delta = _distance_outside(mouse.length_mm, ranges.length_min, ranges.length_max)
    if len_delta > LENGTH_EXCLUDE_DELTA_MM:
        return _excluded(mouse, grip, f"Longueur hors plage de {len_delta:.1f} mm (> {LENGTH_EXCLUDE_DELTA_MM:g} mm)")
    length_pts = _proximity_points(len_delta, LENGTH_PTS_IN_RANGE, LENGTH_PTS_NEAR, LENGTH_NEAR_DELTA_MM)
    if grip is Grip.FINGERTIP:
        len_target = f"≤ {ranges.length_max:.1f} mm"
    else:
        len_target = f"{ranges.length_min:.1f}–{ranges.length_max:.1f} mm"
    details.append(
        f"Longueur {mouse.length_mm:.1f} mm vs cible {len_target} "
        f"({_ecart_text(len_delta)}) : {length_pts} pts"
    )

    # --- Largeur (ajustée : width_max - 3 mm) -----------------------------
    evaluated_width = mouse.width_max_mm - WIDTH_MEASUREMENT_OFFSET_MM
    wid_delta = _distance_outside(evaluated_width, ranges.width_min, ranges.width_max)
    if wid_delta > WIDTH_EXCLUDE_DELTA_MM:
        return _excluded(mouse, grip, f"Largeur de prise hors plage de {wid_delta:.1f} mm (> {WIDTH_EXCLUDE_DELTA_MM:g} mm)")
    width_pts = _proximity_points(wid_delta, WIDTH_PTS_IN_RANGE, WIDTH_PTS_NEAR, WIDTH_NEAR_DELTA_MM)
    details.append(
        f"Largeur de prise {evaluated_width:.1f} mm vs cible {ranges.width_min:.1f}–{ranges.width_max:.1f} mm "
        f"({_ecart_text(wid_delta)}) : {width_pts} pts"
    )

    # --- Compatibilité grip -------------------------------------------------
    fit = mouse.fit_for(grip)
    if fit == GRIP_EXCLUDED_FIT:
        return _excluded(mouse, grip, f"Compatibilité {grip.label} « Faible »")
    grip_pts = GRIP_POINTS[fit]
    details.append(f"Compatibilité {grip.label} : {fit} : {grip_pts} pts")

    # --- Bosse & boutons ----------------------------------------------------
    if grip is Grip.FINGERTIP:
        hump_pts = 0
        details.append("Bosse : ignorée en Fingertip : 0 pt")
    else:
        hump_tokens = set(mouse.hump_position.split("-"))
        hump_ok = bool(hump_tokens & HUMP_IDEAL[grip])
        hump_pts = HUMP_POINTS if hump_ok else 0
        details.append(f"Bosse {mouse.hump_position} : {'adaptée' if hump_ok else 'non adaptée'} : {hump_pts} pts")

    button_ok = mouse.button_height in BUTTON_IDEAL[grip]
    button_pts = BUTTON_POINTS[grip] if button_ok else 0
    details.append(f"Boutons {mouse.button_height} : {'adaptés' if button_ok else 'non adaptés'} : {button_pts} pts")

    breakdown = ScoreBreakdown(
        length_pts=length_pts,
        width_pts=width_pts,
        grip_pts=grip_pts,
        hump_pts=hump_pts,
        button_pts=button_pts,
    )
    return MouseScore(mouse=mouse, grip=grip, breakdown=breakdown, details=tuple(details))


def rank_mice(
    scores: Iterable[MouseScore],
    budget_mode: BudgetMode | None = None,
) -> list[MouseScore]:
    """Filtre les exclues et trie : score décroissant, puis tier budget correspondant."""
    preferred_tier = budget_mode.tier if budget_mode is not None else None
    kept = [s for s in scores if not s.is_excluded]

    def sort_key(s: MouseScore) -> tuple[int, int]:
        tier_match = preferred_tier is not None and s.mouse.budget_tier == preferred_tier
        return (-s.total, 0 if tier_match else 1)

    return sorted(kept, key=sort_key)  # sorted() est stable : l'ordre du catalogue départage le reste


def recommend(
    mice: Sequence[Mouse],
    hand: HandMeasure,
    grip: Grip,
    budget_mode: BudgetMode | None = None,
    max_budget_eur: float | None = None,
    top_n: int = 2,
) -> list[MouseScore]:
    scores = [evaluate_mouse(m, hand, grip, budget_mode, max_budget_eur) for m in mice]
    return rank_mice(scores, budget_mode)[:top_n]
