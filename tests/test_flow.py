"""Simulation du flux Discord (interactions factices) : étapes, erreurs de saisie, édition de message,
isolation des parcours et confidentialité (aucune publication dans le salon).
"""
from __future__ import annotations

import re

import discord

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cogs import finder_flow as flow
from utils import selection
from utils.models import THENAR_LABELS, BudgetMode, ClawVariant, Grip, Thenar
from utils.session import SessionStore

ROOT = Path(__file__).resolve().parents[1]


def make_interaction(user_id: int = 99, store: SessionStore | None = None, has_message: bool = True):
    response = SimpleNamespace(
        send_message=AsyncMock(),
        edit_message=AsyncMock(),
        send_modal=AsyncMock(),
        is_done=MagicMock(return_value=False),
    )
    followup = SimpleNamespace(send=AsyncMock())
    client = SimpleNamespace(sessions=store if store is not None else SessionStore(ttl_seconds=600))
    message = SimpleNamespace(id=1) if has_message else None
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=response,
        followup=followup,
        client=client,
        message=message,
    )


def select_values(select, *values):
    select._values = list(values)  # discord.py lit _values en repli


def modal_with(modal, length=None, width=None):
    modal.length._value = length
    modal.width._value = width
    return modal


def modal_budget(value):
    modal = flow.BudgetModal()
    modal.price._value = value
    return modal


def fields_of(embed):
    return {f.name: f.value for f in embed.fields}


def embeds_of(inter):
    """Embeds envoyés/édités par une interaction (le résultat en compte deux)."""
    return inter.response.edit_message.call_args.kwargs["embeds"]


def main_embed_of(inter):
    return embeds_of(inter)[0]


def start_for(store: SessionStore, user_id: int = 99, grip=None, length=None, width=None,
              thenar=None, variant=None):
    s = store.start(user_id)
    s.grip, s.hand_length_mm, s.hand_width_mm, s.thenar = grip, length, width, thenar
    s.claw_variant = variant
    return s


# ---------------------------------------------------------------------------
# Accueil et étape 1
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_start_button_sends_ephemeral_step1_with_grip_select():
    inter = make_interaction()
    await flow.StartView().start.callback(inter)
    kwargs = inter.response.send_message.call_args.kwargs
    assert kwargs["ephemeral"] is True
    assert isinstance(kwargs["view"], flow.GripView)
    # Le dénominateur dépend de la prise choisie (3 étapes en Fingertip, 4 sinon) : « Étape 1 » sans total.
    assert kwargs["embed"].title.startswith("Étape 1")
    assert "prise" in kwargs["embed"].title.lower()
    session, status = inter.client.sessions.current(99)
    assert status == "ok" and session is not None and session.grip is None


@pytest.mark.asyncio
async def test_grip_selection_edits_message_to_thenar_step():
    """En Palm : prise → thénar (étape 2/4). En Claw, la variante s'intercale (voir test dédié)."""
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    inter = make_interaction(store=store)
    view = flow.GripView()
    select_values(view.children[0], "palm")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_awaited_once()
    assert store.get(s.session_id, 99).grip is Grip.PALM
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ThenarView)
    assert "Étape 2/4" in kwargs["embed"].title


@pytest.mark.asyncio
async def test_claw_selection_asks_the_variant_before_the_thenar_step():
    """Claw : étape 2/5 = variante de la prise (aucun effet sur le score), puis thénar 3/5."""
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    inter = make_interaction(store=store)
    view = flow.GripView()
    select_values(view.children[0], "claw")
    await view.children[0].callback(inter)
    assert store.get(s.session_id, 99).grip is Grip.CLAW
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ClawVariantView)
    assert "Étape 2/5" in kwargs["embed"].title
    options = [(o.label, o.value) for o in kwargs["view"].children[0].options]
    assert options == [("Claw relâchée", "relachee"), ("Claw agressive", "aggressive"),
                       ("Claw pincée", "pincee")]

    suite = make_interaction(store=store)
    select = kwargs["view"].children[0]
    select_values(select, "relachee")
    await select.callback(suite)
    assert store.get(s.session_id, 99).claw_variant is ClawVariant.RELACHEE
    suivant = suite.response.edit_message.call_args.kwargs
    assert isinstance(suivant["view"], flow.ThenarView)
    assert "Étape 3/5" in suivant["embed"].title

    # Le récapitulatif des étapes suivantes porte la variante, sous forme courte.
    fin = make_interaction(store=store)
    select_thenar = suivant["view"].children[0]
    select_values(select_thenar, "moyenne")
    await select_thenar.callback(fin)
    assert "(relâchée)" in fin.response.edit_message.call_args.kwargs["embed"].description


