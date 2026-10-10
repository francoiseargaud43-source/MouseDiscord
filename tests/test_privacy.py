"""Scénarios de confidentialité P02–P12 (voir docs/audit/AUDIT_CONFIDENTIALITE.md).

Chaque test enchaîne de vraies callbacks du flux (StartView, GripView, MeasureModal, BudgetView, BudgetModal,
ResultsView) avec des interactions factices. Les contrôles d'interaction sont centralisés dans ``assert_private``.
Ces tests ne remplacent PAS une validation sur serveur Discord (voir docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md).
"""
from __future__ import annotations

import pytest

from cogs import finder_flow as flow
from tests.test_flow import make_interaction, modal_budget, modal_with, select_values
from utils.models import BudgetMode, Grip
from utils.session import LOOKUP_INACTIVE, LOOKUP_OK, SessionStore


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def assert_private(inter) -> None:
    """Toute réponse de l'interaction doit être éphémère ; aucun envoi public n'est possible ici."""
    for call in inter.response.send_message.call_args_list:
        assert call.kwargs.get("ephemeral") is True, f"réponse non éphémère : {call}"
    for call in inter.followup.send.call_args_list:
        assert call.kwargs.get("ephemeral") is True, f"suivi non éphémère : {call}"


def embed_text(embed) -> str:
    return str(embed.to_dict())


async def run_start(store, user_id):
    """Clic sur le panneau : renvoie (interaction, session_id) du menu grip."""
    inter = make_interaction(user_id=user_id, store=store)
    await flow.StartView().start.callback(inter)
    view = inter.response.send_message.call_args.kwargs["view"]
    return inter, view.children[0].session_id


async def choose_grip(store, user_id, session_id, value):
    inter = make_interaction(user_id=user_id, store=store)
    view = flow.GripView(session_id)
    select_values(view.children[0], value)
    await view.children[0].callback(inter)
    return inter


async def submit_measures(store, user_id, session_id, length, width):
    inter = make_interaction(user_id=user_id, store=store)
    await modal_with(flow.MeasureModal(session_id), length, width).on_submit(inter)
    return inter


async def choose_budget(store, user_id, session_id, mode):
    inter = make_interaction(user_id=user_id, store=store)
    view = flow.BudgetView(session_id)
    select_values(view.children[0], mode.value)
    await view.children[0].callback(inter)
    return inter


# ---------------------------------------------------------------------------
# P02 / P03 / P06 : parcours complet, chaque étape privée, résultat à l'utilisateur seul
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p02_p03_p06_full_path_is_private_and_result_goes_to_participant_only():
    store = SessionStore(ttl_seconds=600)
    start, sid = await run_start(store, 1)
    grip = await choose_grip(store, 1, sid, "palm")
    measures = await submit_measures(store, 1, sid, "180", "90")          # P03 : soumission de modal
    result = await choose_budget(store, 1, sid, BudgetMode.QUALITE_PRIX)

    for inter in (start, grip, measures, result):
        assert_private(inter)
    # P02 : chaque étape est affichée en éditant le message éphémère du parcours
    assert grip.response.edit_message.await_count == 1
    assert measures.response.edit_message.await_count == 1
    # P06 : le résultat n'est édité que dans l'interaction du participant
    assert result.response.edit_message.await_count == 1
    assert "Match Idéal" in embed_text(result.response.edit_message.call_args.kwargs["embed"])
    # Un second participant n'a rien reçu : vérifié en P07 et P08.


@pytest.mark.asyncio
async def test_p02_all_step_openings_are_private():
    store = SessionStore(ttl_seconds=600)
    _, sid = await run_start(store, 1)
    measure_btn = make_interaction(user_id=1, store=store)
    await flow.MeasureView(sid).open_measures.callback(measure_btn)
    measure_btn.response.send_modal.assert_awaited_once()          # le modal n'est pas un message public
    measure_btn.response.send_message.assert_not_awaited()
    budget_custom = make_interaction(user_id=1, store=store)
    s = store.get(sid, 1)
    s.grip, s.hand_length_mm, s.hand_width_mm = Grip.PALM, 180.0, 90.0
    view = flow.BudgetView(sid)
    select_values(view.children[0], BudgetMode.CUSTOM.value)
    await view.children[0].callback(budget_custom)
    budget_custom.response.send_modal.assert_awaited_once()
    budget_custom.response.send_message.assert_not_awaited()


