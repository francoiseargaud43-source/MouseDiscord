"""Les liens d'achat ouvrent-ils LE modèle annoncé, à SON prix — et le contrôle est-il refaisable ?

Demande du propriétaire (2026-10-13) : « vérifie si les liens que je t'ai envoyés correspondent bien au
modèle ». La vérification avait été faite à la main, page par page, et consignée dans le §8 de
`docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`. Elle a trouvé trois défauts réels ce jour-là :

- l'**A9 Plus** publiait 45,00 € (cahier des charges) alors que le bouton ouvre une variante vendue
  **27,95 €** ;
- l'**A9 NB** était à 73,95 € le matin, 72,95 € l'après-midi ;
- la note de l'**A9 Air** nommait un coloris (« Shadow White », celui d'un revendeur) que le bouton
  n'ouvre pas, et celle de la **F1 V2** affirmait que le bouton ouvre « Ultra Max 2.0 / Black » alors
  qu'aucune variante n'était figée — la page ouvre une souris, mais elle en vend trois (la correction a
  **figé** cette variante ; le partage du §7.2/§7.3 est resté en arrière jusqu'au 2026-10-14, voir le
  test du partage plus bas).

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
LISTE = ROOT / "docs" / "LISTE_LIENS_SPONSORISES_2026-10-11.md"


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


def _bloc(numero: str) -> str:
    """Le texte d'une sous-section « ### 7.N … », jusqu'à la sous-section suivante."""
    texte = DOC.read_text(encoding="utf-8")
    début = texte.index(f"### {numero} ")
    suite = texte.find("\n### ", début + 1)
    return texte[début:suite if suite != -1 else len(texte)]


def _identifiants_du_bloc(numero: str) -> set[str]:
    """Les identifiants cités en tête de ligne d'un tableau « | `id` | … » ou « | `id` — Nom | … »."""
    return set(re.findall(r"^\| `([a-z0-9_]+)`", _bloc(numero), re.M))


MOTS_NOMBRES = {10: "dix", 11: "onze", 12: "douze", 13: "treize", 14: "quatorze", 15: "quinze", 16: "seize"}


def test_le_partage_des_liens_qui_figent_une_variante_suit_les_donnees():
    """§7.2 liste les liens ATK qui figent une variante, §7.3 ceux qui n'en figent pas — et rien d'autre.

    Défaut trouvé le 2026-10-14 : le commit `a2bdb5c` (47e passe) a **figé** la variante du F1 V2 sans
    mettre à jour ce partage. La souris est donc restée annoncée « sans variante figée » alors que son
    lien en figeait une (et le titre du §7.2 disait « onze » au lieu de douze). Aucun contrôle ne reliait
    ces tableaux aux liens, donc personne ne pouvait le voir ; celui-ci le fait.
    """
    atk = {k: v for k, v in LIENS.items() if not k.startswith("_") and "atk.store" in v}
    figées = {k for k, v in atk.items() if "variant=" in v}
    libres = set(atk) - figées
    assert len(atk) == 24 and len(figées) == len(libres) == 12
    assert _identifiants_du_bloc("7.2") == figées, "le §7.2 ne liste pas exactement les liens qui figent une variante"
    assert _identifiants_du_bloc("7.3") == libres, "le §7.3 ne liste pas exactement les liens sans variante figée"


@pytest.mark.parametrize("numero", ["7.2", "7.3"])
def test_le_titre_de_chaque_partage_annonce_le_nombre_de_lignes(numero):
    """Un titre qui annonce « onze » au-dessus de douze lignes (ou l'inverse) ferait échouer ce test."""
    bloc = _bloc(numero)
    lignes = len(_identifiants_du_bloc(numero))
    titre = bloc.splitlines()[0]
    annoncé = MOTS_NOMBRES[lignes]
    assert str(lignes) in titre or annoncé in titre, f"titre : {titre!r} pour {lignes} lignes"


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