@pytest.mark.asyncio
async def test_thenar_selection_stores_value_and_moves_to_measures():
    """Parcours 4 étapes : le thénar est stocké puis l'étape mesures s'affiche."""
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.CLAW, variant=ClawVariant.RELACHEE)
    inter = make_interaction(store=store)
    view = flow.ThenarView()
    select_values(view.children[0], "moyenne")
    await view.children[0].callback(inter)
    assert store.get(s.session_id, 99).thenar is Thenar.MOYENNE
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.MeasureView)
    assert "Étape 4/5" in kwargs["embed"].title       # Claw : variante (2/5) puis thénar (3/5)
    assert "Thénar" in kwargs["embed"].description


@pytest.mark.asyncio
async def test_full_claw_walkthrough_follows_the_five_steps():
    """Claw : prise (1/5) → variante (2/5) → thénar (3/5) → mesures (4/5) → budget (5/5) → résultat."""
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)

    prise = make_interaction(store=store)
    view = flow.GripView()
    select_values(view.children[0], "claw")
    await view.children[0].callback(prise)
    assert "Étape 1" not in prise.response.edit_message.call_args.kwargs["embed"].title  # déjà passé

    variante = make_interaction(store=store)
    variante_view = flow.ClawVariantView()
    select_values(variante_view.children[0], "pincee")
    await variante_view.children[0].callback(variante)
    assert "Étape 2/5" in flow.claw_variant_step_embed().title
    assert "Étape 3/5" in variante.response.edit_message.call_args.kwargs["embed"].title

    thenar = make_interaction(store=store)
    thenar_view = flow.ThenarView()
    select_values(thenar_view.children[0], "petite")
    await thenar_view.children[0].callback(thenar)
    assert "Étape 4/5" in thenar.response.edit_message.call_args.kwargs["embed"].title

    mesures = make_interaction(store=store)
    await modal_with(flow.MeasureModal(), "180", "100").on_submit(mesures)
    assert "Étape 5/5" in mesures.response.edit_message.call_args.kwargs["embed"].title

    resultat = make_interaction(store=store)
    budget_view = flow.BudgetView()
    select_values(budget_view.children[0], BudgetMode.QUALITE_PRIX.value)
    await budget_view.children[0].callback(resultat)
    embeds = resultat.response.edit_message.call_args.kwargs["embeds"]
    assert [e.title for e in embeds] == [
        "🎯 Votre recommandation", "📐 Vos repères de taille",
        "🖐️ Un arrière étroit pour votre thénar", "⛰️ La bosse et la forme",
        "🦾 Claw pincée", "🖱️ La hauteur des boutons",
    ]
    assert "(pincée)" in embeds[0].description                      # la variante apparaît en haut
    assert "Claw pincée → bosse arrière, flancs peu bombés" in embeds[3].description
    # Parcours terminé : conservé quelques minutes pour un clic rejoué, plus jamais sur disque.
    assert store.get(s.session_id, 99).finished is True


def test_thenar_select_only_proposes_the_three_valid_sizes():
    view = flow.ThenarView()
    select = view.children[0]
    assert [(o.label, o.value) for o in select.options] == [
        ("Petite", "petite"), ("Moyenne", "moyenne"), ("Grande", "grande"),
    ]


def test_thenar_labels_are_french_and_mapped():
    assert [THENAR_LABELS[t] for t in Thenar] == ["Petite", "Moyenne", "Grande"]


@pytest.mark.asyncio
async def test_fingertip_skips_the_thenar_step_and_shortens_the_path():
    """Fingertip : l'arrière de la souris n'est pas utilisé → pas d'étape thénar (parcours 1 → 3 étapes)."""
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    inter = make_interaction(store=store)
    view = flow.GripView()
    select_values(view.children[0], "fingertip")
    await view.children[0].callback(inter)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.MeasureView), "on va directement à l'étape des mesures"
    assert "Étape 2/3" in kwargs["embed"].title
    session = store.get(s.session_id, 99)
    assert session.grip is Grip.FINGERTIP and session.thenar is None

    measures = make_interaction(store=store)
    await modal_with(flow.MeasureModal(), "190", "95").on_submit(measures)
    budget_title = measures.response.edit_message.call_args.kwargs["embed"].title
    assert "Étape 3/3" in budget_title


