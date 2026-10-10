"""Simulation du flux Discord (interactions factices) : étapes, erreurs de saisie, édition de message."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cogs import finder_flow as flow
from utils.models import BudgetMode, Grip
from utils.session import SessionStore


def make_interaction(user_id: int = 99, store: SessionStore | None = None):
    response = SimpleNamespace(
        send_message=AsyncMock(),
        edit_message=AsyncMock(),
        send_modal=AsyncMock(),
        is_done=MagicMock(return_value=False),
    )
    followup = SimpleNamespace(send=AsyncMock())
    client = SimpleNamespace(sessions=store or SessionStore(ttl_seconds=600))
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id), response=response, followup=followup, client=client
    )


def select_values(select, *values):
    # Simule le choix de l'utilisateur dans un Select.
    select._values = list(values)  # discord.py lit _values en repli


def modal_with(modal, length=None, width=None):
    modal.length._value = length
    modal.width._value = width
    return modal


@pytest.mark.asyncio
async def test_start_button_sends_ephemeral_step1_with_grip_select():
    inter = make_interaction()
    await flow.StartView().start.callback(inter)
    kwargs = inter.response.send_message.call_args.kwargs
    assert kwargs["ephemeral"] is True
    assert isinstance(kwargs["view"], flow.GripView)
    assert "Étape 1/3" in kwargs["embed"].title
    assert inter.client.sessions.get(99) is not None


@pytest.mark.asyncio
async def test_grip_selection_edits_message_to_step2():
    store = SessionStore(ttl_seconds=600)
    store.start(99)
    inter = make_interaction(store=store)
    view = flow.GripView()
    select_values(view.children[0], "claw")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_awaited_once()
    assert store.get(99).grip is Grip.CLAW
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.MeasureView)
    assert "Étape 2/3" in kwargs["embed"].title


@pytest.mark.asyncio
async def test_measure_button_opens_modal_without_new_message():
    store = SessionStore(ttl_seconds=600)
    store.start(99)
    inter = make_interaction(store=store)
    view = flow.MeasureView()
    await view.open_measures.callback(inter)
    inter.response.send_modal.assert_awaited_once()
    inter.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_measures_move_to_budget_step():
    store = SessionStore(ttl_seconds=600)
    store.start(99).grip = Grip.PALM
    inter = make_interaction(store=store)
    modal = modal_with(flow.MeasureModal(), "180", "90")
    await modal.on_submit(inter)
    s = store.get(99)
    assert (s.hand_length_mm, s.hand_width_mm) == (180.0, 90.0)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.BudgetView)
    assert "Étape 3/3" in kwargs["embed"].title


@pytest.mark.asyncio
async def test_invalid_measures_show_error_and_keep_step():
    store = SessionStore(ttl_seconds=600)
    store.start(99).grip = Grip.PALM
    inter = make_interaction(store=store)
    modal = modal_with(flow.MeasureModal(), "abc", "900")
    await modal.on_submit(inter)
    inter.response.edit_message.assert_not_awaited()
    inter.response.send_message.assert_awaited_once()
    msg = inter.response.send_message.call_args.args[0]
    assert "Saisie invalide" in msg and "Longueur" in msg and "Largeur" in msg
    assert inter.response.send_message.call_args.kwargs["ephemeral"] is True
    assert store.get(99).hand_length_mm is None


@pytest.mark.asyncio
async def test_standard_budget_shows_results_with_percentage_wording():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    s.grip, s.hand_length_mm, s.hand_width_mm = Grip.PALM, 180.0, 90.0
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.QUALITE_PRIX.value)
    await view.children[0].callback(inter)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ResultsView)
    fields = {f.name: f.value for f in kwargs["embed"].fields}
    assert "Match Idéal" in " ".join(fields)
    top = next(v for k, v in fields.items() if "Match Idéal" in k)
    alt = next(v for k, v in fields.items() if "Alternative" in k)
    assert "Scyrox V6" in top
    assert "Score de correspondance : **30/40** — **75 %** du maximum théorique du barème" in top
    assert "Z1" in alt
    assert "Pourquoi ce choix" in " ".join(fields)
    assert "ni une probabilité" in kwargs["embed"].footer.text


@pytest.mark.asyncio
async def test_results_show_pending_candidates_separately():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    s.grip, s.hand_length_mm, s.hand_width_mm = Grip.PALM, 180.0, 90.0
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.HAUT_DE_GAMME.value)
    await view.children[0].callback(inter)
    fields = {f.name: f.value for f in inter.response.edit_message.call_args.kwargs["embed"].fields}
    pending = next(v for k, v in fields.items() if "À vérifier" in k)
    assert "Phantom Ultimate" in pending and "non classable" in pending
    top = next(v for k, v in fields.items() if "Match Idéal" in k)
    assert "Phantom" not in top


@pytest.mark.asyncio
async def test_custom_budget_opens_modal_from_select():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    s.grip, s.hand_length_mm, s.hand_width_mm = Grip.PALM, 180.0, 90.0
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.CUSTOM.value)
    await view.children[0].callback(inter)
    inter.response.send_modal.assert_awaited_once()
    inter.response.edit_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_custom_budget_invalid_then_valid():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    s.grip, s.hand_length_mm, s.hand_width_mm = Grip.PALM, 180.0, 90.0

    bad = make_interaction(store=store)
    await modal_budget("trois").on_submit(bad)
    bad.response.edit_message.assert_not_awaited()
    assert "Saisie invalide" in bad.response.send_message.call_args.args[0]

    good = make_interaction(store=store)
    await modal_budget("50").on_submit(good)
    kwargs = good.response.edit_message.call_args.kwargs
    assert store.get(99).budget_mode is BudgetMode.CUSTOM
    assert store.get(99).max_budget_eur == 50.0
    # Budget 50 € : seule l'A9 Plus (45 €) passe le filtre éliminatoire ; V6 (74.90 €) et X1 (75 €) sont exclues.
    embed = kwargs["embed"]
    assert "A9 Plus" in embed.fields[0].value
    assert "Aucune autre" in embed.fields[1].value


def modal_budget(value):
    modal = flow.BudgetModal()
    modal.price._value = value
    return modal


@pytest.mark.asyncio
async def test_expired_session_informs_user():
    inter = make_interaction(store=SessionStore(ttl_seconds=600))
    view = flow.GripView()
    select_values(view.children[0], "palm")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_not_awaited()
    assert "expiré" in inter.response.send_message.call_args.args[0]


@pytest.mark.asyncio
async def test_results_restart_button_resets_session():
    store = SessionStore(ttl_seconds=600)
    store.start(99).grip = Grip.CLAW
    inter = make_interaction(store=store)
    results = flow.ResultsView([], {})
    await results._restart(inter)
    assert store.get(99).grip is None
    assert isinstance(inter.response.edit_message.call_args.kwargs["view"], flow.GripView)
