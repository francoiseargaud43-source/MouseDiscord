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
    MCU_TIERS,
    PERFORMANCE_SENSORS,
    SENSOR_TIERS,
    HAUT_DE_GAMME_TOLERANCE_POINTS,
    PEU_IMPORTE_PRIX_TOLERANCE_POINTS,
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
    assert TOLERANCE_BY_MODE[BudgetMode.PEU_IMPORTE_PRIX] == PEU_IMPORTE_PRIX_TOLERANCE_POINTS == 2


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


def test_peu_importe_prix_keeps_the_best_shape_first():
    """La forme reste maître : une souris plus moderne mais 5 pts en dessous ne passe pas devant."""
    best = mouse("best", 60.0, hump_position="Front", button_height="High")                 # 30
    modern_close = mouse("modern", 25.0, hump_position="Mid", button_height="Mid",
                         polling_hz=8000, sensor="PAW3950 Ultra")                          # 25
    sel = select([scored(best), scored(modern_close)], BudgetMode.PEU_IMPORTE_PRIX)
    assert sel.ranked[0].mouse.id == "best"


def test_peu_importe_prix_breaks_ties_with_documented_components_then_price():
    """À score égal : composants documentés les plus actuels (0-2), puis la moins chère."""
    slow_cheap = mouse("slow_cheap", 20.0, hump_position="Front", button_height="High")     # 30, index 0
    fast_pricey = mouse("fast_pricey", 60.0, hump_position="Front", button_height="High",
                        polling_hz=8000, sensor="PAW3950 Ultra")                            # 30, index 2
    fast_cheap = mouse("fast_cheap", 40.0, hump_position="Front", button_height="High",
                       polling_hz=8000, sensor="PAW3950 Ultra")                             # 30, index 2
    sel = select([scored(slow_cheap), scored(fast_pricey), scored(fast_cheap)],
                 BudgetMode.PEU_IMPORTE_PRIX, top_n=3)
    assert [s.mouse.id for s in sel.ranked] == ["fast_cheap", "fast_pricey", "slow_cheap"]


def test_peu_importe_prix_accepts_a_mouse_without_price():
    """Le prix n'est jamais exigé dans ce mode : une souris sans prix reste classable."""
    unpriced = mouse("unpriced", None, hump_position="Front", button_height="High", polling_hz=8000)
    sel = select([scored(unpriced)], BudgetMode.PEU_IMPORTE_PRIX)
    assert [s.mouse.id for s in sel.ranked] == ["unpriced"]
    assert sel.pending == ()


def test_peu_importe_prix_explanation_states_the_shape_rule():
    sel = select([scored(mouse("a", 40.0)), scored(mouse("b", 50.0))], BudgetMode.PEU_IMPORTE_PRIX)
    assert "Forme d'abord" in sel.explanation
    assert "Le budget ne limite jamais le choix" in sel.explanation


def test_components_index_ranks_sensor_then_mcu_then_switches_then_polling():
    """Capteur (génération) > MCU > switchs > fréquence ; une donnée absente vaut 0 (jamais devinée)."""
    from utils.selection import components_index

    best = mouse("best", 60.0, sensor="PAW3955 Master", mcu="Nordic 54H20",
                 switches="Optiques ATK Custom", polling_hz=8000)
    older = mouse("older", 60.0, sensor="PAW3950", mcu="Nordic 54L15",
                  switches="Optiques (Omron)", polling_hz=8000)
    mecha = mouse("mecha", 60.0, sensor="PAW3950", mcu="Nordic 54L15",
                  switches="ATK Lightblade (mécaniques)", polling_hz=8000)
    unknown = mouse("unknown", 60.0)
    assert components_index(best) > components_index(older) > components_index(mecha) > components_index(unknown)
    assert components_index(unknown) == (0, 0, 0, 0)


def test_no_price_mode_breaks_ties_with_the_documented_components():
    """Deux formes équivalentes : le capteur le plus récent passe devant, quelle que soit la marque."""
    recent = mouse("recent", 60.0, hump_position="Front", button_height="High",
                   sensor="PAW3955 Master", mcu="Nordic 54LM20", switches="Optiques ATK Custom", polling_hz=8000)
    older = mouse("older", 30.0, hump_position="Front", button_height="High",
                  sensor="PAW3395", polling_hz=8000)
    sel = select([scored(older), scored(recent)], BudgetMode.PEU_IMPORTE_PRIX)
    assert [s.mouse.id for s in sel.ranked] == ["recent", "older"]


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


