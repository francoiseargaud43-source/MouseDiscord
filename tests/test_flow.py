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
async def test_un_fichier_d_images_illisible_ne_bloque_pas_la_premiere_etape(monkeypatch, tmp_path):
    """C55 (2026-10-13) : `images.json` en octets non UTF-8 cassait le parcours dès le PREMIER message.

    Le chargeur d'images est appelé par chaque étape (bannière, illustrations) et ne prévoyait que le
    JSON invalide : `UnicodeDecodeError` remontait jusqu'au flux, le membre lisait « une erreur
    inattendue » et **ne pouvait pas démarrer le test**. Désormais : pas d'image, étape affichée.
    """
    images = tmp_path / "images.json"
    images.write_bytes(b'{"banner": "https://x.test/\xff\xfe.png"}')
    monkeypatch.setattr(flow, "IMAGES_CONFIG_PATH", images)
    inter = make_interaction()
    await flow.StartView().start.callback(inter)
    kwargs = inter.response.send_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.GripView)
    assert kwargs["embed"].title.startswith("Étape 1")


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


def test_une_etape_qui_n_existe_pas_pour_la_prise_le_dit():
    """Le thénar n'existe pas en Fingertip, la variante de Claw n'existe qu'en Claw.

    Un appel fautif doit lever une erreur **lisible** qui nomme la prise et l'étape : un ``KeyError``
    ne disait ni l'une ni l'autre (relevé le 2026-10-13 en relisant le code d'affichage).
    """
    assert flow._step_number("thenar", Grip.PALM) == 2
    assert flow._step_number("measure", Grip.FINGERTIP) == 2
    assert flow._step_number("claw_variant", Grip.CLAW) == 2
    with pytest.raises(ValueError, match="thenar.*Fingertip"):
        flow.thenar_step_embed(Grip.FINGERTIP)
    with pytest.raises(ValueError, match="claw_variant.*Palm"):
        flow._step_number("claw_variant", Grip.PALM)
    with pytest.raises(ValueError, match="inexistante"):
        flow._step_number("thenar", None)          # parcours sans prise : rien à numéroter


def etats_du_questionnaire(store: SessionStore) -> list:
    """Les huit états où le questionnaire affiche une étape : un par étape et par prise.

    Chacun est numéroté en commentaire (position / total de sa prise) : ces huit états servent à
    vérifier que la table des numéros, les titres affichés et les légendes d'aperçu disent la même
    chose (C41 et C43).
    """
    return [
        start_for(store, user_id=1, grip=Grip.PALM),                                  # thénar (2/4)
        start_for(store, user_id=2, grip=Grip.PALM, thenar=Thenar.MOYENNE),           # mesures (3/4)
        start_for(store, user_id=3, grip=Grip.PALM, thenar=Thenar.MOYENNE,
                  length=180.0, width=90.0),                                          # budget (4/4)
        start_for(store, user_id=4, grip=Grip.CLAW),                                  # variante (2/5)
        start_for(store, user_id=5, grip=Grip.CLAW, variant=ClawVariant.RELACHEE),    # thénar (3/5)
        start_for(store, user_id=6, grip=Grip.CLAW, variant=ClawVariant.RELACHEE,
                  thenar=Thenar.MOYENNE, length=180.0, width=90.0),                   # budget (5/5)
        start_for(store, user_id=7, grip=Grip.FINGERTIP),                             # mesures (2/3)
        start_for(store, user_id=8, grip=Grip.FINGERTIP, length=180.0, width=90.0),   # budget (3/3)
    ]


def test_chaque_etape_affichee_porte_le_numero_de_la_table():
    """Trouvé le 2026-10-13 en parcourant tous les états du parcours.

    ``step_kind()`` renvoyait « claw_variant » là où la table des numéros disait « variant » : toute
    numérotation de l'étape de variante levait donc un ``ValueError`` (personne ne l'appelait : le
    titre écrivait son numéro **en dur**, deuxième source de vérité). Ici, chaque état possible est
    traversé et les deux doivent dire la même chose : le numéro de la table existe, et il se retrouve
    dans le titre réellement affiché par ``step_for``.
    """
    store = SessionStore(ttl_seconds=600)
    for etat in etats_du_questionnaire(store):
        kind = flow.step_kind(etat)
        assert kind in flow.STEP_NUMBERS[etat.grip], f"{kind} n'a pas de numéro : la table a divergé"
        numero = flow._step_number(kind, etat)
        titre = flow.step_for(etat)[0].title
        assert f"Étape {numero}/{flow._steps_total(etat)}" in titre, f"{kind} : {titre!r}"


def test_le_total_des_etapes_se_lit_dans_la_meme_table_que_les_numeros(monkeypatch):
    """Trouvé le 2026-10-13 en relisant l'affichage des étapes (même famille que C41).

    Le total (« Étape n/N ») était écrit en clair — 3 en Fingertip, 5 en Claw, 4 sinon — à côté de la
    table des numéros : deux sources de vérité pour le même nombre, et la seconde était **silencieuse**
    (un total faux reste plausible : rien ne signale qu'une étape a été ajoutée ou retirée). Preuve par
    mutation : on ajoute une étape à la table, le total ET le titre réellement affiché suivent.
    """
    for grip, numeros in flow.STEP_NUMBERS.items():
        assert flow._steps_total(grip) == max(numeros.values()), grip
        assert numeros["grip"] == flow.GRIP_STEP_NUMBER, grip     # toutes les prises commencent en 1
    assert "Étape 1 — Votre prise" == flow.grip_step_embed().title  # étape 1 : pas de dénominateur

    monkeypatch.setitem(flow.STEP_NUMBERS[Grip.PALM], "etape_en_plus", 5)
    assert flow._steps_total(Grip.PALM) == 5                                  # le total suit la table…
    assert "Étape 2/5" in flow.thenar_step_embed(Grip.PALM).title              # …et le titre affiché aussi
    with pytest.raises(ValueError, match="aucune étape déclarée"):
        flow._steps_total(None)                        # au lieu d'un « /4 » inventé de toutes pièces


