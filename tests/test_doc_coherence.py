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

Depuis le 2026-10-14, il vérifie aussi la **numérotation des passes** du journal : la suite des numéros
ne doit avoir aucun trou (une passe livrée mais non racontée) et une passe qui occupe plusieurs sections
doit le dire (« (suite) », « Complément de la Ne »). Le défaut qui a motivé ce contrôle : la section de
l'aperçu périmé était titrée « 50e passe (suite) » alors que son commit (`1cf2839`) annonce la 51e — le
numéro 51 avait disparu du journal.

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


CHIFFRE_PERIME = re.compile(r"\b178\s+profils|\*\*178\b")
PUBLICATIONS = ([ROOT / "README.md"] + sorted((ROOT / "data").rglob("*.json"))
                + sorted((ROOT / "tests").rglob("*.py")) + sorted((ROOT / "tools").rglob("*.py")))


def test_un_chiffre_perime_ne_reste_pas_publie_comme_une_mesure():
    """Le chiffre qui ne se rejoue pas doit disparaître de partout où l'on publie une mesure.

    Constat (57e passe, §26.42 du ROBUSTESSE) : la paire ATK U2 / U2 V2 Ultimate a fait circuler un
    chiffre périmé — 178, présenté comme un nombre de profils à 0,66 % — un comptage du **moteur
    d'avant** le palier de la 2e place, périmé au moment même où il était écrit. La 58e passe l'a retiré des documents et des notes du catalogue, et a annoncé
    que plus rien ne le citait : **deux docstrings de `tests/test_data.py` l'ont gardé** jusqu'au
    2026-10-14 (63e passe). Les chiffres justes, remesurés sur les deux grilles : **235** profils
    montraient les deux souris (0,86 % des 27 170 itérations d'alors, 1,08 % des 21 736 entrées
    distinctes), **175** changeaient de résultat (0,64 % puis 0,81 %).

    Le journal des constats (`docs/audit/`) a le droit de citer le chiffre fautif — c'est ainsi qu'il
    explique la correction ; les fichiers qui **publient** une mesure (README, données, code, tests) ne
    l'ont pas. Mutation jouée : replacer 178 juste devant « profils » dans `tests/test_data.py` →
    1 échec.
    """
    coupables = [
        f"{f.relative_to(ROOT)}:{numero}"
        for f in PUBLICATIONS
        for numero, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1)
        if CHIFFRE_PERIME.search(ligne)
    ]
    assert coupables == [], f"chiffre périmé republié comme une mesure : {coupables}"


JOURNAL = ROOT / "docs" / "audit" / "ROBUSTESSE_2026-10-12.md"


def _passes_du_journal() -> list[tuple[int, str]]:
    """Les couples (numéro de passe, titre de section) du journal, dans l'ordre du fichier.

    Seules les sections **numérotées du §26** sont lues (« ## 26.35 51e passe — … ») : les premières
    sections de ce paragraphe s'annoncent en toutes lettres (« ## 26. Trente-huitième passe (…) ») et les
    passes racontées avant lui (§7 à §9) sont hors de portée du contrôle — c'est dit ici pour que
    personne ne croie que « aucun trou » vaut pour les 72 passes.
    """
    passes: list[tuple[int, str]] = []
    for ligne in JOURNAL.read_text(encoding="utf-8").splitlines():
        if not ligne.startswith("## 26."):
            continue
        trouvé = re.search(r"(\d+)e passe", ligne)
        if trouvé:
            passes.append((int(trouvé.group(1)), ligne))
    return passes


def test_le_journal_des_passes_ne_saute_aucun_numero():
    """Un trou dans la numérotation veut dire qu'une passe livrée n'est racontée nulle part.

    Défaut trouvé le 2026-10-14 : la section qui raconte l'aperçu périmé (commit `1cf2839`) était titrée
    « 50e passe (suite) » alors que le commit annonce la **51e** — le numéro 51 avait disparu du journal,
    et la suite allait de 50 à 52. Le document cite pourtant lui-même « le défaut des 50e et 51e passes ».
    """
    passes = _passes_du_journal()
    assert passes, "aucune section numérotée lue : le contrôle ne mesure rien"
    numéros = [numéro for numéro, _ in passes]
    assert numéros == sorted(numéros), "le journal revient en arrière"
    attendus = set(range(numéros[0], numéros[-1] + 1))
    manquants = sorted(attendus - set(numéros))
    assert not manquants, f"passes sans aucune section dans le journal : {manquants}"


def test_une_passe_qui_occupe_plusieurs_sections_le_dit():
    """Deux sections du même numéro doivent s'annoncer « (suite) » ou « Complément de la Ne ».

    Sans cette règle, la section d'une passe **suivante** peut se cacher derrière le numéro de la
    précédente : c'est exactement la faute corrigée le 2026-10-14 (§26.35) et celle commise le même jour
    en publiant la 72e sous le numéro de la 71e (§26.59).
    """
    vus: dict[int, str] = {}
    for numéro, titre in _passes_du_journal():
        if numéro in vus:
            assert "(suite)" in titre or "Complément de la" in titre, \
                f"le numéro {numéro} revient sans se dire « (suite) » : {titre!r}"
        vus[numéro] = titre
