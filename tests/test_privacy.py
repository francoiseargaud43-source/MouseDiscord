"""Scénarios de confidentialité et de robustesse P02–P18 (voir docs/audit/AUDIT_CONFIDENTIALITE.md).

Chaque test enchaîne de vraies callbacks du flux (StartView, GripView, MeasureModal, BudgetView,
BudgetModal, ResultsView) avec des interactions factices. Les contrôles d'interaction sont
centralisés dans ``assert_private``.

Depuis le 2026-10-12, les composants des étapes NE portent PLUS d'identifiant de parcours : chaque
action se rattache au parcours vivant du membre qui clique (identifiant Discord), ce qui permet aux
menus de continuer de fonctionner après un redémarrage du bot. Les scénarios P14 à P18 couvrent les
pannes signalées (« ça cherche dans le vide », « ce n'est plus possible », tout recommencer).

Ces tests ne remplacent PAS une validation sur serveur Discord (voir
docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md).
"""
from __future__ import annotations

import json

import pytest

from cogs import finder_flow as flow
from tests.test_flow import make_interaction, modal_budget, modal_with, select_values
from utils.models import BudgetMode, Grip, Thenar
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


def registered_modals(bot) -> set[str]:
    """Identifiants des modals enregistrés auprès de Discord (dispatch après redémarrage).

    ``Bot.persistent_views`` ne liste que les vues à composants ; les modals vivent dans le même
    registre de dispatch, sous leur identifiant. On lit donc ce registre directement : c'est la
    seule façon de prouver qu'un formulaire reste utilisable après un redémarrage.
    """
    return set(bot._connection._view_store._modals)


def current(store: SessionStore, user_id: int):
    session, status = store.current(user_id)
    assert status == LOOKUP_OK and session is not None
    return session


# ---------------------------------------------------------------------------
# Gestes du parcours (mêmes appels que ceux faits par Discord)
# ---------------------------------------------------------------------------
async def run_start(store, user_id):
    inter = make_interaction(user_id=user_id, store=store)
    await flow.StartView().start.callback(inter)
    return inter


async def choose_grip(store, user_id, value):
    inter = make_interaction(user_id=user_id, store=store)
    view = flow.GripView()
    select_values(view.children[0], value)
    await view.children[0].callback(inter)
    return inter


async def choose_thenar(store, user_id, value):
    inter = make_interaction(user_id=user_id, store=store)
    view = flow.ThenarView()
    select_values(view.children[0], value)
    await view.children[0].callback(inter)
    return inter


async def submit_measures(store, user_id, length, width):
    inter = make_interaction(user_id=user_id, store=store)
    await modal_with(flow.MeasureModal(), length, width).on_submit(inter)
    return inter


async def choose_budget(store, user_id, mode):
    inter = make_interaction(user_id=user_id, store=store)
    view = flow.BudgetView()
    select_values(view.children[0], mode.value)
    await view.children[0].callback(inter)
    return inter


async def walk_to_budget(store, user_id, grip="palm", thenar="moyenne", length="180", width="90"):
    """Parcours complet jusqu'à l'étape du budget (mesures saisies)."""
    await run_start(store, user_id)
    await choose_grip(store, user_id, grip)
    await choose_thenar(store, user_id, thenar)
    await submit_measures(store, user_id, length, width)
    return current(store, user_id)


# ---------------------------------------------------------------------------
# P02 / P03 / P06 : parcours complet, chaque étape privée, résultat au seul participant
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p02_p03_p06_full_path_is_private_and_result_goes_to_participant_only():
    store = SessionStore(ttl_seconds=600)
    start = await run_start(store, 1)
    grip = await choose_grip(store, 1, "palm")                # étape 1/4
    thenar = await choose_thenar(store, 1, "moyenne")         # étape 2/4, informative
    measures = await submit_measures(store, 1, "180", "90")   # P03 : soumission de modal
    result = await choose_budget(store, 1, BudgetMode.QUALITE_PRIX)   # étape 4/4

    for inter in (start, grip, thenar, measures, result):
        assert_private(inter)
    # P02 : chaque étape est affichée en éditant le message éphémère du parcours
    assert grip.response.edit_message.await_count == 1
    assert thenar.response.edit_message.await_count == 1
    assert measures.response.edit_message.await_count == 1
    # P06 : le résultat n'est édité que dans l'interaction du participant
    assert result.response.edit_message.await_count == 1
    assert "match idéal" in embed_text(result.response.edit_message.call_args.kwargs["embeds"][0])
    # Le parcours est TERMINÉ (plus enregistré) ; personne d'autre n'a quoi que ce soit.
    assert current(store, 1).finished is True
    assert store.current(2) == (None, LOOKUP_INACTIVE)


