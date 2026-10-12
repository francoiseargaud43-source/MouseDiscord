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
from tools.qa_flow_matrix import check_result_message, message_text  # noqa: E402
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


def _juger(session: FinderSession) -> tuple[list[str], str, tuple]:
    """Rejoue le résultat complet et renvoie (problèmes du banc, texte affiché, les trois places)."""
    selection = compute_selection(session)
    ideal, alternative, economy = result_slots(selection)
    embeds = results_embeds(session, selection)
    problems = check_result_message(session, selection, embeds, ideal, alternative, economy)
    return problems, message_text(embeds), (ideal, alternative, economy)


def test_le_banc_ne_confond_pas_les_places_quand_l_alternative_est_vide():
    """Régression : alternative vide → l'économie reste l'économie (aucun faux positif de prix)."""
    session = _profil(Grip.PALM, 150.0, 65.0, Thenar.PETITE, BudgetMode.CUSTOM, 25.0)
    problems, texte, (ideal, alternative, economy) = _juger(session)
    assert alternative is None                     # la situation qui déclenchait le décalage
    assert economy is not None and economy.mouse.price_eur == 22.95
    assert problems == []
    assert f"{economy.mouse.price_eur:.2f}".replace(".", ",") + " €" in texte


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
