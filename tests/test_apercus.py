"""Les aperçus PNG versionnés ne doivent pas être plus vieux que ce qu'ils montrent.

Défaut trouvé le 2026-10-13 (50e passe) : `docs/apercu_prix_libre.png` montrait encore « Z1 V2 Ultra »
après le renommage du modèle, et personne ne pouvait le voir sans comparer l'image à l'écran du bot.
Chaque aperçu porte désormais dans ses métadonnées une **empreinte des sources** (catalogue, liens,
images, modules qui composent le message) : ce fichier la relit et la recalcule. Un aperçu périmé est un
document faux, au même titre qu'un tableau de chiffres périmé.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from render_preview import CLE_EMPREINTE, empreinte_des_sources, lire_empreinte  # noqa: E402

APERCUS = ("apercu_parcours.png", "apercu_resultat.png", "apercu_prix_libre.png")


@pytest.mark.parametrize("nom", APERCUS)
def test_chaque_apercu_est_de_la_meme_date_que_les_donnees_qu_il_montre(nom):
    chemin = ROOT / "docs" / nom
    assert chemin.exists(), f"{nom} a disparu du dépôt"
    inscrite = lire_empreinte(chemin)
    assert inscrite, (
        f"{nom} ne porte pas d'empreinte de sources : régénérez-le avec "
        "`python tools/render_preview.py`"
    )
    assert inscrite == empreinte_des_sources(), (
        f"{nom} est plus vieux que le catalogue ou le code qu'il montre "
        f"(empreinte inscrite {inscrite}) : relancez `python tools/render_preview.py`"
    )


def test_l_empreinte_change_quand_une_source_change(tmp_path, monkeypatch):
    """Contre-épreuve : l'empreinte suit le contenu d'une source, elle n'est pas décorative.

    Le test travaille sur une **copie** : aucun fichier du dépôt n'est écrit (une suite de tests ne
    doit jamais pouvoir laisser un fichier du bot modifié derrière elle).
    """
    from tools import render_preview as outil

    copie = tmp_path / "catalogue.json"
    copie.write_bytes((ROOT / "data" / "mouse_db.json").read_bytes())
    monkeypatch.setattr(outil, "FICHIERS_SOURCES", (copie,))
    avant = outil.empreinte_des_sources()
    copie.write_bytes(copie.read_bytes() + b" ")
    assert outil.empreinte_des_sources() != avant
    copie.write_bytes(copie.read_bytes()[:-1])
    assert outil.empreinte_des_sources() == avant


def test_l_empreinte_inscrite_se_relit_dans_l_image(tmp_path):
    """Ce que l'outil écrit est ce que le test relit : la métadonnée PNG, pas un fichier annexe."""
    image = Image.new("RGB", (4, 4), (49, 51, 56))
    metadonnees = PngImagePlugin.PngInfo()
    metadonnees.add_text(CLE_EMPREINTE, "abc123def456")
    chemin = tmp_path / "apercu.png"
    image.save(chemin, pnginfo=metadonnees)
    assert lire_empreinte(chemin) == "abc123def456"
    assert lire_empreinte(ROOT / "assets" / "illustrations" / "T08_azemouse_banniere.png") is None