@pytest.mark.asyncio
async def test_p02_all_step_openings_are_private():
    store = SessionStore(ttl_seconds=600)
    await run_start(store, 1)
    await choose_grip(store, 1, "palm")
    await choose_thenar(store, 1, "moyenne")
    measure_btn = make_interaction(user_id=1, store=store)
    await flow.MeasureView().open_measures.callback(measure_btn)
    measure_btn.response.send_modal.assert_awaited_once()          # le modal n'est pas un message public
    measure_btn.response.send_message.assert_not_awaited()

    current(store, 1).hand_length_mm = 180.0
    current(store, 1).hand_width_mm = 90.0
    budget_custom = make_interaction(user_id=1, store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.CUSTOM.value)
    await view.children[0].callback(budget_custom)
    budget_custom.response.send_modal.assert_awaited_once()
    budget_custom.response.send_message.assert_not_awaited()

    # Un bouton cliqué hors de son étape ne publie rien non plus : il réaffiche l'étape réelle.
    store2 = SessionStore(ttl_seconds=600)
    await run_start(store2, 5)
    inter = make_interaction(user_id=5, store=store2)
    await flow.MeasureView().open_measures.callback(inter)
    inter.response.send_modal.assert_not_awaited()
    inter.response.edit_message.assert_awaited_once()
    assert_private(inter)


# ---------------------------------------------------------------------------
# P04 / P05 : erreurs de saisie privées, parcours non avancé
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p04_invalid_measures_are_private_and_do_not_advance():
    store = SessionStore(ttl_seconds=600)
    await run_start(store, 1)
    await choose_grip(store, 1, "palm")
    await choose_thenar(store, 1, "moyenne")
    bad = await submit_measures(store, 1, "abc", "900")
    assert_private(bad)
    bad.response.edit_message.assert_not_awaited()           # le parcours n'avance pas
    assert current(store, 1).hand_length_mm is None          # et rien n'est enregistré
    assert "Saisie invalide" in bad.response.send_message.call_args.args[0]


@pytest.mark.asyncio
async def test_p05_custom_budget_invalid_and_valid_are_private():
    store = SessionStore(ttl_seconds=600)
    await walk_to_budget(store, 1)
    bad = make_interaction(user_id=1, store=store)
    await modal_budget("trois").on_submit(bad)
    assert_private(bad)
    bad.response.edit_message.assert_not_awaited()
    assert current(store, 1).budget_mode is None
    good = make_interaction(user_id=1, store=store)
    await modal_budget("50").on_submit(good)
    assert_private(good)
    assert good.response.edit_message.await_count == 1
    assert current(store, 1).finished is True


# ---------------------------------------------------------------------------
# P07 : deux utilisateurs simultanés, données strictement séparées
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p07_two_simultaneous_participants_do_not_mix_data():
    store = SessionStore(ttl_seconds=600)
    await run_start(store, 1)
    await run_start(store, 2)
    await choose_grip(store, 1, "palm")
    await choose_grip(store, 2, "claw")                       # entrelacement volontaire
    await choose_thenar(store, 1, "moyenne")
    await choose_thenar(store, 2, "grande")
    await submit_measures(store, 1, "180", "90")
    await submit_measures(store, 2, "170", "80")
    sa, sb = current(store, 1), current(store, 2)
    assert (sa.grip, sa.hand_length_mm, sa.hand_width_mm) == (Grip.PALM, 180.0, 90.0)
    assert (sb.grip, sb.hand_length_mm, sb.hand_width_mm) == (Grip.CLAW, 170.0, 80.0)

    res_a = await choose_budget(store, 1, BudgetMode.ECONOMIQUE)
    res_b = await choose_budget(store, 2, BudgetMode.HAUT_DE_GAMME)
    text_a = embed_text(res_a.response.edit_message.call_args.kwargs["embeds"][0])
    text_b = embed_text(res_b.response.edit_message.call_args.kwargs["embeds"][0])
    assert "180 × 90" in text_a and "170 × 80" not in text_a
    assert "170 × 80" in text_b and "180 × 90" not in text_b


# ---------------------------------------------------------------------------
# P08 : aucun utilisateur ne peut agir sur le parcours d'un autre
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p08_intruder_cannot_act_on_any_step_of_another_session():
    store = SessionStore(ttl_seconds=600)
    await run_start(store, 1)
    await choose_grip(store, 1, "palm")
    victim = current(store, 1)
    before = victim.grip

    attempts = []
    grip = make_interaction(user_id=2, store=store)
    view = flow.GripView()
    select_values(view.children[0], "claw")
    attempts.append((grip, view.children[0].callback))
    measure = make_interaction(user_id=2, store=store)
    attempts.append((measure, flow.MeasureView().open_measures.callback))
    msub = make_interaction(user_id=2, store=store)
    attempts.append((msub, modal_with(flow.MeasureModal(), "150", "70").on_submit))
    budget = make_interaction(user_id=2, store=store)
    bview = flow.BudgetView()
    select_values(bview.children[0], BudgetMode.ECONOMIQUE.value)
    attempts.append((budget, bview.children[0].callback))

    for inter, call in attempts:
        await call(inter)
        inter.response.edit_message.assert_not_awaited()
        inter.response.send_modal.assert_not_awaited()
        assert "a expiré" in inter.response.send_message.call_args.args[0]
        assert inter.response.send_message.call_args.kwargs["ephemeral"] is True
        assert isinstance(inter.response.send_message.call_args.kwargs["view"], flow.StartView)
        assert_private(inter)

    session = store.get(victim.session_id, 1)
    assert session is not None
    assert session.grip is before and session.hand_length_mm is None and session.budget_mode is None


