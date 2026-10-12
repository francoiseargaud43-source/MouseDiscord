"""Moteur de compatibilité morphologique Mouse Shape Finder.

Ce module ne fait QUE la compatibilité géométrique (points sur 40). Il ne lit ni les prix,
ni les modes de sélection : ceux-ci sont dans ``utils/selection.py``.

Statuts produits par ``evaluate_mouse`` :
- ``excluded`` : une règle éliminatoire s'applique (écart de longueur > 8 mm, largeur > 5 mm,
  compatibilité de grip « Faible », prix au-dessus d'un budget personnalisé) ;
- ``pending``  : aucune exclusion, mais une donnée nécessaire est absente ou en conflit
  (grip « Inconnu », bosse/boutons « Inconnu », longueur non vérifiée…) : aucun point
  n'est inventé, le score reste partiel et n'est pas classable ;
- ``scored``   : toutes les données sont présentes ; le score est final sur 40.

Les constantes sont regroupées ici et documentées dans README.md (section Moteur de scoring).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from utils.models import UNKNOWN, BudgetMode, Grip, HandMeasure, Mouse, Thenar

# --- A. Équations de base (plages idéales) --------------------------------
LENGTH_BASE_MM = 71.4
LENGTH_SLOPE = 0.2633
LENGTH_SPAN_MM = 5.0           # Max = Min + 5 (Palm/Claw) ; Fingertip : Max = base + L×k + 5

WIDTH_BASE_PALM_CLAW_MM = 48.4
WIDTH_BASE_FINGERTIP_MM = 47.3
WIDTH_SLOPE = 0.08
WIDTH_SPAN_PALM_CLAW_MM = 4.0
WIDTH_SPAN_FINGERTIP_MM = 3.9

# --- B. Largeur de prise (estimation provisoire) --------------------------
# Utilisée UNIQUEMENT si aucune largeur de prise mesurée n'existe pour la souris.
GRIP_WIDTH_ESTIMATE_OFFSET_MM = 3.0
# Ancien nom conservé pour compatibilité des imports et des tests.
WIDTH_MEASUREMENT_OFFSET_MM = GRIP_WIDTH_ESTIMATE_OFFSET_MM

# --- C. Barème (points sur 40) --------------------------------------------
MAX_SCORE = 40

LENGTH_PTS_IN_RANGE = 10
LENGTH_PTS_NEAR = 5
LENGTH_NEAR_DELTA_MM = 3.0       # écart < 3 mm (strict)  -> +5
LENGTH_EXCLUDE_DELTA_MM = 8.0    # écart > 8 mm (strict)  -> exclusion

WIDTH_PTS_IN_RANGE = 10
WIDTH_PTS_NEAR = 5
WIDTH_NEAR_DELTA_MM = 2.0        # écart < 2 mm (strict)  -> +5
WIDTH_EXCLUDE_DELTA_MM = 5.0     # écart > 5 mm (strict)  -> exclusion (seuil porté de 4 à 5 mm : docs/audit/AUDIT.md)

GRIP_POINTS = {"Élevé": 10, "Moyen": 5}   # "Faible" -> exclusion ; "Inconnu" -> en attente
GRIP_MAX_POINTS = 10
GRIP_EXCLUDED_FIT = "Faible"

HUMP_POINTS = 5
HUMP_MAX_POINTS = 5

# Règles de compatibilité bosse / boutons, CENTRALISÉES ici (ne pas les dupliquer ailleurs).
HUMP_IDEAL = {
    Grip.PALM: frozenset({"Front", "Mid"}),
    Grip.CLAW: frozenset({"Mid", "Rear"}),
}                                           # Fingertip : bosse ignorée (0 point, pas de donnée requise)

# Alignement sur le reverse engineering de l'outil Oblivity (2026-10-11, docs/REVERSE_ENGINEERING_OBLIVITY.md) :
# Claw -> « Low » uniquement ; Fingertip -> « Mid-to-Low » (jamais haut) ; Palm -> « Elevated » (High).
BUTTON_IDEAL = {
    Grip.PALM: frozenset({"High"}),
    Grip.CLAW: frozenset({"Low"}),
    Grip.FINGERTIP: frozenset({"Low", "Mid"}),
}
BUTTON_POINTS = {Grip.PALM: 5, Grip.CLAW: 5, Grip.FINGERTIP: 10}
BUTTON_MAX_POINTS = {Grip.PALM: 5, Grip.CLAW: 5, Grip.FINGERTIP: 10}

# --- D bis. Critère non documenté : hauteur des boutons (décision du propriétaire, 2026-10-12) ----
# Aucun fabricant ne publie la hauteur des boutons et aucune base ne la recense : quand c'est la SEULE
# donnée absente, la souris est désormais NOTÉE sur les critères documentés (« score partiel ») au lieu
# d'être écartée. Aucun point n'est inventé : le critère n'est pas noté, le total reste comparé au
# barème complet (40) — donc la souris ne gagne jamais de point qu'elle n'a pas — et le bloc
# d'explication le dit en clair. Toute autre donnée manquante (prise, bosse, longueur…) bloque encore.
PARTIAL_SCORING_ALLOWED = True
PARTIAL_MISSING_ALLOWED = frozenset({"hauteur des boutons non vérifiée"})

# --- D. Ajustement thénar ↔ arrière marqué : mécanisme en place, EFFET EN PAUSE (0 point) -----
# Règle du propriétaire, confirmée le 2026-10-12 : le thénar est collecté, affiché et expliqué,
# mais il N'INFLUENCE PAS le score (« zéro effet sur les équations, seuils, points, score,
# classement, exclusion » — docs/MASTER_PROMPT_AZEMOUSE.md §7.6 ; docs/audit/AUDIT.md §3 et §8 ;
# README « aucun effet sur le score »). L'outil d'Oblivity, lui, ne donne AUCUN point au thénar :
# il s'en sert seulement pour conseiller une forme d'arrière (« arrière étroit en pilule » pour un
# thénar petit ou moyen, aucune contrainte pour un grand) et ne pose pas la question en Fingertip
# (dossier Reverse/, 10 sorties datées 2026-10-11).
#
# Les trois valeurs sont donc NEUTRES : quel que soit le thénar choisi, le barème historique est
# strictement inchangé. Le mécanisme reste en place (ajustement borné dans le sous-score de largeur
# 0–10, uniquement pour les souris à bosse arrière marquée, jamais en Fingertip) : l'hypothèse
# bornée du reverse engineering se réactive en remettant les trois valeurs ci-dessous à
# -2 / 0 / +2 (les deux versions sont décrites dans docs/REVERSE_ENGINEERING_OBLIVITY.md §3).
THENAR_WIDTH_ADJUSTMENT = {Thenar.PETITE: 0, Thenar.MOYENNE: 0, Thenar.GRANDE: 0}
THENAR_REAR_HUMP = "Rear"          # seule géométrie concernée (bosse arrière marquée)
# Libellé accordé au masculin dans la phrase « Thénar <taille> × arrière marqué ».
THENAR_SIZE_LABEL = {Thenar.PETITE: "petit", Thenar.MOYENNE: "moyen", Thenar.GRANDE: "grand"}

# Précision de comparaison : les écarts sont arrondis à 6 décimales avant d'être comparés
# aux seuils stricts, pour qu'un écart « exact » ne soit jamais classé à côté par bruit flottant.
DELTA_DECIMALS = 6

STATUS_SCORED = "scored"
STATUS_PENDING = "pending"
STATUS_EXCLUDED = "excluded"


@dataclass(frozen=True)
class TargetRanges:
    length_min: float      # 0.0 en Fingertip (pas de minimum)
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
    thenar_pts: int = 0     # ajustement thénar (voir THENAR_WIDTH_ADJUSTMENT), borné avec width_pts

    @property
    def total(self) -> int:
        return (self.length_pts + self.width_pts + self.grip_pts + self.hump_pts
                + self.button_pts + self.thenar_pts)


@dataclass(frozen=True)
class MouseScore:
    mouse: Mouse
    grip: Grip
    status: str = STATUS_SCORED
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    details: tuple[str, ...] = ()
    excluded_reason: str | None = None
    missing: tuple[str, ...] = ()          # données manquantes (statut pending)
    computable_max: int = 0                # points maximum pouvant être attribués avec les données présentes
    width_source: str | None = None        # "measured" | "estimated"
    width_used_mm: float | None = None
    thenar_note: str | None = None          # effet thénar appliqué (None si aucun)
    confidence: str | None = None          # "élevée" | "moyenne" | "faible"

    @property
    def is_excluded(self) -> bool:
        return self.status == STATUS_EXCLUDED

    @property
    def is_pending(self) -> bool:
        return self.status == STATUS_PENDING

    @property
    def is_scored(self) -> bool:
        return self.status == STATUS_SCORED

    @property
    def is_partial(self) -> bool:
        """Souris classée sur des critères incomplets (hauteur des boutons non documentée)."""
        return self.status == STATUS_SCORED and bool(self.missing)

    @property
    def total(self) -> int:
        """Points attribués. Pour un candidat en attente, il s'agit d'un score PARTIEL non classable."""
        return 0 if self.is_excluded else self.breakdown.total


def compute_target_ranges(hand: HandMeasure, grip: Grip) -> TargetRanges:
    length_min_base = LENGTH_BASE_MM + hand.length_mm * LENGTH_SLOPE
    length_max = length_min_base + LENGTH_SPAN_MM
    if grip is Grip.FINGERTIP:
        length_min = 0.0
        width_min = WIDTH_BASE_FINGERTIP_MM + hand.width_mm * WIDTH_SLOPE
        width_span = WIDTH_SPAN_FINGERTIP_MM
    else:
        length_min = length_min_base
        width_min = WIDTH_BASE_PALM_CLAW_MM + hand.width_mm * WIDTH_SLOPE
        width_span = WIDTH_SPAN_PALM_CLAW_MM
    return TargetRanges(length_min, length_max, width_min, width_min + width_span)


def grip_width_for_scoring(mouse: Mouse) -> tuple[float, str]:
    """Largeur de prise utilisée pour la comparaison et sa provenance.

    La mesure réelle remplace toujours l'estimation ; sans mesure, on applique le correctif provisoire.
    """
    if mouse.grip_width_mm is not None:
        return mouse.grip_width_mm, "measured"
    return mouse.width_max_mm - GRIP_WIDTH_ESTIMATE_OFFSET_MM, "estimated"


def _round_delta(value: float) -> float:
    return round(value, DELTA_DECIMALS)


def distance_outside(value: float, low: float, high: float) -> float:
    """0 si value ∈ [low, high], sinon l'écart à la plage (arrondi pour comparer proprement)."""
    if value < low:
        return _round_delta(low - value)
    if value > high:
        return _round_delta(value - high)
    return 0.0


