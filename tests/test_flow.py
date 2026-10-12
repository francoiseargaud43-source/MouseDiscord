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
    selection = flow.compute_selection(session)
    ideal, _, _ = flow.result_slots(selection)
    embeds = flow.results_embeds(session, selection)
    # Fingertip : ni thénar, ni arrière étroit, ni conseil de bosse (elle n'y travaille pas).
    assert [e.title for e in embeds] == ["🎯 Votre recommandation", "📐 Vos repères de taille",
                                         "🖱️ La hauteur des boutons"]
    assert not any("Thénar" in field.name for embed in embeds for field in embed.fields)
    assert all("arriere_etroit" not in (embed.image.url or "") for embed in embeds)
    # Boss ignorée en Fingertip → l'illustration est celle des BOUTONS, et elle suit la classe de la
    # souris retenue (toutes les classes possibles sont vérifiées : la souris du scénario peut changer
    # quand le catalogue gagne une valeur mesurée — c'est la règle d'affichage qui est testée ici).
    attendues = {"High": "T01_boutons_hauts", "Low": "T02_boutons_bas", "Mid": "T03_boutons_moyens"}
    illustration = attendues.get(ideal.mouse.button_height)
    assert illustration is not None, f"{ideal.mouse.label} : classe {ideal.mouse.button_height!r} inattendue"
    assert illustration in embeds[0].image.url


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
    # 18e passe (2026-10-12) : la prise publiée par ATK pour le Phantom Ultimate a été relevée sur la
    # fiche officielle, il n'est donc plus « en attente » et passe en tête du profil Palm 180 × 90 en
    # Qualité/Prix (35/40, 88 %, 91,95 €) ; l'alternative est une AUTRE coque trouvée dans
    # l'élargissement de la fenêtre, l'ATK Z1 V2 Ultra (30/40, 75 %, 59,95 €, moins chère que l'idéal).
    assert "ATK Phantom Ultimate" in ideal
    assert "91,95 €" in ideal and "**88 %**" in ideal   # nom · poids · prix · pourcentage · forme
    assert "Score" not in ideal and "Confiance" not in ideal and "pts" not in ideal
    assert "**75 %**" in alt                            # l'alternative porte aussi son pourcentage
    assert "ATK Z1 V2 Ultra" in alt
    assert guide.title == "📐 Vos repères de taille"
    guide_text = (guide.description or "") + " ".join(f.value for f in guide.fields)
    assert "35/40" in guide_text and "maximum théorique" in guide_text   # le score s'explique ici
    # La donnée manquante est annoncée en clair, dans le bloc bas (jamais en haut du message).
    assert "Hauteur des boutons non documentée" in guide_text
    assert "Pourquoi ce choix" in " ".join(f.name for f in guide.fields)
    # La souris choisie est reliée aux repères de taille, juste au-dessus.
    assert any(f.name.startswith("🔎 ATK Phantom Ultimate") and "en clair" in f.name for f in guide.fields)
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
    # Les écartées du profil sont testées nommément (le Phantom, écarté jusqu'au 2026-10-12 faute de
    # prise publiée, est désormais le gagnant : il ne peut plus servir de sentinelle).
    assert "Scyrox V8" not in text and "F1 V3 Ultimate" not in text and "Xlite v4 Large" not in text


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
    assert "35/40" in text and "maximum théorique" in text


def test_result_image_key_prioritises_the_hump_then_the_buttons():
    def score(hump: str, button: str, grip: Grip = Grip.PALM) -> SimpleNamespace:
        return SimpleNamespace(mouse=SimpleNamespace(hump_position=hump, button_height=button), grip=grip)

    assert flow.result_image_key(score("Rear", "Low", Grip.CLAW), Grip.CLAW) == "illustration_hump_rear"
    assert flow.result_image_key(score("Mid-Front", "High"), Grip.PALM) == "illustration_hump_front"
    assert flow.result_image_key(score("Mid", "Mid"), Grip.PALM) == "illustration_hump_mid"
    assert flow.result_image_key(score("Inconnu", "High"), Grip.PALM) == "illustration_buttons_high"
    assert flow.result_image_key(score("Inconnu", "Low", Grip.FINGERTIP), Grip.FINGERTIP) == "illustration_buttons_low"
    assert flow.result_image_key(None, Grip.PALM) is None