# ---------------------------------------------------------------------------
# P09 : une nouvelle recherche ne modifie pas le parcours d'un autre utilisateur
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p09_new_search_does_not_touch_other_users_session():
    store = SessionStore(ttl_seconds=600)
    await run_start(store, 2)
    await choose_grip(store, 2, "fingertip")
    await run_start(store, 1)
    a_old = current(store, 1)
    await run_start(store, 1)                                 # l'utilisateur 1 relance son test
    a_new = current(store, 1)
    assert a_new.session_id != a_old.session_id
    assert store.lookup(a_old.session_id, 1)[1] == LOOKUP_INACTIVE   # l'ancien n'existe plus
    b = current(store, 2)
    assert b.grip is Grip.FINGERTIP                            # l'autre membre est intact


# ---------------------------------------------------------------------------
# P10 : parcours expiré, non utilisable, message clair avec reprise en un clic
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p10_expired_session_cannot_be_used_and_is_removed():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    await run_start(store, 1)
    clock.now = 61
    inter = await choose_grip(store, 1, "palm")
    assert_private(inter)
    inter.response.edit_message.assert_not_awaited()
    assert "a expiré" in inter.response.send_message.call_args.args[0]
    assert isinstance(inter.response.send_message.call_args.kwargs["view"], flow.StartView)
    assert len(store) == 0
    budget = await choose_budget(store, 1, BudgetMode.ECONOMIQUE)
    budget.response.edit_message.assert_not_awaited()
    assert_private(budget)


# ---------------------------------------------------------------------------
# P11 : un redémarrage du bot ne fait plus perdre un parcours en cours (panne du 2026-10-12)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p11_a_restart_keeps_the_running_parcours_and_its_components(tmp_path):
    """Avant : les parcours vivaient en mémoire → un redémarrage (mise à jour, relance du serveur)
    rendait tout clic muet (« interaction échouée ») et le membre devait tout recommencer.
    Maintenant : le parcours repris du fichier d'état ET les composants enregistrés au démarrage
    répondent, exactement là où le questionnaire s'était arrêté.
    """
    from bot import MouseBot

    state = tmp_path / "sessions.json"
    bot1 = MouseBot(sessions_path=state)
    await bot1.setup_hook()
    try:
        await run_start(bot1.sessions, 1)
        await choose_grip(bot1.sessions, 1, "palm")
        await choose_thenar(bot1.sessions, 1, "moyenne")
    finally:
        await bot1.close()
    assert state.is_file()

    bot2 = MouseBot(sessions_path=state)                       # nouveau processus, mémoire vide
    await bot2.setup_hook()
    try:
        assert any(isinstance(v, flow.GripView) for v in bot2.persistent_views)
        assert flow.MEASURE_MODAL_CUSTOM_ID in registered_modals(bot2)
        session = current(bot2.sessions, 1)
        assert session.grip is Grip.PALM and session.thenar is Thenar.MOYENNE
        assert session.hand_length_mm is None
        # Le clic suivant est reconnu : le bot affiche l'étape des mesures (là où on s'était arrêté).
        inter = make_interaction(user_id=1, store=bot2.sessions)
        await flow.MeasureView().open_measures.callback(inter)
        inter.response.send_modal.assert_awaited_once()
        assert_private(inter)
    finally:
        await bot2.close()


@pytest.mark.asyncio
async def test_p11_step_components_are_registered_even_without_any_parcours():
    """Les composants d'étapes sont enregistrés au démarrage, sans dépendre d'un parcours vivant."""
    from bot import MouseBot

    bot = MouseBot(sessions_path=None)     # mémoire seulement : le test n'écrit rien sur le disque
    await bot.setup_hook()
    try:
        assert {type(v).__name__ for v in bot.persistent_views} >= {
            "StartView", "GripView", "ClawVariantView", "ThenarView", "MeasureView", "BudgetView",
        }
        assert registered_modals(bot) >= {flow.MEASURE_MODAL_CUSTOM_ID, flow.BUDGET_MODAL_CUSTOM_ID}
        assert len(bot.sessions) == 0
    finally:
        await bot.close()


