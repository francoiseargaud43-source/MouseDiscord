"""Intégrité des fichiers de données livrés (catalogue v2, liens, images)."""
import json

import pytest

from config import COMMERCIAL_LINKS_PATH, IMAGES_CONFIG_PATH, MOUSE_DB_PATH
from utils.assets import IMAGE_KEYS, load_image_urls
from utils.catalog import CatalogError, load_catalog, load_commercial_links, parse_mouse
from utils.matcher import evaluate_mouse
from utils.models import Grip, HandMeasure

OWNER_IDS = ["scyrox_v8", "scyrox_v6", "atk_f1_ultimate", "atk_x1_ultra_max", "atk_z1_ultra", "atk_a9_plus"]
NEW_ATK_IDS = [
    "atk_phantom_ultimate", "atk_ghost_ultimate", "atk_ghost_extreme", "atk_y9_ultimate", "atk_fierce_x",
    "atk_u2_v2_ultimate", "atk_u2_v2_mini", "atk_zero", "atk_duckbill", "atk_a9_ultimate", "atk_a9_air", "atk_a9_mini",
]


@pytest.fixture(scope="module")
def mice():
    return {m.id: m for m in load_catalog(MOUSE_DB_PATH)}


def test_catalog_contains_owner_models_and_new_verified_variants(mice):
    assert set(OWNER_IDS) <= set(mice)
    assert set(NEW_ATK_IDS) <= set(mice)
    assert len(mice) == len(OWNER_IDS) + len(NEW_ATK_IDS)


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
        assert m.price_eur is None, f"{mid} : aucun prix EUR n'est vérifié"
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


def test_no_commercial_link_is_invented():
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    assert all(url.startswith(("https://", "http://")) for url in links.values())
    assert not any(k in links for k in NEW_ATK_IDS)


def test_commercial_links_reference_known_mice():
    ids = {m.id for m in load_catalog(MOUSE_DB_PATH)}
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    assert set(links) <= ids


def test_images_config_has_all_keys():
    urls = load_image_urls(IMAGES_CONFIG_PATH)
    assert set(urls) == set(IMAGE_KEYS)
    assert "step3_thenar" not in IMAGE_KEYS and "step3_budget" in IMAGE_KEYS


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
