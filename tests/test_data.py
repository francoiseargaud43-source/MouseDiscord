"""Intégrité des fichiers de données livrés (catalogue v2, liens, images)."""
import json
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
# (recherche « produits encore vendus » ; sources ATK Store + EloShapes, voir docs/audit/CATALOGUE_ATK.md §4).
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
    if mouse.fit_status not in {"owner_spec", "manufacturer_guide"}:
        return False
    if mouse.fit_status == "manufacturer_guide" and "Faible" in values:
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
        assert m.fit_status in {"unverified", "manufacturer_guide"}, mid
        assert grip_fields_are_sourced_or_unknown(m), f"{mid} : compatibilité de prise non sourcée"
        assert m.sources, f"{mid} : toute donnée doit citer une source"


def test_two_missing_criteria_still_block_a_mouse(mice):
    """Règle du 2026-10-12 : UNE seule donnée manquante (hauteur des boutons) n'empêche plus le
    classement ; dès qu'il en manque une DEUXIÈME, la souris reste « à vérifier », jamais classée.
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
        else:
            assert s.is_scored and s.is_partial, mid


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
    assert duck.dimension_status == "single_source"
    assert duck.conflicts["length_mm"]["values"] == [118.0, 117.0]
    assert duck.conflicts["width_max_mm"]["values"] == [55.0, 62.5]
    assert any(s.url.startswith("https://www.atk.store/") and "width_max_mm" in s.fields
               for s in duck.sources)
    score = evaluate_mouse(duck, HandMeasure(170, 85), Grip.CLAW)
    assert score.is_scored and not score.is_pending


def test_duckbill_price_matches_the_only_variant_on_sale(mice):
    """La Duckbill n'existe qu'en un modèle (« Ultra », trois coloris) : le prix retenu est le sien.

    Vérifié le 2026-10-12 sur la boutique ATK pays France : 81,95 € pour les trois coloris
    (prix normal 118,95 €). Aucune variante moins chère n'existe, donc le prix ne bouge pas.
    """
    duck = mice["atk_duckbill"]
    assert (duck.price_eur, duck.price_status) == (81.95, "verified")
    assert any(s.url.startswith("https://www.atk.store/") and "price_eur" in s.fields
               for s in duck.sources)
    assert "« Ultra »" in duck.price_note      # modèle unique : le prix est celui de ce modèle


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
