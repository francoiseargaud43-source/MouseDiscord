"""Comportements de `bot.py` : purge périodique, journalisation, démarrage.

Pourquoi ce fichier existe : la mesure de couverture du 2026-10-13 donnait `bot.py` à **67 %**, le
plus bas du dépôt. Les lignes non exercées n'étaient pas décoratives — purge des parcours expirés
(garantie de minimisation : rien ne s'accumule en mémoire ni dans le fichier d'état), erreurs non
gérées, erreurs de commande, démarrage sans jeton. Un test par garantie, chacune vérifiée par
mutation (voir `docs/audit/ROBUSTESSE_2026-10-12.md` §26.26).

Les lignes 32-35 (configuration invalide) et 108 (`__main__`) étaient « hors mesure en processus » : le
vrai démarrage est vérifié par `tests/test_config.py`, qui lance `bot.py` dans un sous-processus que la
mesure de couverture ne voit pas. Les deux cas sont donc **rejoués ici dans le processus de test**
(`runpy` + configuration relue de l'environnement) : mêmes garanties, et plus de ligne non mesurée — sauf
le vrai `MouseBot().run()`, qui exige un jeton Discord.
"""
from __future__ import annotations

import importlib
import logging
import os
import runpy
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from discord.ext import commands

import bot as bot_module
from bot import MouseBot
from utils.session import SessionStore

ROOT = Path(__file__).resolve().parents[1]


class FakeClock:
    """Horloge manuelle : l'expiration se teste sans attendre 30 minutes."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.mark.asyncio
async def test_la_purge_periodique_retire_les_parcours_expires_et_le_dit(caplog):
    """Toutes les 5 minutes : les parcours expirés disparaissent, et le journal dit combien."""
    parcours = MouseBot(sessions_path=None)
    horloge = FakeClock()
    parcours.sessions = SessionStore(ttl_seconds=60, clock=horloge)
    parcours.sessions.start(1)
    parcours.sessions.start(2)
    horloge.now = 61
    with caplog.at_level(logging.INFO):
        await parcours._purge_sessions.coro(parcours)       # corps de la tâche planifiée

    assert len(parcours.sessions) == 0
    assert "Parcours expirés supprimés : 2" in caplog.text


@pytest.mark.asyncio
async def test_la_purge_ne_dit_rien_quand_rien_n_a_expire(caplog):
    """Le journal ne se remplit pas toutes les 5 minutes : un passage sans rien à faire est muet."""
    parcours = MouseBot(sessions_path=None)
    parcours.sessions = SessionStore(ttl_seconds=600, clock=FakeClock())
    parcours.sessions.start(1)
    with caplog.at_level(logging.INFO):
        await parcours._purge_sessions.coro(parcours)

    assert len(parcours.sessions) == 1
    assert caplog.text == ""


@pytest.mark.asyncio
async def test_une_erreur_non_gerée_est_journalisee_sans_arreter_le_bot(caplog):
    """`on_error` : une erreur d'événement ne doit ni passer inaperçue, ni remonter."""
    parcours = MouseBot(sessions_path=None)
    with caplog.at_level(logging.ERROR):
        await parcours.on_error("on_message")               # ne lève pas

    assert "Erreur non gérée dans l'événement on_message" in caplog.text


@pytest.mark.asyncio
async def test_une_commande_inconnue_ne_remplit_pas_les_journaux(caplog):
    """Règle de confidentialité : une faute de frappe dans le salon ne produit NI message NI trace."""
    parcours = MouseBot(sessions_path=None)
    ctx = MagicMock()
    with caplog.at_level(logging.DEBUG):
        await parcours.on_command_error(ctx, commands.CommandNotFound("!nimporte"))

    assert caplog.text == ""


@pytest.mark.asyncio
async def test_une_vraie_erreur_de_commande_est_journalisee(caplog):
    """L'inverse : une erreur réelle laisse une trace exploitable, sans rien publier dans le salon."""
    parcours = MouseBot(sessions_path=None)
    ctx = MagicMock()
    ctx.command = "setup_finder"
    with caplog.at_level(logging.ERROR):
        await parcours.on_command_error(ctx, commands.CommandError("panne simulée"))

    assert "Erreur de commande setup_finder" in caplog.text


@pytest.mark.asyncio
async def test_on_ready_dit_qui_est_connecte_et_ou_sont_les_parcours(caplog, tmp_path):
    """Au démarrage, l'exploitant doit pouvoir lire l'état réel : compte et emplacement du stockage."""
    parcours = MouseBot(sessions_path=tmp_path / "sessions.json")
    with caplog.at_level(logging.INFO):
        await parcours.on_ready()

    assert "Connecté en tant que" in caplog.text
    assert "Parcours en cours : 0" in caplog.text
    assert str(tmp_path / "sessions.json") in caplog.text

    memoire = MouseBot(sessions_path=None)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        await memoire.on_ready()
    assert "mémoire seulement" in caplog.text