def test_thenar_never_changes_the_recommendation():
    """Règle « zéro effet » (MASTER_PROMPT §7.6) : le thénar déclaré ne change ni le choix ni le score.

    Mesure du 2026-10-12, avant correction : avec l'ajustement ±2 activé par erreur, 537 profils sur
    2 805 (19,1 %) changeaient de recommandation selon le thénar déclaré. Ce test verrouille le retour
    à la règle du propriétaire : trois profils (dont un Palm et un Claw où une souris à bosse ARRIÈRE
    gagne) × trois thénar × trois modes → un seul et même résultat.
    """
    profils = ((Grip.PALM, 180.0, 90.0), (Grip.PALM, 150.0, 75.0), (Grip.CLAW, 170.0, 85.0))
    modes = (BudgetMode.QUALITE_PRIX, BudgetMode.HAUT_DE_GAMME, BudgetMode.PEU_IMPORTE_PRIX)
    for grip, length, width in profils:
        for mode in modes:
            reference = None
            for thenar in Thenar:
                store = SessionStore(ttl_seconds=600)
                session = start_for(store, grip=grip, length=length, width=width, thenar=thenar)
                session.budget_mode = mode
                selection = flow.compute_selection(session)
                resultat = (tuple(s.mouse.id for s in selection.ranked),
                            tuple(s.total for s in selection.ranked),
                            selection.reference_score)
                if reference is None:
                    reference = resultat
                assert resultat == reference, f"{grip.label} {length}×{width} {mode.value} thénar {thenar.label}"
                assert selection.ranked, "au moins un résultat attendu sur ces profils"
                assert all(s.breakdown.thenar_pts == 0 for s in (*selection.ranked, *selection.pending))

    # Non-régression du barème Palm 180 × 90 : 30/40 pour les souris du propriétaire (vérifié dans
    # test_matcher), 35/40 pour l'ATK Phantom Ultimate depuis que sa prise est publiée (18e passe).
    store = SessionStore(ttl_seconds=600)
    palm = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.GRANDE)
    palm.budget_mode = BudgetMode.QUALITE_PRIX
    assert flow.compute_selection(palm).ranked[0].total == 35


def test_thenar_petite_adds_a_narrow_rear_paragraph_with_its_illustration(monkeypatch):
    """Thénar « Petite » : un paragraphe dédié, illustré (T13), affiché plus bas dans le message."""
    monkeypatch.setattr("config.IMAGES_BASE_URL", "https://cdn.aze.test/illustrations/")
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    narrow = next(e for e in embeds if "arrière étroit" in e.title)
    assert "arrière étroit" in narrow.title
    assert "pilule" in narrow.description
    # Règle « zéro effet » : le paragraphe dit lui-même que le thénar ne modifie pas le score.
    assert "ne modifie pas le score" in narrow.description
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
    # Illustration liée à la bosse de la souris RÉELLEMENT retenue : la retenue du profil Palm
    # 180 × 90 Qualité/Prix est l'ATK A9 Mini, bosse au milieu (« Center » EloShapes → Mid) → T14.
    assert "T14_bosse_centrale" in main.image.url


@pytest.mark.asyncio
async def test_two_slots_never_show_the_same_shell():
    """2026-10-12 : le match idéal et l'alternative ne sont jamais deux variantes de la même coque.

    Avec l'ATK Phantom Ultimate en tête (35/40, 18ᵉ passe), l'alternative vient de l'élargissement de
    la fenêtre : l'ATK Z1 V2 Ultra (30/40, 59,95 €), autre coque et strictement moins chère que l'idéal.
    """
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    ideal, alternative, _ = flow.result_slots(flow.compute_selection(session))
    assert ideal is not None and alternative is not None
    assert not selection._same_shell(ideal, alternative)
    assert (ideal.mouse.label, alternative.mouse.label) == ("ATK Phantom Ultimate", "ATK Z1 V2 Ultra")


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


# ---------------------------------------------------------------------------
# Chasse aux bugs du 2026-10-12 : chaque correction est verrouillée par un test
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode", list(BudgetMode))
def test_purchase_buttons_match_the_mice_shown_in_the_message(mode):
    """Les boutons d'achat suivent les souris AFFICHÉES (idéal, alternative, économie).

    Avant le correctif, ils suivaient les deux premiers du classement interne : en Qualité/Prix par
    exemple, le message montrait « Scyrox V6 » en alternative alors que le second bouton menait à
    « ATK GHOST Extreme », une souris absente du message — et l'alternative n'avait pas de bouton.
    """
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = mode
    if mode is BudgetMode.CUSTOM:
        session.max_budget_eur = 60.0
    selection = flow.compute_selection(session)
    displayed = [s for s in flow.result_slots(selection) if s is not None]
    assert displayed, mode

    links = {s.mouse.id: f"https://shop.test/{s.mouse.id}" for s in displayed}
    view = flow.ResultsView(displayed, links)
    assert [c.label for c in view.children] == [f"Acheter {s.mouse.label}"[:80] for s in displayed]

    # Une souris classée mais NON montrée ne doit pas avoir de bouton.
    shown_ids = {s.mouse.id for s in displayed}
    hidden = [s for s in selection.ranked if s.mouse.id not in shown_ids]
    if hidden:
        assert all(hidden[0].mouse.label not in c.label for c in view.children), mode


