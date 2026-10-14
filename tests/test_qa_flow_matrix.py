"""Tests du banc d'essai `tools/qa_flow_matrix.py` lui-même.

Un banc d'essai qui se trompe de rôle fait plus de dégâts qu'il n'en évite : le 2026-10-12, la
troisième place était jugée « à la place de l'alternative » dès que celle-ci était vide (liste des
souris montrées filtrée puis relue par position). Résultat : 15 064 avertissements fantômes sur la
grille complète, tous du même faux positif « alternative élargie mais plus chère ». Ces tests
verrouillent la lecture **par rôle** et le contrôle des libellés de la troisième place.
"""
from __future__ import annotations

import sys

import discord
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cogs.finder_flow import compute_selection, result_slots, results_embeds, third_slot_title  # noqa: E402
from config import COMMERCIAL_LINKS_PATH  # noqa: E402
from tests.test_code_hygiene import _paquet_avec_bytecode_perime  # noqa: E402
from tools.qa_flow_matrix import (check_embed_limits, check_result_message, check_view_limits,
                                  deux_places_meme_coque, grille,
                                  message_text, places_au_prix_non_verifie,
                                  profile, verifier_bytecode)  # noqa: E402
from utils.catalog import load_commercial_links  # noqa: E402
from utils.models import BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402
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


def _places_du_profil(grip, length, width, thenar, mode, budget) -> int:
    session = profile(mode, budget)
    session.grip = grip
    session.hand_length_mm = length
    session.hand_width_mm = width
    session.thenar = thenar if grip is not Grip.FINGERTIP else None
    if grip is Grip.CLAW:
        session.claw_variant = ClawVariant.RELACHEE
    return len([place for place in result_slots(compute_selection(session)) if place is not None])


def test_les_places_manquantes_viennent_toutes_d_un_budget_personnalise():
    """« Trois lignes partout où le budget le permet » : un trou ne vient que d'un budget épuisé.

    Mesure de la grille complète (2026-10-14, 21 736 entrées distinctes) : **18 694** profils à trois
    places (86,00 %), **793** à deux, **182** à une, **2 067** sans aucun résultat — et aucun de ces
    trous hors des trois budgets personnalisés serrés (10, 25 et 45 €) : les six autres modes
    remplissent les trois places pour **tous** leurs profils. L'échantillon ci-dessous est petit mais
    il exige des trous : un échantillon vide ne prouverait rien (règle des tests creux).
    """
    prises = [(Grip.PALM, Thenar.PETITE), (Grip.CLAW, None), (Grip.FINGERTIP, None)]
    modes = [(None, None), (BudgetMode.ECONOMIQUE, None), (BudgetMode.CUSTOM, 10.0),
             (BudgetMode.CUSTOM, 25.0), (BudgetMode.CUSTOM, 45.0)]
    trous, pleins = [], 0
    for grip, thenar in prises:
        for length in (150.0, 200.0):
            for width in (60.0, 100.0):
                for mode, budget in modes:
                    places = _places_du_profil(grip, length, width, thenar, mode, budget)
                    if places == 3:
                        pleins += 1
                        continue
                    trous.append((grip.value, length, width, mode, budget, places))
    assert len(trous) >= 10, f"échantillon sans trou : il ne prouverait rien ({len(trous)} trous)"
    assert pleins >= 20, f"échantillon sans profil complet : il ne prouverait rien ({pleins})"
    hors_budget_serre = [t for t in trous if t[3] is not BudgetMode.CUSTOM or t[4] not in (10.0, 25.0, 45.0)]
    assert hors_budget_serre == [], f"des trous hors budget épuisé : {hors_budget_serre}"


def _bloc(titre="", description="", pied="", auteur="", champs=()):
    embed = discord.Embed(title=titre or None, description=description or None)
    if pied:
        embed.set_footer(text=pied)
    if auteur:
        embed.set_author(name=auteur)
    for nom, valeur in champs:
        embed.add_field(name=nom, value=valeur)
    return embed


def test_le_banc_mesure_toutes_les_limites_d_un_bloc_discord():
    """Un bloc hors limites est signalé — titre, pied et auteur compris.

    Le banc ne vérifiait que cinq des neuf limites d'un bloc jusqu'au 2026-10-14 : un titre de plus de
    256 caractères, un pied de plus de 2 048 et un auteur de plus de 256 passaient sans un mot. Ils sont
    désormais mesurés, et le bloc conforme ne produit rien (sinon le contrôle serait bruyant).
    """
    conforme = _bloc(titre="🎯 Votre recommandation", description="court", pied="Repère",
                     auteur="AzeMouse", champs=[("🥇 Le match idéal", "ATK Z1 · 59,95 € · **75 %**")])
    assert check_embed_limits([conforme]) == []
    assert check_embed_limits([_bloc(titre="t" * 257)]) != []
    assert check_embed_limits([_bloc(pied="p" * 2049)]) != []
    assert check_embed_limits([_bloc(auteur="a" * 257)]) != []
    assert check_embed_limits([_bloc(description="d" * 4097)]) != []
    assert check_embed_limits([_bloc(champs=[("n" * 257, "v")])]) != []
    assert check_embed_limits([_bloc(champs=[("n", "v" * 1025)])]) != []
    # Le total (6 000) additionne titre, description, champs, pied ET auteur.
    # 256 + 4 096 + 2 048 + 256 = 6 656 caractères : seule la somme dépasse (chaque partie est à sa
    # limite), donc c'est bien le contrôle du total qui parle.
    gros = _bloc(titre="t" * 256, description="d" * 4096, pied="p" * 2048, auteur="a" * 256)
    assert any("6000" in probleme for probleme in check_embed_limits([gros]))
    assert check_embed_limits([conforme] * 11) != []          # plus de dix blocs


