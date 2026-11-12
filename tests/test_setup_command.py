"""Commande !setup_finder : publication, idempotence (pas de doublon), verrouillage du salon."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord.ext import commands

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


def test_un_etat_illisible_est_traite_comme_absent(tmp_path):
    """Trouvé le 2026-10-13 : seul le JSON invalide était prévu.

    Un **dossier** à la place du fichier d'état, ou un fichier en **octets non UTF-8**, faisait
    remonter l'exception : `!setup_finder` répondait alors « ⚠️ Erreur inattendue » et l'administrateur
    ne pouvait plus publier le message, alors que la bonne réponse est « aucun état » (publier un
    message neuf, comme pour un fichier absent). Même règle que le fichier de sessions.
    """
    dossier = tmp_path / "etat"
    dossier.mkdir()
    assert load_state(dossier) is None                       # dossier à la place du fichier

    binaire = tmp_path / "binaire.json"
    binaire.write_bytes(b'{"channel_id": 1, "message_id": 2, "note": "\xff\xfe caf\xe9"}')
    assert load_state(binaire) is None                       # octets non UTF-8

    for contenu in ("null", "[1, 2, 3]", '"texte"', "12"):
        f = tmp_path / "autre.json"
        f.write_text(contenu, encoding="utf-8")
        assert load_state(f) is None, contenu                # JSON valide mais pas un objet


@pytest.mark.asyncio
async def test_setup_publie_meme_avec_un_etat_illisible(monkeypatch, tmp_path):
    """Un état illisible ne doit pas empêcher la publication — et doit être réécrit proprement."""
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    etat = tmp_path / "state" / "finder_message.json"
    etat.parent.mkdir(parents=True)
    etat.write_bytes(b"\xff\xfe pas du JSON")
    cog = MouseFinderCog(MagicMock(), state_path=etat)
    ctx, channel = make_ctx(sent_id=909)
    await cog.setup_finder.callback(cog, ctx, None)

    channel.send.assert_awaited_once()
    assert "publié" in ctx.send.call_args.args[0]
    assert load_state(etat) == {"channel_id": 111, "message_id": 909}


@pytest.mark.asyncio
async def test_identifiant_non_enregistrable_ne_fait_pas_croire_a_un_echec(monkeypatch, state_file):
    """Trouvé le 2026-10-13 : le message est publié **avant** l'enregistrement de son identifiant.

    Si l'écriture échoue, répondre « ⚠️ Erreur inattendue » est faux et pousse l'administrateur à
    relancer la commande — donc à publier un doublon. La réponse dit maintenant : publié, mais non
    mémorisé, et ce que cela implique.
    """
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)

    def refuse(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(module, "save_state", refuse)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx()
    await cog.setup_finder.callback(cog, ctx, None)

    channel.send.assert_awaited_once()
    reponse = ctx.send.call_args.args[0]
    assert "publié" in reponse and "second message" in reponse
    assert "Erreur inattendue" not in reponse

# ---------------------------------------------------------------------------
# Chemins d'échec vus par l'administrateur : aucun n'était exercé (couverture 82 %)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_un_salon_texte_explicite_prime_sur_la_configuration(monkeypatch, state_file):
    """`!setup_finder #salon` : l'argument explicite était le SEUL chemin non testé de la commande."""
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 123)      # configuration : un autre salon
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, own_channel = make_ctx()
    _, explicite = make_ctx(channel_id=777)
    ctx.guild.get_channel = MagicMock(return_value=None)       # le salon configuré n'existe pas

    await cog.setup_finder.callback(cog, ctx, explicite)

    ctx.guild.get_channel.assert_not_called()                  # l'argument l'emporte
    explicite.send.assert_awaited_once()
    own_channel.send.assert_not_awaited()
    assert load_state(state_file) == {"channel_id": 777, "message_id": 555}


@pytest.mark.asyncio
async def test_un_salon_non_textuel_est_refuse_sans_rien_publier(monkeypatch, state_file):
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, _ = make_ctx()
    vocal = MagicMock(spec=discord.VoiceChannel)

    await cog.setup_finder.callback(cog, ctx, vocal)

    assert "doit être un salon textuel" in ctx.send.call_args.args[0]
    vocal.send.assert_not_called()
    vocal.set_permissions.assert_not_called()
    assert not state_file.exists()


@pytest.mark.asyncio
async def test_verrouillage_impossible_est_signale_mais_n_empeche_pas_la_publication(monkeypatch, state_file):
    """Permission « Gérer les permissions » manquante : le salon reste ouvert, et c'est DIT."""
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", True)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx()
    channel.set_permissions = AsyncMock(
        side_effect=discord.Forbidden(MagicMock(status=403), "missing permissions"))

    await cog.setup_finder.callback(cog, ctx, None)

    channel.send.assert_awaited_once()                         # le message est publié quand même
    reponse = ctx.send.call_args.args[0]
    assert "Impossible de verrouiller le salon" in reponse
    assert "publié" in reponse


@pytest.mark.asyncio
async def test_bot_sans_permission_d_ecriture_est_dit_clairement(monkeypatch, state_file):
    """Sans droit d'écriture, l'administrateur lit la cause exacte : aucun état n'est enregistré."""
    monkeypatch.setattr(module, "FINDER_CHANNEL_ID", 0)
    monkeypatch.setattr(module, "LOCK_FINDER_CHANNEL", False)
    cog = MouseFinderCog(MagicMock(), state_path=state_file)
    ctx, channel = make_ctx()
    channel.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "cannot send"))

    await cog.setup_finder.callback(cog, ctx, None)

    assert "ne peut pas écrire dans" in ctx.send.call_args.args[0]
    assert not state_file.exists()
    assert "publié" not in ctx.send.call_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("erreur, attendu", [
    (commands.MissingPermissions(["manage_guild"]), "réservée aux membres ayant la permission"),
    (commands.NoPrivateMessage(), "doit être utilisée sur un serveur"),
    (commands.BadArgument("salon"), "Salon invalide"),
    (commands.CommandError("panne"), "Erreur inattendue lors de la publication"),
])
async def test_chaque_erreur_de_la_commande_a_son_message(erreur, attendu):
    """Les quatre branches du gestionnaire d'erreur répondaient sans être testées."""
    cog = MouseFinderCog(MagicMock(), state_path=Path("/tmp") / "jamais_ecrit.json")
    ctx = MagicMock()
    ctx.send = AsyncMock()
    await cog.setup_finder_error(ctx, erreur)
    assert attendu in ctx.send.call_args.args[0]
