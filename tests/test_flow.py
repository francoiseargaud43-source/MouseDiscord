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
from utils.models import THENAR_LABELS, BudgetMode, Grip, Thenar
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


def modal_budget(session_id, value):
    modal = flow.BudgetModal(session_id)
    modal.price._value = value
    return modal


def fields_of(embed):
    return {f.name: f.value for f in embed.fields}


def embeds_of(inter):
    """Embeds envoyés/édités par une interaction (le résultat en compte deux)."""
    return inter.response.edit_message.call_args.kwargs["embeds"]


def main_embed_of(inter):
    return embeds_of(inter)[0]


def start_for(store: SessionStore, user_id: int = 99, grip=None, length=None, width=None, thenar=None):
    s = store.start(user_id)
    s.grip, s.hand_length_mm, s.hand_width_mm, s.thenar = grip, length, width, thenar
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
    session = inter.client.sessions.get(kwargs["view"].children[0].session_id, 99)
    assert session is not None


@pytest.mark.asyncio
async def test_grip_selection_edits_message_to_thenar_step():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    inter = make_interaction(store=store)
    view = flow.GripView(s.session_id)
    select_values(view.children[0], "claw")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_awaited_once()
    assert store.get(s.session_id, 99).grip is Grip.CLAW
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ThenarView)
    assert "Étape 2/4" in kwargs["embed"].title


@pytest.mark.asyncio
async def test_thenar_selection_stores_value_and_moves_to_measures():
    """Parcours 4 étapes : le thénar est stocké puis l'étape mesures s'affiche."""
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.CLAW)
    inter = make_interaction(store=store)
    view = flow.ThenarView(s.session_id)
    select_values(view.children[0], "moyenne")
    await view.children[0].callback(inter)
    assert store.get(s.session_id, 99).thenar is Thenar.MOYENNE
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.MeasureView)
    assert "Étape 3/4" in kwargs["embed"].title
    assert "Thénar" in kwargs["embed"].description


def test_thenar_select_only_proposes_the_three_valid_sizes():
    view = flow.ThenarView("session")
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
    view = flow.GripView(s.session_id)
    select_values(view.children[0], "fingertip")
    await view.children[0].callback(inter)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.MeasureView), "on va directement à l'étape des mesures"
    assert "Étape 2/3" in kwargs["embed"].title
    session = store.get(s.session_id, 99)
    assert session.grip is Grip.FINGERTIP and session.thenar is None

    measures = make_interaction(store=store)
    await modal_with(flow.MeasureModal(s.session_id), "190", "95").on_submit(measures)
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
    assert flow._steps_total(Grip.PALM) == 4 and flow._steps_total(Grip.CLAW) == 4
    assert flow._steps_total(Grip.FINGERTIP) == 3


@pytest.mark.asyncio
async def test_measure_button_opens_modal_without_new_message():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    inter = make_interaction(store=store)
    await flow.MeasureView(s.session_id).open_measures.callback(inter)
    inter.response.send_modal.assert_awaited_once()
    inter.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_measures_move_to_budget_step():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM)
    inter = make_interaction(store=store)
    await modal_with(flow.MeasureModal(s.session_id), "180", "90").on_submit(inter)
    s = store.get(s.session_id, 99)
    assert (s.hand_length_mm, s.hand_width_mm) == (180.0, 90.0)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.BudgetView)
    assert "Étape 4/4" in kwargs["embed"].title


@pytest.mark.asyncio
async def test_invalid_measures_show_error_and_keep_step():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM)
    inter = make_interaction(store=store)
    await modal_with(flow.MeasureModal(s.session_id), "abc", "900").on_submit(inter)
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
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    inter = make_interaction(store=store)
    view = flow.BudgetView(s.session_id)
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
    assert "Scyrox V6" in ideal
    assert "74,90 €" in ideal and "**75 %**" in ideal   # nom · prix · pourcentage, rien de plus
    assert "Score" not in ideal and "Confiance" not in ideal and "pts" not in ideal
    assert "**75 %**" in alt                            # l'alternative porte aussi son pourcentage
    assert "Z1" in alt
    assert guide.title == "📐 Vos repères de taille"
    guide_text = (guide.description or "") + " ".join(f.value for f in guide.fields)
    assert "30/40" in guide_text and "maximum théorique" in guide_text   # le score s'explique ici
    assert "Pourquoi ce choix" in " ".join(f.name for f in guide.fields)
    # La souris choisie est reliée aux repères de taille, juste au-dessus.
    assert any(f.name.startswith("🔎 Scyrox V6") and "en clair" in f.name for f in guide.fields)
    assert "Confiance" not in " ".join(str(e.to_dict()) for e in kwargs["embeds"])
    assert "ni une probabilité" in kwargs["embeds"][-1].footer.text