@pytest.mark.asyncio
async def test_fingertip_result_has_no_thenar_note_nor_rear_illustration(monkeypatch):
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.FINGERTIP, length=190.0, width=95.0)
    session.budget_mode = BudgetMode.ECONOMIQUE
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    # Fingertip : ni thénar, ni arrière étroit, ni conseil de bosse (elle n'y travaille pas).
    assert [e.title for e in embeds] == ["🎯 Votre recommandation", "📐 Vos repères de taille",
                                         "🖱️ La hauteur des boutons"]
    assert not any("Thénar" in field.name for embed in embeds for field in embed.fields)
    assert all("arriere_etroit" not in (embed.image.url or "") for embed in embeds)
    assert "T02_boutons_bas" in embeds[0].image.url  # bosse ignorée en Fingertip → illustration des boutons


def test_steps_total_follows_the_grip():
    """Palm 4 étapes, Claw 5 (la variante s'ajoute), Fingertip 3 (le thénar est sauté)."""
    assert flow._steps_total(Grip.PALM) == 4
    assert flow._steps_total(Grip.CLAW) == 5
    assert flow._steps_total(Grip.FINGERTIP) == 3


@pytest.mark.asyncio
async def test_measure_button_opens_modal_without_new_message():
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, thenar=Thenar.MOYENNE)   # le parcours est à l'étape des mesures
    inter = make_interaction(store=store)
    await flow.MeasureView().open_measures.callback(inter)
    inter.response.send_modal.assert_awaited_once()
    inter.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_measures_move_to_budget_step():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    await modal_with(flow.MeasureModal(), "180", "90").on_submit(inter)
    s = store.get(s.session_id, 99)
    assert (s.hand_length_mm, s.hand_width_mm) == (180.0, 90.0)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.BudgetView)
    assert "Étape 4/4" in kwargs["embed"].title


@pytest.mark.asyncio
async def test_invalid_measures_show_error_and_keep_step():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    await modal_with(flow.MeasureModal(), "abc", "900").on_submit(inter)
    inter.response.edit_message.assert_not_awaited()
    inter.response.send_message.assert_awaited_once()
    msg = inter.response.send_message.call_args.args[0]
    assert "Saisie invalide" in msg and "Longueur" in msg and "Largeur" in msg
    assert inter.response.send_message.call_args.kwargs["ephemeral"] is True
    assert store.get(s.session_id, 99).hand_length_mm is None


# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_standard_budget_shows_results_with_percentage_wording():
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.QUALITE_PRIX.value)
    await view.children[0].callback(inter)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ResultsView)
    # Aucun bouton interactif : seuls des liens d'achat, ou le rappel désactivé « Liens à venir ».
    assert all(getattr(c, "url", None) or getattr(c, "disabled", False) for c in kwargs["view"].children)
    # La recommandation (courte) puis les blocs d'explication, plus bas (ici : Palm sans thénar).
    assert len(kwargs["embeds"]) == 4
    main, guide = kwargs["embeds"][0], kwargs["embeds"][1]
    fields = fields_of(main)
    ideal = next(v for k, v in fields.items() if "match idéal" in k)
    alt = next(v for k, v in fields.items() if "alternative" in k)
    # Depuis l'ouverture du critère « hauteur des boutons » (2026-10-12), le classement réel du
    # profil Palm 180 × 90 en Qualité/Prix place l'ATK GHOST Ultimate en tête (30/40, 68,95 €),
    # suivie du Scyrox V6 (30/40) : deux coques différentes, jamais deux variantes de la même.
    assert "ATK GHOST Ultimate" in ideal
    assert "68,95 €" in ideal and "**75 %**" in ideal   # nom · poids · prix · pourcentage · forme
    assert "Score" not in ideal and "Confiance" not in ideal and "pts" not in ideal
    assert "**75 %**" in alt                            # l'alternative porte aussi son pourcentage
    assert "Scyrox V6" in alt
    assert guide.title == "📐 Vos repères de taille"
    guide_text = (guide.description or "") + " ".join(f.value for f in guide.fields)
    assert "30/40" in guide_text and "maximum théorique" in guide_text   # le score s'explique ici
    # La donnée manquante est annoncée en clair, dans le bloc bas (jamais en haut du message).
    assert "Hauteur des boutons non documentée" in guide_text
    assert "Pourquoi ce choix" in " ".join(f.name for f in guide.fields)
    # La souris choisie est reliée aux repères de taille, juste au-dessus.
    assert any(f.name.startswith("🔎 ATK GHOST Ultimate") and "en clair" in f.name for f in guide.fields)
    assert "Confiance" not in " ".join(str(e.to_dict()) for e in kwargs["embeds"])
    assert "ni une probabilité" in kwargs["embeds"][-1].footer.text


@pytest.mark.asyncio
async def test_result_never_mentions_the_excluded_mice():
    """Demande du propriétaire (2026-10-11) : l'utilisateur ne voit plus les souris écartées."""
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    s.budget_mode = BudgetMode.HAUT_DE_GAMME
    text = " ".join(str(e.to_dict()) for e in flow.results_embeds(s, flow.compute_selection(s)))
    assert "écart" not in text and "Non classées" not in text
    assert "matrice_profils" not in text and "docs/" not in text
    assert "Confiance" not in text and "confiance" not in text
    assert "Phantom" not in text


