"""Intégrité des fichiers de données livrés (catalogue v2, liens, images)."""
import json
import math
import re
from pathlib import Path

import pytest

from config import COMMERCIAL_LINKS_PATH, IMAGES_CONFIG_PATH, MOUSE_DB_PATH

ROOT = Path(__file__).resolve().parents[1]
from utils.assets import IMAGE_KEYS, load_image_urls
from utils.catalog import CatalogError, load_catalog, load_commercial_links, parse_mouse
from utils.matcher import evaluate_mouse
from utils.models import Grip, HandMeasure

OWNER_IDS = ["scyrox_v8", "scyrox_v6", "atk_f1_ultimate", "atk_x1_ultra_max", "atk_z1_ultra", "atk_a9_plus"]
NEW_ATK_IDS = [
    "atk_phantom_ultimate", "atk_ghost_ultimate", "atk_ghost_extreme", "atk_y9_ultimate", "atk_fierce_x",
    "atk_u2_v2_ultimate", "atk_u2_v2_mini", "atk_zero", "atk_duckbill", "atk_a9_ultimate", "atk_a9_air", "atk_a9_mini",
]
# Ajouts du 2026-10-11 : souris ATK/VXE actuellement vendues sur atk.store, absentes du catalogue
# (recherche « produits encore vendus » ; sources ATK Store + EloShapes, voir docs/audit/CATALOGUE_ATK.md §5).
STORE_2026_10_11_IDS = [
    "vxe_v3", "vxe_r1", "vxe_mad_r", "vxe_x3", "atk_u2_mini", "atk_a9_nb", "atk_f1_v2", "atk_u2",
]
# Ajouts du 2026-10-12 : souris Pulsar réellement en vente sur la boutique européenne Pulsar,
# relevées une par une sur la fiche officielle du modèle (dimensions, poids, capteur, fréquence,
# switchs, forme, recommandations de prise) — voir docs/audit/PULSAR_CATALOGUE_2026-10-12.md.
PULSAR_IDS = [
    "pulsar_x2_v3_mini", "pulsar_x2h_v3_mini", "pulsar_x2a_v3_medium", "pulsar_x2_crazylight_medium",
    "pulsar_x2_crazylight_mini", "pulsar_x2h_crazylight_mini",
    "pulsar_xlite_crazylight_medium", "pulsar_xlite_v4_mini", "pulsar_xlite_v4_medium",
    "pulsar_xlite_v4_large",
]
# Non retenue à ce stade : « Xlite CrazyLight Mini » (handle `xlite-crazylight-gaming-mouse`) — la
# boutique la range sous « Shape/Symmetrical » alors que toute la famille Xlite est ergonomique main
# droite : forme à trancher, jamais devinée (docs/audit/PULSAR_CATALOGUE_2026-10-12.md §6).


@pytest.fixture(scope="module")
def mice():
    return {m.id: m for m in load_catalog(MOUSE_DB_PATH)}


@pytest.fixture(scope="module")
def raw_entries():
    """Le fichier tel qu'il est écrit, sans passer par le chargeur (contrôles de forme des données)."""
    return json.loads(MOUSE_DB_PATH.read_text(encoding="utf-8"))


def test_catalog_contains_owner_models_and_new_verified_variants(mice):
    assert set(OWNER_IDS) <= set(mice)
    assert set(NEW_ATK_IDS) <= set(mice)
    assert set(STORE_2026_10_11_IDS) <= set(mice)
    assert set(PULSAR_IDS) <= set(mice)
    assert len(mice) == (len(OWNER_IDS) + len(NEW_ATK_IDS) + len(STORE_2026_10_11_IDS) + len(PULSAR_IDS))


def price_is_either_absent_or_sourced(mouse) -> bool:
    """Règle prix : soit aucun prix, soit un prix EUR vérifié, daté et rattaché à une source en ligne."""
    if mouse.price_eur is None:
        return "EUR" in mouse.price_note
    dated_price_source = any(
        "price_eur" in source.fields and source.url.startswith("http") and source.date_checked
        for source in mouse.sources
    )
    return mouse.price_status == "verified" and dated_price_source and "EUR" in mouse.price_note


def grip_fields_are_sourced_or_unknown(mouse) -> bool:
    """Aucune compatibilité de prise n'est inventée : soit « Inconnu », soit attestée par une source.

    Depuis le 2026-10-12, une valeur autre que « Inconnu » est admise si le FABRICANT l'écrit
    (statut « manufacturer_guide ») et qu'une source du catalogue déclare le champ. Une valeur
    « Faible » (éliminatoire) reste réservée au cahier des charges du propriétaire.
    """
    values = (mouse.palm_grip_fit, mouse.claw_grip_fit, mouse.fingertip_grip_fit)
    if all(v == "Inconnu" for v in values):
        return True
    if mouse.fit_status not in {"owner_spec", "manufacturer_guide", "third_party_guide"}:
        return False
    if mouse.fit_status in {"manufacturer_guide", "third_party_guide"} and "Faible" in values:
        return False
    for field, value in zip(("palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit"), values):
        if value != "Inconnu" and not any(field in s.fields for s in mouse.sources):
            return False
    return True


def test_store_additions_are_sourced_and_never_invent_compatibility(mice):
    """Les ajouts « produits vendus » sont sourcés, sans prix EUR inventé ni compatibilité inventée."""
    for mouse_id in STORE_2026_10_11_IDS:
        mouse = mice[mouse_id]
        assert mouse.sources, f"{mouse_id} doit citer au moins une source"
        assert all(s.date_checked and s.url.startswith("http") for s in mouse.sources)
        assert price_is_either_absent_or_sourced(mouse), mouse_id
        assert grip_fields_are_sourced_or_unknown(mouse), mouse_id


def test_small_shape_gap_is_filled_by_the_pulsar_minis(mice):
    """2026-10-12 : les deux premières souris de moins de 118 mm sont des Pulsar « Mini » (115,6 mm).

    La VXE Dragonfly V3 (116,6 mm) reste la plus courte des ATK/VXE déjà au catalogue.
    """
    pulsar_minis = [mice["pulsar_x2_v3_mini"], mice["pulsar_x2h_v3_mini"], mice["pulsar_xlite_v4_mini"]]
    assert [m.length_mm for m in pulsar_minis] == [115.6, 115.6, 115.6]
    assert mice["vxe_v3"].length_mm == 116.6
    others = [
        m.length_mm for m in mice.values()
        if not m.id.startswith("pulsar_") and m.id != "vxe_v3" and m.length_mm is not None
    ]
    assert min(others) > 116.6
    assert min(m.length_mm for m in mice.values() if m.length_mm is not None) == 115.6


def test_owner_models_keep_their_compatibility_values(mice):
    # Non-régression : les compatibilités fournies par le cahier des charges ne doivent pas changer.
    assert (mice["atk_z1_ultra"].palm_grip_fit, mice["atk_z1_ultra"].hump_position, mice["atk_z1_ultra"].button_height) == ("Élevé", "Mid-Front", "High")
    assert (mice["scyrox_v6"].palm_grip_fit, mice["scyrox_v6"].button_height) == ("Moyen", "Mid")
    assert mice["atk_a9_plus"].price_eur == 45.0


def test_a9_plus_width_kept_with_documented_conflict_tolerance(mice):
    a9 = mice["atk_a9_plus"]
    assert a9.width_max_mm == 63.5
    assert a9.dimension_status == "verified"
    assert any(s.url.startswith("https://www.eloshapes.com") for s in a9.sources)


def test_new_models_have_no_invented_compatibility_or_price(mice):
    for mid in NEW_ATK_IDS:
        m = mice[mid]
        assert price_is_either_absent_or_sourced(m), f"{mid} : prix non sourcé"
        assert m.fit_status in {"unverified", "manufacturer_guide", "third_party_guide"}, mid
        assert grip_fields_are_sourced_or_unknown(m), f"{mid} : compatibilité de prise non sourcée"
        assert m.sources, f"{mid} : toute donnée doit citer une source"


def test_two_missing_criteria_still_block_a_mouse(mice):
    """Règle du 2026-10-12 : UNE seule donnée manquante (hauteur des boutons) n'empêche plus le
    classement ; dès qu'il en manque une DEUXIÈME, la souris reste « à vérifier », jamais classée.

    Mise à jour du 2026-10-12 (hauteur des boutons héritée de la coque A9) : une souris dont plus
    AUCUNE donnée ne manque est classée **complète** — c'est désormais le cas des trois variantes
    « large » de la coque A9 (`atk_a9_ultimate`, `atk_a9_air`, `atk_a9_nb`).
    """
    hand = HandMeasure(180, 90)
    for mid in NEW_ATK_IDS:
        mouse = mice[mid]
        s = evaluate_mouse(mouse, hand, Grip.PALM)
        gaps = 0
        gaps += mouse.button_height == "Inconnu"
        gaps += mouse.palm_grip_fit == "Inconnu"
        gaps += mouse.hump_position == "Inconnu"
        gaps += mouse.length_mm is None
        if s.is_excluded or gaps >= 2:
            assert not s.is_scored, f"{mid} ne doit pas être classé avec {gaps} données manquantes"
        elif gaps == 1:
            assert s.is_scored and s.is_partial, mid
        else:
            assert s.is_scored and not s.is_partial, mid


