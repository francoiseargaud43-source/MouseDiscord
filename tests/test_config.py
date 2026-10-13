"""Configuration : lecture de .env indépendante du répertoire courant, erreurs explicites."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

import config

ROOT = Path(__file__).resolve().parents[1]


def _run_config(cwd: Path, extra_env: dict[str, str]) -> str:
    env = {k: v for k, v in os.environ.items() if k not in {"DISCORD_TOKEN", "FINDER_CHANNEL_ID", "SESSION_TTL_SECONDS"}}
    env.update(extra_env)
    code = (
        "import sys; sys.path.insert(0, %r); import config;"
        "print(config.MOUSE_DB_PATH); print(config.DISCORD_TOKEN == 'TOKEN_TEST');"
        "print(config.SESSION_TTL_SECONDS)" % str(ROOT)
    )
    return subprocess.run(
        [sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, check=True
    ).stdout


def test_paths_are_anchored_to_project_not_working_directory(tmp_path):
    out = _run_config(tmp_path, {"DISCORD_TOKEN": "TOKEN_TEST"})
    assert out.splitlines()[0] == str(ROOT / "data" / "mouse_db.json")


def test_env_file_path_is_next_to_config_module():
    assert config.ENV_FILE == ROOT / ".env"


def test_empty_optional_integers_fall_back_to_defaults(tmp_path):
    out = _run_config(tmp_path, {"DISCORD_TOKEN": "TOKEN_TEST", "SESSION_TTL_SECONDS": ""})
    assert out.splitlines()[2] == "1800"


def test_invalid_integer_gives_explicit_error(monkeypatch):
    monkeypatch.setenv("SESSION_TTL_SECONDS", "trente")
    with pytest.raises(config.ConfigError, match="SESSION_TTL_SECONDS doit être un nombre entier"):
        config._env_int("SESSION_TTL_SECONDS", 1800)


def test_integer_parsing_accepts_valid_values(monkeypatch):
    monkeypatch.setenv("FINDER_CHANNEL_ID", " 123456789 ")
    assert config._env_int("FINDER_CHANNEL_ID", 0) == 123456789
    monkeypatch.delenv("FINDER_CHANNEL_ID")
    assert config._env_int("FINDER_CHANNEL_ID", 0) == 0


# --- Chasse aux bugs du 2026-10-12 : une valeur qui casse le parcours est refusée au démarrage ---
def _run_config_expect_failure(extra_env: dict[str, str]):
    env = {k: v for k, v in os.environ.items()
           if k not in {"DISCORD_TOKEN", "FINDER_CHANNEL_ID", "SESSION_TTL_SECONDS"}}
    env.update(extra_env)
    code = f"import sys; sys.path.insert(0, {str(ROOT)!r}); import config"
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                          capture_output=True, text=True)


@pytest.mark.parametrize("value", ["0", "-1", "-1800"])
def test_a_non_positive_session_ttl_is_refused_with_a_clear_message(value):
    """Un TTL nul ferait répondre « ce parcours a expiré » à chaque clic : la cause est dite."""
    proc = _run_config_expect_failure({"DISCORD_TOKEN": "T", "SESSION_TTL_SECONDS": value})
    assert proc.returncode != 0
    assert "SESSION_TTL_SECONDS doit être supérieur à 0" in proc.stderr


def test_a_negative_finder_channel_id_is_refused():
    proc = _run_config_expect_failure({"DISCORD_TOKEN": "T", "FINDER_CHANNEL_ID": "-12"})
    assert proc.returncode != 0
    assert "FINDER_CHANNEL_ID doit être un identifiant positif" in proc.stderr


# --- Chasse aux micro-bugs du 2026-10-13 : une faute de frappe ne doit pas désactiver en silence ---
@pytest.mark.parametrize("valeur", ["1", "true", "TRUE", " on ", "oui", "vrai"])
def test_les_orthographes_vraies_sont_acceptees(monkeypatch, valeur):
    monkeypatch.setenv("LOCK_FINDER_CHANNEL", valeur)
    assert config._env_bool("LOCK_FINDER_CHANNEL", False) is True


@pytest.mark.parametrize("valeur", ["0", "false", "False", "off", "non", "faux"])
def test_les_orthographes_fausses_sont_acceptees(monkeypatch, valeur):
    monkeypatch.setenv("LOCK_FINDER_CHANNEL", valeur)
    assert config._env_bool("LOCK_FINDER_CHANNEL", True) is False


def test_une_valeur_booléenne_inconnue_est_refusee(monkeypatch):
    """Trouvé le 2026-10-13 : `SESSION_PERSIST=ture` (faute de frappe) valait « faux » **en silence**.

    La conservation des parcours était donc désactivée sans un mot, alors que le fichier `.env` du
    serveur annonçait le contraire. Un entier illisible était déjà refusé clairement ; une valeur
    booléenne inconnue l'est maintenant aussi, avec la liste des orthographes acceptées.
    """
    monkeypatch.setenv("SESSION_PERSIST", "ture")
    with pytest.raises(config.ConfigError, match="SESSION_PERSIST doit valoir vrai ou faux"):
        config._env_bool("SESSION_PERSIST", True)


def test_une_valeur_booléenne_inconnue_bloque_le_demarrage_avec_un_message_lisible():
    """Le démarrage s'arrête et le message dit quoi corriger (bot.py le traduit sans trace technique)."""
    proc = _run_config_expect_failure({"DISCORD_TOKEN": "T", "SESSION_PERSIST": "peut-être"})
    assert proc.returncode != 0
    assert "SESSION_PERSIST doit valoir vrai ou faux" in proc.stderr
    assert "Corrigez-la dans le fichier" in proc.stderr


def test_the_bot_turns_a_broken_configuration_into_a_clear_message():
    """bot.py doit quitter proprement (message lisible), pas dérouler une trace technique."""
    env = {k: v for k, v in os.environ.items()
           if k not in {"DISCORD_TOKEN", "FINDER_CHANNEL_ID", "SESSION_TTL_SECONDS"}}
    env.update({"DISCORD_TOKEN": "T", "SESSION_TTL_SECONDS": "0"})
    proc = subprocess.run([sys.executable, str(ROOT / "bot.py")], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    assert proc.returncode == 1
    assert "Configuration invalide" in proc.stderr
    assert "SESSION_TTL_SECONDS doit être supérieur à 0" in proc.stderr
    assert "Traceback" not in proc.stderr
