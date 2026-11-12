"""Configuration : lecture de .env indépendante du répertoire courant, erreurs explicites."""
import importlib
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


@pytest.mark.parametrize("variable, valeur, fragment", [
    ("SESSION_TTL_SECONDS", "0", "SESSION_TTL_SECONDS doit être supérieur à 0"),
    ("FINDER_CHANNEL_ID", "-1", "FINDER_CHANNEL_ID doit être un identifiant positif"),
])
def test_une_valeur_hors_bornes_refuse_le_chargement(monkeypatch, variable, valeur, fragment):
    """Les deux bornes de la configuration sont refusées **au chargement**, pas au premier usage.

    Le sous-processus (ci-dessus) vérifie le vrai démarrage ; ici, le module est rechargé **dans le
    processus de test** — c'est ce chemin que la mesure de couverture voit, et c'est aussi la garantie
    qu'aucun code du bot ne tourne avec une valeur incohérente (durée de vie nulle : chaque parcours
    expirerait aussitôt ; salon négatif : `!setup_finder` viserait un salon inexistant).
    """
    monkeypatch.setenv(variable, valeur)
    monkeypatch.delitem(sys.modules, "config", raising=False)
    try:
        with pytest.raises(ValueError) as erreur:
            importlib.import_module("config")
    finally:
        # La configuration saine reprend sa place pour les tests suivants, quel que soit le résultat :
        # la variable fautive est retirée AVANT de recharger (sinon le rechargement échoue à son tour),
        # et `monkeypatch` remettra l'environnement d'origine à la fin du test.
        monkeypatch.delenv(variable)
        sys.modules.pop("config", None)
        importlib.import_module("config")
    assert type(erreur.value).__name__ == "ConfigError"
    assert fragment in str(erreur.value)
    assert "Corrigez" in str(erreur.value)


# ---------------------------------------------------------------------------
# 53e passe (2026-10-13) : le fichier d'exemple ne peut pas oublier une variable
# ---------------------------------------------------------------------------
def _variables_lues_par_config() -> set[str]:
    """Les noms de variables d'environnement que `config.py` lit, relevés dans le source."""
    import ast

    arbre = ast.parse((ROOT / "config.py").read_text(encoding="utf-8"))
    noms = set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call) or not noeud.args:
            continue
        fonction = noeud.func
        # os.getenv("X") et les aides maison _env_int("X") / _env_bool("X").
        appelee = (fonction.attr if isinstance(fonction, ast.Attribute)
                   else fonction.id if isinstance(fonction, ast.Name) else None)
        if appelee not in {"getenv", "_env_int", "_env_bool"}:
            continue
        premier = noeud.args[0]
        if isinstance(premier, ast.Constant) and isinstance(premier.value, str):
            noms.add(premier.value)
    return noms


def test_le_fichier_d_exemple_documente_toutes_les_variables_de_configuration():
    """`.env.example` est la seule documentation des réglages : une variable absente y est invisible.

    Défaut trouvé le 2026-10-13 (53e passe) : le message d'erreur de `FINDER_CHANNEL_ID` avait été
    corrigé (il dit maintenant que **0 = le salon où la commande est tapée**), mais le fichier d'exemple
    ne le disait toujours pas — l'exploitant qui copie `.env.example` n'avait que le commentaire muet.
    """
    exemple = (ROOT / ".env.example").read_text(encoding="utf-8")
    lues = _variables_lues_par_config()
    assert lues >= {"DISCORD_TOKEN", "FINDER_CHANNEL_ID", "SESSION_TTL_SECONDS", "IMAGES_BASE_URL"}

    oubliees = sorted(nom for nom in lues if f"{nom}=" not in exemple)
    assert oubliees == [], f"variables lues par config.py mais absentes de .env.example : {oubliees}"

    # Chaque variable porte un commentaire juste au-dessus : le fichier explique, il ne liste pas.
    lignes = exemple.splitlines()
    sans_commentaire = [
        nom for nom in sorted(lues) if not lignes[_position(lignes, nom) - 1].startswith("#")
    ]
    assert sans_commentaire == [], f"variables sans commentaire dans .env.example : {sans_commentaire}"

    # Le rappel utile ajouté le 2026-10-13 : sans lui, la phrase de l'erreur est la seule à le dire.
    assert "0 = le salon où la commande est tapée" in exemple


def _position(lignes: list[str], nom: str) -> int:
    return next(i for i, ligne in enumerate(lignes) if ligne.startswith(f"{nom}="))
