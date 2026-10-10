"""Commande d'administration !setup_finder : publie le message persistant d'accueil."""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from config import FINDER_CHANNEL_ID, LOCK_FINDER_CHANNEL
from cogs.finder_flow import StartView, banner_embed

log = logging.getLogger(__name__)


class MouseFinderCog(commands.Cog, name="Mouse Finder"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _target_channel(self, ctx: commands.Context, explicit: discord.TextChannel | None):
        if explicit is not None:
            return explicit
        if FINDER_CHANNEL_ID:
            channel = ctx.guild.get_channel(FINDER_CHANNEL_ID)
            if channel is None:
                return None
            return channel
        return ctx.channel

    @commands.command(name="setup_finder")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def setup_finder(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        """Publie le message Mouse Shape Finder dans le salon cible (FINDER_CHANNEL_ID ou salon courant)."""
        target = self._target_channel(ctx, channel)
        if target is None:
            await ctx.send("❌ Le salon défini par `FINDER_CHANNEL_ID` est introuvable sur ce serveur.")
            return
        if not isinstance(target, discord.TextChannel):
            await ctx.send("❌ Le salon cible doit être un salon textuel.")
            return

        notes: list[str] = []
        if LOCK_FINDER_CHANNEL:
            try:
                await target.set_permissions(
                    ctx.guild.default_role,
                    send_messages=False,
                    add_reactions=False,
                    reason="Mouse Shape Finder : salon en lecture seule",
                )
            except discord.Forbidden:
                notes.append("⚠️ Impossible de verrouiller le salon (permission « Gérer les permissions » manquante).")

        try:
            await target.send(embed=banner_embed(), view=StartView())
        except discord.Forbidden:
            await ctx.send(f"❌ Le bot ne peut pas écrire dans {target.mention}.")
            return

        message = f"✅ Message de départ publié dans {target.mention}."
        if notes:
            message += "\n" + "\n".join(notes)
        await ctx.send(message)

    @setup_finder.error
    async def setup_finder_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("⛔ Cette commande est réservée aux membres ayant la permission « Gérer le serveur ».")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Cette commande doit être utilisée sur un serveur.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Salon invalide. Usage : `!setup_finder` ou `!setup_finder #salon`.")
        else:
            log.exception("Erreur dans !setup_finder", exc_info=error)
            await ctx.send("⚠️ Erreur inattendue lors de la publication du message.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MouseFinderCog(bot))