NOMS_VERIFIES_SUR_LA_BOUTIQUE = {
    # Relevé du 2026-10-13 (boutique ATK, pays France) : ces quatre noms sont ceux que la page qu'ouvre le
    # bouton affiche. Les noms du cahier des charges (« A9 Plus 2.0 », « Z1 V2 Ultra », « F1 V3 Ultimate »
    # — sans « + » —, « X1 V2 Ultra Max » — sans « 2.0 ») ne se retrouvaient PAS sur la page : le membre
    # ne pouvait pas y reconnaître la souris annoncée par le bot.
    "atk_a9_plus": "A9 Plus",
    "atk_z1_ultra": "Z1 V2 Ultimate",
    "atk_f1_ultimate": "F1 V3 Ultimate+",
    "atk_x1_ultra_max": "X1 V2 Ultra Max 2.0",
}


def test_les_quatre_noms_de_modeles_corriges_ne_reviennent_pas_en_arriere():
    """Le nom publié est celui de la boutique : ces quatre noms sont datés, et datés du 2026-10-13."""
    for identifiant, attendu in NOMS_VERIFIES_SUR_LA_BOUTIQUE.items():
        assert CATALOGUE[identifiant]["model"] == attendu, (
            f"{identifiant} : « {CATALOGUE[identifiant]['model']} » publié au lieu de « {attendu} » "
            "(nom relevé sur la page que le bouton ouvre)")


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


def test_le_resume_ne_cache_pas_les_fiches_injoignables(capsys):
    """« 0 écart » alors que rien n'a pu être ouvert serait un faux rassurant : les deux comptes sont dits."""
    def bloque(url: str, delai: float = 15.0) -> dict:
        raise OSError("réseau injoignable")

    liens = {"atk_exemple": "https://www.atk.store/products/exemple"}
    catalogue = [type("S", (), {"id": "atk_exemple", "price_eur": 41.95})()]
    verdicts = analyser(liens, catalogue, telecharger=bloque)
    check_links.rapporter(verdicts)
    assert code_de_sortie(verdicts) == 2
    sortie = capsys.readouterr().out
    assert "1 lien(s) contrôlé(s) · 0 écart(s) · 1 fiche(s) inaccessible(s)." in sortie
    assert "le contrôle n'a pas eu lieu" in sortie


def _pages_de_la_liste_de_travail() -> dict[str, str]:
    """Colonne « page produit » de la liste de travail : {identifiant de souris: handle de la page}."""
    pages: dict[str, str] = {}
    for ligne in LISTE.read_text(encoding="utf-8").splitlines():
        trouve = re.match(r"^\| \d+ \| `([a-z0-9_]+)` \| [^|]* \| (https://\S+) \|", ligne)
        if trouve:
            pages[trouve.group(1)] = trouve.group(2).split("?")[0].rsplit("/products/", 1)[-1]
    return pages


def test_la_liste_de_travail_envoie_sur_la_page_que_le_bouton_ouvre():
    """Défaut trouvé le 2026-10-13 (49e passe) : la liste qui sert à **fabriquer** les liens donnait
    encore l'ancienne page pour deux souris — le U2 V2 Ultimate sur la page « série U2 », le U2 V2 Mini
    sur la page « U2 Mini » — alors que les liens installés ouvrent la page **U2 V2** depuis la
    correction du §6.6. Les deux documents d'audit étaient à jour, la liste de travail non."""
    pages = _pages_de_la_liste_de_travail()
    assert len(pages) == 26          # les 26 souris du relevé du 2026-10-11 ; les Pulsar sont ailleurs
    for identifiant, handle in sorted(pages.items()):
        assert identifiant in LIENS, f"{identifiant} : la liste nomme une souris sans lien installé"
        assert f"/products/{handle}" in LIENS[identifiant], (
            f"{identifiant} : la liste envoie sur « {handle} », le bouton ouvre "
            f"{LIENS[identifiant].split('?')[0]}")