def test_result_sections_follow_the_reference_tool_order():
    """Recommandation, puis repères de taille, bosse et boutons — comme l'outil de référence."""
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    assert [e.title for e in embeds] == [
        "🎯 Votre recommandation",
        "📐 Vos repères de taille",
        "⛰️ La bosse et la forme",
        "🖱️ La hauteur des boutons",
    ]
    assert all("Score" not in f.value and "Confiance" not in f.value for f in embeds[0].fields)
    guide = embeds[1]
    assert "/40" in (guide.description or "")
    names = [f.name for f in guide.fields]
    assert names[0].startswith("🔎 ") and names[0].endswith(" en clair")
    assert names[1] == "🧭 Pourquoi ce choix ?"


def test_result_guides_describe_the_grip_and_show_the_matching_illustrations(monkeypatch):
    """Chaque bloc d'explication porte l'illustration de sa consigne (assets/images.json)."""
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    titles = lambda embeds: [e.title for e in embeds]
    image = lambda embed: embed.image.url.split("/")[-1].removesuffix(".png")

    def embeds_for(grip, thenar=None, variant=None):
        """Résultat pour une prise donnée (la variante de Claw peut être précisée)."""
        store = SessionStore(ttl_seconds=600)
        session = start_for(store, grip=grip, length=180.0, width=90.0, thenar=thenar)
        session.claw_variant = variant
        session.budget_mode = BudgetMode.QUALITE_PRIX
        selection = flow.compute_selection(session)
        return flow.results_embeds(session, selection)

    palm = embeds_for(Grip.PALM, thenar=Thenar.PETITE)
    assert "T13_arriere_etroit" in image(palm[2])          # arrière étroit, juste après les repères
    assert "T14_bosse_centrale" in image(palm[3])          # la bosse conseillée pour Palm
    assert "T01_boutons_hauts" in image(palm[4])           # les boutons conseillés pour Palm
    assert "Palm Grip → bosse" in palm[3].description and "Palm Grip → boutons hauts" in palm[4].description
    assert "**Forme**" in palm[3].description              # la forme de coque est conseillée ici aussi

    # Claw avec variante déclarée : un seul bloc de variante, illustré, et le conseil de bosse adapté.
    claw = embeds_for(Grip.CLAW, variant=ClawVariant.AGGRESSIVE)
    assert titles(claw) == ["🎯 Votre recommandation", "📐 Vos repères de taille",
                            "⛰️ La bosse et la forme", "🦾 Claw agressive",
                            "🖱️ La hauteur des boutons"]
    assert "T07_bosse_arriere" in image(claw[2])           # la bosse conseillée pour la prise
    assert "T05_griffe_agressive" in image(claw[3])        # l'illustration de la variante déclarée
    assert "T02_boutons_bas" in image(claw[4])
    assert "Claw agressive → bosse médiane marquée" in claw[2].description
    assert "Claw Grip → boutons bas" in claw[4].description

    # Sans variante (parcours ouvert avant l'ajout de l'étape) : les trois variantes, en repli.
    legacy = embeds_for(Grip.CLAW)
    assert ["T04_griffe_relachee", "T05_griffe_agressive", "T06_griffe_pince"] == [
        image(e) for e in legacy[3:6]]
    assert "Claw Grip → bosse au milieu ou à l'arrière" in legacy[2].description

    fingertip = embeds_for(Grip.FINGERTIP)
    assert titles(fingertip) == ["🎯 Votre recommandation", "📐 Vos repères de taille",
                                 "🖱️ La hauteur des boutons"]
    assert "T03_boutons_moyens" in image(fingertip[2])
    assert "médians à bas" in fingertip[2].description


@pytest.mark.asyncio
async def test_results_discard_session_after_display():
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.ECONOMIQUE.value)
    await view.children[0].callback(inter)
    # Minimisation : parcours terminé → ses réponses quittent le fichier d'état tout de suite.
    assert store.get(session.session_id, 99).finished is True