@pytest.mark.asyncio
async def test_result_message_links_cover_exactly_the_displayed_mice():
    """Bout en bout : les boutons du message de résultat portent sur les souris des blocs affichés."""
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.QUALITE_PRIX.value)
    await view.children[0].callback(inter)

    embeds = inter.response.edit_message.call_args.kwargs["embeds"]
    fields = fields_of(embeds[0])
    shown = [fields[name] for name in ("🥇 Le match idéal", "🥈 L'alternative", "💸 L'économie")
             if name in fields]
    labels = [c.label for c in inter.response.edit_message.call_args.kwargs["view"].children]
    assert len(labels) == len(shown)
    for line, label in zip(shown, labels):
        assert label == f"Acheter {line.split('**')[1]}"[:80], (line, label)


def _fake_score(mouse_id, total, price, shell_id=None):
    return SimpleNamespace(total=total,
                           mouse=SimpleNamespace(id=mouse_id, label=mouse_id,
                                                 price_eur=price, shell_id=shell_id))


def _fake_selection(ranked, reference, mode=BudgetMode.QUALITE_PRIX):
    return SimpleNamespace(ranked=tuple(ranked), reference_score=reference, mode=mode)


def test_economy_slot_appears_with_the_cheapest_mouse_of_the_zone():
    """Correctif du 2026-10-12 : l'économie est la moins chère de la zone, montrée dès qu'elle est
    moins chère que tout ce qui est affiché (« moins chère que le match idéal ET que l'alternative »).

    Mesure honnête du 2026-10-12 (grille 1 029 profils, tous modes) : la place est remplie dans
    **4 profils sur 1 029 (0,39 %)** avec cette règle, et **2 sur 1 029 (0,19 %)** avant le correctif
    « autre coque » du même jour. Une version antérieure de ce commentaire annonçait « 101 sur 960 » :
    c'était faux (le chiffre ne se reproduisait avec aucune des deux règles) et il faisait croire que
    la troisième place sortait souvent — elle est au contraire structurellement rare, parce qu'il faut
    une souris d'une AUTRE coque, à ≤ 2 points du meilleur score (5 en Économique) et strictement
    moins chère que les deux souris déjà affichées. Chiffres suivis dans
    docs/audit/ROBUSTESSE_2026-10-12.md §8 ; élargir la zone est une décision du propriétaire."""
    ideal = _fake_score("ideal", 30, 90.0)
    alternative = _fake_score("alternative", 29, 55.0)     # meilleur profil des moins chères
    cheapest = _fake_score("cheapest", 28, 40.0)
    selection = _fake_selection([ideal, alternative, cheapest], reference=30)

    got_ideal, got_alternative, economy = flow.result_slots(selection)
    assert got_ideal is ideal
    assert got_alternative is alternative
    assert economy is cheapest
    assert economy.mouse.price_eur < alternative.mouse.price_eur


def test_economy_slot_is_not_cancelled_by_the_different_shell_preference():
    """« D'une autre coque SI POSSIBLE » : la préférence ne doit jamais supprimer la place.

    Avant le correctif du 2026-10-12, le filtrage « autre coque » avait lieu AVANT le plafond de
    prix : dès que la moins chère de l'autre coque était plus chère que l'alternative, la place
    disparaissait alors qu'une souris moins chère de la même coque que l'idéal restait disponible
    (mesure : 2 profils sur 1 029 au lieu de 4).
    """
    ideal = _fake_score("ideal", 30, 90.0, shell_id="coque_1")
    alternative = _fake_score("alternative", 29, 55.0, shell_id="coque_2")
    # Même coque que le match idéal, et moins chère que TOUT ce qui est affiché : la place économie.
    meme_coque = _fake_score("meme_coque", 28, 40.0, shell_id="coque_1")
    # Autre coque, mais plus chère que l'alternative : elle ne peut pas être l'économie.
    autre_coque = _fake_score("autre_coque", 28, 60.0, shell_id="coque_3")
    selection = _fake_selection([ideal, alternative, autre_coque, meme_coque], reference=30)

    got_ideal, got_alternative, economy = flow.result_slots(selection)
    assert got_ideal is ideal and got_alternative is alternative
    assert economy is meme_coque, "la place doit rester affichée, même d'une coque déjà montrée"
    assert economy.mouse.price_eur < alternative.mouse.price_eur


