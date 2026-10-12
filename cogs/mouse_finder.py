"""Commande d'administration !setup_finder : publie OU met à jour le message persistant d'accueil.

Idempotence : l'identifiant du message publié est mémorisé (FINDER_STATE_PATH). Une nouvelle
exécution dans le même salon ÉDITE ce message au lieu d'en publier un second.
Le salon est verrouillé en lecture seule pour @everyone uniquement au niveau du salon
(aucune permission serveur n'est modifiée).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands

from config import FINDER_CHANNEL_ID, FINDER_STATE_PATH, LOCK_FINDER_CHANNEL
from cogs.finder_flow import StartView, banner_embed

log = logging.getLogger(__name__)


def load_state(path: Path) -> dict | None:
    try:
        with Path(path).open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if isinstance(data, dict) and isinstance(data.get("channel_id"), int) and isinstance(data.get("message_id"), int):
        return data
    return None


def save_state(path: Path, channel_id: int, message_id: int) -> None:
    """Écriture atomique (fichier temporaire puis renommage) : jamais de fichier à moitié écrit,
    ce qui publierait un second message d'accueil au redémarrage suivant."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps({"channel_id": channel_id, "message_id": message_id}), encoding="utf-8")
    os.replace(temporary, path)


class MouseFinderCog(commands.Cog, name="Mouse Finder"):
    def __init__(self, bot: commands.Bot, state_path: Path = FINDER_STATE_PATH) -> None:
        self.bot = bot
        self.state_path = Path(state_path)

    def _target_channel(self, ctx: commands.Context, explicit: discord.TextChannel | None):
        if explicit is not None:
            return explicit
        if FINDER_CHANNEL_ID:
            return ctx.guild.get_channel(FINDER_CHANNEL_ID)
        return ctx.channel

    async def _edit_existing(self, target: discord.TextChannel) -> bool:
        """Édite le message déjà publié dans ce salon. False si introuvable (supprimé, autre salon…)."""
        state = load_state(self.state_path)
        if not state or state["channel_id"] != target.id:
            return False
        try:
            message = await target.fetch_message(state["message_id"])
            await message.edit(embed=banner_embed(), view=StartView())
            return True
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
            log.info("Message Finder précédent non modifiable (%s) : publication d'un nouveau message.", exc)
            return False

    @commands.command(name="setup_finder")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def setup_finder(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        """Publie (ou met à jour) le message Mouse Shape Finder dans le salon cible."""
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

        if await self._edit_existing(target):
            message = f"♻️ Message existant mis à jour dans {target.mention} (aucun doublon publié)."
        else:
            try:
                sent = await target.send(embed=banner_embed(), view=StartView())
            except discord.Forbidden:
                await ctx.send(f"❌ Le bot ne peut pas écrire dans {target.mention}.")
                return
            save_state(self.state_path, target.id, sent.id)
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