# ---------------------------------------------------------------------------
# Canaris du classement des COMPOSANTS documentés (2026-10-12)
#
# ``components_index`` rend 0 pour toute valeur qu'il ne connaît pas : une valeur écrite
# autrement dans le catalogue (faute de frappe, espace, suffixe) ferait donc disparaître un
# départage SANS erreur, sans test rouge et sans trace dans le résultat. Ces canaris figent la
# liste exacte des valeurs du catalogue et leur rang : toute nouvelle valeur doit être tranchée
# explicitement, avec sa raison.
# ---------------------------------------------------------------------------
SENSORS_SANS_RANG_ASSUME = {
    "PAW3315": "capteur d'entrée de gamme (VXE X3) : aucune classe publique comparable",
    "Xhero AI / PAW3395 SE": "variante « SE » du PAW3395 (VXE V3) : rang de la version SE non publié, jamais deviné",
}
MCUS_SANS_RANG_ASSUME = {
    "": "aucun MCU publié sur la fiche (ATK U2, Pulsar X2 / X2H / Xlite : le fabricant ne le donne pas)",
    "Broadcom CX52850SE": "puce Broadcom des VXE X3 : aucun comparatif public de génération",
    "Puce BK Custom Esports": "puce maison de l'ATK A9 NB Ultra : aucun comparatif public",
    "Puce NearLink / HiSilicon": "radio NearLink (ATK A9 Plus / A9 Ultimate) : aucun comparatif public",
}
# Capteurs classés « haut de gamme » (rang ≥ 3) mais absents de PERFORMANCE_SENSORS, qui décide du
# mode Haut de Gamme : incohérence DOCUMENTÉE, mesurée sans effet (1 309 profils → 0 recommandation
# modifiée). Aucune valeur n'est ajoutée ici sans mesure.
SENSORS_HORS_PERFORMANCE_SENSORS = {
    "Pulsar XS-1": "capteur maison Pulsar (32 000 dpi / 750 IPS publiés, classe PAW3950) : "
                    "hors PERFORMANCE_SENSORS — incohérence sans effet mesuré (voir ROBUSTESSE §8)",
}


def _catalogue():
    from utils.catalog import load_catalog
    from config import MOUSE_DB_PATH
    return load_catalog(MOUSE_DB_PATH)


def test_every_catalogue_sensor_and_mcu_value_is_ranked_or_explicitly_unranked():
    mice = _catalogue()
    sensors = {m.sensor for m in mice if m.sensor}
    mcus = {m.mcu for m in mice if m.mcu is not None}
    assert sensors - set(SENSOR_TIERS) == set(SENSORS_SANS_RANG_ASSUME), (
        "capteurs sans rang : trancher dans SENSOR_TIERS (avec source) ou justifier dans "
        "SENSORS_SANS_RANG_ASSUME")
    assert mcus - set(MCU_TIERS) == set(MCUS_SANS_RANG_ASSUME), (
        "MCU sans rang : trancher dans MCU_TIERS (avec source) ou justifier dans MCUS_SANS_RANG_ASSUME")


def test_every_ranked_high_end_sensor_is_either_in_performance_sensors_or_justified():
    sensors = {m.sensor for m in _catalogue()}
    hors = {value for value, rang in SENSOR_TIERS.items()
            if rang >= 3 and value not in PERFORMANCE_SENSORS} & sensors
    assert hors == set(SENSORS_HORS_PERFORMANCE_SENSORS), (
        "capteur haut de gamme absent de PERFORMANCE_SENSORS : l'ajouter (avec source) ou le "
        "justifier dans SENSORS_HORS_PERFORMANCE_SENSORS")


def test_every_catalogue_switch_string_is_recognised():
    """Une chaîne de switchs non reconnue vaut 0 : toutes celles du catalogue doivent être lues."""
    from utils.selection import _switch_tier
    sans_rang = sorted({m.switches for m in _catalogue() if m.switches and _switch_tier(m.switches) == 0})
    assert sans_rang == [], f"switchs non reconnus par _switch_tier : {sans_rang}"


def test_deux_fois_la_meme_souris_est_toujours_la_meme_coque():
    """`_same_shell` se décide d'abord sur l'identifiant : la même entrée deux fois est la même coque.

    C'est le garde-fou qui empêche d'afficher deux fois la même souris (bug constaté en 44e passe :
    « l'alternative = la même souris »). Il doit se déclencher même quand la souris n'a **aucune** coque
    partagée renseignée — sinon une entrée dupliquée passerait pour deux souris distinctes.
    """
    from types import SimpleNamespace

    from utils.matcher import STATUS_SCORED, MouseScore
    from utils.selection import _same_shell

    sans_coque = MouseScore(mouse=SimpleNamespace(id="atk_a9_plus", shell_id=None),
                            grip=Grip.PALM, status=STATUS_SCORED)
    coque_a = MouseScore(mouse=SimpleNamespace(id="atk_a9_ultimate", shell_id="atk_a9_large"),
                         grip=Grip.PALM, status=STATUS_SCORED)
    coque_b = MouseScore(mouse=SimpleNamespace(id="atk_a9_air", shell_id="atk_a9_large"),
                         grip=Grip.PALM, status=STATUS_SCORED)

    assert _same_shell(sans_coque, sans_coque) is True          # même identifiant, sans coque partagée
    assert _same_shell(coque_a, coque_b) is True                # deux identifiants, une seule coque
    assert _same_shell(sans_coque, coque_a) is False            # ni identifiant, ni coque commune