@pytest.mark.asyncio
async def test_result_never_mentions_the_excluded_mice():
    """Demande du propriétaire (2026-10-11) : l'utilisateur ne voit plus les souris écartées."""
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    s.budget_mode = BudgetMode.HAUT_DE_GAMME
    text = " ".join(str(e.to_dict()) for e in flow.results_embeds(s, flow.compute_selection(s)))
    assert "écart" not in text and "Non classées" not in text
    assert "matrice_profils" not in text and "docs/" not in text
    assert "Confiance" not in text and "confiance" not in text
    assert "Phantom" not in text


def test_result_sections_follow_the_reference_tool_order():
    """Recommandation, puis repères de taille, bosse et boutons — comme l'outil de référence."""
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    assert [e.title for e in embeds] == [
        "🎯 Votre recommandation",
        "📐 Vos repères de taille",
        "⛰️ La bosse",
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
    import dataclasses

    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    titles = lambda embeds: [e.title for e in embeds]
    image = lambda embed: embed.image.url.split("/")[-1].removesuffix(".png")

    def embeds_for(grip, thenar=None, hump=None, button=None):
        """Résultat pour une prise donnée, en forçant la bosse et les boutons du match idéal."""
        store = SessionStore(ttl_seconds=600)
        session = start_for(store, grip=grip, length=180.0, width=90.0, thenar=thenar)
        session.budget_mode = BudgetMode.QUALITE_PRIX
        selection = flow.compute_selection(session)
        changes = {name: value for name, value in (("hump_position", hump), ("button_height", button))
                   if value is not None}
        if changes:
            winner = dataclasses.replace(selection.ranked[0],
                                         mouse=dataclasses.replace(selection.ranked[0].mouse, **changes))
            selection = dataclasses.replace(selection, ranked=(winner,) + tuple(selection.ranked[1:]))
        return flow.results_embeds(session, selection)

    palm = embeds_for(Grip.PALM, thenar=Thenar.PETITE)
    assert "T13_arriere_etroit" in image(palm[2])          # arrière étroit, juste après les repères
    assert "T14_bosse_centrale" in image(palm[3])          # la bosse conseillée pour Palm
    assert "T01_boutons_hauts" in image(palm[4])           # les boutons conseillés pour Palm
    assert "Palm Grip → bosse" in palm[3].description and "Palm Grip → boutons hauts" in palm[4].description

    claw = embeds_for(Grip.CLAW)
    assert titles(claw) == ["🎯 Votre recommandation", "📐 Vos repères de taille", "⛰️ La bosse",
                            "🦾 Claw relâchée", "🦾 Claw agressive", "🦾 Claw pincée",
                            "🖱️ La hauteur des boutons"]
    assert "T07_bosse_arriere" in image(claw[2])           # la bosse de la souris retenue
    assert ["T04_griffe_relachee", "T05_griffe_agressive", "T06_griffe_pince"] == [
        image(e) for e in claw[3:6]]
    assert "T02_boutons_bas" in image(claw[6])
    assert "Claw Grip → boutons bas" in claw[6].description

    fingertip = embeds_for(Grip.FINGERTIP)
    assert titles(fingertip) == ["🎯 Votre recommandation", "📐 Vos repères de taille",
                                 "🖱️ La hauteur des boutons"]
    assert "T03_boutons_moyens" in image(fingertip[2])
    assert "médians à bas" in fingertip[2].description


@pytest.mark.asyncio
async def test_results_discard_session_after_display():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    inter = make_interaction(store=store)
    view = flow.BudgetView(s.session_id)
    select_values(view.children[0], BudgetMode.ECONOMIQUE.value)
    await view.children[0].callback(inter)
    assert store.lookup(s.session_id, 99)[1] != "ok"  # minimisation : réponses supprimées


@pytest.mark.asyncio
async def test_custom_budget_opens_modal_from_select():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    inter = make_interaction(store=store)
    view = flow.BudgetView(s.session_id)
    select_values(view.children[0], BudgetMode.CUSTOM.value)
    await view.children[0].callback(inter)
    inter.response.send_modal.assert_awaited_once()
    inter.response.edit_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_custom_budget_invalid_then_valid():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)

    bad = make_interaction(store=store)
    await modal_budget(s.session_id, "trois").on_submit(bad)
    bad.response.edit_message.assert_not_awaited()
    assert "Saisie invalide" in bad.response.send_message.call_args.args[0]

    good = make_interaction(store=store)
    await modal_budget(s.session_id, "50").on_submit(good)
    embeds = good.response.edit_message.call_args.kwargs["embeds"]
    assert "A9 Plus" in fields_of(embeds[0])["🥇 Le match idéal"]
    assert "Confiance" not in " ".join(str(e.to_dict()) for e in embeds)
    assert store.lookup(s.session_id, 99)[1] != "ok"  # session supprimée après résultat