# Hauteur des boutons héritée par coque (2026-10-12) : les quatre variantes « large » de la coque A9
# (125 mm) sont la même souris avec des entrailles différentes — le propriétaire a donné la hauteur de
# boutons de la sienne (A9 Plus 2.0 : « Mid »), donc les trois autres la partagent. La A9 Mini (118,4 mm)
# n'est PAS de cette coque : elle garde « Inconnu ».
A9_LARGE_SHELL = ("atk_a9_plus", "atk_a9_ultimate", "atk_a9_air", "atk_a9_nb")


def test_a9_shell_variants_share_the_owners_button_height(mice):
    """Les quatre variantes de la coque A9 « large » ont la même hauteur de boutons, sourcée."""
    assert {mice[i].shell_id for i in A9_LARGE_SHELL} == {"atk_a9_large"}
    for ident in A9_LARGE_SHELL:
        assert mice[ident].button_height == "Mid", ident
    # La valeur d'origine est celle du propriétaire (aucune source web ne la publie) ; les trois
    # variantes héritées déclarent, elles, une source datée qui porte le champ `button_height`.
    assert mice["atk_a9_plus"].fit_status == "owner_spec"
    for ident in ("atk_a9_ultimate", "atk_a9_air", "atk_a9_nb"):
        assert any("button_height" in s.fields and s.date_checked for s in mice[ident].sources), ident
    assert mice["atk_a9_mini"].button_height == "Inconnu"
    # Effet voulu : plus de score « partiel » pour ces trois-là (le critère est désormais compté).
    for ident in ("atk_a9_ultimate", "atk_a9_air", "atk_a9_nb"):
        score = evaluate_mouse(mice[ident], HandMeasure(180, 90), Grip.CLAW)
        assert not score.is_pending, ident


# Versions « allégées » dominées par les règles actuelles (2026-10-12) : mêmes données de score que
# leur jumelle de coque, et **jamais moins chères** — le poids n'entre pas dans le score. Mesuré sur la
# grille complète : 100 % des profils notés les voient devancées par leur jumelle (0 exception).
# Depuis le 2026-10-13, la paire A9 est à **prix égal** (59,95 €) : la boutique ATK vend l'A9 Ultimate
# et l'A9 Air au même prix (relevé officiel du 2026-10-13, variantes « Ultimate / Black » et
# « Air / Black ») ; la domination de l'A9 Air repose donc sur l'ordre du classement à score et prix
# égaux, que la boucle ci-dessous vérifie cas par cas.
PAIRES_DOMINEES = (
    ("atk_a9_air", "atk_a9_ultimate"),
    ("atk_u2_mini", "atk_u2_v2_mini"),
    ("pulsar_x2_crazylight_medium", "pulsar_x2a_v3_medium"),
    ("pulsar_x2h_crazylight_mini", "pulsar_x2h_v3_mini"),
)
CHAMPS_DE_SCORE = ("length_mm", "width_max_mm", "height_mm", "hump_position", "button_height",
                   "palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit")


def test_light_versions_can_never_pass_their_cheaper_twin(mice):
    """Preuve de domination : quatre souris « jamais recommandées » ne peuvent pas gagner.

    Chaque paire partage la même coque (`shell_id`) et **exactement les mêmes données de score** ; seuls
    le poids et le prix diffèrent, et le poids ne compte pas. Dans les cinq modes, à score égal, le
    départage finit par le prix — puis, à prix égal, par l'ordre du catalogue : la version allégée ne
    passe jamais devant sa jumelle (« jamais plus chère » remplace « toujours plus chère » depuis que la
    paire A9 est à prix égal, cf. le commentaire de `PAIRES_DOMINEES`).
    Vérifié sur la grille complète de `tools/recommendation_stats.py` : 11 172 profils pour l'ATK A9 Air
    (0 fois devant), 5 544 pour l'U2 Mini, 4 830 pour la X2 CrazyLight Medium, 3 990 pour la X2H
    CrazyLight Mini. Ce test rejoue le contrôle sur le catalogue entier (cinq modes × trois prises ×
    trois mains) et échoue si la domination disparaît — par exemple si une donnée change d'un côté.
    """
    from utils.models import BudgetMode
    from utils.selection import select

    modes = (None, BudgetMode.ECONOMIQUE, BudgetMode.QUALITE_PRIX, BudgetMode.HAUT_DE_GAMME,
             BudgetMode.PEU_IMPORTE_PRIX, BudgetMode.CUSTOM)
    for allegee, jumelle in PAIRES_DOMINEES:
        a, b = mice[allegee], mice[jumelle]
        assert a.shell_id and a.shell_id == b.shell_id, (allegee, a.shell_id, b.shell_id)
        for champ in CHAMPS_DE_SCORE:
            assert getattr(a, champ) == getattr(b, champ), (allegee, champ)
        assert b.price_eur <= a.price_eur, (allegee, a.price_eur, b.price_eur)
        vus = 0
        for mode in modes:
            # Le mode Budget personnalisé exige un plafond : 200 € couvrent tout le catalogue.
            plafond = 200.0 if mode is BudgetMode.CUSTOM else None
            for grip in Grip:
                for hand in (HandMeasure(160, 75), HandMeasure(180, 90), HandMeasure(200, 100)):
                    scores = [evaluate_mouse(m, hand, grip, mode, plafond) for m in mice.values()]
                    ranked = [s.mouse.id for s in select(scores, mode, top_n=len(scores)).ranked]
                    if allegee not in ranked:
                        continue
                    vus += 1
                    assert ranked.index(jumelle) < ranked.index(allegee), (allegee, mode, grip, hand)
        assert vus > 0, f"aucun cas testé pour {allegee} : le contrôle serait vide"


def test_zero_button_height_measured_on_two_official_views(mice):
    """2026-10-12 : première hauteur de boutons MESURÉE (et non déduite) du catalogue.

    Deux vues de profil officielles de l'ATK Blazing Sky ZERO donnent 43,3 % et 43,7 % de la hauteur
    totale — la référence étalonnée « boutons bas » (43,3 %) — donc la classe « Low ». Les deux vues
    montrent la même coque (écart de silhouette 0,24 %, mesuré par `tools/image_identity_check.py`) et
    l'une porte « ZERO » imprimé : l'identité est établie sur l'image, jamais par le nom de fichier.
    Ce test gèle la valeur, sa provenance et sa reproductibilité.
    """
    zero = mice["atk_zero"]
    assert zero.button_height == "Low"
    sources = [s for s in zero.sources if "button_height" in s.fields]
    assert len(sources) == 1, "une seule source doit porter la hauteur des boutons"
    source = sources[0]
    assert source.date_checked == "2026-10-12"
    assert "atk.store" in source.url
    assert "43,3 %" in source.label and "43,7 %" in source.label, source.label
    # La valeur est mesurée, pas héritée : elle ne vient pas d'une autre souris de la même coque.
    assert zero.shell_id in (None, "") or not any(
        autre.id != zero.id and autre.shell_id == zero.shell_id and autre.button_height == "Low"
        for autre in mice.values())
    # Elle change le classement : la ZERO n'est plus « partielle » en Palm (boutons comptés).
    score = evaluate_mouse(zero, HandMeasure(180, 90), Grip.PALM)
    assert not score.is_pending


def test_les_trois_references_d_etalonnage_viennent_de_mesures_sourcees(mice):
    """Les trois références de `tools/measure_button_height.py` sont des mesures datées et tracées.

    L'outil classe une souris par la référence la plus proche : si une mesure publiée et la constante de
    l'outil divergent, tout l'étalonnage se décale en silence. Ce test relie les deux bouts — la souris
    du catalogue, sa classe, sa source datée et la constante de l'outil — et vérifie que la provenance
    est écrite là où le catalogue la cherche (``sources[].fields`` contient ``button_height``).
    """
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import measure_button_height as outil

    attendu = {                     # souris : (classe, rapport d'étalonnage, mesure publiée)
        "atk_f1_v2": ("Low", 0.433, "43,3 %"),
        "atk_a9_ultimate": ("Mid", 0.473, "47,3 %"),   # la souris des deux rendus mesurés
        "atk_z1_ultra": ("High", 0.551, "55,1 %"),
    }
    references = {klass: ratio for _, klass, ratio in outil.CALIBRATION_REFERENCES}
    assert set(references) == {"Low", "Mid", "High"}, references
    for ident, (klass, ratio, mesure) in attendu.items():
        mouse = mice[ident]
        assert mouse.button_height == klass, ident
        assert references[klass] == pytest.approx(ratio, abs=0.0005), ident
        sources = [s for s in mouse.sources if "button_height" in s.fields]
        assert len(sources) == 1, f"{ident} : une seule source doit porter la hauteur des boutons"
        assert sources[0].date_checked == "2026-10-12", ident
        assert mesure in sources[0].label, sources[0].label
        # La source pointe la page officielle de la souris (le rendu mesuré) ou le protocole ; la note
        # donne toujours la mesure et renvoie au document.
        assert "atk.store" in sources[0].url or "MESURE_BOUTONS" in sources[0].url, sources[0].url
        assert f"« {klass} »" in mouse.notes and mesure in mouse.notes, ident
        assert "MESURE_BOUTONS" in mouse.notes, ident
    # Une seule coque « atk_f1 » : la F1 V3 Ultimate hérite de la même hauteur de boutons, tracée.
    heritee = [s for s in mice["atk_f1_ultimate"].sources if "button_height" in s.fields]
    assert len(heritee) == 1 and heritee[0].date_checked == "2026-10-12", heritee


