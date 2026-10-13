"""Garde-fous de `tools/compare_profiles.py` (la matrice de traçabilité du moteur).

Bug trouvé le 2026-10-12 (28e passe) : le script évaluait **toutes** les souris avec le mode
« Budget personnalisé » plafonné à 75 €, puis classait les **cinq** modes sur cette même liste. Les
quatre modes sans plafond (Économique, Qualité/Prix, Haut de gamme, Peu importe le prix) héritaient
donc silencieusement d'un filtre que le bot n'applique pas, et la matrice annonçait un autre gagnant
que le bot sur **8 lignes sur 15** (ex. profil Palm 180 × 90 mm : Phantom Ultimate 91,95 € écarté par
le plafond, la matrice donnait Z1 V2 Ultra pour « Haut de gamme » — nom de l'époque du relevé ; la souris s'appelle Z1 V2 Ultimate depuis le 2026-10-13, c'est le nom publié par la boutique).

Le bot, lui, passe le mode choisi à `evaluate_mouse` (`cogs/finder_flow.py`) : seul le mode budget
plafonne. La matrice doit décrire le bot, pas un profil hybride.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import compare_profiles  # noqa: E402  (après l'insertion du chemin)


def _rows(markdown: str) -> dict[tuple[str, str], str]:
    """Extrait les lignes « Classement par mode » : (profil, mode) -> ligne brute.

    La ligne du mode budget est ramenée à la clé « Budget », quel que soit le plafond affiché : c'est
    le contenu qui doit dépendre du plafond, pas l'identité de la ligne.
    """
    labels = {label for label, _ in compare_profiles.MODES}
    rows: dict[tuple[str, str], str] = {}
    profile = ""
    for line in markdown.splitlines():
        if line.startswith("## Profil "):
            profile = line.split("—", 1)[0].replace("## Profil", "").strip()
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        if cells[0].startswith("Budget ≤"):
            rows[(profile, "Budget")] = line
        elif cells[0] in labels:
            rows[(profile, cells[0])] = line
    return rows


def test_only_the_budget_row_depends_on_the_custom_budget():
    """Invariant : changer le plafond du mode budget ne doit changer QUE la ligne « Budget ».

    C'est la preuve que le plafond ne fuit plus dans les quatre autres modes. Sous l'ancien code, ce
    test échoue sur 8 lignes : le plafond décidait du gagnant en Économique, Qualité/Prix,
    Haut de gamme et Peu importe le prix.
    """
    reference = _rows(compare_profiles.build(75.0))
    autre = _rows(compare_profiles.build(200.0))
    assert reference and set(reference) == set(autre), "les deux matrices doivent avoir les mêmes lignes"

    for key in reference:
        profil, mode = key
        if mode == "Budget":
            continue
        assert reference[key] == autre[key], (
            f"le plafond du mode budget change la ligne « {mode} » du profil {profil} : "
            "il ne devrait pas"
        )

    # Et au moins une ligne « Budget » doit, elle, dépendre du plafond — sinon le test ne prouve rien.
    budget_rows = [k for k in reference if k[1] == "Budget"]
    assert budget_rows, "aucune ligne Budget trouvée : le test ne vérifie rien"
    assert any(reference[k] != autre[k] for k in budget_rows), (
        "changer le plafond de 75 € à 200 € ne change aucune ligne Budget : "
        "le paramètre n'est pas pris en compte"
    )


def test_every_mode_row_is_ranked_on_a_list_the_bot_would_use():
    """Chaque ligne doit pouvoir être reproduite par le bot (moteur + places affichées).

    Les deux colonnes sont recalculées exactement comme `cogs/finder_flow.py` les calcule : classement
    complet (`select(..., top_n=len(pool))`) puis `result_slots` (match idéal, alternative). C'est le
    contrôle qui interdit à la matrice de décrire autre chose que ce que l'utilisateur voit.
    """
    from cogs.finder_flow import result_slots
    from config import MOUSE_DB_PATH
    from utils.catalog import load_catalog
    from utils.matcher import evaluate_mouse

    mice = load_catalog(MOUSE_DB_PATH)
    markdown = compare_profiles.build()
    rows = _rows(markdown)

    for code, title, hand, grip in compare_profiles.PROFILES:
        capped = [evaluate_mouse(m, hand, grip, compare_profiles.BudgetMode.CUSTOM,
                                 compare_profiles.CUSTOM_MAX_EUR) for m in mice]
        free = [evaluate_mouse(m, hand, grip) for m in mice]
        for label, mode in compare_profiles.MODES:
            label = label.format(cap=compare_profiles.CUSTOM_MAX_EUR)
            key = (code, "Budget" if mode is compare_profiles.BudgetMode.CUSTOM else label)
            pool = capped if mode is compare_profiles.BudgetMode.CUSTOM else free
            ideal, alternative, _economy = result_slots(
                compare_profiles.select(pool, mode, top_n=len(pool))
            )
            first = ideal.mouse.label if ideal else "aucun classable"
            assert f"| {first} (" in rows[key], (
                f"profil {code} / {label} : la matrice n'annonce pas le match idéal que le bot calcule "
                f"({first})"
            )
            if alternative is not None:
                second = f"{alternative.mouse.label} ({alternative.total}/40)"
                assert f"| {second} |" in rows[key] or f"| {second} " in rows[key], (
                    f"profil {code} / {label} : la matrice n'annonce pas l'alternative que le bot "
                    f"affiche ({second})"
                )
