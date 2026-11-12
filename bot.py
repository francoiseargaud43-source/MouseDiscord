"""Point d'entrée : lance le bot Mouse Discord.

Deux garanties tenues ici, parce qu'elles dépendent du démarrage :

1. **Composants durables** — tous les menus des étapes sont enregistrés auprès de Discord au
   démarrage (``add_view``). Sans cet enregistrement, Discord continue d'afficher les menus mais le
   bot ne reconnaît plus les clics après un redémarrage : le membre voyait « interaction échouée »
   et devait recommencer son test (panne corrigée le 2026-10-12).
2. **Parcours conservés** — les questionnaires en cours sont enregistrés dans
   ``state/sessions.json`` (``SESSION_PERSIST``) : une mise à jour du bot ne fait plus perdre un
   parcours commencé. Les réponses d'un parcours terminé ne sont jamais écrites sur le disque.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

from utils.session import SessionStore

try:
    from config import (
        COMMAND_PREFIX,
        DISCORD_TOKEN,
        SESSION_PERSIST,
        SESSION_STATE_PATH,
        SESSION_TTL_SECONDS,
    )
except ValueError as exc:                       # ConfigError : variable d'environnement invalide
    logging.basicConfig(level=logging.ERROR, format="%(levelname)s : %(message)s")
    logging.getLogger("mouse_discord").error("Configuration invalide — %s", exc)
    sys.exit(1)

log = logging.getLogger("mouse_discord")

# Chemin du fichier d'état des parcours ; ``None`` = tout en mémoire (aucun parcours conservé).
DEFAULT_SESSIONS_PATH: Path | None = SESSION_STATE_PATH if SESSION_PERSIST else None


class MouseBot(commands.Bot):
    def __init__(self, sessions_path: Path | str | None = DEFAULT_SESSIONS_PATH) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True  # requis pour les commandes préfixées (!setup_finder)
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
        self.sessions = SessionStore(ttl_seconds=SESSION_TTL_SECONDS, path=sessions_path)

    async def setup_hook(self) -> None:
        from cogs.finder_flow import persistent_views

        # Composants DURABLES : à enregistrer AVANT tout envoi, et à chaque démarrage.
        views = persistent_views()
        for view in views:
            self.add_view(view)
        log.info("Composants durables enregistrés : %d (dont %d formulaires)",
                 len(views), sum(isinstance(v, discord.ui.Modal) for v in views))
        await self.load_extension("cogs.mouse_finder")
        if not self._purge_sessions.is_running():
            self._purge_sessions.start()

    @tasks.loop(minutes=5)
    async def _purge_sessions(self) -> None:
        """Supprime les parcours expirés : rien ne s'accumule en mémoire ni dans le fichier d'état."""
        removed = self.sessions.purge_expired()
        if removed:
            log.info("Parcours expirés supprimés : %d", removed)

    async def close(self) -> None:
        self._purge_sessions.cancel()
        self.sessions.save()          # dernier enregistrement : aucun parcours en cours perdu
        await super().close()

    async def on_ready(self) -> None:
        log.info("Connecté en tant que %s (id=%s)", self.user, self.user.id if self.user else "?")
        log.info(
            "Parcours en cours : %d (stockage : %s)",
            len(self.sessions),
            self.sessions.storage_path or "mémoire seulement",
        )

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Aucune erreur ne doit passer inaperçue : elle est tracée, le bot continue de tourner."""
        log.exception("Erreur non gérée dans l'événement %s", event_method)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Journalise seulement : aucune erreur de commande n'est publiée dans le salon.

        Les erreurs de ``!setup_finder`` sont déjà expliquées en privé par la cog. Cette règle évite
        qu'un message d'erreur puisse, un jour, révéler quelque chose dans un salon public.
        """
        if isinstance(error, commands.CommandNotFound):
            return          # commande inconnue : rien à signaler
        log.exception("Erreur de commande %s", ctx.command, exc_info=error)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    if not DISCORD_TOKEN:
        log.error("DISCORD_TOKEN est vide. Renseignez-le dans le fichier .env.")
        sys.exit(1)
    MouseBot().run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
