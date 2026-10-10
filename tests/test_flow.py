"""Simulation du flux Discord (interactions factices) : étapes, erreurs de saisie, édition de message,
isolation des parcours et confidentialité (aucune publication dans le salon).
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cogs import finder_flow as flow
from utils.models import BudgetMode, Grip
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
    client = SimpleNamespace(sessions=store or SessionStore(ttl_seconds=600))
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


def start_for(store: SessionStore, user_id: int = 99, grip=None, length=None, width=None):
    s = store.start(user_id)
    s.grip, s.hand_length_mm, s.hand_width_mm = grip, length, width
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
    assert "Étape 1/3" in kwargs["embed"].title
    session = inter.client.sessions.get(kwargs["view"].children[0].session_id, 99)
    assert session is not None


@pytest.mark.asyncio
async def test_grip_selection_edits_message_to_step2():
    store = SessionStore(ttl_seconds=600)
    s = store.start(99)
    inter = make_interaction(store=store)
    view = flow.GripView(s.session_id)
    select_values(view.children[0], "claw")
    await view.children[0].callback(inter)
    inter.response.edit_message.assert_awaited_once()
    assert store.get(s.session_id, 99).grip is Grip.CLAW
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.MeasureView)
    assert "Étape 2/3" in kwargs["embed"].title


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
    assert "Étape 3/3" in kwargs["embed"].title


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
    fields = fields_of(kwargs["embed"])
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
    s = start_for(store, grip=Grip.PALM, length=180.0, width=90.0)
    inter = make_interaction(store=store)
    view = flow.BudgetView(s.session_id)
    select_values(view.children[0], BudgetMode.HAUT_DE_GAMME.value)
    await view.children[0].callback(inter)
    fields = fields_of(inter.response.edit_message.call_args.kwargs["embed"])
    pending = next(v for k, v in fields.items() if "À vérifier" in k)
    assert "Phantom Ultimate" in pending and "non classable" in pending
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
    embed = good.response.edit_message.call_args.kwargs["embed"]
    assert "A9 Plus" in embed.fields[0].value
    assert "Aucune autre" in embed.fields[1].value
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


def test_no_public_interaction_reply_in_flow_module():
    """Analyse statique : tout envoi d'interaction (send_message / followup.send) doit être éphémère."""
    tree = ast.parse((ROOT / "cogs" / "finder_flow.py").read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        name = node.func.attr
        target = ast.unparse(node.func.value)
        is_interaction_send = name == "send_message" or (name == "send" and "followup" in target)
        if not is_interaction_send:
            continue
        ephemeral = {k.arg: k.value for k in node.keywords}.get("ephemeral")
        if not (isinstance(ephemeral, ast.Constant) and ephemeral.value is True) and not any(
            k.arg is None for k in node.keywords  # **kwargs : contrôlé par _show_private (ephemeral=True)
        ):
            offenders.append(f"line {node.lineno}: {ast.unparse(node)}")
    assert offenders == []


def test_every_view_and_modal_carries_session_id():
    """Chaque vue / modal de parcours doit recevoir le session_id (pas de clé implicite user_id)."""
    import inspect

    for cls in (flow.GripView, flow.MeasureView, flow.MeasureModal, flow.BudgetView, flow.BudgetModal):
        params = inspect.signature(cls.__init__).parameters
        assert "session_id" in params, cls.__name__
