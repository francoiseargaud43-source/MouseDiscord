"""Script de contrôle de déploiement : diagnostics attendus sur un projet factice."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_deployment", ROOT / "tools" / "check_deployment.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)


@pytest.fixture
def project(tmp_path):
    for rel in cd.REQUIRED_FILES:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("[]" if rel.endswith(".json") else "", encoding="utf-8")
    (tmp_path / "data" / "commercial_links.json").write_text("{}", encoding="utf-8")
    (tmp_path / "assets").mkdir(exist_ok=True)
    (tmp_path / "assets" / "images.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".env").write_text("DISCORD_TOKEN=secret-token-value\n", encoding="utf-8")
    return tmp_path


def levels(results):
    return [lvl for lvl, _ in results]


def test_complete_project_has_no_error(project):
    results = cd.check(project, {}, python_version=(3, 11))
    assert cd.ERROR not in levels(results)


def test_token_value_is_never_printed(project):
    text = " ".join(msg for _, msg in cd.check(project, {}, python_version=(3, 11)))
    assert "secret-token-value" not in text


def test_missing_token_is_blocking(project):
    (project / ".env").write_text("", encoding="utf-8")
    assert cd.ERROR in levels(cd.check(project, {}, python_version=(3, 11)))


def test_process_environment_token_is_accepted(project):
    (project / ".env").write_text("", encoding="utf-8")
    assert cd.ERROR not in levels(cd.check(project, {"DISCORD_TOKEN": "x"}, python_version=(3, 11)))


def test_old_python_is_blocking(project):
    assert cd.ERROR in levels(cd.check(project, {}, python_version=(3, 9)))


def test_missing_required_file_is_blocking(project):
    (project / "cogs" / "finder_flow.py").unlink()
    msgs = " ".join(m for _, m in cd.check(project, {}, python_version=(3, 11)))
    assert "cogs/finder_flow.py" in msgs


def test_invalid_integer_is_blocking(project):
    results = cd.check(project, {"FINDER_CHANNEL_ID": "abc"}, python_version=(3, 11))
    assert any(lvl == cd.ERROR and "FINDER_CHANNEL_ID" in msg for lvl, msg in results)


def test_example_domain_link_is_warning(project):
    (project / "data" / "commercial_links.json").write_text('{"scyrox_v8": "https://url.com/v8"}', encoding="utf-8")
    results = cd.check(project, {}, python_version=(3, 11))
    assert any(lvl == cd.WARN and "scyrox_v8" in msg for lvl, msg in results)
    assert cd.ERROR not in levels(results)


def test_empty_links_and_images_are_not_errors(project):
    assert cd.ERROR not in levels(cd.check(project, {}, python_version=(3, 11)))


# ---------------------------------------------------------------------------
# Illustrations : noms de fichiers résolus par IMAGES_BASE_URL
# ---------------------------------------------------------------------------
def test_bare_image_name_without_base_url_is_a_warning(project):
    (project / "assets" / "images.json").write_text('{"banner": "T08.png"}', encoding="utf-8")
    results = cd.check(project, {}, python_version=(3, 11))
    assert any(lvl == cd.WARN and "IMAGES_BASE_URL" in msg for lvl, msg in results)
    assert cd.ERROR not in levels(results)


def test_bare_image_name_with_base_url_is_resolved(project):
    (project / "assets" / "images.json").write_text('{"banner": "T08.png"}', encoding="utf-8")
    (project / "assets" / "illustrations").mkdir()
    (project / "assets" / "illustrations" / "T08.png").write_text("x", encoding="utf-8")
    results = cd.check(project, {"IMAGES_BASE_URL": "https://compte.alwaysdata.net/illustrations/"},
                       python_version=(3, 11))
    assert any(lvl == cd.OK and "images configurées : 1/1" in msg for lvl, msg in results)
    assert cd.ERROR not in levels(results)


def test_non_https_image_base_url_is_blocking(project):
    (project / "assets" / "images.json").write_text('{"banner": "T08.png"}', encoding="utf-8")
    results = cd.check(project, {"IMAGES_BASE_URL": "http://compte.alwaysdata.net/"}, python_version=(3, 11))
    assert any(lvl == cd.ERROR and "IMAGES_BASE_URL" in msg for lvl, msg in results)


def test_missing_illustration_on_disk_is_a_warning(project):
    (project / "assets" / "images.json").write_text('{"banner": "absent.png"}', encoding="utf-8")
    (project / "assets" / "illustrations").mkdir()          # copie de référence locale incomplète
    results = cd.check(project, {"IMAGES_BASE_URL": "https://x.test/"}, python_version=(3, 11))
    assert any(lvl == cd.WARN and "absent.png" in msg for lvl, msg in results)


def test_illustrations_published_elsewhere_without_local_copy_is_not_a_warning(project):
    """Cas d'un serveur où les images sont publiées dans l'espace web : aucune alerte inutile."""
    (project / "assets" / "images.json").write_text('{"banner": "absent.png"}', encoding="utf-8")
    results = cd.check(project, {"IMAGES_BASE_URL": "https://x.test/"}, python_version=(3, 11))
    assert not any("absent.png" in msg for _, msg in results)
    assert cd.ERROR not in levels(results)