# ---------------------------------------------------------------------------
# P04 / P05 : erreurs de saisie privées, parcours non avancé
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p04_invalid_measures_are_private_and_do_not_advance():
    store = SessionStore(ttl_seconds=600)
    _, sid = await run_start(store, 1)
    await choose_grip(store, 1, sid, "palm")
    bad = await submit_measures(store, 1, sid, "abc", "900")
    assert_private(bad)
    bad.response.edit_message.assert_not_awaited()           # le parcours n'avance pas
    assert store.get(sid, 1).hand_length_mm is None          # et rien n'est enregistré
    assert "Saisie invalide" in bad.response.send_message.call_args.args[0]


@pytest.mark.asyncio
async def test_p05_custom_budget_invalid_and_valid_are_private():
    store = SessionStore(ttl_seconds=600)
    _, sid = await run_start(store, 1)
    await choose_grip(store, 1, sid, "palm")
    await submit_measures(store, 1, sid, "180", "90")
    bad = make_interaction(user_id=1, store=store)
    await modal_budget(sid, "trois").on_submit(bad)
    assert_private(bad)
    bad.response.edit_message.assert_not_awaited()
    assert store.get(sid, 1).budget_mode is None
    good = make_interaction(user_id=1, store=store)
    await modal_budget(sid, "50").on_submit(good)
    assert_private(good)
    assert good.response.edit_message.await_count == 1


# ---------------------------------------------------------------------------
# P07 : deux utilisateurs simultanés, données strictement séparées
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p07_two_simultaneous_participants_do_not_mix_data():
    store = SessionStore(ttl_seconds=600)
    _, a = await run_start(store, 1)
    _, b = await run_start(store, 2)
    await choose_grip(store, 1, a, "palm")
    await choose_grip(store, 2, b, "claw")                    # entrelacement volontaire
    await submit_measures(store, 1, a, "180", "90")
    await submit_measures(store, 2, b, "170", "80")
    sa, sb = store.get(a, 1), store.get(b, 2)
    assert (sa.grip, sa.hand_length_mm, sa.hand_width_mm) == (Grip.PALM, 180.0, 90.0)
    assert (sb.grip, sb.hand_length_mm, sb.hand_width_mm) == (Grip.CLAW, 170.0, 80.0)
    res_a = await choose_budget(store, 1, a, BudgetMode.ECONOMIQUE)
    res_b = await choose_budget(store, 2, b, BudgetMode.HAUT_DE_GAMME)
    text_a = embed_text(res_a.response.edit_message.call_args.kwargs["embed"])
    text_b = embed_text(res_b.response.edit_message.call_args.kwargs["embed"])
    assert "180 × 90" in text_a and "170 × 80" not in text_a
    assert "170 × 80" in text_b and "180 × 90" not in text_b


# ---------------------------------------------------------------------------
# P08 : aucun utilisateur ne peut agir sur le parcours d'un autre
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p08_intruder_cannot_act_on_any_step_of_another_session():
    store = SessionStore(ttl_seconds=600)
    _, victim = await run_start(store, 1)
    await choose_grip(store, 1, victim, "palm")
    before = store.get(victim, 1).grip

    intruder = 2
    attempts = []
    grip = make_interaction(user_id=intruder, store=store)
    view = flow.GripView(victim)
    select_values(view.children[0], "claw")
    attempts.append((grip, view.children[0].callback))
    measure = make_interaction(user_id=intruder, store=store)
    attempts.append((measure, flow.MeasureView(victim).open_measures.callback))
    msub = make_interaction(user_id=intruder, store=store)
    attempts.append((msub, modal_with(flow.MeasureModal(victim), "150", "70").on_submit))
    budget = make_interaction(user_id=intruder, store=store)
    bview = flow.BudgetView(victim)
    select_values(bview.children[0], BudgetMode.ECONOMIQUE.value)
    attempts.append((budget, bview.children[0].callback))

    for inter, call in attempts:
        await call(inter)
        inter.response.edit_message.assert_not_awaited()
        inter.response.send_modal.assert_not_awaited()
        assert "pas disponible pour votre compte" in inter.response.send_message.call_args.args[0]
        assert inter.response.send_message.call_args.kwargs["ephemeral"] is True

    session = store.get(victim, 1)
    assert session.grip is before and session.hand_length_mm is None and session.budget_mode is None


@pytest.mark.asyncio
async def test_p08_intruder_cannot_use_results_buttons_of_another_user():
    store = SessionStore(ttl_seconds=600)
    intruder = make_interaction(user_id=2, store=store)
    results = flow.ResultsView(1, [], {})
    await results._close(intruder)
    await results._restart(intruder)
    intruder.response.edit_message.assert_not_awaited()


