"""Tests du contrôle d'identité d'un corpus d'images (`tools/image_corpus_check.py`).

Enjeu : après la campagne de mesure de la hauteur des boutons, la revue du corpus a montré qu'une
même photo circulait sous **huit noms de modèles différents** (mêmes octets, noms différents). Une
image qui porte plusieurs noms ne peut être attribuée à aucun : ces tests verrouillent la détection
des doublons et le fait que les fichiers non-image sont ignorés.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from image_corpus_check import fingerprint, groups_by_identity, main  # noqa: E402


def _image(path: Path, couleur: tuple[int, int, int]) -> Path:
    Image.new("RGB", (8, 8), couleur).save(path)
    return path


def test_doublons_detectes_par_empreinte_pas_par_nom(tmp_path):
    _image(tmp_path / "atk-zero-side.jpg", (255, 255, 255))
    (tmp_path / "atk-x1-side.jpg").write_bytes((tmp_path / "atk-zero-side.jpg").read_bytes())
    _image(tmp_path / "vraie-image-unique.jpg", (0, 0, 0))
    (tmp_path / "notes.txt").write_text("ce fichier n'est pas une image", encoding="utf-8")

    duplicated, unique = groups_by_identity(tmp_path)

    assert duplicated == [["atk-x1-side.jpg", "atk-zero-side.jpg"]]
    assert unique == ["vraie-image-unique.jpg"]        # le .txt est ignoré


def test_empreinte_distinguen_deux_images_differentes(tmp_path):
    a = _image(tmp_path / "a.png", (10, 20, 30))
    b = _image(tmp_path / "b.png", (30, 20, 10))
    assert fingerprint(a) != fingerprint(b)
    assert fingerprint(a) == fingerprint(a)


def test_cli_json_liste_les_groupes(tmp_path, capsys):
    _image(tmp_path / "un.jpg", (1, 1, 1))
    (tmp_path / "deux.jpg").write_bytes((tmp_path / "un.jpg").read_bytes())

    assert main([str(tmp_path), "--json"]) == 0

    rapport = json.loads(capsys.readouterr().out)
    assert rapport["fichiers"] == 2
    assert rapport["images_distinctes"] == 1
    assert rapport["doublons"] == [["deux.jpg", "un.jpg"]]
    assert rapport["uniques"] == []


def test_dossier_absent_est_une_erreur_lisible(tmp_path, capsys):
    try:
        main([str(tmp_path / "absent")])
    except SystemExit as exc:            # argparse termine avec un code non nul et un message clair
        assert exc.code == 2
    else:                                 # pragma: no cover - la branche ne doit jamais être atteinte
        raise AssertionError("un dossier absent doit être signalé")
    assert "dossier introuvable" in capsys.readouterr().err
