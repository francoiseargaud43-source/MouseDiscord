"""Les quatre textes variables des cartes de résultat sont mesurés, bornés, et **jamais coupés**.

`cogs/finder_flow.py` coupe quatre textes aux limites Discord — un champ d'embed fait 1 024 caractères,
une description 4 096 — et personne ne savait si ces coupes pouvaient mordre un jour :

| Texte coupé | Où | Coupe |
|---|---|---|
| Le résumé du parcours (« ✋ Palm Grip • 📏 175 × 82,5 mm », gamme comprise) | description de « 🎯 Votre recommandation » | `header[:4096]` |
| Le **sommaire morphologique** (« Longueur dans la cible, largeur de prise dans la cible… ») | fin de `_match_summary` | `sentence[:1024]` |
| La ligne « en clair » (cotes · prix · sommaire) | champ « 🔎 … en clair » | `[:1024]` |
| La **justification du choix** (« Forme d'abord : … ») | champ « 🧭 Pourquoi ce choix ? » | `explanation[:1024]` |

**Mesure du 2026-10-13, grille complète (18 522 profils, `cogs` réel, 46 s)** : ces quatre textes font au
plus **107 caractères** (résumé), **160** (sommaire), **211** (ligne en clair) et **320** (justification),
soit des marges de 3 989, 864, 813 et 704 caractères. Les mêmes 18 522 messages ont aussi été mesurés sur
les limites qui, elles, ne sont pas coupées : champ le plus long **320**, description la plus longue
**435**, bloc le plus long **1 039**, message le plus long **2 780** — les plafonds Discord (1 024 / 4 096 /
6 000) et le plafond mobile du projet (700 par champ) n'étaient approchés par personne.

**Pourquoi ces tests existent** : la vérification d'outillage `tools/qa_flow_matrix.py` cherche le texte
entier dans le message, mais elle ne parcourt que ses profils de contrôle, aucun ne poussant les textes à
leur maximum ; et `tests/test_flow.py` mesure les limites Discord sur **un seul** profil (Claw 180 × 90,
« le cas le plus long »). Un texte coupé en plein mot serait passé inaperçu. Les quatre tests ci-dessous
rejouent la garantie en quelques secondes : grille resserrée du comparateur de données (420 profils), pire
cas construit indépendant de toute grille, et un contrôle de coupe qui lit le **message réellement produit**.

Une coupe ne se voit pas toujours de l'extérieur : celle qui est **interne** à `_match_summary` ne se laisse
pas comparer, l'appelant recevant déjà le texte coupé. Deux angles la démasquent : sa **ponctuation finale**
(coupée en plein mot, la phrase perd son point — vérifié ici) et sa position dans la ligne « en clair », qui
doit, elle, être portée entière par le message.
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
LIMITE_DESCRIPTION = 4096       # limite Discord d'une description, appliquée par `header[:4096]`
LIMITE_MOBILE = 700             # plafond de lisibilité mobile du projet (tests/test_flow.py)
CHAMP_EN_CLAIR = 0              # 1er champ du bloc « 📐 Vos repères de taille »
CHAMP_JUSTIFICATION = 1         # 2e champ du même bloc : « 🧭 Pourquoi ce choix ? »


def _resume(session) -> str:
    """Le texte de la description de la recommandation, tel que `results_embeds` le coupe."""
    resume = flow._recap(session)
    if session.budget_mode is None:
        resume = f"{resume}  •  🎚️ **Classement morphologique**"
    return resume


def _en_clair(ideal) -> str:
    """La ligne « en clair » d'une souris, telle que le bloc des repères la compose."""
    return f"{flow._size_text(ideal.mouse)} · {flow._price_text(ideal)}\n{flow._match_summary(ideal)}"


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