def test_result_slots_never_show_the_same_mouse_twice():
    """Quelle que soit la combinaison, les trois places restent distinctes."""
    ideal = _fake_score("ideal", 30, 70.0)
    other = _fake_score("other", 28, 60.0)
    third = _fake_score("third", 28, 50.0)
    selection = _fake_selection([ideal, other, third], reference=30)

    slots = [s for s in flow.result_slots(selection) if s is not None]
    assert len(slots) == len({s.mouse.id for s in slots})


def test_economy_slot_stays_empty_when_nothing_is_cheaper():
    ideal = _fake_score("ideal", 30, 40.0)          # déjà la moins chère de la zone
    other = _fake_score("other", 29, 55.0)
    selection = _fake_selection([ideal, other], reference=30)

    _, _, economy = flow.result_slots(selection)
    assert economy is None


def test_match_summary_does_not_lowercase_the_grip_label():
    """« prise palm grip bien soutenue » : le libellé « Palm Grip » était écrasé par capitalize()."""
    from utils.matcher import STATUS_SCORED, MouseScore, ScoreBreakdown

    mouse = SimpleNamespace(label="Test M1", id="t", length_mm=120.0, width_max_mm=60.0,
                            hump_position="Mid", button_height="Low", price_eur=49.9,
                            price_status="verified", shape="Symmetrical", hump_position_label=None)
    score = MouseScore(mouse=mouse, grip=Grip.PALM, status=STATUS_SCORED,
                       breakdown=ScoreBreakdown(length_pts=10, width_pts=10, grip_pts=10,
                                                hump_pts=5, button_pts=5))
    text = flow._match_summary(score)
    assert "Palm Grip" in text
    assert text.startswith("Longueur dans la cible")


def test_match_summary_never_claims_a_direction_the_score_does_not_carry():
    """« largeur de prise un peu large » était faux pour une souris PLUS ÉTROITE que la cible.

    Le score ne porte pas le sens de l'écart (trop large / trop étroit, trop long / trop court) :
    la phrase de bilan doit donc rester neutre (correctif du 2026-10-12).
    """
    from utils.matcher import STATUS_SCORED, MouseScore, ScoreBreakdown

    mouse = SimpleNamespace(label="Test M2", id="t2", length_mm=110.0, width_max_mm=52.0,
                            hump_position="Inconnu", button_height="Inconnu", price_eur=30.0,
                            price_status="verified", shape="Symmetrical")
    score = MouseScore(mouse=mouse, grip=Grip.CLAW, status=STATUS_SCORED,
                       breakdown=ScoreBreakdown(length_pts=10, width_pts=0, grip_pts=10))
    text = flow._match_summary(score)
    assert "largeur de prise un peu hors de la cible" in text
    assert "un peu large" not in text and "retrait" not in text


@pytest.mark.asyncio
async def test_double_tap_on_start_shows_no_error_and_opens_the_parcours():
    """Double appui sur le bouton d'accueil : le second clic n'affiche plus « erreur inattendue »."""
    store = SessionStore(ttl_seconds=600)
    inter = make_interaction(store=store)
    inter.response.send_message = AsyncMock(side_effect=discord.InteractionResponded(inter))
    await flow.StartView().start.callback(inter)
    inter.followup.send.assert_not_awaited()            # aucune erreur affichée
    session, status = store.current(99)
    assert status == "ok" and session is not None        # le parcours est bien ouvert


@pytest.mark.asyncio
async def test_expired_notice_is_an_orange_embed_with_the_restart_button():
    """Le message d'expiration garde la charte (orange) ET permet de repartir sur place."""
    store = SessionStore(ttl_seconds=600)
    inter = make_interaction(store=store)
    await flow.GripView().children[0].callback(inter)   # aucun parcours ouvert : refus privé
    kwargs = inter.response.send_message.call_args.kwargs
    assert kwargs["embed"].color == discord.Color.orange()
    assert kwargs["embed"].title == "⏱️ Session expirée"
    assert isinstance(kwargs["view"], flow.StartView)
    assert kwargs["ephemeral"] is True