def test_les_legendes_d_apercu_suivent_le_titre_des_embeds():
    """Trouvé le 2026-10-13 dans l'aperçu livré ``docs/apercu_prix_libre.png`` : sa légende annonçait
    « Étape 5/5 — budget » au-dessus d'un embed titré « Étape 4/4 » (parcours Palm, budget en 4).

    Les légendes de ce fichier d'aperçu sont désormais dérivées de la même table que les titres :
    voici la garantie, sur les huit états du questionnaire.
    """
    from tools import render_preview                # import paresseux : cet outil a besoin de Pillow

    def numero(texte: str) -> str:
        """Numéro d'étape lu dans un titre ou une légende : « Étape 4/4 — … » → « Étape 4 »."""
        return texte.split("Étape ", 1)[1].split("/", 1)[0].split(" —", 1)[0].strip()

    store = SessionStore(ttl_seconds=600)
    claw = start_for(store, user_id=20, grip=Grip.CLAW, variant=ClawVariant.RELACHEE,
                     thenar=Thenar.MOYENNE, length=200.0, width=110.0)   # parcours complet : 5 étapes
    palm = start_for(store, user_id=21, grip=Grip.PALM, thenar=Thenar.MOYENNE,
                     length=180.0, width=90.0)                            # parcours Palm : 4 étapes
    palm.budget_mode = BudgetMode.PEU_IMPORTE_PRIX
    cartes_prix_libre = render_preview.etapes_du_prix_libre(palm, flow.compute_selection(palm))
    cartes = render_preview.etapes_du_parcours(claw) + cartes_prix_libre
    verifiees = 0
    for legende, embed, _, _ in cartes:
        if not embed.title.startswith("Étape "):        # cartes « Accueil » et « Résultat »
            continue
        verifiees += 1
        assert numero(legende) == numero(embed.title), f"{legende!r} vs {embed.title!r}"
    # 5 cartes d'étape pour le parcours Claw + 1 pour l'aperçu « prix libre » (Palm).
    assert verifiees == 6
    # Le cas exact du défaut : l'étape budget d'un parcours Palm est la 4/4, jamais la 5/5.
    assert f"Étape {flow._step_number('budget', palm)}/{flow._steps_total(palm)} — " == "Étape 4/4 — "
    legende_palm = cartes_prix_libre[0][0]
    assert legende_palm.startswith("Étape 4/4 — budget : 5 options"), legende_palm


