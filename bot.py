"""Point d'entrée : lance le bot Mouse Discord."""
from __future__ import annotations

import logging
import sys

import discord
from discord.ext import commands

from config import COMMAND_PREFIX, DISCORD_TOKEN, SESSION_TTL_SECONDS
from utils.session import SessionStore

log = logging.getLogger("mouse_discord")


class MouseBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True  # requis pour les commandes préfixées (!setup_finder)
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
        self.sessions = SessionStore(ttl_seconds=SESSION_TTL_SECONDS)

    async def setup_hook(self) -> None:
        from cogs.finder_flow import ResultsView, StartView

        # Vues persistantes : elles répondent même après un redémarrage du bot.
        # StartView : le bouton du panneau public. ResultsView.persistent() : « Fermer » et
        # « Refaire le test » d'un résultat déjà affiché (le lien d'achat, lui, ne dépend pas du bot).
        self.add_view(StartView())
        self.add_view(ResultsView.persistent())
        await self.load_extension("cogs.mouse_finder")

    async def on_ready(self) -> None:
        log.info("Connecté en tant que %s (id=%s)", self.user, self.user.id if self.user else "?")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    if not DISCORD_TOKEN:
        log.error("DISCORD_TOKEN est vide. Renseignez-le dans le fichier .env.")
        sys.exit(1)
    MouseBot().run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