@pytest.mark.asyncio
async def test_custom_budget_opens_modal_from_select():
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.CUSTOM.value)
    await view.children[0].callback(inter)
    inter.response.send_modal.assert_awaited_once()
    inter.response.edit_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_custom_budget_invalid_then_valid():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)

    bad = make_interaction(store=store)
    await modal_budget("trois").on_submit(bad)
    bad.response.edit_message.assert_not_awaited()
    assert "Saisie invalide" in bad.response.send_message.call_args.args[0]

    good = make_interaction(store=store)
    await modal_budget("50").on_submit(good)
    embeds = good.response.edit_message.call_args.kwargs["embeds"]
    # Le mode choisit la tête de son classement ; on vérifie la mise en forme, pas une marque figée.
    assert "**" in fields_of(embeds[0])["🥇 Le match idéal"]
    assert "Confiance" not in " ".join(str(e.to_dict()) for e in embeds)
    assert store.get(s.session_id, 99).finished is True   # parcours terminé après résultat


# ---------------------------------------------------------------------------
# Confidentialité et isolation des parcours
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_old_message_never_breaks_a_running_parcours():
    """Panne corrigée le 2026-10-12 : un ancien message ne casse plus le parcours en cours.

    Avant, un clic dans le message d'une relance précédente répondait « ce parcours n'est plus
    actif » et le membre devait tout recommencer à zéro. Maintenant, l'action porte sur le parcours
    vivant du membre : le questionnaire se réaffiche au bon endroit, sans rien casser.
    """
    store = SessionStore(ttl_seconds=600)
    store.start(99)                    # premier envoi (son message reste affiché chez le membre)
    running = store.start(99)          # relance : c'est ce parcours qui est vivant
    inter = make_interaction(store=store)
    stale = flow.GripView()            # identifiant de composant identique dans les deux messages
    select_values(stale.children[0], "claw")
    await stale.children[0].callback(inter)
    assert store.get(running.session_id, 99).grip is Grip.CLAW     # le parcours vivant avance
    assert inter.response.send_message.call_args is None           # aucun message d'échec
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ClawVariantView)        # étape cohérente : la variante


@pytest.mark.asyncio
async def test_intruder_acts_only_on_his_own_parcours():
    """Aucun composant ne peut atteindre le parcours d'un autre membre.

    Le rattachement se fait par l'identifiant Discord de celui qui clique : l'intrus n'a pas de
    parcours, il reçoit le message de reprise, et le parcours de la victime reste intact.
    """
    store = SessionStore(ttl_seconds=600)
    victim = start_for(store, user_id=1, grip=Grip.PALM, thenar=Thenar.MOYENNE)
    intruder = make_interaction(user_id=2, store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.HAUT_DE_GAMME.value)
    await view.children[0].callback(intruder)
    intruder.response.edit_message.assert_not_awaited()
    msg = intruder.response.send_message.call_args.args[0]
    assert "a expiré" in msg
    assert isinstance(intruder.response.send_message.call_args.kwargs["view"], flow.StartView)
    assert store.get(victim.session_id, 1).budget_mode is None      # parcours de la victime intact
    assert store.get(victim.session_id, 1).finished is False


@pytest.mark.asyncio
async def test_intruder_cannot_open_the_measures_of_someone_else():
    store = SessionStore(ttl_seconds=600)
    victim = start_for(store, user_id=1, grip=Grip.PALM, thenar=Thenar.MOYENNE)
    intruder = make_interaction(user_id=2, store=store)
    await flow.MeasureView().open_measures.callback(intruder)
    intruder.response.send_modal.assert_not_awaited()

    intruder2 = make_interaction(user_id=2, store=store)
    await modal_with(flow.MeasureModal(), "180", "90").on_submit(intruder2)
    intruder2.response.edit_message.assert_not_awaited()
    assert store.get(victim.session_id, 1).hand_length_mm is None


def test_result_view_has_no_interactive_button_only_purchase_links():
    """Le résultat ne porte plus « Fermer » / « Refaire » / « Détails » (retirés le 2026-10-11).

    Restent les liens d'achat — des composants gérés par Discord, qui fonctionnent même si le bot
    redémarre — ou, faute de lien, le rappel désactivé « Liens à venir ». Aucun bouton du résultat
    ne peut donc rester muet.
    """
    from config import MOUSE_DB_PATH
    from utils.catalog import load_catalog

    mouse = load_catalog(MOUSE_DB_PATH)[0]
    linked = flow.ResultsView([SimpleNamespace(mouse=mouse)], {mouse.id: "https://shop.test/x"})
    assert [c.label for c in linked.children] == [f"Acheter {mouse.label}"[:80]]
    assert all(getattr(c, "url", None) for c in linked.children)
    assert linked.timeout is None

    empty = flow.ResultsView([SimpleNamespace(mouse=mouse)], {})
    assert [c.label for c in empty.children] == ["Liens à venir"]
    assert empty.children[0].disabled is True
    assert all(getattr(c, "custom_id", None) is None or c.disabled for c in empty.children)


