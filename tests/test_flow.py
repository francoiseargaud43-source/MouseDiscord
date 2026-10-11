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
    main, details = kwargs["embeds"]
    fields = fields_of(main)
    top = next(v for k, v in fields.items() if "Match Idéal" in k)
    alt = next(v for k, v in fields.items() if "Alternative" in k)
    assert "Scyrox V6" in top
    assert "Score : **30/40 — 75 % du maximum théorique**" in top
    assert "Confiance faible" in top  # Scyrox : dimensions « owner_spec_unverified »
    assert "Z1" in alt  # performances documentées différentes : alternative pertinente
    assert "Pourquoi ce choix" in " ".join(fields)
    assert "ni une probabilité" in main.footer.text
    # Second embed : repères de taille, jamais de points internes.
    assert "Repères de taille" in details.title
    assert "118.8" in details.description and "59.6" in details.description


@pytest.mark.asyncio
async def test_results_show_pending_candidates_separately():
    store = SessionStore(ttl_seconds=600)
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    inter = make_interaction(store=store)
    view = flow.BudgetView(s.session_id)
    select_values(view.children[0], BudgetMode.HAUT_DE_GAMME.value)
    await view.children[0].callback(inter)
    fields = fields_of(main_embed_of(inter))
    pending = next(v for k, v in fields.items() if "À vérifier" in k)
    assert "écartées du classement" in pending and "pts" not in pending
    assert "matrice_profils.md" in pending
    top = next(v for k, v in fields.items() if "Match Idéal" in k)
    assert "Phantom" not in top


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
    embed = main_embed_of(good)
    assert "A9 Plus" in embed.fields[0].value
    assert "🟡 Confiance moyenne" in embed.fields[0].value  # ATK vérifié + largeur estimée
    assert "Aucune alternative pertinente" in embed.fields[1].value
    assert store.lookup(s.session_id, 99)[1] != "ok"  # session supprimée après résultat


@pytest.mark.asyncio
async def test_results_view_restart_resets_session():
    store = SessionStore(ttl_seconds=600)
    store.start(99)
    inter = make_interaction(store=store)
    results = flow.ResultsView(99, [], {})
    await results._restart(inter)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.GripView)
    new_id = kwargs["view"].children[0].session_id
    assert store.lookup(new_id, 99)[1] == "ok"


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


@pytest.mark.asyncio
async def test_results_close_is_owner_only_and_clears_message():
    store = SessionStore(ttl_seconds=600)
    intruder = make_interaction(user_id=2, store=store)
    results = flow.ResultsView(1, [], {})
    await results._close(intruder)
    intruder.response.edit_message.assert_not_awaited()

    owner = make_interaction(user_id=1, store=store)
    await results._close(owner)
    kwargs = owner.response.edit_message.call_args.kwargs
    assert kwargs["embed"] is None and kwargs["view"] is None
    owner.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_results_restart_is_owner_only():
    store = SessionStore(ttl_seconds=600)
    store.start(1).grip = Grip.CLAW
    intruder = make_interaction(user_id=2, store=store)
    await flow.ResultsView(1, [], {})._restart(intruder)
    intruder.response.edit_message.assert_not_awaited()
    assert store.get(store.start(1).session_id, 1).grip is None  # nouveau parcours vierge, ancien intact


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

    # ResultsView est volontairement exclue : elle ne porte pas de session_id (résultat déjà produit,
    # propriétaire vérifié par owner_id) — voir tests/test_privacy.py.
    for cls in (flow.GripView, flow.ThenarView, flow.ThenarSelect, flow.MeasureView, flow.MeasureModal,
                flow.BudgetView, flow.BudgetModal):
        params = inspect.signature(cls.__init__).parameters
        assert "session_id" in params, cls.__name__


def test_missing_commercial_link_shows_disabled_placeholder_button():
    """Sans URL d'achat : un seul bouton désactivé « Liens à venir », jamais d'erreur ni de lien inventé."""
    from config import MOUSE_DB_PATH
    from utils.catalog import load_catalog

    mouse = load_catalog(MOUSE_DB_PATH)[0]
    view = flow.ResultsView(1, [SimpleNamespace(mouse=mouse)], {})
    placeholder = [c for c in view.children if getattr(c, "disabled", False)]
    assert len(placeholder) == 1, "un seul bouton informatif, jamais un bouton grisé par souris"
    assert placeholder[0].label == "Liens à venir"
    assert not any(getattr(c, "url", None) for c in view.children if getattr(c, "disabled", False))
    assert [c.label for c in view.children if c.label in ("Fermer", "Refaire le test")] == ["Fermer", "Refaire le test"]


