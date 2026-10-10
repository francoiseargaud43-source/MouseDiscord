"""Commande !setup_finder : publication du message persistant et verrouillage du salon."""
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.mouse_finder import MouseFinderCog
from cogs import mouse_finder as module


def make_ctx():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.set_permissions = AsyncMock()
    channel.mention = "#mouse-finder"
    ctx = MagicMock()
    ctx.guild.default_role = "everyone"
    ctx.guild.get_channel = MagicMock(return_value=None)
    ctx.channel = channel
    ctx.send = AsyncMock()
    return ctx, channel


@pytest.mark.asyncio
async def test_setup_posts_banner_and_locks_channel(monkeypatch):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", True)
    cog = MouseFinderCog(MagicMock())
    ctx, channel = make_ctx()
    await cog.setup_finder.callback(cog, ctx, None)

    channel.set_permissions.assert_awaited_once()
    args, kwargs = channel.set_permissions.call_args
    assert args[0] == "everyone" and kwargs["send_messages"] is False
    send_kwargs = channel.send.call_args.kwargs
    assert send_kwargs["embed"].title == "🖱️ Mouse Shape Finder"
    assert len(send_kwargs["view"].children) == 1
    assert send_kwargs["view"].children[0].custom_id == "mouse_finder:start"
    ctx.send.assert_awaited()


@pytest.mark.asyncio
async def test_setup_targets_configured_channel(monkeypatch):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 123)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    cog = MouseFinderCog(MagicMock())
    ctx, own_channel = make_ctx()
    _, target = make_ctx()
    ctx.guild.get_channel = MagicMock(return_value=target)
    await cog.setup_finder.callback(cog, ctx, None)
    ctx.guild.get_channel.assert_called_once_with(123)
    target.send.assert_awaited_once()
    own_channel.send.assert_not_awaited()
    target.set_permissions.assert_not_awaited()


@pytest.mark.asyncio
async def test_setup_reports_missing_configured_channel(monkeypatch):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 123)
    cog = MouseFinderCog(MagicMock())
    ctx, _ = make_ctx()
    await cog.setup_finder.callback(cog, ctx, None)
    assert "introuvable" in ctx.send.call_args.args[0]
