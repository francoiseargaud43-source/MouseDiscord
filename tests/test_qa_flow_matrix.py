"""Tests du banc d'essai `tools/qa_flow_matrix.py` lui-même.

Un banc d'essai qui se trompe de rôle fait plus de dégâts qu'il n'en évite : le 2026-10-12, la
troisième place était jugée « à la place de l'alternative » dès que celle-ci était vide (liste des
souris montrées filtrée puis relue par position). Résultat : 15 064 avertissements fantômes sur la
grille complète, tous du même faux positif « alternative élargie mais plus chère ». Ces tests
verrouillent la lecture **par rôle** et le contrôle des libellés de la troisième place.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cogs.finder_flow import compute_selection, result_slots, results_embeds, third_slot_title  # noqa: E402
from config import COMMERCIAL_LINKS_PATH  # noqa: E402
from tools.qa_flow_matrix import (check_result_message, deux_places_meme_coque, grille,
                                  message_text, places_au_prix_non_verifie)  # noqa: E402
from utils.catalog import load_commercial_links  # noqa: E402
from utils.models import BudgetMode, Grip, Thenar  # noqa: E402
from utils.session import FinderSession  # noqa: E402
from types import SimpleNamespace  # noqa: E402

LINKS = load_commercial_links(COMMERCIAL_LINKS_PATH)


def _profil(grip: Grip, length: float, width: float, thenar: Thenar | None,
            mode: BudgetMode | None = None, budget: float | None = None) -> FinderSession:
    session = FinderSession(user_id=7)
    session.grip = grip
    session.hand_length_mm = length
    session.hand_width_mm = width
    session.thenar = thenar if grip is not Grip.FINGERTIP else None
    session.budget_mode = mode
    session.max_budget_eur = budget if mode is BudgetMode.CUSTOM else None
    return session


class _BlocFactice:
    """Bloc minimal au texte choisi.

    Piège de discord.py 2.7 : ``Embed.fields`` renvoie des ``EmbedProxy`` en **lecture seule** — une
    écriture dessus est acceptée puis **silencieusement perdue**. Pour la contre-épreuve, on fabrique
    donc un bloc dont le texte est celui qu'on veut faire lire au banc.
    """

    def __init__(self, texte: str) -> None:
        self.title = texte
        self.description = None
        self.fields: list = []
        self.footer = _PiedVide()


class _PiedVide:
    text = None


def _juger(session: FinderSession) -> tuple[list[str], str, tuple]:
    """Rejoue le résultat complet et renvoie (problèmes du banc, texte affiché, les trois places)."""
    selection = compute_selection(session)
    ideal, alternative, economy = result_slots(selection)
    embeds = results_embeds(session, selection)
    problems = check_result_message(session, selection, embeds, ideal, alternative, economy)
    return problems, message_text(embeds), (ideal, alternative, economy)


def test_le_banc_ne_confond_pas_les_places_quand_l_alternative_est_vide():
    """Régression : l'économie n'est jamais jugée comme une alternative (faux positif de prix).

    Le décalage se produisait dès que la deuxième place était vide : le banc relisait la liste des
    souris montrées **par position**. Depuis, chaque place est contrôlée par rôle. Le cas est donc
    provoqué explicitement (l'alternative passée à ``None`` alors que le message, lui, montre trois
    lignes) : les trois places restent lues séparément.
    """
    session = _profil(Grip.PALM, 150.0, 65.0, Thenar.PETITE, BudgetMode.CUSTOM, 25.0)
    problems, texte, (ideal, alternative, economy) = _juger(session)
    assert problems == [] and alternative is not None and economy is not None
    selection = compute_selection(session)
    embeds = results_embeds(session, selection)
    problems = check_result_message(session, selection, embeds, ideal, None, economy)
    assert problems == [], "l'économie hors zone ne doit PAS être reprochée comme une alternative"
    assert f"{economy.mouse.price_eur:.2f}".replace(".", ",") + " €" in texte

    # Contre-épreuve : si le message annonce « L'alternative » là où le moteur propose une piste
    # (ici l'U2, hors de la zone du mode et plus chère que le match idéal), le banc le dit.
    menteur = _BlocFactice(texte.replace("🔎 Autre piste", "🥈 L'alternative"))
    problems = check_result_message(session, selection, [menteur], ideal, alternative, economy)
    assert any("deuxième place « autre piste » sans le dire" in p for p in problems), problems


def test_le_banc_accepte_le_libelle_l_autre_option_quand_la_troisieme_place_coute_plus_cher():
    """Décision du propriétaire du 2026-10-12 : la 3e place reste remplie, et le titre dit la vérité."""
    session = _profil(Grip.PALM, 160.0, 70.0, Thenar.PETITE)
    problems, texte, (ideal, alternative, economy) = _juger(session)
    assert economy is not None and alternative is not None
    assert economy.mouse.price_eur > min(ideal.mouse.price_eur, alternative.mouse.price_eur)
    libelle = third_slot_title(economy, ideal, alternative)
    assert libelle == "➕ L'autre option"
    assert libelle in texte
    assert problems == []


def test_le_banc_accepte_le_libelle_economie_quand_la_troisieme_place_coute_moins_cher():
    session = _profil(Grip.PALM, 160.0, 100.0, Thenar.PETITE)
    problems, texte, (ideal, alternative, economy) = _juger(session)
    assert economy is not None and alternative is not None
    assert economy.mouse.price_eur < min(ideal.mouse.price_eur, alternative.mouse.price_eur)
    assert third_slot_title(economy, ideal, alternative) == "💸 L'économie"
    assert "💸 L'économie" in texte
    assert problems == []


def test_le_banc_detecte_un_libelle_de_troisieme_place_qui_ment():
    """Contre-épreuve : si le titre annoncé ne correspond plus au prix, le banc le dit."""
    session = _profil(Grip.PALM, 160.0, 70.0, Thenar.PETITE)
    problems, texte, (ideal, alternative, economy) = _juger(session)
    assert problems == []
    assert "➕ L'autre option" in texte
    menteur = _BlocFactice(texte.replace("➕ L'autre option", "💸 L'économie"))
    problems = check_result_message(session, compute_selection(session), [menteur],
                                    ideal, alternative, economy)
    assert any("troisième place mal étiquetée" in probleme for probleme in problems)


def test_les_libelles_comptes_par_le_rapport_statistique_sont_ceux_du_moteur():
    """Le rapport compte les titres « 💸 L'économie » / « ➕ L'autre option » produits par le moteur :
    ses constantes doivent être exactement ces libellés (sinon le comptage tombe à zéro en silence)."""
    from tools import recommendation_stats as stats

    assert stats.ECONOMIE_TITLE == third_slot_title(
        SimpleNamespace(mouse=SimpleNamespace(price_eur=10.0)),
        SimpleNamespace(mouse=SimpleNamespace(price_eur=100.0)), None)
    assert stats.AUTRE_OPTION_TITLE == third_slot_title(
        SimpleNamespace(mouse=SimpleNamespace(price_eur=100.0)),
        SimpleNamespace(mouse=SimpleNamespace(price_eur=10.0)), None)


def test_le_compteur_du_prix_non_verifie_ne_compte_que_les_places_affichees():
    """Le chiffre publié (« 3 332 places portent « (prix non vérifié) » ») vient de cette fonction :
    elle ne doit compter ni les places vides, ni les prix attestés."""
    atteste = SimpleNamespace(mouse=SimpleNamespace(price_status="verified"))
    non_atteste = SimpleNamespace(mouse=SimpleNamespace(price_status="owner_spec_unverified"))
    assert places_au_prix_non_verifie((non_atteste, atteste, None)) == 1
    assert places_au_prix_non_verifie((atteste, atteste, atteste)) == 0
    assert places_au_prix_non_verifie((None, None, None)) == 0
    assert places_au_prix_non_verifie((non_atteste, non_atteste, non_atteste)) == 3


def test_le_compteur_de_coque_partagee_regarde_toutes_les_paires():
    """Défaut réel du 2026-10-14 : le banc ne comptait que les paires formées avec le match idéal.

    Sa phrase, elle, parle de « deux places » — et le rapport statistique, sur la même grille, comptait
    **1 367** profils là où le banc en annonçait **966** : la paire (alternative, économie), réelle quand
    la deuxième place a trouvé une autre coque et que la troisième reprend celle du match idéal, était
    ignorée. Ce test fige la règle : **toute** paire de places affichées compte.
    """
    from utils.matcher import STATUS_SCORED, MouseScore, ScoreBreakdown

    def score(ident: str, coque: str | None) -> MouseScore:
        souris = SimpleNamespace(label=ident, id=ident, shell_id=coque, length_mm=120.0,
                                 width_max_mm=60.0, hump_position="Inconnu", button_height="Inconnu",
                                 price_eur=49.9, price_status="verified", shape="Symmetrical")
        return MouseScore(mouse=souris, grip=Grip.PALM, status=STATUS_SCORED, breakdown=ScoreBreakdown())

    a, b, c = score("a", "coque_1"), score("b", "coque_2"), score("c", "coque_3")
    # Cas que le banc ratait : seule la paire (alternative, économie) partage une coque.
    assert deux_places_meme_coque((a, b, c)) is False
    alt_eco = score("c2", "coque_2")
    assert deux_places_meme_coque((a, b, alt_eco)) is True
    # Les autres paires comptent aussi, et une place vide ne compte jamais.
    ideal_eco = score("c3", "coque_1")
    assert deux_places_meme_coque((a, b, ideal_eco)) is True
    assert deux_places_meme_coque((a, score("b2", "coque_1"), None)) is True
    assert deux_places_meme_coque((a, None, None)) is False
    assert deux_places_meme_coque((None, None, None)) is False
    # Même souris montrée deux fois (jamais censé arriver) : c'est déjà un problème signalé ailleurs,
    # mais le compteur de coque doit, lui aussi, le voir.
    assert deux_places_meme_coque((a, score("a", "coque_1"), None)) is True


def test_la_grille_du_banc_ne_contient_aucun_profil_duplique():
    """Défaut réel du 2026-10-14 : le banc itérait les trois thénars **aussi en Fingertip**.

    Le parcours n'y pose pas la question (`session.thenar = None`), donc les trois itérations
    produisaient la même entrée moteur : 5 434 des 27 170 profils annoncés (20,0 %) étaient le même
    profil mesuré trois fois. Chaque pourcentage « sur 27 170 » portait un dénominateur gonflé d'un
    cinquième. Ce test tient les deux grilles : **aucun doublon**, et les tailles attendues.
    """
    for rapide, attendu in ((True, 576), (False, 21736)):
        profils = list(grille(rapide))
        assert len(profils) == attendu, f"grille {'rapide' if rapide else 'complète'} : {len(profils)}"
        assert len(set(profils)) == len(profils), "profil mesuré deux fois dans la grille"
    # La règle du parcours, écrite noir sur blanc : thénar demandé en Palm et en Claw, jamais en
    # Fingertip — et un seul profil Fingertip par couple taille/prise.
    complet = list(grille(False))
    assert {e[3] for e in complet if e[0] is Grip.FINGERTIP} == {None}
    assert {e[3] for e in complet if e[0] is Grip.PALM} == {Thenar.PETITE, Thenar.MOYENNE, Thenar.GRANDE}
    assert None in {e[3] for e in complet if e[0] is Grip.CLAW}          # cas « thénar non répondu »
    assert sum(1 for e in complet if e[0] is Grip.FINGERTIP) == 2717