def test_real_link_creates_purchase_button_without_placeholder():
    from config import MOUSE_DB_PATH
    from utils.catalog import load_catalog

    mouse = load_catalog(MOUSE_DB_PATH)[0]
    view = flow.ResultsView(1, [SimpleNamespace(mouse=mouse)], {mouse.id: "https://shop.test/x"})
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
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    assert len(embeds) == 2, "un résultat tient en deux embeds (recommandation + repères de taille)"
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
    assert "Score : **" in text and "du maximum théorique" in text


def test_pending_text_lists_at_most_five_names_without_partial_scores():
    def fake(index: int) -> SimpleNamespace:
        return SimpleNamespace(
            mouse=SimpleNamespace(label=f"Souris {index}", price_eur=None),
            grip=Grip.PALM,
            missing=("compatibilité Palm Grip non vérifiée",),
        )

    text = flow._pending_text(tuple(fake(i) for i in range(1, 6)))
    assert text.count("•") == 5 and "Souris 5" in text and "pts" not in text


def test_pending_text_summarises_instead_of_listing_when_many():
    def fake(index: int) -> SimpleNamespace:
        return SimpleNamespace(
            mouse=SimpleNamespace(label=f"Souris {index}", price_eur=None),
            grip=Grip.CLAW,
            missing=("compatibilité Claw Grip non vérifiée",),
        )

    text = flow._pending_text(tuple(fake(i) for i in range(20)))
    assert "20 souris écartées du classement" in text
    assert "Souris 1" not in text and "pts" not in text


def test_result_image_key_prioritises_the_hump_then_the_buttons():
    def score(hump: str, button: str, grip: Grip = Grip.PALM) -> SimpleNamespace:
        return SimpleNamespace(mouse=SimpleNamespace(hump_position=hump, button_height=button), grip=grip)

    assert flow.result_image_key(score("Rear", "Low", Grip.CLAW), Grip.CLAW) == "illustration_hump_rear"
    assert flow.result_image_key(score("Mid-Front", "High"), Grip.PALM) == "illustration_hump_front"
    assert flow.result_image_key(score("Mid", "Mid"), Grip.PALM) == "illustration_hump_mid"
    assert flow.result_image_key(score("Inconnu", "High"), Grip.PALM) == "illustration_buttons_high"
    assert flow.result_image_key(score("Inconnu", "Low", Grip.FINGERTIP), Grip.FINGERTIP) == "illustration_buttons_low"
    assert flow.result_image_key(None, Grip.PALM) is None


def test_thenar_is_stored_and_not_scored():
    """§7.6 : le thénar est stocké et affiché, mais n'influence AUCUN calcul (ni score, ni classement)."""
    store_a = SessionStore(ttl_seconds=600)
    without = start_for(store_a, user_id=1, grip=Grip.PALM, length=180.0, width=90.0)
    without.budget_mode = BudgetMode.QUALITE_PRIX
    store_b = SessionStore(ttl_seconds=600)
    with_thenar = start_for(store_b, user_id=2, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.GRANDE)
    with_thenar.budget_mode = BudgetMode.QUALITE_PRIX
    base = flow.compute_selection(without)
    other = flow.compute_selection(with_thenar)
    assert base == other, "le thénar ne doit modifier ni les scores, ni le classement, ni les explications"
    assert base.ranked[0].total == 30  # non-régression du barème Palm 180 × 90


def test_thenar_petite_adds_a_purely_informative_narrow_rear_note(monkeypatch):
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    details = flow.results_embeds(session, flow.compute_selection(session))[1]
    names = " ".join(field.name for field in details.fields)
    values = " ".join(field.value for field in details.fields)
    assert "Thénar Petite" in names
    assert "non prise en compte dans le score" in values
    assert details.image is not None and "T13_arriere_etroit" in details.image.url


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