@pytest.mark.asyncio
async def test_expired_session_informs_user_privately():
    inter = make_interaction(store=SessionStore(ttl_seconds=600))
    view = flow.GripView()
    select_values(view.children[0], "palm")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_not_awaited()
    assert "expiré" in inter.response.send_message.call_args.args[0]
    assert inter.response.send_message.call_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_show_private_falls_back_to_ephemeral_without_message():
    """Modal non lié à un composant (message absent) : repli sur un envoi éphémère, jamais public."""
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store, has_message=False)
    await modal_with(flow.MeasureModal(), "180", "90").on_submit(inter)
    inter.response.edit_message.assert_not_awaited()
    kwargs = inter.response.send_message.call_args.kwargs
    assert kwargs["ephemeral"] is True
    assert isinstance(kwargs["view"], flow.BudgetView)


@pytest.mark.asyncio
async def test_error_message_is_ephemeral_when_response_already_done():
    inter = make_interaction()
    inter.response.is_done.return_value = True
    await flow._send_ephemeral(inter, "x")
    inter.followup.send.assert_awaited_once()
    assert inter.followup.send.call_args.kwargs["ephemeral"] is True


# Contrôle statique de confidentialité : voir tests/test_privacy_scan.py (remplace l'ancien test textuel).


def test_every_step_component_is_persistent_and_unique():
    """Les composants des étapes doivent survivre à un redémarrage du bot (panne du 2026-10-12).

    Un composant durable n'a aucun délai et porte un identifiant FIXE, enregistré au démarrage par
    ``bot.add_view`` : c'est ce qui permet à un clic de fonctionner après un redémarrage. Deux
    composants ne peuvent pas partager le même couple (type, identifiant), sinon Discord enverrait
    le clic au mauvais menu.
    """
    import inspect

    views = flow.persistent_views()
    assert len(views) == 8
    assert isinstance(views[0], flow.StartView)
    seen = set()
    for view in views:
        assert view.timeout is None, type(view).__name__
        assert view.is_persistent(), type(view).__name__
        for item in view.walk_children():
            if not item.is_dispatchable():
                continue
            assert item.custom_id, type(item).__name__
            key = (type(item).__name__, item.custom_id)
            assert key not in seen, key
            seen.add(key)
    # Aucune vue d'étape ne dépend d'une donnée inscrite dans le message : elle se rattache au
    # membre qui clique (c'est ce qui rend la relance du bot transparente).
    for cls in (flow.GripView, flow.ClawVariantView, flow.ThenarView, flow.MeasureView,
                flow.BudgetView, flow.MeasureModal, flow.BudgetModal):
        assert list(inspect.signature(cls.__init__).parameters) == ["self"], cls.__name__


def test_missing_commercial_link_shows_disabled_placeholder_button():
    """Sans URL d'achat : un seul bouton désactivé « Liens à venir », jamais d'erreur ni de lien inventé."""
    from config import MOUSE_DB_PATH
    from utils.catalog import load_catalog

    mouse = load_catalog(MOUSE_DB_PATH)[0]
    view = flow.ResultsView([SimpleNamespace(mouse=mouse)], {})
    placeholder = [c for c in view.children if getattr(c, "disabled", False)]
    assert len(placeholder) == 1, "un seul bouton informatif, jamais un bouton grisé par souris"
    assert placeholder[0].label == "Liens à venir"
    assert not any(getattr(c, "url", None) for c in view.children if getattr(c, "disabled", False))
    assert not [c for c in view.children if c.label in ("Fermer", "Refaire le test", "Détails")]


def test_real_link_creates_purchase_button_without_placeholder():
    from config import MOUSE_DB_PATH
    from utils.catalog import load_catalog

    mouse = load_catalog(MOUSE_DB_PATH)[0]
    view = flow.ResultsView([SimpleNamespace(mouse=mouse)], {mouse.id: "https://shop.test/x"})
    link_buttons = [c for c in view.children if getattr(c, "url", None)]
    assert len(link_buttons) == 1 and link_buttons[0].label.startswith("Acheter ")
    assert link_buttons[0].url == "https://shop.test/x"
    assert not any(getattr(c, "disabled", False) for c in view.children)


# ---------------------------------------------------------------------------
# Refonte visuelle : charte, allègement du résultat, aucune donnée de debug
# ---------------------------------------------------------------------------
def test_embed_colors_follow_the_azemouse_charter():
    """Bordeaux #8A2342 partout, sauf « session expirée » (orange), et image de bannière branchée."""
    bordeaux = discord.Color.from_rgb(138, 35, 66)
    embeds = [
        flow.banner_embed(),
        flow.grip_step_embed(),
        flow.thenar_step_embed(),
        flow.budget_step_embed(start_for(SessionStore(ttl_seconds=600), grip=Grip.PALM,
                                         length=180.0, width=90.0, thenar=Thenar.MOYENNE)),
    ]
    assert all(e.color == bordeaux for e in embeds)
    assert flow.expired_embed().color == discord.Color.orange()


