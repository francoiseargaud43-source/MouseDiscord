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
