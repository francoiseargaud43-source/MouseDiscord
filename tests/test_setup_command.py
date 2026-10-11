"""Commande !setup_finder : publication, idempotence (pas de doublon), verrouillage du salon."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs import mouse_finder as module
from cogs.mouse_finder import MouseFinderCog, load_state


def make_ctx(channel_id: int = 111, sent_id: int = 555):
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = channel_id
    channel.send = AsyncMock(return_value=SimpleNamespace(id=sent_id))
    channel.set_permissions = AsyncMock()
    channel.fetch_message = AsyncMock()
    channel.mention = "#mouse-finder"
    ctx = MagicMock()
    ctx.guild.default_role = "everyone"
    ctx.guild.get_channel = MagicMock(return_value=None)
    ctx.channel = channel
    ctx.send = AsyncMock()
    return ctx, channel


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "state" / "finder_message.json"


@pytest.mark.asyncio
async def test_setup_posts_banner_locks_channel_and_saves_state(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", True)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx()
    await cog.setup_finder.callback(cog, ctx, None)

    channel.set_permissions.assert_awaited_once()
    args, kwargs = channel.set_permissions.call_args
    assert args[0] == "everyone" and kwargs["send_messages"] is False
    send_kwargs = channel.send.call_args.kwargs
    assert send_kwargs["embed"].title == "🖱️ AzeMouse — Mouse Shape Finder"
    assert send_kwargs["view"].children[0].custom_id == "mouse_finder:start"
    assert load_state(state_file) == {"channel_id": 111, "message_id": 555}


@pytest.mark.asyncio
async def test_repeated_setup_edits_existing_message_instead_of_posting(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx()
    await cog.setup_finder.callback(cog, ctx, None)      # 1re exécution : publication

    existing = MagicMock()
    existing.edit = AsyncMock()
    channel.fetch_message = AsyncMock(return_value=existing)
    await cog.setup_finder.callback(cog, ctx, None)      # 2e exécution : édition

    channel.send.assert_awaited_once()                    # un seul message publié au total
    channel.fetch_message.assert_awaited_once_with(555)
    existing.edit.assert_awaited_once()
    assert "mis à jour" in ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_deleted_previous_message_triggers_new_publication(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    state_file.parent.mkdir(parents=True)
    state_file.write_text('{"channel_id": 111, "message_id": 42}', encoding="utf-8")
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx(sent_id=777)
    channel.fetch_message = AsyncMock(side_effect=discord.NotFound(MagicMock(status=404), "unknown message"))
    await cog.setup_finder.callback(cog, ctx, None)
    channel.send.assert_awaited_once()
    assert load_state(state_file)["message_id"] == 777


@pytest.mark.asyncio
async def test_state_from_another_channel_is_ignored(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    state_file.parent.mkdir(parents=True)
    state_file.write_text('{"channel_id": 999, "message_id": 42}', encoding="utf-8")
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx(channel_id=111)
    await cog.setup_finder.callback(cog, ctx, None)
    channel.fetch_message.assert_not_awaited()
    channel.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_targets_configured_channel(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 123)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, own_channel = make_ctx()
    _, target = make_ctx(channel_id=123)
    ctx.guild.get_channel = MagicMock(return_value=target)
    await cog.setup_finder.callback(cog, ctx, None)
    ctx.guild.get_channel.assert_called_once_with(123)
    target.send.assert_awaited_once()
    own_channel.send.assert_not_awaited()
    target.set_permissions.assert_not_awaited()


@pytest.mark.asyncio
async def test_setup_reports_missing_configured_channel(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 123)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, _ = make_ctx()
    await cog.setup_finder.callback(cog, ctx, None)
    assert "introuvable" in ctx.send.call_args.args[0]


def test_corrupted_state_file_is_treated_as_absent(tmp_path):
    f = tmp_path / "s.json"
    f.write_text("{not json", encoding="utf-8")
    assert load_state(f) is None
    f.write_text('{"channel_id": "x", "message_id": 1}', encoding="utf-8")
    assert load_state(f) is None
