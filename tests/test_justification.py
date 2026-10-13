"""La justification du choix (« 🧭 Pourquoi ce choix ? ») est mesurée, bornée, et **jamais coupée**.

Question laissée ouverte par la 38e passe : `cogs/finder_flow.py` écrit `explanation[:1024]`, la limite
de 1 024 caractères d'un champ d'embed Discord. Cette coupe est-elle une simple ceinture de sécurité, ou
peut-elle mordre un jour ? Personne ne l'avait mesurée — un texte tronqué en plein mot resterait invisible
dans les tests, et un contrôle d'outillage (`tools/qa_flow_matrix.py`) qui cherche la phrase entière dans
le message ne verrait rien s'il ne parcourait pas le profil qui déborde.

**Mesure du 2026-10-13, grille complète (18 522 profils, `cogs` réel, 44 s)** : la phrase la plus longue
fait **320 caractères**, toujours en « Peu importe le prix » (la phrase la plus longue du moteur), soit
**704 caractères de marge** avant la coupe ; les quatre autres modes plafonnent à 169 (Qualité/Prix),
167 (Haut de gamme), 150 (Budget personnalisé) et 138 (Économique).

Les deux tests ci-dessous rejouent la garantie assez vite pour la suite : la **grille resserrée** du
comparateur de données (420 profils, ~1 s, qui atteint elle aussi 320) et le **pire cas construit**, qui ne
dépend d'aucune grille. Le premier lit le message réellement produit et exige que le champ porte la phrase
**entière** : c'est la coupe qui est vérifiée là, pas le moteur.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import recommendation_stats as rs  # noqa: E402  (outil du dépôt : la grille des profils)
from cogs import finder_flow as flow  # noqa: E402
from config import MOUSE_DB_PATH  # noqa: E402
from utils.catalog import load_catalog  # noqa: E402
from utils.matcher import MAX_SCORE, evaluate_mouse  # noqa: E402
from utils.models import BudgetMode, Grip, HandMeasure  # noqa: E402
from utils.selection import MAX_PERFORMANCE_INDEX, _explanation  # noqa: E402

LIMITE_CHAMP_EMBED = 1024       # limite Discord d'un champ d'embed, appliquée par `explanation[:1024]`
CHAMP_JUSTIFICATION = 1         # « 🧭 Pourquoi ce choix ? » : 2e champ du bloc « 📐 Vos repères de taille »


def test_la_plus_longue_justification_du_parcours_garde_la_moitie_du_champ_libre():
    """Grille resserrée : la phrase la plus longue mesurée, portée **en entier** par le message réel.

    Un plafond de 512 (la moitié de la limite Discord) est volontairement large : il ne fige pas la
    rédaction actuelle, il garantit qu'aucun profil du parcours ne s'approche de la coupe.
    """
    meilleur = None
    for grip, thenar, length, width, mode, budget in rs.profiles(fast=True):
        session = rs.make_session(grip, thenar, length, width, mode, budget)
        selection = flow.compute_selection(session)
        if meilleur is None or len(selection.explanation) > len(meilleur[1].explanation):
            meilleur = (session, selection)

    session, selection = meilleur
    phrase = selection.explanation
    assert selection.ranked, "le profil à la phrase la plus longue doit avoir un résultat (sinon rien à couper)"
    assert len(phrase) > 200, f"phrase étonnamment courte ({len(phrase)} caractères) : le test ne mesure plus rien"
    assert len(phrase) <= LIMITE_CHAMP_EMBED // 2, f"{len(phrase)} caractères : la coupe de 1 024 va mordre"

    guide = flow.results_embeds(session, selection)[1]
    champ = guide.fields[CHAMP_JUSTIFICATION]
    assert champ.name == "🧭 Pourquoi ce choix ?"
    assert champ.value == phrase, "le bloc ne porte plus la phrase entière : la coupe de 1 024 a mordu"


def test_le_pire_cas_de_la_phrase_de_justification_reste_bien_en_dessous_de_la_limite():
    """Le pire cas ne dépend pas de la grille : libellé le plus long, meilleur score, zone la plus large.

    Chaque partie variable de la phrase est bornée par les données ou par une constante :
    le libellé vient du catalogue (le plus long y fait 42 caractères), `reference` vaut au plus
    `MAX_SCORE` (40), la zone au plus une souris par entrée du catalogue, et l'indice de performance d'un
    bloc « Haut de gamme » vaut 0, 1 ou 2 (`MAX_PERFORMANCE_INDEX`) : un chiffre, quoi qu'il arrive.
    """
    mice = load_catalog(MOUSE_DB_PATH)
    plus_longue = max(mice, key=lambda m: len(m.label))
    assert len(plus_longue.label) > 30, "libellé le plus long du catalogue : la borne doit rester significative"

    pire = evaluate_mouse(plus_longue, HandMeasure(180.0, 90.0), Grip.PALM)
    zone = [pire] * len(mice)                   # « parmi les N souris à … » : N au maximum possible
    assert len(str(MAX_PERFORMANCE_INDEX)) == 1, "un indice à deux chiffres allongerait la phrase : à revoir"

    for mode in BudgetMode:
        phrase = _explanation(mode, pire, zone, MAX_SCORE)
        assert len(phrase) <= LIMITE_CHAMP_EMBED // 2, f"{mode.value} : {len(phrase)} caractères"
