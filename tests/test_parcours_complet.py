"""Parcours complet des trois prises, de bout en bout, avec les vraies callbacks du bot.

**Pourquoi ce fichier existe.** Les étapes étaient couvertes une par une, et la prise Palm parcourue en
entier, mais **aucun test ne traversait les trois prises d'un bout à l'autre** : pour Claw (prise →
variante → thénar → mesures → budget) et pour Fingertip (le thénar est sauté), l'enchaînement réel —
titres d'étape affichés, étape suivante décidée par ce qui vient d'être enregistré, résultat final —
n'était vérifié nulle part. C'est exactement là qu'un défaut se voit : un numéro faux, une étape sautée
ou en trop, un résultat qui ne correspond pas aux réponses.

Chaque scène enchaîne les callbacks réelles (`StartView`, `GripView`, `ClawVariantView`, `ThenarView`,
`MeasureModal`, `BudgetView`) avec les interactions factices de `tests/test_flow.py`, puis **relit ce qui
a réellement été envoyé** (titre de l'étape, texte du résultat).

Ce fichier ne remplace pas une validation sur un serveur Discord réel : voir
`docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md`.
"""
from __future__ import annotations

import pytest

from cogs import finder_flow as flow
from tests.test_flow import make_interaction, modal_budget, modal_with, select_values
from utils.models import BudgetMode, ClawVariant, Grip, Thenar
from utils.session import LOOKUP_OK, SessionStore

# Titres d'étape attendus, écrits à la main : c'est la promesse faite au membre. L'étape 1 n'annonce
# pas de total (« Étape 1 — Votre prise ») parce que le nombre d'étapes dépend de la prise choisie —
# c'est justement au clic suivant qu'on sait s'il y en a 3, 4 ou 5.
TITRES_ATTENDUS = {
    Grip.PALM: ["Étape 1 — Votre prise", "Étape 2/4 — Votre éminence thénar",
                "Étape 3/4 — Vos mesures", "Étape 4/4 — Budget et gamme"],
    Grip.CLAW: ["Étape 1 — Votre prise", "Étape 2/5 — Votre variante de Claw",
                "Étape 3/5 — Votre éminence thénar", "Étape 4/5 — Vos mesures",
                "Étape 5/5 — Budget et gamme"],
    Grip.FINGERTIP: ["Étape 1 — Votre prise", "Étape 2/3 — Vos mesures",
                     "Étape 3/3 — Budget et gamme"],
}
CLIC_THENAR = Thenar.MOYENNE.value
CLIC_VARIANTE = ClawVariant.RELACHEE.value

# Les trois places attendues pour le profil de référence (Palm, 180 × 90 mm, thénar moyenne, mode
# « Qualité-prix »), **relevées sur le moteur le 2026-10-14** et écrites ici en clair : le test ne
# redemande jamais ses attentes au code qu'il vérifie. Un test qui les recalculait avec
# `flow.result_slots` validait n'importe quel ordre — c'est exactement ce qui a laissé passer, le
# 2026-10-14, une mutation échangeant les deux dernières places (et qui a fait publier au banc d'essai
# 10 678 problèmes fantômes, tous mesurés sur le bytecode muté : voir `tools/check_bytecode.py`).
PLACES_ATTENDUES = [
    ("ATK Phantom Ultimate", 88, "91,95 €"),
    ("ATK Z1 V2 Ultimate", 75, "59,95 €"),
    ("ATK A9 Mini", 75, "59,95 €"),
]


def _blocs_envoyes(inter) -> list:
    """Les blocs réellement remis à Discord (édition d'étape, envoi du panneau, ou repli privé)."""
    for objet in (inter.response, inter.followup):
        for nom in ("edit_message", "send_message", "edit_original_response", "send"):
            methode = getattr(objet, nom, None)
            if methode is None or not getattr(methode, "await_count", 0):
                continue
            kwargs = methode.call_args.kwargs
            blocs = list(kwargs.get("embeds") or [])
            if kwargs.get("embed") is not None:
                blocs.append(kwargs["embed"])
            if blocs:
                return blocs
    return []


def _titre(inter) -> str:
    blocs = _blocs_envoyes(inter)
    return (blocs[0].title or "") if blocs else ""


def _texte(inter) -> str:
    return " ".join(str(bloc.to_dict()) for bloc in _blocs_envoyes(inter))


async def _clic(store: SessionStore, fabrique, valeur: str):
    """Un clic sur le menu d'une vue, exactement comme le ferait Discord."""
    inter = make_interaction(user_id=7, store=store)
    vue = fabrique()
    select_values(vue.children[0], valeur)
    await vue.children[0].callback(inter)
    return inter


async def _jusqu_au_budget(store: SessionStore, grip: Grip, *, mesures=("180", "90")):
    """Le parcours réel jusqu'à l'étape du budget (sans le clic final) ; rend les titres vus."""
    titres = []
    inter = make_interaction(user_id=7, store=store)
    await flow.StartView().start.callback(inter)
    titres.append(_titre(inter))

    titres.append(_titre(await _clic(store, flow.GripView, grip.value)))
    if grip is Grip.CLAW:
        titres.append(_titre(await _clic(store, flow.ClawVariantView, CLIC_VARIANTE)))
    if grip is not Grip.FINGERTIP:
        titres.append(_titre(await _clic(store, flow.ThenarView, CLIC_THENAR)))

    inter = make_interaction(user_id=7, store=store)
    await modal_with(flow.MeasureModal(), *mesures).on_submit(inter)
    titres.append(_titre(inter))
    return titres