def test_no_shell_mixes_two_button_heights(mice):
    """Invariant de coque : deux souris de la MÊME coque ne peuvent pas annoncer deux hauteurs de
    boutons différentes — une coque est une seule pièce de plastique.

    Exception documentée : la VXE X3 partage la coque de l'ATK X1 V2 Ultra Max, mais ni sa hauteur de
    boutons ni sa bosse ne sont propagées — la bosse de l'X1 est contestée par une source tierce
    (« Back - minimal » chez EloShapes contre « Mid » du propriétaire), et rien ne prouve encore que la
    X3, gamme VXE à switchs Omron et puce Broadcom, reprend les boutons de la X1.
    """
    exceptions = {"vxe_x3"}
    par_coque: dict[str, set] = {}
    for mouse in mice.values():
        if not mouse.shell_id or mouse.id in exceptions:
            continue
        par_coque.setdefault(mouse.shell_id, set()).add(mouse.button_height)
    incoherentes = {coque: valeurs for coque, valeurs in par_coque.items() if len(valeurs) > 1}
    assert incoherentes == {}, f"coques avec deux hauteurs de boutons : {incoherentes}"


def test_bosse_des_xlite_et_prix_de_l_a9_mini_sont_sources(mice):
    """Données ajoutées le 2026-10-12 : bosse des Pulsar Xlite (EloShapes) et prix de l'ATK A9 Mini.

    Ce sont les deux manques qui empêchaient ces souris d'entrer dans le tableau des recommandations.
    Aucune valeur devinée : chaque champ ajouté cite une source datée, et la souris devient classable
    (partielle) dès qu'il ne lui reste qu'UN manque.
    """
    for ident in ("pulsar_xlite_v4_mini", "pulsar_xlite_v4_medium", "pulsar_xlite_v4_large",
                  "pulsar_xlite_crazylight_medium"):
        mouse = mice[ident]
        assert mouse.hump_position == "Mid", ident
        assert any("eloshapes.com" in s.url and "hump_position" in s.fields for s in mouse.sources), ident
        # Un seul manque restant (la hauteur des boutons) : plus jamais « à vérifier » faute de bosse.
        # Pour un profil donné la souris peut bien sûr être écartée par ses mesures (une « Large » ne
        # convient pas à une main de 180 mm), mais elle n'est plus mise en attente.
        assert not evaluate_mouse(mouse, HandMeasure(180, 90), Grip.PALM).is_pending, ident
    a9 = mice["atk_a9_mini"]
    assert (a9.price_eur, a9.price_status) == (59.95, "verified")
    assert (a9.hump_position, a9.dimension_status) == ("Mid", "verified")
    assert any(s.url.startswith("https://www.atk.store/") and "price_eur" in s.fields for s in a9.sources)
    score = evaluate_mouse(a9, HandMeasure(180, 90), Grip.PALM)
    assert score.is_scored and score.is_partial      # un seul manque : hauteur des boutons


def test_duckbill_dimensions_resolved_from_the_manufacturer(mice):
    """2026-10-12 : la fiche officielle ATK publie 118 × 55 × 37,4 mm.

    Règle « le fabricant prime sur une tierce » : la largeur cesse d'être la valeur d'EloShapes (62,5)
    et la longueur n'est plus bloquée par l'article du blog ATK (117 mm). Les deux écarts restent
    consignés dans « conflicts », et la souris devient classable (score partiel : boutons non
    documentés) au lieu d'être « à vérifier » sur toute la grille.
    """
    duck = mice["atk_duckbill"]
    assert (duck.length_mm, duck.width_max_mm, duck.height_mm) == (118.0, 55.0, 37.4)
    # Statut corrigé le 2026-10-12 (34e passe) : « single_source » (« une seule source, tierce »)
    # contredisait les trois sources de cotes de l'entrée, dont deux du fabricant. La règle écrite
    # (README) rend « verified » obligatoire dès que la boutique officielle publie les cotes ; aucun
    # score ne change (seul le statut ``conflicting`` bloque une souris). Le sens inverse est
    # désormais contrôlé par ``test_le_statut_des_cotes_ne_reste_pas_sous_estime``.
    assert duck.dimension_status == "verified"
    assert duck.conflicts["length_mm"]["values"] == [118.0, 117.0]
    assert duck.conflicts["width_max_mm"]["values"] == [55.0, 62.5]
    assert any(s.url.startswith("https://www.atk.store/") and "width_max_mm" in s.fields
               for s in duck.sources)
    score = evaluate_mouse(duck, HandMeasure(170, 85), Grip.CLAW)
    assert score.is_scored and not score.is_pending


def test_duckbill_price_matches_the_only_variant_on_sale(mice):
    """La Duckbill n'existe qu'en un modèle (« Ultra », trois coloris) : le prix retenu est le sien.

    Relevé sur la boutique ATK pays France : 81,95 € le 2026-10-12, **82,95 € le 2026-10-13**
    (prix normal 118,95 €, inchangé pour les trois coloris). Aucune variante moins chère n'existe,
    donc le prix de la fiche est celui de ce modèle — et il suit la boutique, pas l'ancien relevé.
    Le prix et la note gardent la trace des deux dates.
    """
    duck = mice["atk_duckbill"]
    assert (duck.price_eur, duck.price_status) == (82.95, "verified")
    assert any(s.url.startswith("https://www.atk.store/") and "price_eur" in s.fields
               for s in duck.sources)
    assert "« Ultra »" in duck.price_note      # modèle unique : le prix est celui de ce modèle
    assert "2026-10-13" in duck.price_note      # la date du relevé qui fait foi est écrite
    assert "81,95" in duck.price_note           # l'ancien relevé reste expliqué, pas effacé


def test_chaque_prix_de_souris_est_date_par_une_source(mice):
    """Aucun prix ne vit sans une source datée qui dit À QUOI il correspond.

    Défaut trouvé le 2026-10-13 (37e passe) : quatre fiches annonçaient un prix que la page du
    marchand n'affichait plus (F1 V2 et MAD R 40,95 € au lieu de 41,95 €, A9 NB 72,95 € au lieu de
    73,95 €, Duckbill 81,95 € au lieu de 82,95 €) — la boutique avait relevé ses prix d'un euro
    sans que le catalogue le sache. Le contrôle ci-dessous exige, pour chaque souris, au moins une
    source de boutique officielle (atk.store, eu.pulsar.gg, scyrox.com) dont l'adresse rappelle le
    relevé de prix : impossible de publier un prix sans écrire d'où il vient.
    """
    for ident, mouse in sorted(mice.items()):
        assert mouse.price_eur > 0, ident
        assert re.search(r"20\d\d-\d\d-\d\d", mouse.price_note or ""), (
            f"{ident} : la note de prix ne dit pas quand le prix a été relevé"
        )
        sources_prix = [s for s in mouse.sources if "price_eur" in s.fields]
        assert sources_prix, f"{ident} : aucune source ne trace le prix"
        assert all(re.fullmatch(r"20\d\d-\d\d-\d\d", s.date_checked) for s in sources_prix), (
            f"{ident} : une source de prix n'est pas datée"
        )


def test_ghost_prices_are_read_variant_by_variant(mice):
    """Le GHOST existe en quatre variantes ; chaque fiche du catalogue reçoit SON prix.

    Relevé du 2026-10-12 sur la fiche ATK pays France (`?country=FR`, prix en euros, jamais
    convertis) : Ultimate 68,95 €, Ultimate+ 77,95 €, Extreme 86,95 €, Extreme+ 95,95 €. La fiche
    GHOST Extreme annonçait 86,95 € depuis la 19e passe : la relecture la confirme au lieu de la
    remplacer par le minimum de la famille (68,95 €) ou par son maximum (95,95 €).
    """
    ultimate, extreme = mice["atk_ghost_ultimate"], mice["atk_ghost_extreme"]
    assert (ultimate.price_eur, extreme.price_eur) == (68.95, 86.95)
    assert extreme.price_eur > ultimate.price_eur
    for mouse, variante in ((ultimate, "Ultimate"), (extreme, "Extreme")):
        assert mouse.price_status == "verified", mouse.id
        assert any(s.url.startswith("https://www.atk.store/") and "price_eur" in s.fields
                   for s in mouse.sources), mouse.id
        assert f"« {variante} »" in mouse.price_note, mouse.id
    assert "95,95" in extreme.price_note     # la variante la plus chère ne doit pas être masquée


