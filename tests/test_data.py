"""Intégrité des fichiers de données livrés."""
from config import COMMERCIAL_LINKS_PATH, IMAGES_CONFIG_PATH, MOUSE_DB_PATH
from utils.assets import IMAGE_KEYS, load_image_urls
from utils.catalog import load_catalog, load_commercial_links


def test_catalog_loads_all_six_mice():
    mice = load_catalog(MOUSE_DB_PATH)
    assert [m.id for m in mice] == [
        "scyrox_v8", "scyrox_v6", "atk_f1_ultimate", "atk_x1_ultra_max", "atk_z1_ultra", "atk_a9_plus",
    ]


def test_commercial_links_reference_known_mice():
    ids = {m.id for m in load_catalog(MOUSE_DB_PATH)}
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    assert links and set(links) <= ids


def test_images_config_has_all_keys():
    urls = load_image_urls(IMAGES_CONFIG_PATH)
    assert set(urls) == set(IMAGE_KEYS)


def test_invalid_image_url_is_ignored(tmp_path):
    f = tmp_path / "images.json"
    f.write_text('{"banner": "javascript:alert(1)", "step1_grip": "https://x.test/a.png"}', encoding="utf-8")
    urls = load_image_urls(f)
    assert urls["banner"] is None
    assert urls["step1_grip"] == "https://x.test/a.png"
