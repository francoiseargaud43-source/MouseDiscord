"""Données corrompues : le bot doit refuser proprement (message clair), jamais planter au résultat.

Chasse aux bugs du 2026-10-12. Avant ces garde-fous, un fichier de données abîmé à la main
pouvait faire remonter une exception technique au milieu d'une réponse d'interaction : le membre
voyait « une erreur inattendue est survenue » sans savoir pourquoi, et le parcours semblait cassé.
"""
import json

import pytest

from utils.assets import load_image_urls
from utils.catalog import CatalogError, load_catalog, load_commercial_links

MOUSE = {
    "id": "test_mouse", "brand": "Test", "model": "M1", "budget_tier": "Économique",
    "width_max_mm": 60.0, "hump_position": "Mid", "button_height": "Low",
    "palm_grip_fit": "Élevé", "claw_grip_fit": "Élevé", "fingertip_grip_fit": "Inconnu",
    "fit_rationale": "test", "length_mm": 120.0,
}


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.parametrize("broken, motif", [
    (["pas un objet"], "objet attendu"),
    ([{**MOUSE, "sensor": 1234}], "sensor doit être du texte"),
    ([{**MOUSE, "mcu": ["nrf"]}], "mcu doit être du texte"),
    ([{**MOUSE, "switches": 2}], "switches doit être du texte"),
    ([{**MOUSE, "family": 5}], "family doit être du texte"),
    ([{**MOUSE, "sources": {"label": "x"}}], "sources doit être une liste"),
    ([{**MOUSE, "sources": [{"label": "sans url ni date"}]}], "source mal formée"),
    ([{**MOUSE, "conflicts": ["length_mm"]}], "conflicts doit être un objet"),
    ([{**MOUSE, "conflicts": {"length_mm": "douze"}}], "conflit « length_mm » mal formé"),
    # Ajouts du 2026-10-13 (passe de couverture) : quatre gardes de structure du catalogue
    # n'étaient exercées par aucun test — un catalogue édité à la main pouvait les franchir.
    ([{**MOUSE, "shape": "Ronflante"}], "shape invalide"),
    ([{**MOUSE, "fit_status": "peut-être"}], "fit_status invalide"),
    ([{**MOUSE, "width_max_mm": None}], "width_max_mm est obligatoire"),
    ([{**MOUSE, "shape": "Symmetrical"}], "shape renseigné sans source listant « shape »"),
])
def test_a_broken_catalog_entry_is_refused_with_a_clear_message(tmp_path, broken, motif):
    path = _write(tmp_path, "mouse_db.json", broken)
    with pytest.raises(CatalogError, match=motif):
        load_catalog(path)


def test_un_catalogue_qui_n_est_pas_une_liste_est_refuse(tmp_path):
    """Racine objet (`{...}`) : refusée avec la phrase qui dit la forme attendue (l.169 de `catalog.py`)."""
    path = _write(tmp_path, "mouse_db.json", {"souris": [MOUSE]})
    with pytest.raises(CatalogError, match="mouse_db.json doit contenir une liste"):
        load_catalog(path)


def test_a_valid_entry_still_loads(tmp_path):
    """Non-régression : les garde-fous n'ajoutent aucune exigence aux données valides."""
    path = _write(tmp_path, "mouse_db.json", [MOUSE])
    mouse = load_catalog(path)[0]
    assert (mouse.id, mouse.length_mm, mouse.sensor) == ("test_mouse", 120.0, None)


def test_a_links_file_that_is_not_an_object_is_ignored(tmp_path):
    """Un lien qui n'est pas un objet JSON ne doit pas empêcher l'affichage du résultat."""
    path = _write(tmp_path, "commercial_links.json", ["https://shop.test/x"])
    assert load_commercial_links(path) == {}


def test_an_images_file_that_is_not_an_object_shows_no_image(tmp_path):
    path = _write(tmp_path, "images.json", ["T01.png"])
    assert set(load_image_urls(path).values()) == {None}


def test_un_fichier_d_images_illisible_n_empeche_pas_le_parcours(tmp_path):
    """C55 (2026-10-13) : tronqué, non UTF-8 ou remplacé par un dossier, il cassait la 1re étape.

    `load_image_urls` est appelé par chaque étape (bannière, illustrations). Il ne prévoyait que le
    JSON invalide : un octet non UTF-8 (`UnicodeDecodeError`) ou un dossier (`IsADirectoryError`)
    remontait jusqu'au flux et le membre recevait « une erreur inattendue » au lieu de l'étape 1 —
    le parcours était impossible à démarrer. Règle de la maison (fichier de sessions, état du
    `!setup_finder`) : ``OSError`` et ``ValueError`` couvrent tout ce que le fichier peut subir.
    """
    # Contenu écrit tel quel : `_write` encode en JSON, ce qui donnerait une **chaîne** valide, pas
    # un fichier tronqué — et le contrôle passerait par la mauvaise branche (forme inattendue au lieu
    # de JSON invalide).
    tronque = tmp_path / "tronque.json"
    tronque.write_text('{"banner": "https://x.test/b.png"', encoding="utf-8")
    assert set(load_image_urls(tronque).values()) == {None}
    octets = tmp_path / "octets.json"
    octets.write_bytes(b'{"banner": "https://x.test/\xff\xfe.png"}')
    assert set(load_image_urls(octets).values()) == {None}
    dossier = tmp_path / "dossier.json"
    dossier.mkdir()
    assert set(load_image_urls(dossier).values()) == {None}