def test_third_party_grip_guide_fills_only_what_the_brand_silences(mice):
    """2026-10-12 : une source tierce AUTORISÉE (mouseshape.com) complète les prises non publiées.

    Règles vérifiées ici, sans exception :
    - la valeur vient d'une fiche mouseshape datée qui déclare le champ ;
    - le fabricant garde la main : une souris tierce garde aussi sa source constructeur, et une valeur
      fabricant n'est jamais remplacée (vérifié champ par champ sur deux cas concrets) ;
    - « Recommended » → « Élevé », « Okay » → « Moyen » ;
    - « Not ideal » n'est JAMAIS converti en « Faible » : une valeur tierce n'exclut personne.
    """
    tiers = [m for m in mice.values() if m.fit_status == "third_party_guide"]
    assert len(tiers) >= 10, "les dix souris complétées doivent porter le statut dédié"
    for mouse in tiers:
        valeurs = (mouse.palm_grip_fit, mouse.claw_grip_fit, mouse.fingertip_grip_fit)
        assert "Faible" not in valeurs, mouse.id
        assert not all(v == "Inconnu" for v in valeurs), mouse.id
        assert any("atk.store" in s.url or "eu.pulsar.gg" in s.url for s in mouse.sources), mouse.id
        tierce = [s for s in mouse.sources if "mouseshape.com" in s.url]
        assert tierce and all(s.date_checked == "2026-10-12" for s in tierce), mouse.id
        for champ in ("palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit"):
            if getattr(mouse, champ) != "Inconnu":
                assert any(champ in s.fields for s in mouse.sources), (mouse.id, champ)

    # Cas concrets : « Recommended » accepté, « Not ideal » laissé « Inconnu ».
    xlite = mice["pulsar_xlite_v4_medium"]
    assert (xlite.palm_grip_fit, xlite.claw_grip_fit) == ("Élevé", "Élevé")
    assert xlite.fingertip_grip_fit == "Inconnu"          # « Not ideal » n'est pas « Faible »
    x2 = mice["pulsar_x2_v3_mini"]
    assert (x2.claw_grip_fit, x2.fingertip_grip_fit) == ("Élevé", "Élevé")
    assert x2.palm_grip_fit == "Inconnu"                  # idem pour le palm
    # Résultat : ces souris sont notées dès qu'une prise leur manque n'est PAS celle du profil.
    for ident, grip in (("pulsar_x2h_v3_mini", Grip.FINGERTIP), ("atk_fierce_x", Grip.FINGERTIP),
                        ("atk_u2_mini", Grip.FINGERTIP), ("pulsar_xlite_v4_large", Grip.CLAW)):
        score = evaluate_mouse(mice[ident], HandMeasure(175, 85), grip)
        assert score.is_scored or score.is_excluded, (ident, grip)


def test_commercial_links_are_official_and_verified():
    """Liens fournis par le propriétaire le 2026-10-11, vérifiés un par un sur les boutiques officielles.

    Détail de la vérification : docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md.
    Aucun lien d'exemple ne doit subsister, et une souris dont le lien n'a pas été fourni reste
    sans lien : le résultat affiche alors « Liens à venir », jamais un lien inventé.
    Les dix Pulsar ajoutées le 2026-10-12 mènent à la fiche officielle du modèle sur la boutique
    européenne (prix affiché en euros, donc en EUR — jamais de conversion) et portent le paramètre
    d'affiliation fourni par le propriétaire le 2026-10-12 (`?ref=AZE`).
    """
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    assert links, "les liens d'achat vérifiés doivent être livrés"
    assert all(
        url.startswith(("https://www.atk.store/", "https://scyrox.com/", "https://eu.pulsar.gg/"))
        for url in links.values()
    )
    assert not any("url.com" in url for url in links.values())
    assert "atk_a9_nb" in links  # 26e lien, fourni par le propriétaire le 2026-10-11 (A9 NB Ultra, 72,95 €)
    assert all("country=FR" in url for key, url in links.items() if "atk.store" in url)  # prix en euros
    assert all(
        url.startswith("https://eu.pulsar.gg/products/")
        for key, url in links.items() if key.startswith("pulsar_")
    )
    # Affiliation Pulsar fournie par le propriétaire le 2026-10-12 : le paramètre fait partie du lien.
    assert all(
        "ref=AZE" in url for key, url in links.items() if key.startswith("pulsar_")
    )
    assert len([key for key in links if key.startswith("pulsar_")]) == len(PULSAR_IDS)


def test_commercial_links_reference_known_mice():
    ids = {m.id for m in load_catalog(MOUSE_DB_PATH)}
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    assert set(links) <= ids


def test_images_config_has_all_keys():
    urls = load_image_urls(IMAGES_CONFIG_PATH)
    assert set(urls) == set(IMAGE_KEYS)
    assert "step2_thenar" in IMAGE_KEYS and "step3_budget" in IMAGE_KEYS
    assert "step3_thenar" not in IMAGE_KEYS  # ancienne clé de l'étape thénar retirée du parcours


def test_every_configured_illustration_exists_in_assets_illustrations():
    """Intégration graphique : chaque nom de fichier de assets/images.json existe vraiment (bons fichiers au bon endroit)."""
    raw = json.loads(IMAGES_CONFIG_PATH.read_text(encoding="utf-8"))
    names = [v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str) and v]
    assert names, "les 15 assets ImageUse doivent être référencés"
    for name in names:
        assert not name.startswith("http"), f"{name} doit rester un nom de fichier local (assets/illustrations/)"
        assert (ROOT / "assets" / "illustrations" / name).is_file(), f"illustration absente du dépôt : {name}"


def test_illustration_folder_contains_only_referenced_files():
    raw = json.loads(IMAGES_CONFIG_PATH.read_text(encoding="utf-8"))
    referenced = {v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str) and v}
    on_disk = {p.name for p in (ROOT / "assets" / "illustrations").iterdir() if p.is_file()}
    assert on_disk == referenced, f"fichiers non référencés : {sorted(on_disk - referenced)}"


def test_images_resolve_with_the_base_url(tmp_path):
    """Un simple nom de fichier est résolu avec IMAGES_BASE_URL (déploiement : une seule variable à changer)."""
    f = tmp_path / "images.json"
    f.write_text('{"banner": "T08_azemouse_banniere.png"}', encoding="utf-8")
    urls = load_image_urls(f, base_url="https://compte.alwaysdata.net/illustrations")
    assert urls["banner"] == "https://compte.alwaysdata.net/illustrations/T08_azemouse_banniere.png"


def test_bare_filename_without_base_url_or_with_bad_scheme_is_ignored(tmp_path):
    f = tmp_path / "images.json"
    f.write_text('{"banner": "T08_azemouse_banniere.png"}', encoding="utf-8")
    assert load_image_urls(f, base_url="")["banner"] is None
    assert load_image_urls(f, base_url="http://compte.alwaysdata.net/")["banner"] is None
    assert load_image_urls(f, base_url="https://x.test/")["banner"] is not None


def test_full_https_urls_are_used_as_is(tmp_path):
    """Compatibilité : une URL complète reste prioritaire (hébergement externe possible)."""
    f = tmp_path / "images.json"
    f.write_text('{"banner": "https://cdn.test/T08.png"}', encoding="utf-8")
    assert load_image_urls(f, base_url="https://autre.test/")["banner"] == "https://cdn.test/T08.png"


@pytest.mark.parametrize("valeur", [
    "https://exemple.fr/T01 .png",
    "https://exemple.fr/T01\nhttps://exemple.fr/T02.png",
    "https://exemple.fr/T01\t.png",
    "https://exemple.fr/T01\x00.png",
])
def test_une_url_d_image_inutilisable_n_affiche_rien(valeur):
    """Même famille que les liens d'achat (trouvé le 2026-10-13).

    Une « URL » contenant un espace, un saut de ligne ou un caractère de contrôle n'en est pas une :
    Discord refuse l'image au moment de l'envoi. Le contrat de ce module est « aucune image plutôt
    qu'une exception » — la valeur est donc écartée, avec un avertissement dans les journaux.
    """
    from utils.assets import build_image_url

    assert build_image_url(valeur, "https://aze.fr/img") is None


def test_invalid_image_url_is_ignored(tmp_path):
    f = tmp_path / "images.json"
    f.write_text('{"banner": "javascript:alert(1)", "step1_grip": "https://x.test/a.png"}', encoding="utf-8")
    urls = load_image_urls(f)
    assert urls["banner"] is None
    assert urls["step1_grip"] == "https://x.test/a.png"


def test_legacy_budget_image_key_is_used_as_fallback(tmp_path):
    f = tmp_path / "images.json"
    f.write_text('{"step4_budget": "https://x.test/budget.png"}', encoding="utf-8")
    assert load_image_urls(f)["step3_budget"] == "https://x.test/budget.png"


def test_missing_image_file_gives_no_images(tmp_path):
    assert set(load_image_urls(tmp_path / "absent.json").values()) == {None}


def test_missing_links_file_gives_empty_mapping(tmp_path):
    assert load_commercial_links(tmp_path / "absent.json") == {}


def test_links_file_skips_invalid_entries(tmp_path):
    f = tmp_path / "links.json"
    f.write_text(json.dumps({"_aide": "x", "a": "https://shop.test/a", "b": "javascript:x", "c": 3}), encoding="utf-8")
    assert load_commercial_links(f) == {"a": "https://shop.test/a"}


def test_un_lien_avec_espace_ou_saut_de_ligne_est_ecarte(tmp_path):
    """Trouvé le 2026-10-13 (fichiers du serveur attaqués).

    Un lien contenant un espace, une tabulation, un saut de ligne ou un caractère de contrôle était
    transmis tel quel au bouton du résultat. Une telle adresse n'est pas une URL : Discord refuse le
    composant au moment de l'envoi — c'est alors le **résultat entier** qui échoue, et le membre voit
    « erreur inattendue » au lieu de ses trois souris. Le chargeur écarte ce seul lien ; les autres
    souris gardent le leur, et une espace encodée (`%20`) reste valide.
    """
    f = tmp_path / "links.json"
    f.write_text(json.dumps({
        "espace": "https://shop.test/a b",
        "tabulation": "https://shop.test/a\tb",
        "saut": "https://shop.test/a\nhttps://evil.test",
        "controle": "https://shop.test/a\x00b",
        "encode": "https://shop.test/a%20b",
        "normal": "https://shop.test/ok",
    }), encoding="utf-8")
    assert load_commercial_links(f) == {"encode": "https://shop.test/a%20b", "normal": "https://shop.test/ok"}