def _proximity_points(delta: float, in_pts: int, near_pts: int, near_threshold: float) -> int:
    if delta == 0.0:
        return in_pts
    if delta < near_threshold:
        return near_pts
    return 0


def _ecart(delta: float) -> str:
    return "dans la plage" if delta == 0.0 else f"écart {delta:.1f} mm"


def _confidence(mouse: Mouse, width_source: str) -> str:
    if mouse.dimension_status != "verified" or mouse.fit_status != "owner_spec":
        return "faible"
    if width_source == "measured":
        return "élevée"
    return "moyenne"   # dimensions vérifiées mais largeur de prise estimée


def _finish(mouse, grip, status, breakdown, details, missing, computable_max, width_source, width_used,
            excluded_reason=None, thenar_note=None):
    return MouseScore(
        mouse=mouse,
        grip=grip,
        status=status,
        breakdown=breakdown,
        details=tuple(details),
        excluded_reason=excluded_reason,
        missing=tuple(missing),
        computable_max=computable_max,
        width_source=width_source,
        width_used_mm=width_used,
        thenar_note=thenar_note,
        confidence=None if status == STATUS_EXCLUDED else _confidence(mouse, width_source or "estimated"),
    )


def evaluate_mouse(
    mouse: Mouse,
    hand: HandMeasure,
    grip: Grip,
    budget_mode: BudgetMode | None = None,
    max_budget_eur: float | None = None,
    thenar: Thenar | None = None,
) -> MouseScore:
    """Évalue la compatibilité morphologique d'une souris pour une main et un grip donnés.

    ``thenar`` est facultatif : sans lui (valeur par défaut), le score est strictement identique
    au barème historique. Avec lui, l'ajustement thénar ne joue que sur les souris à bosse
    arrière marquée, et jamais en Fingertip (leur outil ne pose pas la question).
    """
    # --- Filtre éliminatoire budget personnalisé (prix inconnu = non conforme par défaut)
    if budget_mode is BudgetMode.CUSTOM:
        if max_budget_eur is None:
            raise ValueError("max_budget_eur est requis pour le mode Budget Personnalisé.")
        if mouse.price_eur is not None and mouse.price_eur > max_budget_eur:
            return _finish(mouse, grip, STATUS_EXCLUDED, ScoreBreakdown(), [], [], 0, None, None,
                           excluded_reason=f"Prix {mouse.price_eur:.2f} € au-dessus du budget maximal {max_budget_eur:.2f} €")

    ranges = compute_target_ranges(hand, grip)
    details: list[str] = []
    missing: list[str] = []
    computable = 0

    if mouse.dimension_status == "conflicting":
        missing.append("dimensions en conflit entre sources")

    # --- Longueur -------------------------------------------------------------
    length_pts = 0
    if mouse.length_mm is None:
        missing.append("longueur non vérifiée")
    else:
        len_delta = distance_outside(mouse.length_mm, ranges.length_min, ranges.length_max)
        if len_delta > LENGTH_EXCLUDE_DELTA_MM:
            return _finish(mouse, grip, STATUS_EXCLUDED, ScoreBreakdown(), [], missing, 0, None, None,
                           excluded_reason=f"Longueur hors plage de {len_delta:.1f} mm (> {LENGTH_EXCLUDE_DELTA_MM:g} mm)")
        length_pts = _proximity_points(len_delta, LENGTH_PTS_IN_RANGE, LENGTH_PTS_NEAR, LENGTH_NEAR_DELTA_MM)
        computable += LENGTH_PTS_IN_RANGE
        target = (f"≤ {ranges.length_max:.1f} mm" if grip is Grip.FINGERTIP
                  else f"{ranges.length_min:.1f}–{ranges.length_max:.1f} mm")
        details.append(f"Longueur {mouse.length_mm:.1f} mm vs cible {target} ({_ecart(len_delta)}) : {length_pts} pts")

    # --- Largeur de prise (mesurée ou estimée) -------------------------------
    width_used, width_source = grip_width_for_scoring(mouse)
    wid_delta = distance_outside(width_used, ranges.width_min, ranges.width_max)
    if wid_delta > WIDTH_EXCLUDE_DELTA_MM:
        return _finish(mouse, grip, STATUS_EXCLUDED, ScoreBreakdown(), [], missing, 0, width_source, width_used,
                       excluded_reason=f"Largeur de prise hors plage de {wid_delta:.1f} mm (> {WIDTH_EXCLUDE_DELTA_MM:g} mm)")
    width_pts = _proximity_points(wid_delta, WIDTH_PTS_IN_RANGE, WIDTH_PTS_NEAR, WIDTH_NEAR_DELTA_MM)
    computable += WIDTH_PTS_IN_RANGE
    origin = "mesurée" if width_source == "measured" else "estimée (coque − 3 mm, provisoire)"
    details.append(
        f"Largeur de prise {origin} {width_used:.1f} mm vs cible {ranges.width_min:.1f}–{ranges.width_max:.1f} mm "
        f"({_ecart(wid_delta)}) : {width_pts} pts"
    )

    # --- Ajustement thénar (uniquement arrière marqué, jamais en Fingertip) ----
    thenar_pts = 0
    thenar_note = None
    applies = (
        thenar is not None
        and grip is not Grip.FINGERTIP
        and mouse.hump_position == THENAR_REAR_HUMP
    )
    if applies:
        adjustment = THENAR_WIDTH_ADJUSTMENT.get(thenar, 0)
        combined = min(WIDTH_PTS_IN_RANGE, max(0, width_pts + adjustment))
        thenar_pts = combined - width_pts
        if thenar_pts:
            size = THENAR_SIZE_LABEL.get(thenar, thenar.value)
            thenar_note = (
                f"Thénar {size} × arrière marqué : {thenar_pts:+d} pt sur la largeur de prise"
            )
            details.append(thenar_note)

    # --- Compatibilité grip ---------------------------------------------------
    grip_pts = 0
    fit = mouse.fit_for(grip)
    if fit == GRIP_EXCLUDED_FIT:
        return _finish(mouse, grip, STATUS_EXCLUDED, ScoreBreakdown(), [], missing, 0, width_source, width_used,
                       excluded_reason=f"Compatibilité {grip.label} « Faible »")
    if fit == UNKNOWN:
        missing.append(f"compatibilité {grip.label} non vérifiée")
    else:
        grip_pts = GRIP_POINTS[fit]
        computable += GRIP_MAX_POINTS
        details.append(f"Compatibilité {grip.label} : {fit} : {grip_pts} pts")

    # --- Bosse ----------------------------------------------------------------
    hump_pts = 0
    if grip is Grip.FINGERTIP:
        details.append("Bosse : ignorée en Fingertip : 0 pt")
    elif mouse.hump_position == UNKNOWN:
        missing.append("position de la bosse non vérifiée")
    else:
        hump_tokens = set(mouse.hump_position.split("-"))
        hump_ok = bool(hump_tokens & HUMP_IDEAL[grip])
        hump_pts = HUMP_POINTS if hump_ok else 0
        computable += HUMP_MAX_POINTS
        details.append(f"Bosse {mouse.hump_position} : {'adaptée' if hump_ok else 'non adaptée'} : {hump_pts} pts")

    # --- Boutons --------------------------------------------------------------
    button_pts = 0
    if mouse.button_height == UNKNOWN:
        missing.append("hauteur des boutons non vérifiée")
    else:
        button_ok = mouse.button_height in BUTTON_IDEAL[grip]
        button_pts = BUTTON_POINTS[grip] if button_ok else 0
        computable += BUTTON_MAX_POINTS[grip]
        details.append(f"Boutons {mouse.button_height} : {'adaptés' if button_ok else 'non adaptés'} : {button_pts} pts")

    breakdown = ScoreBreakdown(length_pts=length_pts, width_pts=width_pts, grip_pts=grip_pts,
                               hump_pts=hump_pts, button_pts=button_pts, thenar_pts=thenar_pts)
    blocking = [item for item in missing if item not in PARTIAL_MISSING_ALLOWED] if PARTIAL_SCORING_ALLOWED else missing
    status = STATUS_SCORED if not blocking else STATUS_PENDING
    return _finish(mouse, grip, status, breakdown, details, missing, computable, width_source, width_used,
                   thenar_note=thenar_note)


def rank_by_compatibility(scores: Sequence[MouseScore]) -> list[MouseScore]:
    """Classement purement morphologique : score décroissant, puis ordre du catalogue (stable)."""
    return sorted((s for s in scores if s.is_scored), key=lambda s: -s.total)


def compatibility_percent(score: MouseScore) -> int:
    """Pourcentage du MAXIMUM THÉORIQUE du barème (score/40). Ce n'est PAS une probabilité."""
    return int(score.total * 100 / MAX_SCORE + 0.5)
