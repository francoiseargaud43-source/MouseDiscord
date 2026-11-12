"""Versions d'une même souris (2026-11-12) : `data/versions.json` et le bloc « 🧩 Plusieurs versions ».

Le propriétaire a demandé que le membre voie, pour la souris conseillée, les autres versions vendues
sous le même nom (Ultimate, Extreme…), ce qui change et si cela vaut le supplément. Ces tests gardent
les règles des données (rien d'inventé, prix en euros, lien affilié, version épuisée cachée) et le
lien avec le catalogue (la version « du résultat » est bien celle que le bouton d'achat ouvre).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import discord

from config import COMMERCIAL_LINKS_PATH, MOUSE_DB_PATH, VERSIONS_PATH
from utils.catalog import load_catalog, load_commercial_links
from utils.versions import champs, conseil, load_versions

LIEN = "https://www.atk.store/en-fr/products/x?country=FR&ref=aze&variant="


def _ecrire(tmp_path: Path, contenu: dict) -> Path:
    chemin = tmp_path / "versions.json"
    chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")
    return chemin


def test_une_version_sans_affiliation_epuisee_ou_sans_prix_n_est_pas_proposee(tmp_path):
    chemin = _ecrire(tmp_path, {"souris": {"versions": [
        {"nom": "Base", "prix_eur": 40.0, "dispo": True, "lien": LIEN + "1"},
        {"nom": "Plus", "prix_eur": 50.0, "dispo": True, "lien": LIEN + "2"},
        {"nom": "Sans ref", "prix_eur": 60.0, "dispo": True,
         "lien": "https://www.atk.store/en-fr/products/x?country=FR&variant=3"},
        {"nom": "Épuisée", "prix_eur": 70.0, "dispo": False, "lien": LIEN + "4"},
        {"nom": "Dispo inconnue", "prix_eur": 70.0, "lien": LIEN + "5"},
        {"nom": "Sans prix", "dispo": True, "lien": LIEN + "6"},
    ]}})
    gamme = load_versions(chemin)["souris"]
    assert [v.nom for v in gamme.versions] == ["Base", "Plus"]


def test_une_seule_version_en_stock_ne_fait_pas_de_bloc(tmp_path):
    chemin = _ecrire(tmp_path, {"souris": {"versions": [
        {"nom": "Base", "prix_eur": 40.0, "dispo": True, "lien": LIEN + "1"},
        {"nom": "Plus", "prix_eur": 50.0, "dispo": False, "lien": LIEN + "2"},
    ]}})
    assert load_versions(chemin) == {}


def test_un_fichier_absent_ou_casse_ne_prive_pas_du_resultat(tmp_path):
    assert load_versions(tmp_path / "absent.json") == {}
    casse = tmp_path / "casse.json"
    casse.write_text("{", encoding="utf-8")
    assert load_versions(casse) == {}


def test_ce_qui_change_est_dit_par_rapport_a_la_moins_chere(tmp_path):
    chemin = _ecrire(tmp_path, {"souris": {"versions": [
        {"nom": "Air", "prix_eur": 52.71, "dispo": True, "lien": LIEN + "2", "capteur": "PAW3950 Ultra",
         "hz": 8000, "poids_g": 47, "switchs": "ATK Swiftlight Optical"},
        {"nom": "Ultra Max", "prix_eur": 39.53, "dispo": True, "lien": LIEN + "1", "capteur": "PAW3950 Ultra",
         "hz": 8000, "poids_g": 55, "switchs": "ATK Lightblade Mechanical", "resultat": True},
    ]}})
    gamme = load_versions(chemin)["souris"]
    texte = "\n".join(champs(gamme))
    assert texte.index("Ultra Max") < texte.index("Air")              # de la moins chère à la plus chère
    assert "39,53 €" in texte and "52,71 € (+13,18 €)" in texte
    assert "8 g plus légère" in texte and "clics optiques" in texte
    assert "← celle du résultat" in texte.split("\n")[0]
    assert "La moins chère (Ultra Max)" in conseil(gamme)


def test_le_vrai_fichier_suit_le_catalogue_et_les_liens_d_achat():
    """Chaque gamme parle d'une souris du catalogue ; sa version « du résultat » est celle que le bouton
    d'achat ouvre, au prix publié par le catalogue. Sinon le membre lirait deux prix pour la même souris."""
    brut = json.loads(Path(VERSIONS_PATH).read_text(encoding="utf-8"))
    catalogue = {m.id: m for m in load_catalog(MOUSE_DB_PATH)}
    liens = load_commercial_links(COMMERCIAL_LINKS_PATH)
    gammes = load_versions(VERSIONS_PATH)
    assert gammes, "data/versions.json ne propose aucune version"
    for ident, entree in brut.items():
        if ident.startswith("_"):
            continue
        assert ident in catalogue, ident
        resultat = [v for v in entree["versions"] if v.get("resultat")]
        assert len(resultat) == 1, ident
        variante = re.search(r"variant=(\d+)", resultat[0]["lien"]).group(1)
        assert f"variant={variante}" in liens[ident], ident
        assert resultat[0]["prix_eur"] == catalogue[ident].price_eur, ident
    for gamme in gammes.values():
        for valeur in champs(gamme):
            assert len(valeur) <= 1024


def test_le_bloc_tient_dans_le_message_et_suit_la_recommandation():
    from cogs import finder_flow as flow
    from utils.models import BudgetMode, Grip, Thenar
    from utils.session import FinderSession

    session = FinderSession(user_id=1)
    session.grip, session.thenar = Grip.PALM, Thenar.MOYENNE
    session.hand_length_mm, session.hand_width_mm = 180.0, 90.0
    session.budget_mode = BudgetMode.QUALITE_PRIX
    selection = flow.compute_selection(session)
    embeds = flow.results_embeds(session, selection, load_versions(VERSIONS_PATH))
    assert embeds[1].title == "🧩 Plusieurs versions de la même souris"
    assert sum(len(e) for e in embeds) <= 6000 and len(embeds) <= 10
    # Sans données, rien ne change au message d'avant.
    assert [e.title for e in flow.results_embeds(session, selection)] == \
        [e.title for e in embeds if e.title != "🧩 Plusieurs versions de la même souris"]
    assert all(isinstance(e, discord.Embed) for e in embeds)