# ---------------------------------------------------------------------------
# Validation du schéma : chaque erreur doit être détectée
# ---------------------------------------------------------------------------
def base_raw(**overrides):
    raw = dict(
        id="t", brand="B", model="M", budget_tier="Qualité-Prix", width_max_mm=63.0, length_mm=120.0,
        hump_position="Mid", button_height="Mid", palm_grip_fit="Élevé", claw_grip_fit="Élevé",
        fingertip_grip_fit="Élevé", fit_rationale="x",
    )
    raw.update(overrides)
    return raw


def test_valid_minimal_record_parses():
    assert parse_mouse(base_raw(), 1).id == "t"


@pytest.mark.parametrize("override", [
    {"palm_grip_fit": "Bof"},
    {"button_height": "Tall"},
    {"hump_position": "Top"},
    {"budget_tier": "Luxe"},
    {"dimension_status": "guessed"},
    {"price_status": "maybe"},
    {"width_max_mm": -1},
    {"polling_hz": "8000"},
])
def test_invalid_values_are_rejected(override):
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(**override), 1)


@pytest.mark.parametrize("override", [
    {"weight_g": "55 g"},
    {"weight_g": [55]},
    {"weight_g": {"grammes": 55}},
    {"weight_g": -5},
    {"weight_g": float("nan")},
    {"length_mm": float("nan")},
    {"length_mm": float("inf")},
    {"width_max_mm": float("nan")},
    {"height_mm": float("inf")},
    {"grip_width_mm": float("nan")},
    {"price_eur": float("nan")},
    {"price_eur": float("inf")},
    {"polling_hz": True},
    {"length_mm": True},
])
def test_un_nombre_hostile_est_refuse_au_chargement(override):
    """Trouvé le 2026-10-13 (catalogue attaqué avec des valeurs hostiles).

    Le chargement promet une erreur **immédiate et lisible** plutôt qu'un échec à l'affichage. Ce
    n'était pas le cas des nombres : un poids en texte, une liste ou un objet passaient la validation,
    puis l'affichage du résultat levait `ValueError: Unknown format code 'g'` (poids en texte) ou
    `TypeError` (liste, objet) — donc « erreur inattendue » pour le membre. Et un `NaN`, un infini ou
    un booléen traversaient tout : `nan <= 0` et `inf <= 0` sont faux, et `True` est un `int` en
    Python. Ils s'affichaient tels quels (« nan g », « inf € », « 1 Hz »).
    """
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(**override), 1)


def test_les_nombres_du_vrai_catalogue_sont_finis_et_positifs(mice):
    """Le durcissement ne touche aucune donnée réelle : tout est fini, positif, du bon type."""
    for mouse in mice.values():
        for nom, valeur in (("weight_g", mouse.weight_g), ("length_mm", mouse.length_mm),
                            ("height_mm", mouse.height_mm), ("grip_width_mm", mouse.grip_width_mm),
                            ("price_eur", mouse.price_eur)):
            if valeur is None:
                continue
            assert isinstance(valeur, float), f"{mouse.id} : {nom} n'est pas un flottant"
            assert math.isfinite(valeur) and valeur > 0, f"{mouse.id} : {nom} = {valeur!r}"
        if mouse.polling_hz is not None:
            assert isinstance(mouse.polling_hz, int) and not isinstance(mouse.polling_hz, bool)
            assert mouse.polling_hz > 0


def test_length_null_requires_documented_conflict_or_note():
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(length_mm=None), 1)
    assert parse_mouse(base_raw(length_mm=None, notes="en attente"), 1).length_mm is None


def test_conflict_needs_two_values_and_sources():
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(conflicts={"length_mm": {"values": [118.0], "sources": ["a"]}}), 1)
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(conflicts={"length_mm": {"values": [118.0, 117.0], "sources": []}}), 1)


def test_verified_dimensions_require_a_source():
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(dimension_status="verified", sources=[]), 1)


def test_verified_price_requires_a_price():
    with pytest.raises(CatalogError):
        parse_mouse(base_raw(price_status="verified", price_eur=None), 1)


def test_duplicate_ids_rejected(tmp_path):
    f = tmp_path / "db.json"
    f.write_text(json.dumps([base_raw(), base_raw()]), encoding="utf-8")
    with pytest.raises(CatalogError):
        load_catalog(f)


def test_missing_required_field_rejected():
    raw = base_raw()
    del raw["palm_grip_fit"]
    with pytest.raises(CatalogError):
        parse_mouse(raw, 1)

def test_every_mouse_shape_is_sourced():
    """La forme de coque (« Symmetrical » / « Ergonomic ») est renseignée et attestée par une source.

    Elle sert au bloc « la bosse et la forme » du résultat : jamais de forme devinée, et toute
    donnée vient d'une source qui la liste explicitement (champ « shape »).
    """
    from utils.models import SHAPES, UNKNOWN

    for mouse in load_catalog(MOUSE_DB_PATH):
        assert mouse.shape in SHAPES, mouse.id
        assert mouse.shape != UNKNOWN, f"{mouse.id} : forme non renseignée"
        assert any("shape" in source.fields for source in mouse.sources), mouse.id


def test_every_mouse_weight_is_known_and_sourced():
    """Le poids s'affiche à côté du match idéal et de l'alternative : toutes, chacune sourcée."""
    for mouse in load_catalog(MOUSE_DB_PATH):
        assert mouse.weight_g, f"{mouse.id} : poids manquant"
        assert 20 <= mouse.weight_g <= 120, f"{mouse.id} : poids invraisemblable ({mouse.weight_g})"
        assert any("weight_g" in source.fields for source in mouse.sources), mouse.id


def test_pulsar_entries_are_sourced_and_never_invent_components(mice):
    """2026-10-12 : les fiches Pulsar sont relevées sur la fiche officielle du modèle, une par une.

    Règles tenues : prix en EUR vérifié, forme et compatibilités sourcées, fréquence = valeur
    publiée (1 000 Hz) et jamais le maximum commercial, MCU vide (non publié par le fabricant).
    """
    for mid in PULSAR_IDS:
        mouse = mice[mid]
        assert mouse.brand == "Pulsar" and mouse.budget_tier == "Haut de Gamme"
        assert price_is_either_absent_or_sourced(mouse), mid
        assert mouse.price_status == "verified" and mouse.price_eur, mid
        assert any(s.url.startswith("https://eu.pulsar.gg/") for s in mouse.sources), mid
        assert mouse.dimension_status == "verified", mid
        assert mouse.mcu == "", f"{mid} : MCU non publié par Pulsar, il doit rester vide"
        assert mouse.polling_hz == 1000, f"{mid} : 1 000 Hz publié (8 000 Hz = dongle séparé)"
        assert "dongle" in mouse.notes.lower(), mid


def test_pulsar_additions_make_claw_and_fingertip_less_repetitive(mice):
    """Effet attendu : au moins une Pulsar devient classable en Claw et en Fingertip.

    Avant cet ajout, seules six souris du catalogue pouvaient être classées (toutes de la même
    famille ATK/Scyrox) : c'est ce qui faisait « toujours les mêmes » suggestions.
    """
    for grip in (Grip.CLAW, Grip.FINGERTIP):
        hand = HandMeasure(180, 90)
        scored = [
            m.id for m in mice.values()
            if m.id.startswith("pulsar_") and evaluate_mouse(m, hand, grip).is_scored
        ]
        assert scored, f"aucune Pulsar classable en {grip.label}"


def test_every_documented_component_is_sourced():
    """Capteur, fréquence, switchs, MCU : un champ rempli cite la source qui l'atteste."""
    for mouse in load_catalog(MOUSE_DB_PATH):
        for field in ("sensor", "polling_hz", "switches", "mcu"):
            if getattr(mouse, field):
                assert any(field in source.fields for source in mouse.sources), (mouse.id, field)


def test_partial_scoring_opens_the_choice_without_inventing_points(mice):
    """Ouverture du critère « hauteur des boutons » (2026-10-12) : mesurée souris par souris.

    Effets attendus : la Y9 (ergonomique main droite, palm Élevé publié par ATK) devient classable en
    Palm, et les Pulsar Mini en Claw/Fingertip. Les souris qui gardent DEUX manques restent, elles,
    « à vérifier » — après le relevé de la bosse des Xlite v4 (EloShapes, 2026-10-12), l'exemple réel
    de deux manques est la VXE X3 (bosse inconnue + prise non publiée).
    """
    palm = {m.id: evaluate_mouse(m, HandMeasure(180, 90), Grip.PALM) for m in mice.values()}
    assert palm["atk_y9_ultimate"].is_scored, "la Y9 doit être classable en Palm"
    assert palm["atk_y9_ultimate"].is_partial
    # Depuis le 2026-10-12 (bosse des Xlite v4 relevée sur EloShapes → Mid), ces Pulsar n'ont plus
    # qu'UN manque (la hauteur des boutons) : elles entrent dans le choix, partielles comme la Y9.
    assert palm["pulsar_xlite_v4_mini"].is_scored, "bosse connue : un seul manque, donc classable"
    assert palm["pulsar_xlite_v4_mini"].is_partial
    # La règle des DEUX manques, elle, reste vérifiée sur une souris réelle : la VXE X3 cumule une
    # bosse inconnue et une prise non publiée.
    assert palm["vxe_x3"].is_pending, "deux manques : toujours « à vérifier »"
    claw = {m.id: evaluate_mouse(m, HandMeasure(150, 75), Grip.CLAW) for m in mice.values()}
    assert sum(1 for s in claw.values() if s.is_scored) >= 13, "le profil Claw 150 × 75 doit s'ouvrir"