def test_le_banc_mesure_toutes_les_limites_d_une_vue_discord():
    """Un composant hors limites est signalé — ces limites-là, Discord les refuse à l'envoi.

    `discord.py` ne refuse à la construction que le nombre d'enfants (25) et les rangées (0 à 4) :
    un libellé de bouton de 100 caractères, une adresse de 620, un `custom_id` de 150 et un menu à
    30 options **passent** la construction et sont refusés par Discord **à l'envoi** — le membre ne
    verrait alors aucun résultat, sans erreur lisible. Le banc les mesure depuis le 2026-10-14.
    """
    conforme = discord.ui.View()
    conforme.add_item(discord.ui.Button(label="Acheter ATK Z1 Ultra", url="https://exemple.test/z1"))
    conforme.add_item(discord.ui.Select(options=[discord.SelectOption(label="Palm Grip", value="p")]))
    assert check_view_limits(conforme) == []

    long_libelle = discord.ui.View()
    long_libelle.add_item(discord.ui.Button(label="l" * 100, url="https://exemple.test/z1"))
    assert check_view_limits(long_libelle) != []

    longue_url = discord.ui.View()
    longue_url.add_item(discord.ui.Button(label="ok", url="https://exemple.test/" + "x" * 600))
    assert any("adresse" in probleme for probleme in check_view_limits(longue_url))

    long_id = discord.ui.View()
    long_id.add_item(discord.ui.Button(label="ok", custom_id="c" * 150))
    assert any("custom_id" in probleme for probleme in check_view_limits(long_id))

    trente_options = discord.ui.View()
    trente_options.add_item(discord.ui.Select(
        options=[discord.SelectOption(label=f"option {i}", value=f"v{i}") for i in range(30)]))
    assert any("options" in probleme for probleme in check_view_limits(trente_options))

    longue_option = discord.ui.View()
    longue_option.add_item(discord.ui.Select(
        options=[discord.SelectOption(label="x" * 120, value="v",
                                      description="d" * 120)]))
    problemes = check_view_limits(longue_option)
    assert any("libellé d'option" in p for p in problemes)
    assert any("description d'option" in p for p in problemes)

    assert check_view_limits(discord.ui.View()) != []          # vue vide


def test_le_banc_releve_la_limite_la_plus_remplie_du_passage():
    """La ligne de synthèse nomme le composant le plus proche de son plafond, et se rejoue.

    « 0 dépassement » ne dit pas si l'on passe à un cheveu d'une limite ou si l'on a de la place : le
    banc relève donc la plus grande valeur vue pour chaque limite, et publie la plus **remplie** (en
    fraction de sa limite — un compte d'options et une longueur de texte ne se soustraient pas).
    """
    import tools.qa_flow_matrix as banc_mod

    sauvegarde = dict(banc_mod.MARGES)
    try:
        banc_mod.MARGES.clear()
        assert "aucune mesure" in banc_mod.resume_des_marges()      # banc interrompu : le dire
        check_embed_limits([_bloc(titre="t" * 100, champs=[("n", "v" * 20)])])
        assert banc_mod.MARGES["titre de bloc"] == (100, 256)
        assert banc_mod.MARGES["valeur de champ"] == (20, 1024)
        assert "titre de bloc" in banc_mod.resume_des_marges()      # 100/256 > 20/1024
        vue = discord.ui.View()
        vue.add_item(discord.ui.Select(options=[discord.SelectOption(label="Palm Grip", value="p",
                                                                     description="d" * 99)]))
        check_view_limits(vue)
        assert "« description d'option » — 99/100 (99 % de la limite)" in banc_mod.resume_des_marges()
    finally:
        banc_mod.MARGES.clear()
        banc_mod.MARGES.update(sauvegarde)


def test_le_banc_refuse_de_mesurer_sur_un_bytecode_perime(tmp_path, monkeypatch):
    """Un banc qui mesure un autre code que le code livré ne vaut rien : il doit refuser la mesure.

    Défaut trouvé le 2026-10-14 (68e passe, C90) : une mutation d'essai de `result_slots` a survécu
    dans le `.pyc` (source remise à l'identique : même taille, même seconde), et le banc a publié
    10 678 problèmes — dont « 9 768 profils » où l'ordre des pourcentages n'était pas garanti — sur un
    moteur que le dépôt n'avait pas. Le refus est vérifié sur un dossier piégé plutôt que sur le dépôt
    lui-même : un test ne modifie jamais le code livré, et la garde doit tenir dans les deux cas.
    """
    assert verifier_bytecode() is None, "le dépôt lui-même doit être propre"

    _paquet_avec_bytecode_perime(tmp_path)
    monkeypatch.setattr("tools.qa_flow_matrix.ROOT", tmp_path)

    refus = verifier_bytecode()

    assert refus is not None and "mesure refusée" in refus
    assert "check_bytecode.py --purge" in refus
