"""Pack IA (tools/build_ai_bundle.py) : contenu attendu, absence de secret, identifiants listés."""
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_ai_bundle", ROOT / "tools" / "build_ai_bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


def test_bundle_contains_the_expected_files(tmp_path):
    output = bundle.build_bundle(tmp_path / "pack.zip", ROOT)
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    for rel in bundle.BUNDLE_FILES:
        assert rel in names, rel
    assert {"ids_existants.txt", "LISEZ-MOI.txt"} <= names
    assert "docs/PROMPT_RECHERCHE_SOURIS_ATK.md" in names


def test_bundle_never_contains_a_secret_or_local_state(tmp_path):
    output = bundle.build_bundle(tmp_path / "pack.zip", ROOT)
    with zipfile.ZipFile(output) as archive:
        names = " ".join(archive.namelist())
    for forbidden in (".env", "state/", ".venv", "commercial_links.json", ".git/", "bot.log"):
        assert forbidden not in names, f"le pack ne doit pas contenir {forbidden}"


def test_bundle_lists_existing_ids_and_labels(tmp_path):
    output = bundle.build_bundle(tmp_path / "pack.zip", ROOT)
    with zipfile.ZipFile(output) as archive:
        listing = archive.read("ids_existants.txt").decode("utf-8")
    assert "scyrox_v6" in listing and "atk_a9_plus" in listing
    assert listing.count("\n") >= 20  # 18 souris + titre + ligne vide


def test_missing_file_is_reported(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "mouse_db.json").write_text("[]", encoding="utf-8")
    assert bundle.missing_files(tmp_path)  # la plupart des fichiers attendus sont absents
    with pytest.raises(FileNotFoundError):
        bundle.build_bundle(tmp_path / "pack.zip", tmp_path)