# Deux entrées dont les dimensions publiées sont identiques au dixième de millimètre décrivent la
# même coque : le moteur ne doit jamais les proposer comme DEUX choix dans un résultat (« le match
# idéal » puis « l'alternative » étant la même souris). Encore faut-il que la coque soit enregistrée
# dans ``shell_id`` : mesure du 2026-10-12, 92 profils montraient deux fois la même souris
# (A9 Plus 2.0 + A9 NB Ultra ; X2A v3 + X2 CrazyLight Medium) faute de ce champ. Corrigé pour
# l'A9 NB Ultra, les deux U2 Mini et la X3 ; deux paires restent en attente d'une source fabricant
# explicite (elles ne sortent aujourd'hui jamais ensemble, mais le champ doit être tranché).
SAME_SHELL_PAIRS_PENDING_SOURCE = (
    ("atk_u2", "atk_u2_v2_ultimate"),
)


def test_two_entries_with_identical_dimensions_share_their_shell(mice):
    """Canari : aucune paire de dimensions identiques ne doit rester sans coque partagée."""
    groupes: dict[tuple, list[str]] = {}
    for mouse in mice.values():
        key = (mouse.length_mm, mouse.width_max_mm, mouse.height_mm)
        if None in key:
            continue
        groupes.setdefault(key, []).append(mouse.id)
    inexpliquees = []
    for identifiants in groupes.values():
        for i, premier in enumerate(identifiants):
            for second in identifiants[i + 1:]:
                paire = (premier, second)
                if mice[premier].shell_id and mice[premier].shell_id == mice[second].shell_id:
                    continue
                if paire in SAME_SHELL_PAIRS_PENDING_SOURCE or paire[::-1] in SAME_SHELL_PAIRS_PENDING_SOURCE:
                    continue
                inexpliquees.append(paire)
    assert inexpliquees == [], f"coque à enregistrer (shell_id) : {inexpliquees}"


def test_shells_documented_in_the_catalogue_notes_are_registered_in_shell_id(mice):
    """Les coques déjà documentées dans les notes du catalogue doivent l'être aussi dans shell_id."""
    attendus = {
        "atk_a9_nb": "atk_a9_large",        # « coque A9 pleine taille », « même coque »
        "atk_u2_mini": "atk_u2_mini",       # une seule fiche ATK « U2 Mini », dimensions identiques
        "atk_u2_v2_mini": "atk_u2_mini",
        "vxe_x3": "atk_x1",                 # « coque de la famille X1 »
        # Pulsar X2 taille Medium (2026-10-12) : la fiche officielle de la X2A v3 la classe dans la série
        # « X2 » (étiquettes « Series/X2 », « X2 », taille « Medium ») ; les deux entrées Medium publient
        # les mêmes dimensions au dixième de millimètre (120,4 × 63 × 38), la même bosse (Mid), les mêmes
        # boutons (Low) et la même forme (Symétrique) — exactement la règle déjà appliquée aux deux Minis
        # (« pulsar_x2_mini »). C'était le dernier cas où deux entrées de la même coque pouvaient occuper
        # deux places du même résultat.
        "pulsar_x2a_v3_medium": "pulsar_x2_medium",
        "pulsar_x2_crazylight_medium": "pulsar_x2_medium",
    }
    for identifiant, coque in attendus.items():
        assert mice[identifiant].shell_id == coque, identifiant
    # Deux entrées de la même coque ne peuvent plus occuper deux places du même résultat.
    assert mice["atk_a9_nb"].shell_id == mice["atk_a9_plus"].shell_id == mice["atk_a9_ultimate"].shell_id


def test_chaque_coque_partagee_declare_la_source_qui_l_atteste(mice):
    """Provenance des coques : une entrée seule n'a rien à prouver, une coque PARTAGÉE si.

    ``shell_id`` est le seul champ du catalogue laissé hors de ``CHAMPS_TRAÇABLES`` : pour une souris
    sans jumelle il dit seulement « aucune autre entrée du catalogue ne partage ce moule », et c'est
    ``test_two_entries_with_identical_dimensions_share_their_shell`` qui protège le cas dangereux
    (deux cotes identiques sans coque commune). Dès que **deux** entrées partagent une coque, en
    revanche, ce regroupement écarte une alternative réelle du résultat (deux variantes du même moule
    ne s'affichent plus côte à côte) : chaque entrée doit alors citer la source qui l'atteste **et**
    dire dans son libellé ce qui la justifie. Le fabricant ou un document du projet peuvent attester
    un moule ; un guide de prise tiers ne le peut pas (il ne connaît pas les moules).
    """
    from urllib.parse import urlparse

    groupes: dict[str, list[str]] = {}
    for mouse in mice.values():
        if mouse.shell_id:
            groupes.setdefault(mouse.shell_id, []).append(mouse.id)
    partagees = {coque: sorted(membres) for coque, membres in groupes.items() if len(membres) > 1}
    # Garde-fou du test lui-même : l'inventaire doit rester celui du catalogue (8 coques partagées).
    assert len(partagees) >= 8, f"coques partagées attendues : {partagees}"
    justifications = ("coque", "moule", "famille", "série")
    for coque, membres in sorted(partagees.items()):
        for ident in membres:
            declarantes = [s for s in mice[ident].sources if "shell_id" in s.fields]
            assert declarantes, f"{ident} : coque partagée « {coque} » sans source déclarante"
            for source in declarantes:
                hote = urlparse(source.url).hostname or ""
                assert hote in DOMAINES_FABRICANT or hote == "github.com", (ident, source.url)
                assert any(mot in source.label.lower() for mot in justifications), (ident, source.label)


def test_f1_v2_inherits_the_grip_verdicts_of_its_twin_shell(mice):
    """2026-10-12 : l'ATK F1 V2 était la SEULE souris sans aucune compatibilité de prise publiée —
    donc jamais classable, jamais recommandée (rapport STATISTIQUES : 0 sortie sur 18 522 profils).

    Sa coque est celle de l'ATK F1 V3 Ultimate (shell_id « atk_f1 » : 118,2 × 62,4 × 38,8 mm, bosse
    « Mid », boutons bas) : les verdicts du cahier des charges sont repris tels quels et sourcés.
    La fiche ATK du 2026-10-12 annonce « Grip Style: Claw / Palm » : accord total sur Claw ; pour
    Palm, le verdict du propriétaire sur cette coque (exclusion 180×90) reste prioritaire.
    """
    v2, v3 = mice["atk_f1_v2"], mice["atk_f1_ultimate"]
    assert v2.shell_id == v3.shell_id == "atk_f1"
    verdicts = ("Faible", "Élevé", "Élevé")
    assert (v2.palm_grip_fit, v2.claw_grip_fit, v2.fingertip_grip_fit) == verdicts
    assert (v3.palm_grip_fit, v3.claw_grip_fit, v3.fingertip_grip_fit) == verdicts
    assert v2.fit_status == "owner_spec"
    assert grip_fields_are_sourced_or_unknown(v2)
    # Elle est désormais classée là où la coque a un verdict non éliminatoire, et exclue en Palm.
    claw = evaluate_mouse(v2, HandMeasure(150, 75), Grip.CLAW)
    assert claw.is_scored and not claw.is_pending
    assert evaluate_mouse(v2, HandMeasure(180, 90), Grip.PALM).is_excluded


def test_no_sold_mouse_is_left_without_grip_compatibility(mice):
    """2026-10-12 : plus aucune souris vendue ne reste « à vérifier » faute de compatibilité de prise."""
    assert [m.id for m in mice.values() if m.fit_status == "unverified"] == []


# ---------------------------------------------------------------------------
# Audit du 2026-10-12 : la traçabilité du catalogue devient VÉRIFIABLE par la machine
# ---------------------------------------------------------------------------
# Contexte : les valeurs sont écrites à la main (recherches web, mesures, cahier des charges). Une
# relecture a montré que 44 valeurs sur 492 étaient bien SOURCÉES dans les notes, mais que la source
# correspondante ne DÉCLARAIT pas le champ dans ``sources[].fields`` : la chaîne de provenance
# n'était pas vérifiable automatiquement (et rien ne l'était, sauf pour ``shape`` et les prises).
# Ces quatre tests transforment la règle en invariant : toute valeur renseignée cite la source qui
# l'atteste, tout écart est consigné dans ``conflicts``, aucune clé n'est vide, et un statut
# « verified » se justifie par ses sources.
CHAMPS_TRAÇABLES = (
    "length_mm", "width_max_mm", "height_mm", "weight_g", "grip_width_mm", "price_eur",
    "hump_position", "button_height", "shape", "sensor", "switches", "mcu", "polling_hz",
    "palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit",
)
COTES_MM = ("length_mm", "width_max_mm", "height_mm")
# Boutiques du FABRICANT (pas des revendeurs) : une cote qui n'y figure que là est tenue pour établie.
DOMAINES_FABRICANT = frozenset({"www.atk.store", "atk.store", "eu.pulsar.gg", "scyrox.com"})
# Tolérance de concordance déjà appliquée aux données (voir « verified » dans README) : deux sources
# qui divergent de plus de 0,5 mm ne concordent pas ; deux entrées d'une même coque non plus.
TOLERANCE_CONCORDANCE_MM = 0.5