# ---------------------------------------------------------------------------
# P09 : une nouvelle recherche ne modifie pas le parcours d'un autre utilisateur
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p09_new_search_does_not_touch_other_users_session():
    store = SessionStore(ttl_seconds=600)
    _, b = await run_start(store, 2)
    await choose_grip(store, 2, b, "fingertip")
    _, a_old = await run_start(store, 1)
    _, a_new = await run_start(store, 1)                      # l'utilisateur 1 relance son test
    assert store.lookup(b, 2)[1] == LOOKUP_OK
    assert store.get(b, 2).grip is Grip.FINGERTIP
    # Conception : la session précédente du MÊME utilisateur est remplacée et devient inutilisable.
    assert store.lookup(a_old, 1)[1] == LOOKUP_INACTIVE
    assert store.lookup(a_new, 1)[1] == LOOKUP_OK


# ---------------------------------------------------------------------------
# P10 : session expirée non utilisable normalement
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p10_expired_session_cannot_be_used_and_is_removed():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    _, sid = await run_start(store, 1)
    clock.now = 61
    inter = await choose_grip(store, 1, sid, "palm")
    assert_private(inter)
    inter.response.edit_message.assert_not_awaited()
    assert "plus actif" in inter.response.send_message.call_args.args[0]
    assert len(store) == 0
    budget = await choose_budget(store, 1, sid, BudgetMode.ECONOMIQUE)
    budget.response.edit_message.assert_not_awaited()
    assert_private(budget)


# ---------------------------------------------------------------------------
# P11 : après redémarrage, panneau persistant fonctionnel ; anciennes interactions traitées proprement
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p11_persistent_panel_works_after_restart_in_fresh_bot_instance():
    from bot import MouseBot

    old_bot = MouseBot()
    await old_bot.setup_hook()
    _, stale_sid = await run_start(old_bot.sessions, 1)     # menu ouvert AVANT redémarrage
    await old_bot.close()

    new_bot = MouseBot()                                    # nouveau processus : mémoire vide
    await new_bot.setup_hook()
    try:
        assert any(isinstance(v, flow.StartView) for v in new_bot.persistent_views)
        assert len(new_bot.sessions) == 0
        # Le bouton du panneau répond (même custom_id, enregistré au démarrage)
        inter = make_interaction(user_id=1, store=new_bot.sessions)
        await flow.StartView().start.callback(inter)
        assert_private(inter)
        assert isinstance(inter.response.send_message.call_args.kwargs["view"], flow.GripView)
        # Ancien menu éphémère : session absente du nouveau processus → traitée comme expirée
        stale = make_interaction(user_id=1, store=new_bot.sessions)
        select_values(flow.GripView(stale_sid).children[0], "palm")
        await flow.GripView(stale_sid).children[0].callback(stale)
        stale.response.edit_message.assert_not_awaited()
        assert "plus actif" in stale.response.send_message.call_args.args[0]
    finally:
        await new_bot.close()


# ---------------------------------------------------------------------------
# P12 : la fermeture ne touche que le résultat de son propriétaire, et ne modifie aucune session
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p12_close_affects_only_owner_result_and_no_session():
    store = SessionStore(ttl_seconds=600)
    other = store.start(2)
    intruder = make_interaction(user_id=2, store=store)
    results = flow.ResultsView(1, [], {})
    await results._close(intruder)
    intruder.response.edit_message.assert_not_awaited()
    owner = make_interaction(user_id=1, store=store)
    await results._close(owner)
    assert owner.response.edit_message.call_args.kwargs["view"] is None
    assert store.lookup(other.session_id, 2)[1] == LOOKUP_OK   # la session d'un autre n'est pas touchée


@pytest.mark.asyncio
async def test_results_buttons_still_work_after_session_was_discarded():
    store = SessionStore(ttl_seconds=600)
    _, sid = await run_start(store, 1)
    await choose_grip(store, 1, sid, "palm")
    await submit_measures(store, 1, sid, "180", "90")
    shown = await choose_budget(store, 1, sid, BudgetMode.QUALITE_PRIX)
    assert store.lookup(sid, 1)[1] != LOOKUP_OK              # session supprimée après affichage
    results_view = shown.response.edit_message.call_args.kwargs["view"]
    close = make_interaction(user_id=1, store=store)
    await results_view._close(close)                         # Fermer : fonctionne
    close.response.edit_message.assert_awaited_once()
    restart = make_interaction(user_id=1, store=store)
    await results_view._restart(restart)                     # Refaire le test : fonctionne
    assert isinstance(restart.response.edit_message.call_args.kwargs["view"], flow.GripView)