def test_importer_l_outil_d_apercu_ne_change_rien_au_bot(monkeypatch):
    """Trouvé le 2026-10-13 en écrivant le test ci-dessus : importer ``tools/render_preview.py``
    branchait ses faux domaines d'images sur le module du bot. Le test « sans URL d'images » échouait
    alors selon l'ordre d'exécution — un outil qui se contente d'être importé ne doit rien changer.
    Le détournement est maintenant demandé explicitement (``images_locales()``, appelé par ``main``).
    """
    from tools import render_preview

    monkeypatch.setattr("config.IMAGES_BASE_URL", "")
    avant = flow.load_image_urls
    assert callable(render_preview.images_locales)         # l'outil expose la bascule...
    assert flow.load_image_urls is avant                   # ...mais l'import n'a rien rebranché
    assert flow.grip_step_embed().image.url is None        # et le bot reste sans image


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
    # l'élargissement de la fenêtre, l'ATK Z1 V2 Ultimate (30/40, 75 %, 59,95 €, moins chère que
    # l'idéal) — nom de la boutique officielle depuis le 2026-10-13 (« Z1 V2 Ultra » n'existe pas).
    assert "ATK Phantom Ultimate" in ideal
    assert "91,95 €" in ideal and "**88 %**" in ideal   # nom · poids · prix · pourcentage · forme
    assert "Score" not in ideal and "Confiance" not in ideal and "pts" not in ideal
    assert "**75 %**" in alt                            # l'alternative porte aussi son pourcentage
    assert "ATK Z1 V2 Ultimate" in alt
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
async def test_un_fichier_de_liens_casse_ne_prive_pas_le_membre_de_son_resultat(monkeypatch, tmp_path):
    """C54 (2026-10-13) : un `commercial_links.json` tronqué faisait échouer le résultat ENTIER.

    Le chargeur lève alors `JSONDecodeError`, et il est appelé APRÈS le calcul, hors de la garde
    « catalogue illisible » : le membre lisait « une erreur inattendue », et « refaites l'action » ne
    pouvait pas aboutir tant que le fichier restait cassé. Désormais une lecture impossible est traitée
    comme un fichier absent : les souris s'affichent, les boutons d'achat cèdent la place au rappel
    « Liens à venir ».
    """
    liens = tmp_path / "commercial_links.json"
    liens.write_text('{"atk_a9_ultimate": "https://www.atk.store/x"', encoding="utf-8")
    monkeypatch.setattr(flow, "COMMERCIAL_LINKS_PATH", liens)
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.QUALITE_PRIX.value)
    await view.children[0].callback(inter)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert isinstance(kwargs["view"], flow.ResultsView)
    assert len(kwargs["embeds"]) == 4                       # le résultat, entier
    ideal = next(v for k, v in fields_of(kwargs["embeds"][0]).items() if "match idéal" in k)
    assert "ATK Phantom Ultimate" in ideal                  # la recommandation est bien là
    placeholders = [c for c in kwargs["view"].children if getattr(c, "disabled", False)]
    assert len(placeholders) == 1 and placeholders[0].label == "Liens à venir"
    assert not any(getattr(c, "url", None) for c in kwargs["view"].children)


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
    assert "Scyrox V8" not in text and "F1 V3 Ultimate+" not in text and "Xlite v4 Large" not in text


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
    la fenêtre : l'ATK Z1 V2 Ultimate (30/40, 59,95 €), autre coque et strictement moins chère que l'idéal.
    """
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    session.budget_mode = BudgetMode.QUALITE_PRIX
    ideal, alternative, troisieme = flow.result_slots(flow.compute_selection(session))
    assert ideal is not None and alternative is not None
    assert not selection._same_shell(ideal, alternative)
    assert (ideal.mouse.label, alternative.mouse.label) == ("ATK Phantom Ultimate", "ATK Z1 V2 Ultimate")
    # Troisième place (décision du 2026-10-12) : elle est remplie, d'une TROISIÈME coque, et son titre
    # dit la vérité — l'ATK A9 Mini est au même prix que l'alternative (59,95 €), donc « L'autre option ».
    assert troisieme is not None and troisieme.mouse.label == "ATK A9 Mini"
    assert not selection._same_shell(ideal, troisieme) and not selection._same_shell(alternative, troisieme)
    assert flow.third_slot_title(troisieme, ideal, alternative) == "➕ L'autre option"


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
    noms_possibles = ("🥇 Le match idéal", "🥈 L'alternative", "💸 L'économie", "➕ L'autre option")
    shown = [fields[name] for name in noms_possibles if name in fields]
    labels = [c.label for c in inter.response.edit_message.call_args.kwargs["view"].children]
    assert len(labels) == len(shown)
    for line, label in zip(shown, labels):
        assert label == f"Acheter {line.split('**')[1]}"[:80], (line, label)


@pytest.mark.asyncio
async def test_the_result_always_shows_three_lines_when_the_budget_allows_it():
    """Décision du propriétaire (2026-10-12) : « 3 lignes partout où le budget le permet ».

    Profil Budget personnalisé serré (Palm 150 × 65, plafond 25 €) : la zone du mode ne contient rien
    de comparable à la VXE V3 (13,95 €), qui gagne le classement. Les deux autres lignes sont remplies
    par le dernier palier — l'U2 (22,95 €, dans le budget) puis la R1 — et chaque ligne qui n'est pas
    une vraie alternative porte le titre « 🔎 Autre piste ». Mesure de référence : 3 lignes
    sur 85,50 % de la grille du banc (23 231 des 27 170 profils) ; les trous restants sont
    exclusivement des budgets épuisés (1 196 profils à 2 lignes, 182 à 1, 2 561 sans aucun résultat).
    """
    store = SessionStore(ttl_seconds=600)
    session = start_for(store, grip=Grip.PALM, length=150.0, width=65.0, thenar=Thenar.PETITE)
    session.budget_mode = BudgetMode.CUSTOM
    session.max_budget_eur = 25.0
    selection = flow.compute_selection(session)
    ideal, alternative, economy = flow.result_slots(selection)
    assert (ideal.mouse.id, alternative.mouse.id, economy.mouse.id) == ("vxe_v3", "atk_u2", "vxe_r1")
    embeds = flow.results_embeds(session, selection)
    lignes = [field.value for field in embeds[0].fields]
    montrees = [score for score in (ideal, alternative, economy) if score is not None]
    assert len(montrees) == 3
    assert len(lignes) == 3
    for score in montrees:                      # chaque souris montrée est là, avec son prix
        assert any(score.mouse.label in ligne for ligne in lignes), score.mouse.label
        assert f"{score.mouse.price_eur:.2f}".replace(".", ",") + " €" in " ".join(lignes)
    # Les deux lignes du dernier palier portent le titre qui dit la vérité (la 1re reste le match idéal).
    noms = [field.name for field in embeds[0].fields]
    assert noms[0] == "🥇 Le match idéal"
    assert noms[1] == noms[2] == flow.PISTE_TITLE
    assert all(score.mouse.price_eur is not None and score.mouse.price_eur <= 25.0 for score in montrees)


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


def test_third_slot_takes_the_cheapest_other_option_when_nothing_is_cheaper():
    """Décision du propriétaire (2026-10-12) : quand plus rien n'est moins cher que le match idéal
    (cas d'une souris qui est déjà la moins chère du catalogue), la troisième place reste remplie par
    l'option la moins chère de la fenêtre — donc « un peu plus chère » au minimum — et son libellé dit
    la vérité (``third_slot_title``) : ce n'est plus « l'économie »."""
    ideal = _fake_score("ideal", 30, 40.0)          # déjà la moins chère de la zone
    alternative = _fake_score("alternative", 29, 55.0)
    option = _fake_score("option", 28, 60.0)
    selection = _fake_selection([ideal, alternative, option], reference=30)

    got_ideal, got_alternative, third = flow.result_slots(selection)
    assert (got_ideal, got_alternative) == (ideal, alternative)
    assert third is option, "la troisième place doit rester remplie"
    assert third.mouse.price_eur > ideal.mouse.price_eur
    assert flow.third_slot_title(third, ideal, alternative) == "➕ L'autre option"


def test_third_slot_is_the_cheapest_of_the_window_not_an_expensive_one():
    """« Un peu plus chère » : c'est la moins chère des options restantes, pas la plus chère."""
    ideal = _fake_score("ideal", 30, 20.0)
    proche = _fake_score("proche", 29, 45.0)
    loin = _fake_score("loin", 28, 150.0)
    selection = _fake_selection([ideal, loin, proche], reference=30)

    _, alternative, third = flow.result_slots(selection)
    assert alternative is proche, "l'alternative est le meilleur profil des moins chères"
    assert third is loin, "il ne reste que la plus chère"
    assert flow.third_slot_title(third, ideal, alternative) == "➕ L'autre option"


def test_third_slot_prefers_another_shell_over_a_variant_of_a_shown_mouse():
    """Décision du 2026-10-12 appliquée à la troisième place : « deux places ne montrent jamais la
    même coque ». Quand la moins chère des options restantes est une variante d'une coque déjà
    affichée, la place prend la moins chère des coques DIFFÉRENTES — mesuré sur la grille de
    référence : 1 338 profils concernés, surcoût médian +4,00 € (61 % sous +10 €), et 837 profils où
    aucune autre coque n'existe dans la fenêtre (là, la variante reste la seule option)."""
    ideal = _fake_score("ideal", 30, 20.0, shell_id="s1")
    alternative = _fake_score("alternative", 29, 45.0, shell_id="s2")
    variante = _fake_score("variante", 28, 41.95, shell_id="s2")   # même coque que l'alternative
    autre = _fake_score("autre", 27, 59.95, shell_id="s3")
    selection = _fake_selection([ideal, alternative, variante, autre], reference=30)

    got_ideal, got_alternative, third = flow.result_slots(selection)
    assert (got_ideal, got_alternative) == (ideal, alternative)
    assert variante.mouse.price_eur < autre.mouse.price_eur      # la moins chère est une variante…
    assert third is autre, "…mais la même coque deux fois n'offre aucun choix"
    assert flow.third_slot_title(third, ideal, alternative) == "➕ L'autre option"


def test_third_slot_keeps_a_variant_when_no_other_shell_exists_in_the_window():
    """Repli : s'il n'y a AUCUNE autre coque dans la fenêtre, la variante reste montrée (place
    remplie) — 837 profils sur la grille de référence. Jamais de place vide par principe."""
    ideal = _fake_score("ideal", 30, 45.0, shell_id="s1")
    alternative = _fake_score("alternative", 29, 22.95, shell_id="s2")
    variante = _fake_score("variante", 28, 41.95, shell_id="s1")
    selection = _fake_selection([ideal, alternative, variante], reference=30)

    _, _, third = flow.result_slots(selection)
    assert third is variante
    assert flow.third_slot_title(third, ideal, alternative) == "➕ L'autre option"


def test_economy_slot_stays_price_first_when_no_other_shell_is_cheaper():
    """« L'économie » d'abord au prix : si la seule souris moins chère que les deux autres partage une
    coque déjà affichée, elle reste montrée — c'est le prix qui fait le rôle de cette place (18 profils
    sur la grille de référence)."""
    ideal = _fake_score("ideal", 30, 90.0, shell_id="s1")
    alternative = _fake_score("alternative", 29, 55.0, shell_id="s2")
    meme_coque = _fake_score("meme_coque", 28, 40.0, shell_id="s1")
    selection = _fake_selection([ideal, alternative, meme_coque], reference=30)

    _, _, third = flow.result_slots(selection)
    assert third is meme_coque
    assert third.mouse.price_eur < min(ideal.mouse.price_eur, alternative.mouse.price_eur)
    assert flow.third_slot_title(third, ideal, alternative) == "💸 L'économie"


def test_third_slot_falls_back_to_the_best_remaining_mouse_when_the_window_is_empty():
    """Dernier palier (décision du propriétaire, 2026-10-12) : la fenêtre est vide → la place prend la
    meilleure souris restante et s'intitule « 🔎 Autre piste ». Deux lignes ne suffisent pas : une place
    vide n'informe pas."""
    ideal = _fake_score("ideal", 30, 60.0, shell_id="s1")
    alternative = _fake_score("alternative", 29, 45.0, shell_id="s2")
    loin = _fake_score("loin", 18, 80.0, shell_id="s3")      # 12 points sous le meilleur score, plus chère
    selection = _fake_selection([ideal, alternative, loin], reference=30)

    _, _, third = flow.result_slots(selection)
    assert third is loin
    assert flow.third_slot_title(third, ideal, alternative, 30) == flow.PISTE_TITLE
    assert flow.third_slot_title(third, ideal, alternative, 30) == "🔎 Autre piste"


def test_second_slot_falls_back_to_the_best_remaining_mouse_and_says_it():
    """Même palier pour la DEUXIÈME place : pas de trou au milieu du résultat."""
    ideal = _fake_score("ideal", 30, 60.0, shell_id="s1")
    loin = _fake_score("loin", 18, 40.0, shell_id="s3")
    selection = _fake_selection([ideal, loin], reference=30)

    _, alternative, third = flow.result_slots(selection)
    assert alternative is loin and third is None
    assert flow.alternative_slot_title(loin, ideal, 30, tolerance=2) == flow.PISTE_TITLE
    # Une souris comparable (dans la zone du mode) garde son titre de place.
    zone = _fake_score("zone", 29, 40.0, shell_id="s3")
    assert flow.alternative_slot_title(zone, ideal, 30, tolerance=2) == "🥈 L'alternative"


def test_the_economy_label_wins_over_the_piste_label_when_the_mouse_is_cheaper():
    """Le prix d'abord : une souris **strictement moins chère** que tout ce qui est affiché reste
    « l'économie », même si elle vient du dernier palier (574 profils de la grille, 1,8 % des trois
    places) — c'est un fait vérifiable à l'écran."""
    ideal = _fake_score("ideal", 30, 60.0, shell_id="s1")
    alternative = _fake_score("alternative", 25, 81.95, shell_id="s2")
    passee = _fake_score("passee", 20, 13.95, shell_id="s3")     # 10 points sous le meilleur score
    sous_plafond = _fake_score("sous_plafond", 12, 74.9, shell_id="s4")
    selection = _fake_selection([ideal, alternative, passee, sous_plafond], reference=30)

    _, _, third = flow.result_slots(selection)
    assert third is passee
    assert flow.third_slot_title(third, ideal, alternative, 30) == "💸 L'économie"


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


def test_le_poids_des_36_souris_s_affiche_sans_planter_ni_charabia():
    """Le poids est la seule ligne du résultat construite par un formatage direct (`_num`).

    Trouvé le 2026-10-13 en attaquant le catalogue : un poids en texte, une liste ou un objet passait
    la validation puis faisait lever l'affichage du résultat (`ValueError: Unknown format code 'g'`),
    soit « erreur inattendue » pour le membre. Le chargeur refuse désormais ces valeurs
    (`tests/test_data.py`), et ici la chaîne complète est parcourue : aucune des 36 souris du
    catalogue livré ne peut produire autre chose qu'un nombre de grammes.
    """
    for mouse in flow.load_catalog(flow.MOUSE_DB_PATH):
        texte = flow._weight_text(mouse)
        assert texte.endswith(" g"), f"{mouse.id} : {texte!r}"
        nombre = texte[:-2].replace(",", ".")
        assert float(nombre) == mouse.weight_g, f"{mouse.id} : {texte!r}"


@pytest.mark.asyncio
async def test_deux_appuis_sur_le_panneau_ne_laissent_qu_un_parcours_vivant():
    """Deux appuis distincts sur le bouton d'accueil : un seul parcours reste vivant, le plus récent.

    Un double appui mobile envoie deux interactions distinctes : chacune ouvre son parcours, et la
    seconde **remplace** la première. La garantie tenue est donc « un seul parcours vivant pour ce
    membre », pas « une seule réponse » — le commentaire du code affirmait le contraire avant le
    2026-10-13. Les deux messages restent utilisables : leurs composants retrouvent le parcours du
    membre qui clique (`SessionStore.current`).
    """
    store = SessionStore(ttl_seconds=600)
    premier = make_interaction(user_id=99, store=store)
    second = make_interaction(user_id=99, store=store)
    await flow.StartView().start.callback(premier)
    premiere_session, _ = store.current(99)
    await flow.StartView().start.callback(second)
    session, status = store.current(99)
    assert status == "ok" and session is not None
    assert len(store) == 1, "deux parcours vivants pour le même membre"
    assert session.session_id != premiere_session.session_id
    assert premier.response.send_message.await_count == 1
    assert second.response.send_message.await_count == 1


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


# ---------------------------------------------------------------------------
# Décisions du propriétaire du 2026-10-13 : ordre des pourcentages, marqueur de prix, pied de message
# ---------------------------------------------------------------------------
def _trois_places(mode, budget=None, grip=Grip.PALM, longueur=180.0, largeur=90.0,
                  thenar=Thenar.PETITE):
    """Résultat du moteur pour un profil donné : session, sélection et trois places."""
    session = flow.FinderSession(user_id=1)
    session.budget_mode = mode
    session.max_budget_eur = budget if mode is BudgetMode.CUSTOM else None
    session.grip = grip
    session.hand_length_mm = longueur
    session.hand_width_mm = largeur
    session.thenar = None if grip is Grip.FINGERTIP else thenar
    if grip is Grip.CLAW:
        session.claw_variant = ClawVariant.RELACHEE
    selection = flow.compute_selection(session)
    return session, selection, flow.result_slots(selection)


def test_le_pourcentage_ne_remonte_jamais_d_une_place_a_l_autre():
    """Ordre garanti (décision du propriétaire, 2026-10-13) : idéal ≥ alternative ≥ économie.

    Avant, le mode Économique pouvait afficher une deuxième place mieux notée que le « match idéal » —
    c'est la règle du mode (le match idéal y est la souris la MOINS CHÈRE de la zone) : **1 622 profils
    (6,0 %)** sur la grille complète, et la troisième place dépassait la deuxième sur 24 à 128 profils
    selon le mode. Le membre lisait alors un « idéal » moins bien noté que la ligne du dessous.
    """
    from utils.matcher import compatibility_percent

    cas = [
        (None, None), (BudgetMode.ECONOMIQUE, None), (BudgetMode.QUALITE_PRIX, None),
        (BudgetMode.HAUT_DE_GAMME, None), (BudgetMode.PEU_IMPORTE_PRIX, None),
        (BudgetMode.CUSTOM, 300.0), (BudgetMode.CUSTOM, 45.0), (BudgetMode.CUSTOM, 15.0),
    ]
    profils = 0
    replis: list[str] = []
    for mode, budget in cas:
        for grip in (Grip.PALM, Grip.CLAW, Grip.FINGERTIP):
            for longueur, largeur in ((150.0, 85.0), (160.0, 70.0), (180.0, 90.0),
                                      (200.0, 110.0), (225.0, 85.0)):
                _, selection, (ideal, alternative, economy) = _trois_places(mode, budget, grip,
                                                                            longueur, largeur)
                montrees = [score for score in (ideal, alternative, economy) if score is not None]
                if not montrees:
                    continue
                profils += 1
                pourcentages = [compatibility_percent(score) for score in montrees]
                if pourcentages == sorted(pourcentages, reverse=True):
                    continue
                # Repli documenté (règle du 2026-10-12 : jamais de trou dans le résultat) : il ne peut
                # s'appliquer que si AUCUNE souris du classement ne passe sous le plafond. Le test le
                # VÉRIFIE au lieu de le tolérer — sinon le repli masquerait une vraie régression.
                montrees_ids = {score.mouse.id for score in montrees}
                for place in range(1, len(montrees)):
                    plafond = montrees[place - 1].total
                    if montrees[place].total <= plafond:
                        continue
                    candidats = [score for score in selection.ranked[1:]
                                 if score.mouse.id not in montrees_ids and score.total <= plafond]
                    assert candidats == [], (
                        f"{mode}/{grip}/{longueur}x{largeur} : le plafond laissait "
                        f"{[(c.mouse.label, c.total) for c in candidats]}")
                    replis.append(f"{mode}/{grip}/{longueur}x{largeur} place {place + 1}")
    assert profils >= 100, f"trop peu de profils contrôlés ({profils}) : le contrôle ne prouve rien"
    assert len(replis) <= profils * 0.02, f"trop de replis d'ordre ({len(replis)} sur {profils})"


def test_le_match_ideal_ne_change_pas_avec_la_regle_d_ordre():
    """La règle d'ordre ne touche JAMAIS le match idéal : elle plafonne les places du dessous.

    Mesuré sur la grille complète dans `docs/audit/ROBUSTESSE_2026-10-12.md` §24 : 0 profil sur
    24 609 change de match idéal ; seules les 2e et 3e places bougent (1 615 et 1 976 profils).
    """
    for mode, budget in ((BudgetMode.ECONOMIQUE, None), (BudgetMode.CUSTOM, 45.0)):
        _, selection, (ideal, _, _) = _trois_places(mode, budget)
        assert ideal is not None and ideal.mouse.id == selection.ranked[0].mouse.id


def test_a_prix_non_verifie_le_message_le_dit():
    """Marqueur de prix (décision du propriétaire, 2026-10-13) : le message ne fait pas passer un prix

    non attesté pour un prix vérifié. Le master prompt le montrait dans ses exemples, mais l'onglet
    « Détails » qui le portait a été retiré le 2026-10-11 : plus rien ne l'affichait (16 % des profils).
    """
    # Profil où le catalogue affiche bien une souris à prix non attesté (Scyrox V6, prix du cahier
    # des charges : la boutique du fabricant vend en dollars, jamais convertis).
    session, selection, _ = _trois_places(None, None, Grip.PALM, 160.0, 70.0)
    embeds = flow.results_embeds(session, selection)
    texte = "\n".join((embed.description or "") + "".join(f.value for f in embed.fields) for embed in embeds)
    montrees = [s for s in flow.result_slots(selection) if s is not None]
    attendues = [s for s in montrees if s.mouse.price_status != "verified"]
    assert attendues, "aucune souris à prix non attesté dans ce profil : le test ne prouverait rien"
    for score in attendues:
        assert f"{score.mouse.price_eur:.2f}".replace(".", ",") + " € (prix non vérifié)" in texte
    for score in (s for s in montrees if s.mouse.price_status == "verified"):
        assert "(prix non vérifié)" not in flow._price_text(score, verified_hint=True)


def test_le_pied_de_message_ne_renvoie_plus_a_un_bloc_disparu():
    """Le renvoi « Comment lire ce résultat » (bloc supprimé le 2026-10-11) est corrigé (C27).

    Le pied de page renvoie désormais au bloc qui EXISTE — « 🧭 Pourquoi ce choix ? » — et seulement
    quand ce bloc est bien dans le message : sur un parcours incomplet, il n'y a aucun renvoi.
    """
    assert "Comment lire ce résultat" not in flow.SCORE_DISCLAIMER
    session, selection, _ = _trois_places(BudgetMode.QUALITE_PRIX)
    embeds = flow.results_embeds(session, selection)
    assert "Pourquoi ce choix ?" in embeds[-1].footer.text
    assert "Comment lire ce résultat" not in embeds[-1].footer.text
    # Parcours incomplet (aucune mesure) : aucun renvoi, puisque le bloc n'est pas affiché.
    incomplet = flow.FinderSession(user_id=1)
    incomplet.grip = Grip.PALM
    assert flow.results_embeds(incomplet, selection)[0].footer.text == flow.SCORE_DISCLAIMER


def test_une_place_au_score_partiel_l_annonce_sur_sa_ligne():
    """Score partiel en 2e / 3e place (décision du propriétaire, 2026-10-13) : la ligne le dit.

    Une souris dont la hauteur des boutons n'est pas documentée est notée sur les critères disponibles
    : son pourcentage est donc calculé SANS ce critère, donc **sous-estimé** (le critère ne peut que
    rapporter des points, jamais en retirer). La note longue du bloc « 📐 Vos repères de taille » n'est
    écrite que pour le match idéal : sans le marqueur, les 2e et 3e places affichaient un pourcentage
    amputé comme s'il était complet (**8 187 places** sur 27 170 profils, mesuré le 2026-10-13).
    """
    session, selection, (ideal, alternative, economy) = _trois_places(
        BudgetMode.ECONOMIQUE, None, Grip.CLAW, 140.0, 60.0)
    assert ideal is not None and not ideal.is_partial, "le profil de contrôle doit avoir un idéal complet"
    assert alternative is not None and alternative.is_partial
    assert economy is not None and economy.is_partial
    main = flow.results_embeds(session, selection)[0]
    lignes = {f.name: f.value.split("\n")[0]
              for f in main.fields if f.name.startswith(("🥇", "🥈", "🔎", "➕", "💸"))}
    assert len(lignes) == 3
    assert all(flow.PARTIAL_HINT not in ligne for name, ligne in lignes.items()
               if name.startswith("🥇")), "le match idéal est expliqué en clair : pas de marqueur"
    marquees = [ligne for name, ligne in lignes.items() if not name.startswith("🥇")]
    assert len(marquees) == 2 and all(ligne.endswith(flow.PARTIAL_HINT) for ligne in marquees), marquees
    # Le marqueur vient APRÈS la forme de coque : la comparaison « Symétrique / Ergonomique » reste
    # alignée tout à droite (demande du propriétaire du 2026-10-11).
    assert all(ligne.split(" · ")[-2] in ("Symétrique", "Ergonomique") for ligne in marquees)


def test_la_note_du_score_partiel_ne_se_repete_pas_sur_la_ligne_du_match_ideal():
    """Quand le match idéal est au score partiel, la note longue en tient lieu : pas de marqueur en plus."""
    session, selection, (ideal, _, _) = _trois_places(None, None, Grip.PALM, 140.0, 60.0)
    assert ideal is not None and ideal.is_partial
    embeds = flow.results_embeds(session, selection)
    main = embeds[0]
    ligne = next(f.value.split("\n")[0] for f in main.fields if f.name.startswith("🥇"))
    assert flow.PARTIAL_HINT not in ligne
    note = "\n".join((embed.description or "") for embed in embeds)
    assert "Hauteur des boutons non documentée" in note

# ---------------------------------------------------------------------------
# Chemins d'échec et chemins de reprise : les seuls que la suite ne touchait pas
# (mesure du 2026-10-13 : couverture des modules du bot à 95 %, ces branches à 0 %)
# ---------------------------------------------------------------------------
def test_un_prix_absent_est_annonce_comme_non_renseigne():
    """`_price_text` ne doit jamais afficher un montant inventé ni un vide muet.

    Aucune souris du catalogue n'a de prix manquant aujourd'hui : la branche n'était donc exercée
    par aucun test. Elle dit « prix non renseigné » — l'information existe pour le membre, et le
    mode « Peu importe le prix » reste utilisable avec une souris sans prix connu.
    """
    score = SimpleNamespace(mouse=SimpleNamespace(price_eur=None, price_status="unknown"))
    assert flow._price_text(score, verified_hint=True) == "prix non renseigné"
    # Un prix présent mais non attesté porte le marqueur ; un prix vérifié n'en porte aucun.
    assert flow._price_text(SimpleNamespace(mouse=SimpleNamespace(price_eur=91.95, price_status="verified"))) == "91,95 €"
    assert "(prix non vérifié)" in flow._price_text(
        SimpleNamespace(mouse=SimpleNamespace(price_eur=45.0, price_status="owner_spec_unverified")),
        verified_hint=True)


def test_aucun_match_classable_reste_une_reponse_honnete_et_utile():
    """Profil sans candidat (petite main, budget 10 €) : une seule carte, qui dit quoi faire.

    C'est le cas de 2 561 profils sur 27 170 de la grille complète. Le message ne rejette la faute
    ni sur le membre ni sur des « données manquantes » : il propose les deux seules issues réelles
    (changer de gamme, élargir le budget).
    """
    session, selection, places = _trois_places(BudgetMode.CUSTOM, 10.0, Grip.PALM, 140.0, 60.0)
    assert places == (None, None, None)
    embeds = flow.results_embeds(session, selection)
    assert len(embeds) == 1
    champs = fields_of(embeds[0])
    assert "Aucun match classable" in champs
    valeur = champs["Aucun match classable"]
    assert "Essayez une autre gamme ou un budget plus élevé" in valeur
    assert embeds[0].footer.text == flow.SCORE_DISCLAIMER
    assert not [f.name for f in embeds[0].fields if "match idéal" in f.name]


def test_le_message_sans_candidat_n_accuse_pas_le_catalogue():
    """Le message doit nommer la vraie cause : les critères fournis, jamais les données des souris.

    Trouvé le 2026-10-13 (46e passe, C59) : le texte disait « aucune souris ne peut être classée avec
    les données vérifiées pour ces critères ». Or cette carte s'affiche dans trois cas réels — mesures
    hors de la plage des 36 souris, budget trop serré, gamme sans candidat — où des souris **sont**
    classables et où le catalogue n'a rien à se reprocher : le membre recevait une explication fausse,
    qui l'incitait à attendre une correction de données au lieu d'essayer une autre gamme.
    """
    # 1. Un budget trop serré (140 × 60 mm en Palm : beaucoup de souris compatibles, aucune à 10 €).
    serre = flow.FinderSession(user_id=1)
    serre.grip, serre.thenar = Grip.PALM, Thenar.MOYENNE
    serre.hand_length_mm, serre.hand_width_mm = 140.0, 60.0
    serre.budget_mode, serre.max_budget_eur = BudgetMode.CUSTOM, 10.0
    # 2. Des mesures hors de la plage du catalogue (main de 260 × 130 mm).
    hors_plage = flow.FinderSession(user_id=1)
    hors_plage.grip, hors_plage.thenar = Grip.PALM, Thenar.MOYENNE
    hors_plage.hand_length_mm, hors_plage.hand_width_mm = 260.0, 130.0
    hors_plage.budget_mode = BudgetMode.PEU_IMPORTE_PRIX

    for session in (serre, hors_plage):
        selection = flow.compute_selection(session)
        assert flow.result_slots(selection) == (None, None, None)
        assert not selection.ranked                       # aucune souris classable pour ces critères
        valeur = fields_of(flow.results_embeds(session, selection)[0])["Aucun match classable"]
        assert "Aucune souris ne peut être retenue avec ces critères." in valeur
        assert "Essayez une autre gamme ou un budget plus élevé" in valeur
        for accusation in ("données vérifiées", "illisible", "non vérifiée", "à vérifier"):
            assert accusation not in valeur, f"le message accuse le catalogue : {valeur!r}"


@pytest.mark.asyncio
async def test_un_catalogue_illisible_dit_la_vraie_raison_au_membre(monkeypatch, tmp_path):
    """La garde « catalogue illisible » du résultat n'était jamais exercée.

    Si `mouse_db.json` devient illisible entre deux clics (édition à la main, transfert
    interrompu), le membre doit lire une phrase qui dit quoi faire — jamais « erreur inattendue »,
    ni un résultat vide. Le parcours n'est pas consommé : il peut réessayer.
    """
    casse = tmp_path / "mouse_db.json"
    casse.write_text('{"pas": "une liste"', encoding="utf-8")
    monkeypatch.setattr(flow, "MOUSE_DB_PATH", casse)
    store = SessionStore(ttl_seconds=600)
    start_for(store, grip=Grip.PALM, length=180.0, width=90.0, thenar=Thenar.MOYENNE)
    inter = make_interaction(store=store)
    view = flow.BudgetView()
    select_values(view.children[0], BudgetMode.QUALITE_PRIX.value)
    await view.children[0].callback(inter)
    assert not inter.response.edit_message.await_count
    message = inter.response.send_message.await_args.args[0]
    assert "momentanément illisibles" in message
    assert "prévenez la personne qui gère le bot" in message


@pytest.mark.asyncio
async def test_le_parcours_reprend_l_etape_manquante_si_ses_reponses_ont_disparu():
    """Clic sur « Budget » après un redémarrage sans état : on reprend à l'étape manquante.

    C'est le filet qui évite une impasse (mesures perdues par expiration ou fichier d'état
    inutilisable) : la garde existait, aucun test ne la touchait.
    """
    # Prise choisie, thénar pas encore répondu : on reprend à l'étape qui manque, pas au début.
    session = flow.FinderSession(user_id=99, grip=Grip.PALM)
    inter = make_interaction()
    await flow._show_results(inter, session)
    # Le message d'origine existe encore : l'étape reprend DANS ce message (édition), sans en créer un.
    kwargs = inter.response.edit_message.call_args.kwargs
    assert kwargs["embed"].title.startswith("Étape 2")
    assert isinstance(kwargs["view"], flow.ThenarView)
    assert not inter.response.send_message.await_count

    # Thénar renseigné, mesures absentes : la reprise saute à l'étape des mesures.
    session.thenar = Thenar.MOYENNE
    inter = make_interaction()
    await flow._show_results(inter, session)
    kwargs = inter.response.edit_message.call_args.kwargs
    assert kwargs["embed"].title.startswith("Étape 3")
    assert isinstance(kwargs["view"], flow.MeasureView)


@pytest.mark.asyncio
async def test_un_message_deja_repondu_est_edite_par_original_response():
    """Après un `defer` ou une interaction déjà répondue, l'édition passe par la réponse d'origine."""
    inter = make_interaction()
    inter.edit_original_response = AsyncMock()
    inter.response.is_done = MagicMock(return_value=True)
    await flow._show_private(inter, content="texte")
    inter.edit_original_response.assert_awaited_once_with(content="texte")
    assert not inter.response.edit_message.await_count


@pytest.mark.asyncio
async def test_un_message_non_modifiable_part_dans_un_nouveau_message_prive():
    """Message supprimé par le membre : un nouveau message privé prend le relais (jamais de silence)."""
    inter = make_interaction()
    inter.response.edit_message = AsyncMock(side_effect=discord.ClientException("message supprimé"))
    await flow._show_private(inter, content="étape suivante")
    inter.response.edit_message.assert_awaited_once()
    inter.response.send_message.assert_awaited_once_with(ephemeral=True, content="étape suivante")


@pytest.mark.asyncio
async def test_show_private_ne_leve_jamais_meme_si_le_repli_echoue():
    """Dernier maillon : si le repli échoue aussi (interaction expirée), l'erreur est journalisée."""
    inter = make_interaction()
    inter.response.edit_message = AsyncMock(side_effect=discord.ClientException("supprimé"))
    inter.response.send_message = AsyncMock(side_effect=discord.ClientException("interaction expirée"))
    await flow._show_private(inter, content="texte")          # ne lève pas
    assert not inter.followup.send.await_count


@pytest.mark.asyncio
async def test_send_ephemeral_ne_leve_jamais_sur_une_interaction_morte():
    """`_send_ephemeral` promet de ne jamais lever : la promesse était sans test."""
    inter = make_interaction()
    inter.response.send_message = AsyncMock(side_effect=discord.ClientException("expirée"))
    await flow._send_ephemeral(inter, "⚠️ message")
    inter.response.is_done = MagicMock(return_value=True)
    inter.followup.send = AsyncMock(side_effect=discord.ClientException("expirée"))
    await flow._send_ephemeral(inter, "⚠️ message")

# ---------------------------------------------------------------------------
# Suite de la passe de couverture (2026-10-13) : branches atteignables en vrai, jamais exercées
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_un_composant_du_parcours_sans_parcours_renvoie_la_reprise():
    """Variante de Claw, thénar et plafond de budget cliqués **hors parcours** (expiré, redémarré).

    Trois composants, un seul filet : le membre reçoit la carte « Session expirée » avec le bouton
    pour repartir, au lieu d'un clic qui ne répond pas. Seuls les menus de prise et le budget étaient
    vérifiés ; ces trois chemins-là n'étaient exercés par aucun test.
    """
    store = SessionStore(ttl_seconds=600)

    variante = make_interaction(store=store)
    await flow.ClawVariantView().children[0].callback(variante)
    thenar = make_interaction(store=store)
    await flow.ThenarView().children[0].callback(thenar)
    budget = make_interaction(store=store)
    await modal_budget("45").on_submit(budget)

    for inter in (variante, thenar, budget):
        kwargs = inter.response.send_message.call_args.kwargs
        assert kwargs["embed"].title == "⏱️ Session expirée"
        assert isinstance(kwargs["view"], flow.StartView)
        assert kwargs["ephemeral"] is True
        inter.response.edit_message.assert_not_awaited()


def test_un_resultat_sans_gamme_choisie_dit_le_classement_morphologique():
    """Mode absent (classement morphologique) : le récapitulatif ne porte pas de budget, il le DIT."""
    session, selection, (ideal, _, _) = _trois_places(None, None, Grip.PALM, 180.0, 90.0)
    assert flow._budget_text(session) == "—"
    assert "Budget" not in flow._recap(session)

    main = flow.results_embeds(session, selection)[0]
    assert "🎚️ **Classement morphologique**" in main.description
    assert "Budget" not in main.description


def test_aucun_repere_ni_conseil_n_est_invente_sur_un_parcours_incomplet():
    """Sans prise ni mesures, les blocs de conseil valent ``None`` — jamais une valeur par défaut."""
    session, _, (ideal, _, _) = _trois_places(None, None, Grip.PALM, 180.0, 90.0)

    vide = flow.FinderSession(user_id=1)
    assert flow._hand_of(vide) is None
    assert flow._dimensions_embed(vide, ideal, "peu importe") is None
    assert flow._buttons_guide_embed(vide) is None

    partielle = flow.FinderSession(user_id=1, grip=Grip.PALM)     # prise connue, mesures absentes
    assert flow._hand_of(partielle) is None
    assert flow._dimensions_embed(partielle, ideal, "peu importe") is None
    assert flow._buttons_guide_embed(partielle) is not None      # le conseil de boutons reste possible


def test_le_titre_de_l_alternative_reste_la_place_quand_la_regle_est_appelee_seule():
    """Appel direct (outil, test) sans référence ni tolérance : titre de la place, jamais « piste »."""
    _, _, (ideal, alternative, _) = _trois_places(BudgetMode.QUALITE_PRIX, None, Grip.PALM, 180.0, 90.0)
    assert flow.alternative_slot_title(alternative, ideal) == "🥈 L'alternative"


def test_une_meme_souris_ne_produit_qu_un_seul_bouton_d_achat():
    """Garde-fou du résultat : deux fois la même souris dans la liste ⇒ un seul bouton (pas de doublon)."""
    _, _, (ideal, _, _) = _trois_places(BudgetMode.QUALITE_PRIX, None, Grip.PALM, 180.0, 90.0)
    view = flow.ResultsView([ideal, ideal], {ideal.mouse.id: "https://www.atk.store/fr-fr/products/x"})
    assert len(view.children) == 1
    assert view.children[0].url.endswith("/x")


@pytest.mark.asyncio
async def test_une_interaction_deja_repondue_recoit_l_etape_par_le_suivi():
    """Après un `defer` (réponse déjà envoyée), la suite part en message de suivi éphémère."""
    inter = make_interaction()
    inter.message = None                       # réponse déjà envoyée : plus de message d'origine
    inter.response.is_done = MagicMock(return_value=True)
    inter.followup.send = AsyncMock()
    await flow._show_private(inter, content="étape suivante")
    inter.followup.send.assert_awaited_once_with(ephemeral=True, content="étape suivante")
    assert not inter.response.edit_message.await_count