def test_chaque_valeur_du_catalogue_cite_la_source_qui_l_atteste(mice):
    """Aucune valeur renseignée ne peut exister sans qu'une source déclare le champ correspondant.

    C'est la règle « jamais d'invention » rendue exécutable : le catalogue garde ses notes, mais c'est
    ``sources[].fields`` qui fait foi pour la machine (et c'est là que le chargeur regarde pour la
    forme depuis l'origine). « Inconnu », une chaîne vide et ``None`` signifient « pas de valeur » et
    n'ont donc rien à attester.
    """
    inventaire = 0
    sans_source: list[str] = []
    for mouse in mice.values():
        declares = {champ for source in mouse.sources for champ in source.fields}
        for champ in CHAMPS_TRAÇABLES:
            valeur = getattr(mouse, champ)
            if valeur in (None, "", "Inconnu"):
                continue
            inventaire += 1
            if champ not in declares:
                sans_source.append(f"{mouse.id}.{champ} = {valeur!r}")
    # Garde-fou du test lui-même : si l'inventaire devenait vide, le contrôle ne prouverait plus rien.
    assert inventaire > 450, f"inventaire des valeurs renseignées suspect : {inventaire}"
    assert sans_source == [], "valeurs sans source déclarante : " + " | ".join(sans_source)


def test_les_ecarts_de_forme_sont_consignes_dans_conflicts(mice):
    """Un écart connu ne se raconte pas seulement dans les notes : il est consigné dans ``conflicts``.

    Les deux souris de la coque F1 / X1 ont une bosse « Mid » du cahier des charges, alors que la page
    EloShapes annonce « Back - minimal » : la valeur du propriétaire est conservée (règle « le
    propriétaire prime »), mais l'écart reste lisible par la machine au lieu de disparaître.
    """
    for ident in ("atk_f1_ultimate", "atk_x1_ultra_max"):
        mouse = mice[ident]
        conflit = mouse.conflicts.get("hump_position")
        assert conflit, f"{ident} : écart de bosse non consigné dans « conflicts »"
        assert mouse.hump_position in conflit["values"], ident
        assert any("Back - minimal" in valeur for valeur in conflit["values"]), ident
        assert conflit["sources"] and len(conflit["values"]) >= 2, ident
        # La note de la fiche dit la même chose que le conflit (jamais deux versions divergentes).
        assert "Back - minimal" in mouse.notes and "Mid" in mouse.notes, ident


def test_le_catalogue_ne_contient_aucune_valeur_vide():
    """Une chaîne vide n'est pas une donnée : « absent » et « inconnu » se disent par l'absence de clé.

    Le 2026-10-12, dix entrées Pulsar portaient ``"mcu": ""`` là où les autres n'ont pas la clé du
    tout : deux écritures pour un même état, que le chargeur traite identiquement — mais qui rendent
    les audits par script faux (une clé absente se lit ``None``, jamais ``""``).
    """
    raw = json.loads(MOUSE_DB_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, list) and len(raw) >= 36
    vides = [f"{entree.get('id')}.{cle}" for entree in raw for cle, valeur in entree.items() if valeur == ""]
    assert vides == [], "clés à valeur vide : " + ", ".join(vides)
    sans_source = [entree.get("id") for entree in raw if not entree.get("sources")]
    assert sans_source == [], f"entrées sans aucune source : {sans_source}"


def test_un_statut_verified_se_justifie_par_ses_sources(mice):
    """« verified » = au moins DEUX sources de cotes concordantes, ou UNE seule source quand c'est le
    fabricant lui-même (sa boutique officielle) — précision écrite dans le README le 2026-10-12.

    Sans cette précision, dix entrées Pulsar (relevées une par une sur la fiche officielle du
    fabricant) portaient un statut que la règle documentée n'autorisait pas ; à l'inverse, une cote
    reprise d'un revendeur ne peut jamais être « verified » toute seule.
    """
    from urllib.parse import urlparse

    for mouse in mice.values():
        if mouse.dimension_status != "verified":
            continue
        sources_cotes = [s for s in mouse.sources if set(COTES_MM) & set(s.fields)]
        fabricant = [s for s in sources_cotes if urlparse(s.url).netloc in DOMAINES_FABRICANT]
        assert len(sources_cotes) >= 2 or fabricant, (
            f"{mouse.id} : « verified » sans deux sources de cotes ni source du fabricant "
            f"({[s.label[:40] for s in sources_cotes]})")


def test_deux_entrees_de_la_meme_coque_ne_divergent_pas_hors_tolerance(mice):
    """Deux entrées d'une même coque décrivent une seule pièce de plastique.

    Écart admis : la tolérance de concordance (0,5 mm) — l'ATK A9 Plus 2.0 (cahier des charges,
    63,5 mm) et l'A9 Ultimate (EloShapes, 64,0 mm) sont à l'intérieur. Au-delà, c'est une erreur de
    saisie ou deux coques différentes, et le test le dit.
    """
    par_coque: dict[str, list] = {}
    for mouse in mice.values():
        if mouse.shell_id:
            par_coque.setdefault(mouse.shell_id, []).append(mouse)
    assert par_coque, "aucune coque enregistrée : le contrôle serait vide"
    for coque, groupe in par_coque.items():
        for champ in COTES_MM:
            valeurs = [getattr(m, champ) for m in groupe if getattr(m, champ) is not None]
            assert valeurs, f"{coque}.{champ} : aucune valeur"
            ecart = max(valeurs) - min(valeurs)
            assert ecart <= TOLERANCE_CONCORDANCE_MM, (coque, champ, valeurs, ecart)


def test_aucune_source_ne_declare_un_champ_resté_vide(raw_entries):
    """Une source qui déclare un champ est une preuve : le champ doit porter une valeur.

    Défaut trouvé le 2026-10-12 : les deux Scyrox déclaraient ``height_mm`` (« cahier des charges du
    propriétaire ») alors que la valeur était restée ``null`` — un auditeur lisait donc « hauteur
    attestée » et « hauteur inconnue » en même temps. Le contrôle porte sur TOUT le catalogue, pour
    que la même erreur ne puisse pas revenir à la faveur d'une édition manuelle.
    """
    assert len(raw_entries) >= 36, "catalogue incomplet : le contrôle serait vide"
    declarees = vides = 0
    for entree in raw_entries:
        for source in entree.get("sources", []):
            for champ in source.get("fields", []):
                declarees += 1
                if entree.get(champ) in (None, ""):
                    vides += 1
                    print(f"{entree.get('id')} : {champ} déclaré par « {source.get('label', '')[:60]} » mais vide")
    assert declarees >= 500, f"trop peu de champs déclarés ({declarees}) : le contrôle ne prouve rien"
    assert vides == 0, f"{vides} champ(s) déclaré(s) par une source mais resté(s) vide(s)"


def test_l_ecart_de_largeur_de_la_coque_a9_est_consigne(mice):
    """La coque A9 « large » publie **63,5 mm** partout, et l'écart avec EloShapes reste écrit.

    Historique (tranché le 2026-10-12, 33e passe) : la coque avait deux largeurs publiées — 63,5 mm
    (cahier des charges du propriétaire, boutique ATK, A9 NB) et 64,0 mm (EloShapes, pour l'A9
    Ultimate et l'A9 Air) — soit une même pièce de plastique décrite de deux façons. La fiche
    officielle ATK de la série A9 a été relue le 2026-10-12 : elle annonce « 125 x 63.5 x 40 mm »
    pour la coque pleine taille. Règle du projet : le fabricant prime sur une tierce, et le
    propriétaire a mesuré la sienne à 63,5 mm — la coque est donc alignée à 63,5 mm.
    L'écart n'est pas effacé : il reste dans ``conflicts``, avec ses deux sources.
    """
    for ident in A9_LARGE_SHELL:
        mouse = mice[ident]
        assert mouse.width_max_mm == 63.5, (ident, mouse.width_max_mm)
        # La valeur publiée est attestée par une source datée qui déclare le champ.
        assert any("width_max_mm" in s.fields and s.date_checked for s in mouse.sources), ident
    # Les trois entrées que la source tierce relève à 64,0 mm gardent l'écart consigné.
    for ident in ("atk_a9_plus", "atk_a9_ultimate", "atk_a9_air"):
        mouse = mice[ident]
        conflit = mouse.conflicts.get("width_max_mm")
        assert conflit, f"{ident} : écart de largeur non consigné dans « conflicts »"
        assert sorted(conflit["values"]) == [63.5, 64.0], conflit["values"]
        assert mouse.width_max_mm in conflit["values"], "la valeur publiée doit être une des valeurs du conflit"
        assert len(conflit["sources"]) >= 2 and conflit.get("note"), conflit
        assert TOLERANCE_CONCORDANCE_MM == 0.5 and max(conflit["values"]) - min(conflit["values"]) <= 0.5
        assert "63.5" in mouse.notes and "64.0" in mouse.notes, "la note doit donner les deux valeurs"
        # La source fabricant qui fonde la valeur est bien présente et datée — sauf pour l'A9 Plus,
        # dont la largeur vient de la souris du propriétaire (le fabricant dit la même chose : 63,5 mm).
        if ident == "atk_a9_plus":
            assert any("width_max_mm" in s.fields and "propriétaire" in s.label for s in mouse.sources), ident
        else:
            assert any("atk.store" in s.url and "width_max_mm" in s.fields and s.date_checked
                       for s in mouse.sources), ident