def test_le_demarrage_sans_jeton_s_arrete_avec_un_message(monkeypatch, caplog):
    """Un `.env` sans jeton ne doit pas lancer un bot muet : le démarrage s'arrête et dit quoi faire."""
    monkeypatch.setattr(bot_module, "DISCORD_TOKEN", "")
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as sortie:
        bot_module.main()

    assert sortie.value.code == 1
    assert "DISCORD_TOKEN est vide" in caplog.text


def test_le_demarrage_lance_le_bot_avec_le_jeton(monkeypatch):
    """Le jeton lu dans `.env` est celui passé à discord.py — et les journaux restent les nôtres."""
    monkeypatch.setattr(bot_module, "DISCORD_TOKEN", "jeton-de-test")
    instance = MagicMock()
    monkeypatch.setattr(bot_module, "MouseBot", MagicMock(return_value=instance))

    bot_module.main()

    instance.run.assert_called_once_with("jeton-de-test", log_handler=None)


@pytest.fixture
def configuration_rechargeable(monkeypatch):
    """Rend `config` relisible depuis l'environnement, et remet la configuration d'origine après.

    `bot.py` lit la configuration par `from config import ...` : le module gardé en cache par la session
    de tests porte les valeurs du tout premier import. Pour mesurer un vrai démarrage, il faut donc un
    module frais — relu avec l'environnement imposé par le test, puis restauré pour les tests suivants.
    """
    noms = ("DISCORD_TOKEN", "SESSION_TTL_SECONDS", "FINDER_CHANNEL_ID")
    original = {nom: os.environ.get(nom) for nom in noms}
    yield
    for nom, valeur in original.items():
        if valeur is None:
            monkeypatch.delenv(nom, raising=False)
        else:
            monkeypatch.setenv(nom, valeur)
    sys.modules.pop("config", None)
    importlib.import_module("config")


def test_lancer_le_fichier_comme_un_script_sans_jeton_dit_quoi_faire(monkeypatch, configuration_rechargeable, caplog):
    """`python bot.py` sans jeton : une phrase, code 1 — et la ligne `__main__` est ainsi mesurée."""
    monkeypatch.setenv("DISCORD_TOKEN", "")
    monkeypatch.delitem(sys.modules, "config", raising=False)

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as sortie:
        runpy.run_path(str(ROOT / "bot.py"), run_name="__main__")

    assert sortie.value.code == 1
    assert "DISCORD_TOKEN est vide" in caplog.text


def test_lancer_le_fichier_avec_une_configuration_invalide_refuse_de_demarrer(
        monkeypatch, configuration_rechargeable, caplog):
    """Une valeur hors bornes dans `.env` : le bot ne démarre pas « à moitié », il le dit et sort.

    C'est le chemin des lignes 32-35 de `bot.py` : la configuration lève pendant l'import, le point
    d'entrée traduit l'erreur en une phrase et sort en code 1 (aucune trace technique pour l'exploitant).
    """
    monkeypatch.setenv("DISCORD_TOKEN", "jeton-de-test")
    monkeypatch.setenv("SESSION_TTL_SECONDS", "0")
    monkeypatch.delitem(sys.modules, "config", raising=False)

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as sortie:
        runpy.run_path(str(ROOT / "bot.py"), run_name="__main__")

    assert sortie.value.code == 1
    assert "Configuration invalide" in caplog.text
    assert "SESSION_TTL_SECONDS doit être supérieur à 0" in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
async def test_setup_hook_ne_demarre_pas_deux_fois_la_purge_periodique(monkeypatch):
    """Démarrage appelé deux fois dans le même processus : la purge ne repart pas.

    Branche jamais prise avant cette passe (`if not self._purge_sessions.is_running()` — cas « elle
    tourne déjà »). Sans cette garde, `tasks.loop.start()` lève « Task is already running » et l'erreur
    remonterait dans le démarrage du bot — au pire moment, puisque c'est la reprise après incident.
    """
    parcours = MouseBot(sessions_path=None)
    monkeypatch.setattr(MouseBot, "load_extension", AsyncMock())   # déjà chargée au premier passage

    try:
        await parcours.setup_hook()
        assert parcours._purge_sessions.is_running()

        await parcours.setup_hook()          # ne lève pas : la purge n'est pas relancée
        assert parcours._purge_sessions.is_running()
    finally:
        parcours._purge_sessions.cancel()
        await parcours.close()

