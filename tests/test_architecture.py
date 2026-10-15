"""`docs/ARCHITECTURE.md` ne peut pas se périmer en silence (80e passe, 2026-10-15).

La première cause de défaut de ce dépôt est un document qui affirme ce que le code ne fait plus (famille 1
du brief de reprise). Le document de vérité courante recopie quelques règles du moteur pour être lisible
sans le code : chacune est ici reconstruite DEPUIS le code et cherchée mot pour mot dans le document.
Changer une constante sans changer la phrase fait échouer la suite.
"""
from __future__ import annotations

from pathlib import Path

from config import SESSION_TTL_SECONDS
from utils import matcher, selection, slots
from utils.models import BudgetMode, Grip

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")


def fr(valeur: float) -> str:
    """71.4 → « 71,4 » ; 5.0 → « 5 » (écriture du document)."""
    return f"{valeur:g}".replace(".", ",")


def test_les_plages_cibles_sont_celles_du_moteur():
    assert f"`{fr(matcher.LENGTH_BASE_MM)} + {fr(matcher.LENGTH_SLOPE)} × L`" in DOC
    assert f"à cette valeur + {fr(matcher.LENGTH_SPAN_MM)} mm" in DOC
    assert f"`{fr(matcher.WIDTH_BASE_PALM_CLAW_MM)} + {fr(matcher.WIDTH_SLOPE)} × W` à + {fr(matcher.WIDTH_SPAN_PALM_CLAW_MM)} mm" in DOC
    assert f"`{fr(matcher.WIDTH_BASE_FINGERTIP_MM)} + {fr(matcher.WIDTH_SLOPE)} × W` à + {fr(matcher.WIDTH_SPAN_FINGERTIP_MM)} mm" in DOC
    assert f"largeur de coque − {fr(matcher.GRIP_WIDTH_ESTIMATE_OFFSET_MM)} mm" in DOC


def test_le_bareme_est_celui_du_moteur():
    assert (f"| Longueur | {matcher.LENGTH_PTS_IN_RANGE} | dans la plage : {matcher.LENGTH_PTS_IN_RANGE} · "
            f"à moins de {fr(matcher.LENGTH_NEAR_DELTA_MM)} mm : {matcher.LENGTH_PTS_NEAR} · "
            f"à plus de {fr(matcher.LENGTH_EXCLUDE_DELTA_MM)} mm") in DOC
    assert (f"| Largeur de prise | {matcher.WIDTH_PTS_IN_RANGE} | dans la plage : {matcher.WIDTH_PTS_IN_RANGE} · "
            f"à moins de {fr(matcher.WIDTH_NEAR_DELTA_MM)} mm : {matcher.WIDTH_PTS_NEAR} · "
            f"à plus de {fr(matcher.WIDTH_EXCLUDE_DELTA_MM)} mm") in DOC
    assert (f"« Élevé » {matcher.GRIP_POINTS['Élevé']} · « Moyen » {matcher.GRIP_POINTS['Moyen']} · "
            f"« {matcher.GRIP_EXCLUDED_FIT} »") in DOC
    assert f"| Bosse | {matcher.HUMP_POINTS} |" in DOC
    assert (f"| Hauteur des boutons | {matcher.BUTTON_POINTS[Grip.PALM]} "
            f"({matcher.BUTTON_POINTS[Grip.FINGERTIP]} en Fingertip) |") in DOC
    boutons = " · ".join(f"{g.name.capitalize()} → {{{', '.join(sorted(matcher.BUTTON_IDEAL[g]))}}}"
                         for g in (Grip.PALM, Grip.CLAW, Grip.FINGERTIP))
    assert boutons in DOC
    assert matcher.HUMP_IDEAL[Grip.PALM] == {"Front", "Mid"} and "Palm : avant ou milieu" in DOC
    assert matcher.HUMP_IDEAL[Grip.CLAW] == {"Mid", "Rear"} and "Claw : milieu ou arrière" in DOC
    assert f"sur **{matcher.MAX_SCORE}** dans les trois prises" in DOC
    for grip in Grip:     # le maximum vaut bien 40 dans chaque prise (la bosse est ignorée en Fingertip)
        bosse = matcher.HUMP_MAX_POINTS if grip in matcher.HUMP_IDEAL else 0
        total = (matcher.LENGTH_PTS_IN_RANGE + matcher.WIDTH_PTS_IN_RANGE + matcher.GRIP_MAX_POINTS
                 + bosse + matcher.BUTTON_MAX_POINTS[grip])
        assert total == matcher.MAX_SCORE, grip


def test_les_zones_des_modes_et_des_places_sont_celles_du_code():
    lignes = {BudgetMode.ECONOMIQUE: "| Économique | {} points", BudgetMode.QUALITE_PRIX: "| Qualité/Prix | {} points",
              BudgetMode.HAUT_DE_GAMME: "| Haut de gamme | {} points",
              BudgetMode.PEU_IMPORTE_PRIX: "| Peu importe le prix | {} points",
              BudgetMode.CUSTOM: "| Budget libre | {} points"}
    for mode, gabarit in lignes.items():
        assert gabarit.format(selection.TOLERANCE_BY_MODE[mode]) in DOC, mode
    assert f"fréquence ≥ {selection.PERFORMANCE_POLLING_HZ:,} Hz".replace(",", " ") in DOC
    assert f"élargie une fois à\n   {slots.ALTERNATIVE_EXTENSION_POINTS} points" in DOC
    assert f"fenêtre de\n   {slots.ECONOMY_SLOT_TOLERANCE_POINTS} points" in DOC
    for titre in (slots.ECONOMY_TITLE, slots.OTHER_OPTION_TITLE, slots.PISTE_TITLE):
        emoji, mots = titre.split(" ", 1)
        assert f"« {emoji} {mots[0].lower()}{mots[1:]}" in DOC.replace("\n   ", " "), titre


def test_le_delai_d_expiration_et_la_carte_des_fichiers_sont_exacts():
    assert f"({round(SESSION_TTL_SECONDS / 60)} minutes par défaut" in DOC
    livres = sorted(p.relative_to(ROOT).as_posix() for d in ("cogs", "utils") for p in (ROOT / d).glob("*.py")
                    if p.name != "__init__.py")
    for fichier in livres + ["bot.py", "config.py"]:
        assert f"| `{fichier}` |" in DOC, f"{fichier} absent de la carte des fichiers"