# ---------------------------------------------------------------------------
# Confidentialité et isolation des parcours
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stale_grip_menu_cannot_write_into_new_session():
    """Parcours 1 ouvert, puis relancé : l'ancien menu ne doit plus modifier le parcours 2."""
    store = SessionStore(ttl_seconds=600)
    old = store.start(99)
    new = store.start(99)
    inter = make_interaction(store=store)
    stale = flow.GripView(old.session_id)
    select_values(stale.children[0], "claw")
    await stale.children[0].callback(inter)
    assert store.get(new.session_id, 99).grip is None
    inter.response.edit_message.assert_not_awaited()
    assert "plus actif" in inter.response.send_message.call_args.args[0]
    assert inter.response.send_message.call_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_other_user_cannot_use_session_id():
    store = SessionStore(ttl_seconds=600)
    victim = start_for(store, user_id=1, grip=Grip.PALM, length=180.0, width=90.0)
    inter = make_interaction(user_id=2, store=store)
    view = flow.BudgetView(victim.session_id)
    select_values(view.children[0], BudgetMode.HAUT_DE_GAMME.value)
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_not_awaited()
    msg = inter.response.send_message.call_args.args[0]
    assert "pas disponible pour votre compte" in msg
    # le parcours de la victime est intact
    assert store.get(victim.session_id, 1).budget_mode is None


@pytest.mark.asyncio
async def test_other_user_cannot_open_measures_or_submit_modal():
    store = SessionStore(ttl_seconds=600)
    victim = start_for(store, user_id=1, grip=Grip.PALM)
    intruder = make_interaction(user_id=2, store=store)
    await flow.MeasureView(victim.session_id).open_measures.callback(intruder)
    intruder.response.send_modal.assert_not_awaited()

    intruder2 = make_interaction(user_id=2, store=store)
    await modal_with(flow.MeasureModal(victim.session_id), "180", "90").on_submit(intruder2)
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
    view = flow.GripView("expire-ou-inconnu")
    select_values(view.children[0], "palm")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_not_awaited()
    assert "expiré" in inter.response.send_message.call_args.args[0]
    assert inter.response.send_message.call_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_show_private_falls_back_to_ephemeral_without_message():
    """Modal non lié à un composant (message absent) : repli sur un envoi éphémère, jamais public."""
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM)
    inter = make_interaction(store=store, has_message=False)
    await modal_with(flow.MeasureModal(s.session_id), "180", "90").on_submit(inter)
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


def test_every_view_and_modal_carries_session_id():
    """Chaque vue / modal de parcours doit recevoir le session_id (pas de clé implicite user_id)."""
    import inspect

    # ResultsView est volontairement exclue : le résultat n'a plus besoin de session_id (parcours
    # terminé, aucun bouton interactif) — elle ne porte que des liens d'achat.
    for cls in (flow.GripView, flow.ThenarView, flow.ThenarSelect, flow.MeasureView, flow.MeasureModal,
                flow.BudgetView, flow.BudgetModal):
        params = inspect.signature(cls.__init__).parameters
        assert "session_id" in params, cls.__name__


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
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
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
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    main = flow.results_embeds(session, flow.compute_selection(session))[0]
    assert "T14_bosse_centrale" in main.image.url  # V6 (Palm) : bosse Mid → illustration T14