def test_result_lines_show_the_weight_then_the_shape_at_the_far_right():
    """Ligne du match idéal et de l'alternative : nom · poids · prix · % · forme (tout à droite)."""
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    fields = fields_of(embeds[0])
    for cle in ("🥇 Le match idéal", "🥈 L'alternative"):
        ligne = fields[cle]
        assert re.search(r"· \d+ g ·", ligne), ligne
        assert ligne.rstrip().endswith(("Symétrique", "Ergonomique")), ligne


def test_shape_is_not_invented_when_the_mouse_has_no_verified_shape():
    """Forme « Inconnu » : la ligne s'arrête au pourcentage (aucune mention inventée)."""
    assert flow.SHAPE_LINE_LABELS.get("Inconnu") is None
    assert flow.SHAPE_LINE_LABELS == {"Symmetrical": "Symétrique", "Ergonomic": "Ergonomique"}


def test_budget_step_proposes_five_modes_including_no_price():
    view = flow.BudgetView()
    options = view.children[0].options
    assert [o.value for o in options] == [
        "economique", "qualite_prix", "haut_de_gamme", "peu_importe_prix", "custom",
    ]
    no_price = options[3]
    assert no_price.label == "Peu importe le prix"
    assert "forme la plus adaptée" in no_price.description


def test_no_price_mode_shows_the_price_in_small_text_with_the_components():
    """« Peu importe le prix » : nom · pourcentage, puis le prix en petit + composants documentés."""
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.PEU_IMPORTE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    ideal = fields_of(embeds[0])["🥇 Le match idéal"]
    headline, small = ideal.split("\n")
    assert "%**" in headline and "€" not in headline        # le prix ne concurrence pas le pourcentage
    assert small.startswith("-# ") and "€" in small         # … il passe en tout petit
    assert "sans effet sur ce classement" in small
    assert "⚙️" in small                                    # composants documentés de la souris retenue


def test_price_is_still_on_the_main_line_in_the_other_modes():
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    ideal = fields_of(embeds[0])["🥇 Le match idéal"]
    assert "€" in ideal and "- #" not in ideal and "- #" not in ideal and "-#" not in ideal


def test_embeds_respect_discord_limits_and_stay_short():
    """Limites Discord et lisibilité mobile : champs ≤ 1024, description ≤ 4096, total ≤ 6000."""
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.CLAW, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    # Cas le plus long : recommandation, repères, arrière étroit, bosse, 3 variantes de Claw, boutons.
    assert len(embeds) == 8
    total = 0
    for embed in embeds:
        assert len(embed) <= 6000
        assert len(embed.fields) <= 4
        assert len(embed.description or "") <= 4096
        for field in embed.fields:
            assert len(field.value) <= 1024, field.name
            assert len(field.value) <= 700, f"champ trop long pour mobile : {field.name}"
        total += len(embed)
    assert total <= 6000


def test_result_never_exposes_internal_scoring_details():
    """P1 : aucune ligne « … : 10 pts », aucun score partiel, aucun « 100 % » nu."""
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.HAUT_DE_GAMME
    text = " ".join(str(embed.to_dict()) for embed in flow.results_embeds(session, flow.compute_selection(session)))
    # Aucune ligne de barème « … : N pts » ; la tolérance du mode reste dite en toutes lettres.
    assert re.search(r"\d+ pts(?! ou moins)", text) is None
    assert "adaptée : " not in text and "adaptés : " not in text and "vs cible" not in text
    assert "/25" not in text and "partiel" not in text
    assert "30/40" in text and "maximum théorique" in text


def test_result_image_key_prioritises_the_hump_then_the_buttons():
    def score(hump: str, button: str, grip: Grip = Grip.PALM) -> SimpleNamespace:
        return SimpleNamespace(mouse=SimpleNamespace(hump_position=hump, button_height=button), grip=grip)

    assert flow.result_image_key(score("Rear", "Low", Grip.CLAW), Grip.CLAW) == "illustration_hump_rear"
    assert flow.result_image_key(score("Mid-Front", "High"), Grip.PALM) == "illustration_hump_front"
    assert flow.result_image_key(score("Mid", "Mid"), Grip.PALM) == "illustration_hump_mid"
    assert flow.result_image_key(score("Inconnu", "High"), Grip.PALM) == "illustration_buttons_high"
    assert flow.result_image_key(score("Inconnu", "Low", Grip.FINGERTIP), Grip.FINGERTIP) == "illustration_buttons_low"
    assert flow.result_image_key(None, Grip.PALM) is None


