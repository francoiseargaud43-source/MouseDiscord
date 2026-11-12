"""Garde-fou du générateur de catalogue : jamais de destruction silencieuse de données.

Le script ``tools/build_mouse_db.py`` est l'artefact de traçabilité du premier relevé (18 entrées).
Le catalogue réel est enrichi à la main (36 souris, prix, mesures, sources) : une exécution par
distraction ne doit jamais l'écraser. Ces tests vérifient le refus, le message et l'écriture
atomique sous ``--force``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_mouse_db  # noqa: E402  (module de l'outil, importé après l'ajout du chemin)


@pytest.fixture()
def catalogue_enrichi(tmp_path: Path) -> Path:
    """Un catalogue cible plus riche que ce que le script génère (comme le vrai data/mouse_db.json)."""
    target = tmp_path / "mouse_db.json"
    contenu = [{"id": "souris_gardee"}, {"id": "atk_phantom"}, *({"id": m["id"]} for m in build_mouse_db.mice)]
    target.write_text(json.dumps(contenu), encoding="utf-8")
    return target


def test_refuse_to_overwrite_a_richer_catalogue(catalogue_enrichi, capsys):
    avant = catalogue_enrichi.read_text(encoding="utf-8")
    assert build_mouse_db.main(["--sortie", str(catalogue_enrichi)]) == 1
    sortie = capsys.readouterr().out
    assert "REFUS" in sortie
    assert "souris_gardee" in sortie                      # les entrées perdues sont nommées
    assert catalogue_enrichi.read_text(encoding="utf-8") == avant   # fichier intact


def test_force_writes_the_generated_catalogue(catalogue_enrichi):
    assert build_mouse_db.main(["--sortie", str(catalogue_enrichi), "--force"]) == 0
    data = json.loads(catalogue_enrichi.read_text(encoding="utf-8"))
    stored = {m["id"] for m in data}
    assert "souris_gardee" not in stored
    assert stored == {m["id"] for m in build_mouse_db.mice}
    assert not (catalogue_enrichi.parent / "mouse_db.json.tmp").exists()   # écriture atomique terminée


def test_writes_a_new_file_without_guard(tmp_path, capsys):
    cible = tmp_path / "nouveau.json"
    assert build_mouse_db.main(["--sortie", str(cible)]) == 0
    assert json.loads(cible.read_text(encoding="utf-8"))
    assert "entrées écrites" in capsys.readouterr().out