# ---------------------------------------------------------------------------
# P12 : le résultat ne porte aucun composant interactif et ne touche aucune session
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p12_result_has_no_interactive_component_and_touches_no_session():
    store = SessionStore(ttl_seconds=600)
    other = store.start(2)
    await walk_to_budget(store, 1)
    shown = await choose_budget(store, 1, BudgetMode.QUALITE_PRIX)
    assert_private(shown)
    view = shown.response.edit_message.call_args.kwargs["view"]
    assert isinstance(view, flow.ResultsView)
    assert view.timeout is None
    for child in view.children:   # liens d'achat, ou rappel désactivé : rien à cliquer côté bot
        assert getattr(child, "url", None) or child.disabled
    assert store.lookup(other.session_id, 2)[1] == LOOKUP_OK   # la session d'un autre est intacte


# ---------------------------------------------------------------------------
# P14 : un clic rejoué (double appui, réémission Discord) reçoit le même résultat
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p14_replayed_click_after_the_result_gets_the_same_result():
    """Avant : le second envoi disait « ce parcours n'est plus actif ». Maintenant : même résultat."""
    store = SessionStore(ttl_seconds=600)
    await walk_to_budget(store, 1)
    first = await choose_budget(store, 1, BudgetMode.QUALITE_PRIX)
    replay = await choose_budget(store, 1, BudgetMode.QUALITE_PRIX)
    first_embeds = [e.to_dict() for e in first.response.edit_message.call_args.kwargs["embeds"]]
    replay_embeds = [e.to_dict() for e in replay.response.edit_message.call_args.kwargs["embeds"]]
    assert replay_embeds == first_embeds
    replay.response.send_message.assert_not_awaited()
    assert_private(replay)


# ---------------------------------------------------------------------------
# P15 : une erreur inattendue est expliquée en privé, jamais un silence
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p15_unexpected_error_is_explained_privately_and_never_left_silent(monkeypatch):
    store = SessionStore(ttl_seconds=600)
    await run_start(store, 1)
    view = flow.MeasureView()      # bouton : le chemin de dispatch est le même, sans valeurs

    async def boom(interaction):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(flow, "_current_session", boom)
    inter = make_interaction(user_id=1, store=store)
    await view._scheduled_task(view.children[0], inter)      # chemin réel de dispatch de discord.py
    assert_private(inter)
    assert inter.response.send_message.await_count == 1
    assert "erreur inattendue" in inter.response.send_message.call_args.args[0].lower()


@pytest.mark.asyncio
async def test_p15_modal_error_is_also_explained_privately():
    inter = make_interaction(user_id=1, store=SessionStore(ttl_seconds=600))
    await flow.MeasureModal().on_error(inter, RuntimeError("panne simulée"))
    assert_private(inter)
    assert "erreur inattendue" in inter.response.send_message.call_args.args[0].lower()


# ---------------------------------------------------------------------------
# P16–P18 : le fichier d'état des parcours (state/sessions.json)
# ---------------------------------------------------------------------------
def test_p16_state_file_only_holds_running_parcours(tmp_path):
    """Seuls les parcours EN COURS sont écrits ; à la fin du parcours, les réponses sont retirées."""
    state = tmp_path / "sessions.json"
    store = SessionStore(ttl_seconds=600, path=state)
    session = store.start(1)
    session.grip = Grip.PALM
    session.hand_length_mm = 180.0
    session.hand_width_mm = 90.0
    store.save()
    raw = json.loads(state.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert len(raw["sessions"]) == 1
    entry = raw["sessions"][0]
    assert entry["grip"] == "palm" and entry["hand_length_mm"] == 180.0
    assert 0.0 <= entry["age_seconds"] < 600

    store.finish(session.session_id)                          # résultat produit
    raw = json.loads(state.read_text(encoding="utf-8"))
    assert raw["sessions"] == []                              # les réponses ne traînent plus sur disque


def test_p17_expired_parcours_is_not_restored(tmp_path):
    state = tmp_path / "sessions.json"
    store = SessionStore(ttl_seconds=60, path=state)
    store.start(1)
    raw = json.loads(state.read_text(encoding="utf-8"))
    raw["sessions"][0]["age_seconds"] = 120.0                 # inactif depuis plus que le délai
    state.write_text(json.dumps(raw), encoding="utf-8")
    assert len(SessionStore(ttl_seconds=60, path=state)) == 0


def test_p18_unreadable_state_file_never_breaks_the_bot(tmp_path):
    state = tmp_path / "sessions.json"
    state.write_text("{ceci n'est pas du JSON", encoding="utf-8")
    store = SessionStore(ttl_seconds=60, path=state)
    assert len(store) == 0
    session = store.start(1)                                  # le bot démarre quand même
    assert store.current(1)[0] is session