def test_thenar_only_weighs_on_rear_hump_mice():
    """Reverse engineering Oblivity (2026-10-11) : le thénar ne touche que les souris à bosse arrière."""
    store_a = SessionStore(ttl_seconds=600)
    without = start_for(store_a, user_id=1, grip=Grip.PALM, length=180.0, width=90.0)
    without.budget_mode = BudgetMode.QUALITE_PRIX
    store_b = SessionStore(ttl_seconds=600)
    with_thenar = start_for(store_b, user_id=2, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.GRANDE)
    with_thenar.budget_mode = BudgetMode.QUALITE_PRIX
    base = flow.compute_selection(without)
    other = flow.compute_selection(with_thenar)
    # Le gagnant Palm (bosse Mid) n'est pas concerné : classement et scores identiques.
    assert base.ranked[0].mouse.id == other.ranked[0].mouse.id
    assert base.ranked[0].total == other.ranked[0].total == 30  # non-régression du barème Palm 180 × 90
    assert all(s.breakdown.thenar_pts == 0 for s in other.ranked if s.mouse.hump_position != "Rear")


def test_thenar_petite_adds_a_narrow_rear_paragraph_with_its_illustration(monkeypatch):
    """Thénar « Petite » : un paragraphe dédié, illustré (T13), affiché plus bas dans le message."""
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    narrow = next(e for e in embeds if "arrière étroit" in e.title)
    assert "arrière étroit" in narrow.title
    assert "pilule" in narrow.description and "pénalisée à la marge" in narrow.description
    assert narrow.image is not None and "T13_arriere_etroit" in narrow.image.url
    # Le bloc « comment lire ce résultat » garde l'illustration des repères de taille.
    assert "T12_souris_longueur_largeur" in embeds[1].image.url


def test_step_illustrations_are_branched_when_image_base_url_is_set(monkeypatch):
    """Assets ImageUse : bannière T08, grips T09, thénar T10, mesures T11 (résolution IMAGES_BASE_URL)."""
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    assert "T08_azemouse_banniere" in flow.banner_embed().image.url
    assert "T09_griffe_paume_doigts" in flow.grip_step_embed().image.url
    assert "T10_tailles_de_main" in flow.thenar_step_embed().image.url
    session = start_for(SessionStore(ttl_seconds=600), grip=Grip.PALM, length=180.0, width=90.0)
    assert "T11_mesurer_la_main" in flow.measure_step_embed(session).image.url
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    details = embeds[1]
    assert "T12_souris_longueur_largeur" in details.image.url


def test_without_image_base_url_no_image_is_attached_and_nothing_breaks(monkeypatch):
    monkeypatch.setattr("config.IMAGES_BASE_URL", "")
    assert flow.banner_embed().image.url is None
    assert flow.grip_step_embed().image.url is None


def test_result_hump_illustration_follows_the_winner(monkeypatch):
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    main = flow.results_embeds(session, flow.compute_selection(session))[0]
    # Illustration liée à la bosse de la souris RÉELLEMENT retenue : ATK GHOST (bosse arrière) → T07.
    assert "T07_bosse_arriere" in main.image.url


@pytest.mark.asyncio
async def test_two_slots_never_show_the_same_shell():
    """2026-10-12 : le match idéal et l'alternative ne sont jamais deux variantes de la même coque.

    « ATK GHOST Ultimate » puis « ATK GHOST Extreme » serait la même souris deux fois : le résultat
    descend donc la liste jusqu'à une coque différente.
    """
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    ideal, alternative, _ = flow.result_slots(flow.compute_selection(session))
    assert ideal is not None and alternative is not None
    assert not selection._same_shell(ideal, alternative)
    assert (ideal.mouse.label, alternative.mouse.label) == ("ATK GHOST Ultimate", "Scyrox V6")


@pytest.mark.asyncio
async def test_double_tap_on_the_measure_button_does_not_show_an_error():
    """Double appui (fréquent sur mobile) : le second clic ne produit ni erreur ni second formulaire."""
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    inter.response.send_modal = AsyncMock(side_effect=discord.InteractionResponded(inter))
    await flow.MeasureView().open_measures.callback(inter)
    inter.response.send_message.assert_not_awaited()
    inter.followup.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_double_tap_on_the_custom_budget_menu_does_not_show_an_error():
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.CUSTOM.value)
    inter.response.send_modal = AsyncMock(side_effect=discord.InteractionResponded(inter))
    await view.children[0].callback(inter)
    inter.response.send_message.assert_not_awaited()
    inter.followup.send.assert_not_awaited()