def test_les_quatre_textes_coupes_des_cartes_portent_toujours_leur_texte_entier():
    """Les quatre coupes de `results_embeds`, mesurées sur la grille resserrée **et lues dans le message**.

    Pour chacun des quatre textes, on retient le profil qui le rend le plus long, on vérifie qu'il tient
    dans la moitié de la limite Discord, puis on relit le **message réellement produit** : le texte doit y
    être, entier. C'est la coupe qui est vérifiée là — un moteur qui allongerait un texte sans que la
    carte suive serait vu ici et nulle part ailleurs.
    """
    pires = {}                                  # nom → (longueur, texte, session, sélection)
    for grip, thenar, length, width, mode, budget in rs.profiles(fast=True):
        session = rs.make_session(grip, thenar, length, width, mode, budget)
        selection = flow.compute_selection(session)

        textes = {"résumé": _resume(session), "justification": selection.explanation}
        if selection.ranked:
            ideal = selection.ranked[0]
            textes["sommaire"] = flow._match_summary(ideal)
            textes["en clair"] = _en_clair(ideal)
        for nom, texte in textes.items():
            if nom not in pires or len(texte) > pires[nom][0]:
                pires[nom] = (len(texte), texte, session, selection)

    assert set(pires) == {"résumé", "sommaire", "en clair", "justification"}
    for nom, (longueur, texte, _, _) in pires.items():
        assert longueur <= LIMITE_CHAMP_EMBED // 2, f"{nom} : {longueur} caractères, la coupe va mordre"
        # Un texte coupé en plein mot perd sa ponctuation finale : la phrase se termine par un point,
        # et le résumé du parcours ne traîne pas d'ellipse. C'est le seul angle sous lequel la coupe
        # **interne** de `_match_summary` (`sentence[:1024]`, invisible depuis l'appelant qui reçoit
        # déjà le texte coupé) se laisse voir : à 50 caractères, la phrase finissait par « … dans la ».
        if nom in {"sommaire", "justification"}:
            assert texte.endswith("."), f"{nom} : texte coupé en plein mot ({texte[-40:]!r})"
        assert not texte.endswith(("…", "...", " ")), f"{nom} : {texte[-40:]!r}"

    # Le résumé du parcours : la description du bloc « Votre recommandation », entier.
    embeds = flow.results_embeds(pires["résumé"][2], pires["résumé"][3])
    assert embeds[0].description == pires["résumé"][1]
    assert "…" not in embeds[0].description[-3:], "la description finit sur des points de suspension"

    # La justification : deuxième champ du bloc des repères, entière.
    guide = flow.results_embeds(pires["justification"][2], pires["justification"][3])[1]
    assert guide.fields[CHAMP_JUSTIFICATION].value == pires["justification"][1]

    # La ligne « en clair » : premier champ du même bloc, entière — le sommaire morphologique y est inclus.
    guide = flow.results_embeds(pires["en clair"][2], pires["en clair"][3])[1]
    assert guide.fields[CHAMP_EN_CLAIR].value == pires["en clair"][1]
    assert pires["sommaire"][1] in guide.fields[CHAMP_EN_CLAIR].value


def test_toute_la_grille_resserree_respecte_les_limites_discord_et_la_lecture_mobile():
    """Le contrôle de `tests/test_flow.py` porte sur **un** profil (Claw 180 × 90) : ici, les 420.

    Mêmes plafonds, mais mesurés sur toute la grille resserrée (prises, longueurs, largeurs, gammes et
    budgets mêlés) : champs ≤ 700 (mobile), description ≤ 4 096, bloc ≤ 6 000, message ≤ 6 000, et dix
    blocs au plus par message (limite Discord).
    """
    pires = {"champ": 0, "description": 0, "bloc": 0, "message": 0, "blocs": 0, "profil": None}
    for grip, thenar, length, width, mode, budget in rs.profiles(fast=True):
        session = rs.make_session(grip, thenar, length, width, mode, budget)
        selection = flow.compute_selection(session)
        embeds = flow.results_embeds(session, selection)
        profil = (grip.value, length, width, mode.value if mode else None, budget)
        pires["blocs"] = max(pires["blocs"], len(embeds))
        pires["message"] = max(pires["message"], sum(len(e) for e in embeds))
        for embed in embeds:
            pires["bloc"] = max(pires["bloc"], len(embed))
            pires["description"] = max(pires["description"], len(embed.description or ""))
            for champ in embed.fields:
                if len(champ.value) > pires["champ"]:
                    pires["champ"], pires["profil"] = len(champ.value), (champ.name, profil)

    assert pires["blocs"] <= 10, f"{pires['blocs']} blocs dans un message"
    assert pires["bloc"] <= 6000, f"un bloc fait {pires['bloc']} caractères"
    assert pires["message"] <= 6000, f"un message fait {pires['message']} caractères"
    assert pires["description"] <= LIMITE_DESCRIPTION, f"une description fait {pires['description']} caractères"
    assert pires["champ"] <= LIMITE_MOBILE, f"champ trop long pour mobile : {pires['profil']}"
