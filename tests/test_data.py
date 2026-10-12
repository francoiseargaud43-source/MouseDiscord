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


def test_store_additions_are_sourced_and_never_invent_compatibility(mice):
    """Les ajouts « produits vendus » sont sourcés, sans prix EUR inventé ni compatibilité de prise inventée."""
    for mouse_id in STORE_2026_10_11_IDS:
        mouse = mice[mouse_id]
        assert mouse.sources, f"{mouse_id} doit citer au moins une source"
        assert all(s.date_checked and s.url.startswith("http") for s in mouse.sources)
        assert price_is_either_absent_or_sourced(mouse), mouse_id
        assert mouse.fit_status == "unverified", mouse_id
        assert {mouse.palm_grip_fit, mouse.claw_grip_fit, mouse.fingertip_grip_fit} == {"Inconnu"}, mouse_id


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
        assert m.palm_grip_fit == "Inconnu" and m.claw_grip_fit == "Inconnu" and m.fingertip_grip_fit == "Inconnu"
        assert m.fit_status == "unverified"
        assert m.sources, f"{mid} : toute donnée doit citer une source"


def test_new_models_are_pending_not_ranked_for_palm(mice):
    hand = HandMeasure(180, 90)
    for mid in NEW_ATK_IDS:
        s = evaluate_mouse(mice[mid], hand, Grip.PALM)
        assert not s.is_scored, f"{mid} ne doit pas être classé sans compatibilité vérifiée"


def test_duckbill_length_is_not_filled_while_sources_conflict(mice):
    duck = mice["atk_duckbill"]
    assert duck.length_mm is None
    assert duck.conflicts["length_mm"]["values"] == [118.0, 117.0]


def test_commercial_links_are_official_and_verified():
    """Liens fournis par le propriétaire le 2026-10-11, vérifiés un par un sur les boutiques officielles.

    Détail de la vérification : docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md.
    Aucun lien d'exemple ne doit subsister, et une souris dont le lien n'a pas été fourni reste
    sans lien : le résultat affiche alors « Liens à venir », jamais un lien inventé.
    Les six Pulsar ajoutées le 2026-10-12 mènent à la fiche officielle du modèle sur la boutique
    européenne (prix affiché en euros, donc en EUR — jamais de conversion).
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