def test_la_note_de_l_x1_ne_contredit_pas_ses_champs(mice):
    """Une fiche ne peut pas dire « non renseigné » d'un champ qui porte une valeur.

    Défaut trouvé le 2026-10-12 (33e passe) : la note de l'ATK X1 V2 Ultra Max annonçait un capteur
    « non renseigné » alors que le champ publiait « PAW3395 Ultra », et deux paragraphes plus loin la
    même note le citait — deux versions de la même fiche dans le même champ. Le capteur reste la
    valeur des trois sources du modèle exact (EloShapes, Maxesport, TechnoGeek BD) ; le tableau du
    fabricant couvre toute la série et reste consigné dans ``conflicts``.
    """
    mouse = mice["atk_x1_ultra_max"]
    assert "non renseigné" not in mouse.notes, "la note contredit un champ renseigné"
    assert mouse.sensor == "PAW3395 Ultra", mouse.sensor
    declarants = [s for s in mouse.sources if "sensor" in s.fields]
    assert len(declarants) >= 3, [s.label for s in declarants]
    conflict = mouse.conflicts.get("sensor")
    assert conflict and len(conflict["values"]) >= 2 and conflict.get("note"), conflict
    assert mouse.sensor in conflict["values"], conflict["values"]


def test_deux_entrees_de_la_meme_coque_publient_les_memes_cotes(mice):
    """Une coque est une seule pièce de plastique : deux entrées publient les mêmes cotes.

    L'égalité est exigée exactement ; un écart n'est admis QUE s'il est consigné dans ``conflicts``
    (une divergence non documentée n'est pas une mesure, c'est un défaut de données).

    Cas tranché le 2026-10-12 : la largeur de la coque A9 « large » valait 63,5 mm côté propriétaire
    et fabricant, 64,0 mm côté EloShapes. La fiche officielle ATK annonce « 125 x 63.5 x 40 mm » pour
    la coque pleine taille (relevé du 2026-10-12) : la règle « le fabricant prime » s'applique, les
    quatre entrées publient 63,5 mm, et l'écart reste écrit dans ``conflicts`` pour ne pas disparaître.
    """
    par_coque: dict[str, list] = {}
    for mouse in mice.values():
        if mouse.shell_id:
            par_coque.setdefault(mouse.shell_id, []).append(mouse)
    assert len(par_coque) >= 8, "trop peu de coques enregistrées : le contrôle ne prouve rien"
    ecarts: list[str] = []
    for coque, groupe in par_coque.items():
        for champ in COTES_MM:
            valeurs = {m.id: getattr(m, champ) for m in groupe if getattr(m, champ) is not None}
            if len(set(valeurs.values())) <= 1:
                continue
            non_consigne = [ident for ident in valeurs if champ not in mice[ident].conflicts]
            if non_consigne:
                ecarts.append(f"{coque}.{champ} = {valeurs} (non consigné pour {non_consigne})")
    assert ecarts == [], "cotes divergentes entre entrées d'une même coque : " + " ; ".join(ecarts)


def test_aucune_source_n_est_enregistree_deux_fois_dans_une_entree(raw_entries):
    """Une source identique (même libellé, même URL, même date) ne peut pas être listée deux fois.

    Défaut trouvé le 2026-10-12 (34e passe) : l'ATK Y9 Ultimate portait **deux fois** la même fiche
    du fabricant — deux entrées au libellé, à l'URL et à la date rigoureusement identiques —, la
    première déclarant ``claw_grip_fit`` et la seconde ``price_eur``. Le catalogue paraissait donc
    attester deux fois la même lecture, et tout comptage de sources (règle des deux sources
    concordantes, audits par script) gonflait d'une unité. Les deux entrées sont fusionnées en une
    seule, qui déclare les deux champs.

    À ne pas confondre : **deux lectures d'une même page** (dates ou libellés différents, par exemple
    une première lecture des cotes puis une relecture du tableau de dimensions) restent deux sources
    légitimes — c'est le doublon *strict* qui est interdit ici.
    """
    assert len(raw_entries) >= 36, "catalogue incomplet : le contrôle serait vide"
    vues = doublons = 0
    fautives: list[str] = []
    for entree in raw_entries:
        cles: set[tuple] = set()
        for source in entree.get("sources", []):
            vues += 1
            cle = (source.get("label"), source.get("url"), source.get("date_checked"))
            if cle in cles:
                doublons += 1
                fautives.append(f"{entree.get('id')} → {str(cle[0])[:50]} ({cle[2]})")
            cles.add(cle)
    assert vues >= 200, f"trop peu de sources ({vues}) : le contrôle ne prouve rien"
    assert doublons == 0, "source enregistrée deux fois à l'identique : " + " ; ".join(fautives)


def test_le_statut_des_cotes_ne_reste_pas_sous_estime(mice):
    """La règle des statuts se vérifie DANS LES DEUX SENS.

    Le sens « statut fort sans preuve » est contrôlé par
    ``test_un_statut_verified_se_justifie_par_ses_sources``. Le sens inverse n'était vérifié nulle
    part : une entrée pouvait garder ``single_source`` alors que ses propres sources réunissaient déjà
    les conditions de ``verified`` (deux sources distinctes de cotes, ou la boutique officielle du
    fabricant). Trois cas mesurés le 2026-10-12 (34e passe) — l'ATK Duckbill (trois sources de cotes,
    dont deux du fabricant), l'ATK A9 Air et la VXE X3 (la fiche du fabricant) — annonçaient
    « une seule source tierce » alors que la fiche officielle du fabricant attestait les cotes : le
    statut est corrigé, et ce test interdit le retour d'un statut sous-estimé.

    Les sources sont comptées **distinctes** (libellé + URL + date) : un doublon ne vaut pas deux
    attestations (voir ``test_aucune_source_n_est_enregistree_deux_fois_dans_une_entree``). Le statut
    ``conflicting`` reste hors contrôle : il signale un désaccord, pas une faiblesse de provenance.
    """
    from urllib.parse import urlparse

    controle = 0
    sous_estimes: list[str] = []
    for mouse in mice.values():
        if mouse.dimension_status in {"verified", "conflicting"}:
            continue
        uniques = {(s.label, s.url, s.date_checked): s for s in mouse.sources}
        cotes = [s for s in uniques.values() if set(COTES_MM) & set(s.fields)]
        fabricant = [s for s in cotes if urlparse(s.url).netloc in DOMAINES_FABRICANT]
        controle += 1
        if len(cotes) >= 2 or fabricant:
            sous_estimes.append(
                f"{mouse.id} = {mouse.dimension_status} ({len(cotes)} source(s) de cotes, "
                f"{len(fabricant)} du fabricant)")
    assert controle >= 5, f"trop peu d'entrées contrôlées ({controle}) : le contrôle ne prouve rien"
    assert sous_estimes == [], ("statut de cotes sous-estimé (les sources justifient « verified ») : "
                               + " ; ".join(sous_estimes))


def test_le_prix_de_l_a9_ultimate_est_celui_de_sa_variante(mice):
    """Corrigé le 2026-10-13 : la fiche A9 Ultimate portait le prix « à partir de » d'une autre édition.

    La boutique ATK vend plusieurs éditions de l'A9 sur la même page ; notre bouton d'achat ouvre
    depuis toujours la variante **« Ultimate / Black »**, mais le prix publié (41,95 €) était le minimum
    de la page — celui de la variante « Ultra Max 2.0 / Black ». Le membre lisait donc 41,95 € et en
    payait 59,95 €. Même piège que la Y9 Ultimate et la Z1 V2, corrigées le 2026-10-12 ; règle
    appliquée : **le prix d'une fiche est celui de la variante figée par son lien d'achat**. Ce test
    gèle le prix, la provenance et la variante.
    """
    a9 = mice["atk_a9_ultimate"]
    assert (a9.price_eur, a9.price_status) == (59.95, "verified")
    assert "« Ultimate / Black »" in a9.price_note
    assert "41,95" in a9.price_note or "41.95" in a9.price_note   # l'ancien relevé reste expliqué
    source = [s for s in a9.sources if "46878654005466" in s.url]
    assert len(source) == 1, "la variante figée par le bouton doit être citée par une source datée"
    assert "price_eur" in source[0].fields and source[0].date_checked == "2026-10-13"


def test_chaque_lien_a_variante_est_trace_par_une_source(mice):
    """Traçabilité des liens d'achat : toute variante figée (`?variant=…`) doit être citée par une source.

    Le prix publié est celui de cette variante (règle du 2026-10-12, appliquée à la Y9, la Z1 V2 puis à
    l'A9 Ultimate) : sans la source qui NOMME la variante, une relecture du prix ne sait plus quel
    modèle vérifier — c'est exactement l'angle mort qui a laissé la fiche A9 Ultimate à 41,95 € pendant
    deux jours. Le test ne vérifie pas le prix (cela demande une connexion) : il interdit qu'un lien
    figé reste sans provenance.
    """
    from config import COMMERCIAL_LINKS_PATH
    import re
    from utils.catalog import load_commercial_links

    liens = load_commercial_links(COMMERCIAL_LINKS_PATH)
    figes = {mid: re.search(r"variant=(\d+)", url).group(1)
             for mid, url in liens.items() if "variant=" in url}
    assert len(figes) >= 10, f"trop peu de liens figés ({len(figes)}) : le contrôle serait vide"
    manquants = []
    for mid, variante in figes.items():
        mouse = mice[mid]
        if not any(variante in s.url for s in mouse.sources):
            manquants.append(f"{mid} (variant={variante})")
    assert manquants == [], f"variantes figées sans source : {', '.join(manquants)}"
