"""Cohérence arithmétique des documents : un pourcentage doit correspondre à son « N sur M ».

Pourquoi ce test existe : le 2026-10-13, deux passages annonçaient un pourcentage **juste, mais rapporté
à un autre ensemble que celui écrit juste à côté** — « 6 148 sur 23 569 » présenté comme 22,63 % (c'est
22,63 % des 27 170 profils de la grille entière, et 26,1 % des 23 569), et « 84 profils sur 24 609 »
présenté comme 0,31 % (0,31 % des 27 170, 0,34 % des 24 609). Aucun de ces écarts ne casse le bot, aucun
test ne pouvait le voir, et une relecture les laisse passer : le nombre est plausible.

Le contrôle est volontairement **local et strict**, pour ne signaler que ce qu'il peut prouver :

- il ne juge que la forme « N sur M » (le nombre **juste avant** « sur », espaces seulement), pris sur
  la ligne du pourcentage **ou sur celle qui précède** (l'ordre de lecture) — jamais un dénominateur
  implicite. Le sens inverse (ensemble après le pourcentage) a été essayé : il signalait des tableaux
  qui parlent de deux choses différentes d'une ligne à l'autre (« 19 sur 36 » des souris, « 16,8 % »
  des profils), donc il a été écarté ;
- quand une ligne porte un « N sur M » et un pourcentage, au moins un couple doit être juste, à 0,05 point
  près (un pourcentage arrondi au dixième, « 0,3 % » pour 0,34 %, reste accepté) ;
- un « N sur M » avec N = 0 n'est pas jugé : « après correction : 0 profil sur 2 805 » voisine les
  pourcentages d'avant correction et aucun rapport ne peut y correspondre.

Ce qu'il ne voit pas, donc vérifié à la main (balayage décrit dans `docs/audit/ROBUSTESSE_2026-10-12.md`
§26.18) : un pourcentage dont le dénominateur est implicite — « N profils sur les 24 609 », ou une cellule
de tableau dont la grille est dans l'en-tête. Élargir le motif a été essayé et **écarté** : il laissait
passer le défaut corrigé (un couple juste sur la ligne d'à côté excusait le mauvais), ce qui rendait le
contrôle rassurant à tort.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = sorted((ROOT / "docs").rglob("*.md"))

POURCENTAGE = re.compile(r"(\d+(?:,\d+)?)\s*%")
ENSEMBLE = re.compile(r"(\d[\d\u00a0 ]*)\s+sur\s+(\d[\d\u00a0 ]*)")
TOLERANCE = 0.05


def _nombre(texte: str) -> float:
    return float(re.sub(r"[\s\u00a0]", "", texte))


def _fr_entier(valeur: float) -> str:
    return f"{valeur:,.0f}".replace(",", " ")


def _fr_pourcent(valeur: float) -> str:
    return f"{valeur:.2f}".replace(".", ",")


def _ensembles(ligne: str) -> list[tuple[float, float]]:
    return [(_nombre(n), _nombre(m)) for n, m in ENSEMBLE.findall(ligne) if _nombre(n) > 0]


def defauts_d_un_texte(texte: str, etiquette: str = "") -> list[str]:
    """Lignes où aucun « N sur M » (de la ligne ou de la précédente) ne justifie les pourcentages."""
    lignes = texte.splitlines()
    defauts = []
    for index, ligne in enumerate(lignes):
        pourcentages = [float(p.replace(",", ".")) for p in POURCENTAGE.findall(ligne)]
        if not pourcentages:
            continue
        ensembles = _ensembles(ligne) + (_ensembles(lignes[index - 1]) if index else [])
        if not ensembles:
            continue
        if any(abs(p - 100 * n / m) <= TOLERANCE for p in pourcentages for n, m in ensembles):
            continue
        attendus = ", ".join(f"{_fr_entier(n)} sur {_fr_entier(m)} = {_fr_pourcent(100 * n / m)} %"
                             for n, m in ensembles)
        annonces = ", ".join(f"{_fr_pourcent(p)} %" for p in pourcentages)
        defauts.append(f"{etiquette}:{index + 1} — la ligne annonce {annonces} ; les ensembles cités "
                       f"donnent {attendus}")
    return defauts


def lignes_controlees() -> int:
    """Nombre de lignes jugées (elles portent un « N sur M » et un pourcentage) — garde anti-vide."""
    total = 0
    for chemin in DOCUMENTS:
        lignes = chemin.read_text(encoding="utf-8").splitlines()
        for index, ligne in enumerate(lignes):
            avant = _ensembles(lignes[index - 1]) if index else []
            if POURCENTAGE.findall(ligne) and (_ensembles(ligne) or avant):
                total += 1
    return total


def test_chaque_pourcentage_correspond_a_son_ensemble():
    defauts = []
    for chemin in DOCUMENTS:
        defauts += defauts_d_un_texte(chemin.read_text(encoding="utf-8"),
                                      str(chemin.relative_to(ROOT)))
    # Garde : si plus aucune ligne ne porte les deux formes, ce test ne vérifie plus rien.
    assert lignes_controlees() >= 3, "le contrôle ne trouve plus de « N sur M » avec un pourcentage"
    assert not defauts, "pourcentage incohérent avec l'ensemble cité :\n" + "\n".join(defauts)


def test_le_controle_detecte_un_pourcentage_du_mauvais_ensemble():
    """Le contrôle doit échouer sur la forme exacte du défaut corrigé (sinon il ne prouve rien)."""
    texte_davant_le_2026_10_13 = (
        "1. **Troisième place (économie) enfin utile** : elle n'apparaissait donc que dans **0,3 %** des\n"
        "   profils (80 sur 23 569). Elle apparaît dans **22,63 %** des profils (6 148 sur 23 569) — mesure\n"
        "   par `tools/flow_effect.py`, avant/après.\n")
    defauts = defauts_d_un_texte(texte_davant_le_2026_10_13, "exemple")
    assert len(defauts) == 1, defauts
    assert "22,63 %" in defauts[0]
    assert "6 148 sur 23 569 = 26,09 %" in defauts[0]


def test_un_pourcentage_arrondi_au_dixieme_reste_accepte():
    """« 0,3 % » pour 0,34 % (arrondi au dixième) ne doit pas être signalé comme une erreur."""
    assert defauts_d_un_texte("n'apparaissait que dans **0,3 %** des profils (80 sur 23 569).") == []


def test_un_pourcentage_peut_se_rapporter_a_l_ensemble_de_la_ligne_precedente():
    """Cas réel (§8.3 du ROBUSTESSE) : « … soit » termine la ligne, le pourcentage suit."""
    texte = ("Le test affirmait « 1 profil sur 960 avant, **101 sur 960 après** » le correctif — soit\n"
             "10,5 % des profils. La mesure ne se reproduit pas : 4 sur 1 029 pour l'ancienne règle.\n")
    assert defauts_d_un_texte(texte, "exemple") == []