async def _parcours_complet(store: SessionStore, grip: Grip, *, mode: BudgetMode = BudgetMode.QUALITE_PRIX):
    """Le parcours entier ; rend (titres vus, interaction du résultat)."""
    titres = await _jusqu_au_budget(store, grip)
    resultat = await _clic(store, flow.BudgetView, mode.value)
    titres.append(_titre(resultat))
    return titres, resultat


@pytest.mark.asyncio
async def test_les_trois_prises_enchainent_les_bonnes_etapes_dans_l_ordre():
    """Palm 4 étapes, Claw 5 (la variante AVANT le thénar), Fingertip 3 (jamais de thénar).

    Les titres lus sont ceux réellement envoyés à Discord, pas ceux recalculés par le test.
    """
    for grip, attendus in TITRES_ATTENDUS.items():
        titres, _ = await _parcours_complet(SessionStore(ttl_seconds=600), grip)
        etapes, resultat = titres[:-1], titres[-1]
        assert etapes == attendus, f"{grip.label} : {etapes}"
        assert "Votre recommandation" in resultat, resultat
        if grip is Grip.FINGERTIP:
            assert all("thénar" not in titre.lower() for titre in titres), titres


@pytest.mark.asyncio
async def test_le_resultat_du_parcours_est_celui_du_moteur_pour_les_reponses_donnees():
    """Le message final montre les trois places du moteur, **dans leur ordre**, avec leurs vrais chiffres.

    Contrôle dans les deux sens : les trois places écrites en clair dans ``PLACES_ATTENDUES`` sont bien
    celles du moteur (comparaison d'ensembles, jamais recalculée pour l'ordre), **et** elles
    s'affichent dans cet ordre-là, chacune avec son pourcentage et son prix de catalogue. Une mutation
    qui échange deux places fait donc échouer ce test — c'est précisément ce qui manquait avant.
    """
    store = SessionStore(ttl_seconds=600)
    _, resultat = await _parcours_complet(store, Grip.PALM)
    session = store.current(7)[0]
    assert session is not None and session.finished is True

    selection = flow.compute_selection(session)
    du_moteur = [score for score in flow.result_slots(selection) if score is not None]
    assert len(du_moteur) == 3, "profil de référence : trois places attendues"
    assert {score.mouse.label for score in du_moteur} == {etiquette for etiquette, _, _ in PLACES_ATTENDUES}, \
        "le moteur ne propose plus les mêmes souris pour ce profil"

    texte = _texte(resultat)
    positions = []
    for rang, (etiquette, pourcentage, prix) in enumerate(PLACES_ATTENDUES, start=1):
        assert f"**{etiquette}**" in texte, f"place {rang} absente du message : {etiquette}"
        assert f"**{pourcentage} %**" in texte, f"pourcentage de la place {rang} ({pourcentage} %) absent"
        assert prix in texte, f"prix de la place {rang} ({prix}) absent"
        positions.append(texte.find(etiquette))
    assert positions == sorted(positions), "les places ne s'affichent pas dans l'ordre du moteur"
    # Aucune souris écartée ni « en attente » ne s'affiche.
    assert "À vérifier" not in texte


@pytest.mark.asyncio
async def test_deux_parcours_identiques_donnent_exactement_le_meme_resultat():
    """Le parcours est déterministe : mêmes réponses, même message — au caractère près."""
    titres_un, inter_un = await _parcours_complet(SessionStore(ttl_seconds=600), Grip.CLAW)
    titres_deux, inter_deux = await _parcours_complet(SessionStore(ttl_seconds=600), Grip.CLAW)
    assert titres_un == titres_deux
    blocs_un = [bloc.to_dict() for bloc in _blocs_envoyes(inter_un)]
    blocs_deux = [bloc.to_dict() for bloc in _blocs_envoyes(inter_deux)]
    assert blocs_un, "aucun bloc envoyé : le contrôle ne prouverait rien"
    assert blocs_un == blocs_deux


@pytest.mark.asyncio
async def test_le_budget_personnalise_saisi_au_clavier_termine_le_parcours():
    """Le chemin « Budget personnalisé » (formulaire) va jusqu'au résultat, comme le menu.

    C'est le seul chemin du parcours qui passe par une **saisie clavier** : s'il s'arrêtait à l'étape du
    budget, le membre n'aurait aucun résultat — et un test qui ne clique que les menus ne le verrait pas.
    """
    store = SessionStore(ttl_seconds=600)
    await _jusqu_au_budget(store, Grip.FINGERTIP)
    session = store.current(7)[0]
    assert session is not None and flow.step_kind(session) == "budget"
    assert store.current(7)[1] == LOOKUP_OK

    inter = make_interaction(user_id=7, store=store)
    await modal_budget("60").on_submit(inter)
    assert "Votre recommandation" in _titre(inter), _titre(inter)
    session = store.current(7)[0]
    assert session is not None
    assert session.budget_mode is BudgetMode.CUSTOM and session.max_budget_eur == 60.0
    assert session.finished is True
