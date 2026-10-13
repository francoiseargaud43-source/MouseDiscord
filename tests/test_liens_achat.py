"""Les liens d'achat ouvrent-ils LE modèle annoncé, à SON prix — et le contrôle est-il refaisable ?

Demande du propriétaire (2026-10-13) : « vérifie si les liens que je t'ai envoyés correspondent bien au
modèle ». La vérification avait été faite à la main, page par page, et consignée dans le §8 de
`docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`. Elle a trouvé trois défauts réels ce jour-là :

- l'**A9 Plus** publiait 45,00 € (cahier des charges) alors que le bouton ouvre une variante vendue
  **27,95 €** ;
- l'**A9 NB** était à 73,95 € le matin, 72,95 € l'après-midi ;
- la note de l'**A9 Air** nommait un coloris (« Shadow White », celui d'un revendeur) que le bouton
  n'ouvre pas, et celle de la **F1 V2** affirmait que le bouton ouvre « Ultra Max 2.0 / Black » alors
  qu'aucune variante n'était figée — la page ouvre une souris, mais elle en vend trois.

Deux choses sont verrouillées ici : le **tableau §8.1** (lu par les deux bouts, contre
`data/commercial_links.json` et `data/mouse_db.json`) et **l'outil** `tools/check_links.py`, essayé hors
réseau avec une fausse boutique — parce qu'un contrôle qui n'est pas rejouable redevient une opinion.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import check_links  # noqa: E402  (après l'insertion du chemin)
from check_links import (  # noqa: E402
    INACCESSIBLE,
    LIEN_INEXPLOITABLE,
    PRIX_DIFFERENT,
    SANS_CATALOGUE,
    VARIANTE_ABSENTE,
    EntreeInvalide,
    analyser,
    code_de_sortie,
    extraire,
    lire_fiche,
    main,
)

DOC = ROOT / "docs" / "VERIFICATION_LIENS_SPONSORISES_2026-10-11.md"
LIENS = json.loads((ROOT / "data" / "commercial_links.json").read_text(encoding="utf-8"))
CATALOGUE = {m["id"]: m for m in json.loads((ROOT / "data" / "mouse_db.json").read_text(encoding="utf-8"))}


def _lignes_du_tableau() -> dict[str, list[str]]:
    """Les lignes du tableau §8.1 : {identifiant de souris: cellules} — la source de la relecture."""
    lignes: dict[str, list[str]] = {}
    for ligne in DOC.read_text(encoding="utf-8").splitlines():
        if not ligne.startswith("| `"):
            continue
        cellules = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cellules) != 7:
            continue
        identifiant = cellules[0].strip("`")
        if identifiant in CATALOGUE:  # le §8.1 seul : pas les tableaux des passes précédentes
            lignes[identifiant] = cellules
    return lignes


def _montant(cellule: str) -> tuple[float, str]:
    """« 59,95 € » → (59.95, "EUR") · « 69,99 USD » → (69.99, "USD")."""
    trouvé = re.match(r"^([\d\s]+,\d\d)\s*(€|USD)$", cellule)
    assert trouvé, f"montant illisible dans le tableau §8.1 : {cellule!r}"
    nombre = float(trouvé.group(1).replace(" ", "").replace(",", "."))
    return nombre, "EUR" if trouvé.group(2) == "€" else "USD"


def test_le_tableau_de_relecture_couvre_les_36_liens_et_rien_d_autre():
    """Un lien retiré ou ajouté sans toucher au tableau (ou l'inverse) casserait ce test."""
    du_depot = sorted(k for k in LIENS if not k.startswith("_"))
    du_tableau = sorted(_lignes_du_tableau())
    assert du_tableau == du_depot
    assert len(du_tableau) == len(CATALOGUE) == 36


def test_le_tableau_nomme_le_handle_et_la_variante_que_chaque_lien_ouvre():
    """« Le lien correspond-il au modèle ? » : le handle du lien est celui du tableau, et la variante
    figée (ou son absence) aussi — c'est cette colonne qui a rattrapé la F1 V2."""
    for identifiant, cellules in _lignes_du_tableau().items():
        handle, variante = cellules[1].strip("`"), cellules[2].strip("`")
        lien = LIENS[identifiant]
        assert f"/products/{handle}" in lien, f"{identifiant} : le lien n'ouvre pas la fiche « {handle} »"
        figée = re.search(r"variant=(\d+)", lien)
        if variante == "—":
            assert figée is None, f"{identifiant} : le tableau dit « pas de variante », le lien en fige une"
        else:
            assert figée and figée.group(1) == variante, \
                f"{identifiant} : le lien ne fige pas la variante {variante} annoncée"


def test_le_prix_publie_est_celui_de_la_boutique_et_la_monnaie_est_dite():
    """Le prix du catalogue est celui de la fiche ouverte, et une fiche en dollars est dite « USD ».

    Les deux lignes sans prix en euros (Scyrox, boutique en dollars) ne peuvent pas être comparées :
    elles doivent au moins le dire, pour qu'aucune conversion ne s'invite dans le catalogue.
    """
    for identifiant, cellules in _lignes_du_tableau().items():
        prix_boutique, devise = _montant(cellules[4])
        prix_publie, devise_publiee = _montant(cellules[5])
        assert devise_publiee == "EUR", f"{identifiant} : le catalogue ne publie qu'en euros"
        assert CATALOGUE[identifiant]["price_eur"] == pytest.approx(prix_publie)
        if devise == "EUR":
            assert prix_boutique == pytest.approx(prix_publie), \
                f"{identifiant} : la boutique affiche {prix_boutique} €, le catalogue publie {prix_publie} €"
        else:
            note = CATALOGUE[identifiant].get("price_note") or ""
            assert "dollar" in note.lower(), \
                f"{identifiant} : prix hors euros publié sans que la note dise pourquoi"


def test_une_note_qui_annonce_la_variante_du_bouton_exige_que_le_lien_la_fige():
    """Défaut réel du 2026-10-13 : la note de la F1 V2 disait « celle que le bouton d'achat ouvre » alors
    que le lien ne figeait aucune variante — la fiche vend trois éditions (41,95 / 54,95 / 77,95 €).

    Toute note qui affirme qu'un bouton ouvre une variante précise doit être vérifiable : le lien fige
    cette variante. Si une note parle du bouton sans que le lien fige quoi que ce soit, c'est un mensonge
    silencieux — exactement ce que cette chasse aux bugs cherche à supprimer.
    """
    marqueurs = ("bouton d'achat", "cible du bouton", "figée par le bouton", "figé par le bouton",
                 "que le bouton ouvre")
    fautives = []
    for identifiant, souris in CATALOGUE.items():
        note = souris.get("price_note") or ""
        if any(m in note for m in marqueurs) and "variant=" not in LIENS.get(identifiant, ""):
            fautives.append(identifiant)
    assert fautives == [], f"notes qui parlent du bouton sans lien figé : {fautives}"


# ---------------------------------------------------------------------------
# L'outil de contrôle, essayé hors réseau (fausse boutique injectée)
# ---------------------------------------------------------------------------
def _boutique(variantes: list[dict], titre: str = "ATK Exemple"):
    """Une réponse de boutique au format `products/<handle>.json`."""
    def telecharger(url: str, delai: float = 15.0) -> dict:
        return {"product": {"title": titre, "variants": variantes}}
    return telecharger


def _variante(identifiant: int, titre: str, prix: float, devise: str = "EUR") -> dict:
    return {"id": identifiant, "title": titre, "price": f"{prix:.2f}", "price_currency": devise}


def test_le_lien_fige_est_le_seul_lu():
    """`extraire` sépare l'hôte, le chemin, le handle et la variante — et refuse un lien bricolé."""
    hote, prefixe, handle, variante = extraire(
        "https://www.atk.store/en-fr/products/atk-dragonfly-a9-series-lightweight-wireless-mouse"
        "?country=FR&ref=aze&variant=46320046047450")
    assert (hote, prefixe, handle, variante) == (
        "www.atk.store", "/en-fr", "atk-dragonfly-a9-series-lightweight-wireless-mouse", "46320046047450")
    assert extraire("https://eu.pulsar.gg/products/x2-v3-mini-gaming-mouse")[3] is None
    for bricole in ("pas-une-url", "https://www.atk.store/collections/mice", "https://www.atk.store/products/"):
        with pytest.raises(EntreeInvalide):
            extraire(bricole)


def test_une_fiche_coherente_est_dite_coherente():
    liens = {"atk_exemple": "https://www.atk.store/products/exemple?variant=1"}
    catalogue = [type("S", (), {"id": "atk_exemple", "price_eur": 41.95})()]
    verdicts = analyser(liens, catalogue, telecharger=_boutique([_variante(1, "Ultra Max 2.0 / Black", 41.95)]))
    assert verdicts[0].verdict == check_links.OK
    assert verdicts[0].fiche.libelle == "ATK Exemple — Ultra Max 2.0 / Black"
    assert code_de_sortie(verdicts) == 0


def test_une_variante_figee_absente_de_la_fiche_est_signalee():
    """Le produit existe, la variante a disparu (coloris retiré) : l'outil le dit, il ne devine pas."""
    liens = {"atk_exemple": "https://www.atk.store/products/exemple?variant=999"}
    catalogue = [type("S", (), {"id": "atk_exemple", "price_eur": 41.95})()]
    verdicts = analyser(liens, catalogue, telecharger=_boutique([_variante(1, "Ultra Max 2.0 / Black", 41.95)]))
    assert verdicts[0].verdict.startswith(VARIANTE_ABSENTE)
    assert verdicts[0].echec and code_de_sortie(verdicts) == 1


def test_un_prix_devenu_different_est_signale():
    """La boutique vend 45,95 € là où le catalogue publie 41,95 € : écart, jamais « presque bon »."""
    liens = {"atk_exemple": "https://www.atk.store/products/exemple?variant=1"}
    catalogue = [type("S", (), {"id": "atk_exemple", "price_eur": 41.95})()]
    verdicts = analyser(liens, catalogue, telecharger=_boutique([_variante(1, "Ultra Max 2.0 / Black", 45.95)]))
    assert verdicts[0].verdict == PRIX_DIFFERENT
    assert code_de_sortie(verdicts) == 1


def test_une_fiche_en_dollars_n_est_pas_convertie():
    """Scyrox vend en dollars : l'outil le constate et ne conclut rien — aucune conversion n'est faite."""
    liens = {"scyrox_exemple": "https://scyrox.com/products/scyrox-v8"}
    catalogue = [type("S", (), {"id": "scyrox_exemple", "price_eur": 74.90})()]
    verdicts = analyser(liens, catalogue, telecharger=_boutique([_variante(7, "Black", 69.99, "USD")]))
    assert verdicts[0].verdict == check_links.HORS_COMPARAISON
    assert not verdicts[0].echec and code_de_sortie(verdicts) == 0


def test_un_lien_qui_ne_pointe_vers_aucune_souris_du_catalogue_est_signale():
    liens = {"inconnue": "https://www.atk.store/products/exemple"}
    verdicts = analyser(liens, [], telecharger=_boutique([_variante(1, "Noir", 10.0)]))
    assert verdicts[0].verdict == SANS_CATALOGUE
    assert code_de_sortie(verdicts) == 1


def test_un_lien_bricole_est_signale_sans_reseau():
    """Aucune requête n'est nécessaire pour voir qu'un lien n'est pas un lien de produit."""
    liens = {"atk_exemple": "https://www.atk.store/collections/mice"}
    catalogue = [type("S", (), {"id": "atk_exemple", "price_eur": 41.95})()]
    verdicts = analyser(liens, catalogue, telecharger=_boutique([_variante(1, "Noir", 41.95)]))
    assert verdicts[0].verdict.startswith(LIEN_INEXPLOITABLE)


def test_sans_reseau_le_controle_dit_qu_il_n_a_pas_eu_lieu():
    """Un réseau qui bloque les boutiques (bac à sable, pare-feu) n'est PAS un catalogue faux : code 2."""
    def bloque(url: str, delai: float = 15.0) -> dict:
        raise OSError("réseau injoignable")

    liens = {"atk_exemple": "https://www.atk.store/products/exemple", "autre": "https://scyrox.com/products/v8"}
    catalogue = [type("S", (), {"id": identifiant, "price_eur": 41.95})() for identifiant in liens]
    verdicts = analyser(liens, catalogue, telecharger=bloque)
    assert all(v.verdict.startswith(INACCESSIBLE) for v in verdicts)
    assert code_de_sortie(verdicts) == 2
    assert code_de_sortie([]) == 2


def test_une_fiche_sans_variante_ne_fait_pas_planter_le_controle():
    """Fiche dépubliée ou format changé : une phrase, pas un `KeyError` au milieu du rapport."""
    with pytest.raises(EntreeInvalide):
        lire_fiche({"product": {"title": "Vide", "variants": []}}, None)
    with pytest.raises(EntreeInvalide):
        lire_fiche({}, None)


def test_un_identifiant_de_souris_inconnu_est_refuse_avec_un_message(capsys):
    """`--souris atk_a9_pluss` (faute de frappe) : refusé en code 2 plutôt qu'un rapport vide, rassurant."""
    with pytest.raises(SystemExit) as sortie:
        main(["--souris", "atk_a9_pluss"])
    assert sortie.value.code == 2
    assert "souris inconnue" in capsys.readouterr().err


def test_le_rapport_complet_s_ecrit_sur_la_sortie_standard(capsys):
    """Le rapport nomme chaque souris, la variante ouverte, le prix de la boutique et celui publié."""
    liens = {"atk_exemple": "https://www.atk.store/products/exemple?variant=1"}
    catalogue = [type("S", (), {"id": "atk_exemple", "price_eur": 41.95})()]
    verdicts = analyser(liens, catalogue, telecharger=_boutique([_variante(1, "Ultra Max 2.0 / Black", 41.95)]))
    check_links.rapporter(verdicts)
    sortie = capsys.readouterr().out
    assert "41,95€" in sortie.replace(" ", "")
    assert "1 lien(s) contrôlé(s) · 0 écart(s)." in sortie
