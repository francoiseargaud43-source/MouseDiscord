"""Flux Discord du Mouse Shape Finder : message persistant, étapes éphémères, modals.

Navigation : chaque étape remplace le message éphémère existant via
``interaction.response.edit_message()`` (aucun nouveau message dans le salon).
L'état de l'utilisateur vit dans ``bot.sessions`` (session_id = user_id).

Parcours : grip -> mesures de la main -> budget (3 étapes).
Le muscle thénar a été retiré du parcours (il n'entrait dans aucun calcul).
"""
from __future__ import annotations

import logging

import discord

from config import COMMERCIAL_LINKS_PATH, IMAGES_CONFIG_PATH, MOUSE_DB_PATH
from utils.assets import load_image_urls
from utils.catalog import load_catalog, load_commercial_links
from utils.matcher import MAX_SCORE, MouseScore, compatibility_percent, evaluate_mouse
from utils.models import BUDGET_LABELS, GRIP_LABELS, BudgetMode, Grip, HandMeasure
from utils.selection import Selection, select
from utils.session import FinderSession
from utils.validation import InputError, parse_budget, parse_hand_measures

log = logging.getLogger(__name__)

VIEW_TIMEOUT = 900
START_CUSTOM_ID = "mouse_finder:start"
COLOR = discord.Color.from_rgb(88, 101, 242)
SCORE_DISCLAIMER = (
    "Score géométrique provisoire : ce n'est ni une probabilité d'achat, ni une validation biomécanique. "
    "Largeur de prise estimée (coque − 3 mm) tant qu'elle n'est pas mesurée."
)
MAX_PENDING_SHOWN = 5

GRIP_OPTIONS = (
    (Grip.PALM, "Palm Grip", "Paume entièrement posée sur la coque"),
    (Grip.CLAW, "Claw Grip", "Doigts arqués, contact par les pulpes"),
    (Grip.FINGERTIP, "Fingertip Grip", "Contact uniquement par le bout des doigts"),
)
BUDGET_OPTIONS = (
    (BudgetMode.ECONOMIQUE, "Économique", "Petit budget, meilleur rapport prix"),
    (BudgetMode.QUALITE_PRIX, "Rapport Qualité/Prix", "Bon compromis performance / prix"),
    (BudgetMode.HAUT_DE_GAMME, "Haut de Gamme (Max Perf)", "Performances documentées les plus élevées"),
    (BudgetMode.CUSTOM, "Budget Personnalisé Maximal", "Saisir un prix maximum en €"),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _send_ephemeral(interaction: discord.Interaction, content: str) -> None:
    """Envoie un message éphémère, en tenant compte de l'état de la réponse.

    Ne lève jamais d'exception : si l'interaction a expiré, l'erreur est journalisée seulement.
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)
    except discord.HTTPException as exc:
        log.warning("Impossible de répondre à l'interaction (expirée ?) : %s", exc)


async def require_session(interaction: discord.Interaction) -> FinderSession | None:
    """Retourne la session active ou informe l'utilisateur qu'elle a expiré."""
    session = interaction.client.sessions.get(interaction.user.id)
    if session is None:
        await _send_ephemeral(
            interaction,
            "⏱️ Votre session a expiré. Cliquez à nouveau sur **Start Mouse Shape Finder**.",
        )
    return session


def _image(embed: discord.Embed, key: str) -> discord.Embed:
    url = load_image_urls(IMAGES_CONFIG_PATH).get(key)
    if url:
        embed.set_image(url=url)
    return embed


def _recap(session: FinderSession) -> str:
    parts = []
    if session.grip:
        parts.append(f"✋ Grip : **{GRIP_LABELS[session.grip]}**")
    if session.hand_length_mm and session.hand_width_mm:
        parts.append(f"📏 Main : **{session.hand_length_mm:g} × {session.hand_width_mm:g} mm**")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Embeds
# ---------------------------------------------------------------------------
def banner_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🖱️ Mouse Shape Finder",
        description=(
            "Trouvez la souris dont la géométrie épouse **votre** main.\n\n"
            "Cliquez sur le bouton ci-dessous : trois questions rapides "
            "(grip, mesures de la main, budget) et une recommandation personnalisée.\n\n"
            "*Les réponses sont privées : seul vous voyez le résultat.*"
        ),
        color=COLOR,
    )
    return _image(embed, "banner")


def grip_step_embed() -> discord.Embed:
    description = "\n".join(f"**{label}** : {desc}" for _, label, desc in GRIP_OPTIONS)
    embed = discord.Embed(
        title="Étape 1/3 — Votre style de prise",
        description=f"Quel grip utilisez-vous le plus souvent ?\n\n{description}",
        color=COLOR,
    )
    return _image(embed, "step1_grip")


def measure_step_embed(session: FinderSession) -> discord.Embed:
    embed = discord.Embed(
        title="Étape 2/3 — Mesure de votre main",
        description=(
            f"{_recap(session)}\n\n"
            "Avec une règle, mesurez :\n"
            "• **Longueur** : du pli du poignet jusqu'au bout du majeur.\n"
            "• **Largeur** : au niveau des articulations, **sans le pouce**.\n\n"
            "Cliquez sur **Saisir mes mesures** quand vous êtes prêt."
        ),
        color=COLOR,
    )
    return _image(embed, "step2_measure")


def budget_step_embed(session: FinderSession) -> discord.Embed:
    embed = discord.Embed(
        title="Étape 3/3 — Budget et gamme",
        description=f"{_recap(session)}\n\nChoisissez votre gamme de prix.",
        color=COLOR,
    )
    return _image(embed, "step3_budget")


def _budget_text(session: FinderSession) -> str:
    if session.budget_mode is BudgetMode.CUSTOM and session.max_budget_eur is not None:
        return f"Budget max {session.max_budget_eur:.2f} €"
    if session.budget_mode is not None:
        return BUDGET_LABELS[session.budget_mode]
    return "—"


def _price_text(score: MouseScore) -> str:
    mouse = score.mouse
    if mouse.price_eur is None:
        return "prix non renseigné"
    text = f"{mouse.price_eur:.2f} €"
    if mouse.price_status != "verified":
        text += " (prix non vérifié)"
    return text


def _score_text(score: MouseScore) -> str:
    pct = compatibility_percent(score)
    return f"Score de correspondance : **{score.total}/{MAX_SCORE}** — **{pct} %** du maximum théorique du barème"


def _candidate_text(score: MouseScore) -> str:
    lines = [
        f"**{score.mouse.label}** — {_price_text(score)}",
        _score_text(score),
        f"Confiance des données : {score.confidence}",
    ]
    lines += [f"• {line}" for line in score.details]
    if score.mouse.fit_rationale:
        lines.append(f"💬 {score.mouse.fit_rationale}")
    return "\n".join(lines)[:1024]


def _pending_text(pending: tuple[MouseScore, ...]) -> str:
    lines = []
    for item in pending[:MAX_PENDING_SHOWN]:
        partial = f" — score partiel {item.total}/{item.computable_max} pts (non classable)" if item.computable_max else ""
        lines.append(f"• **{item.mouse.label}** : {', '.join(item.missing)}{partial}")
    if len(pending) > MAX_PENDING_SHOWN:
        lines.append(f"… et {len(pending) - MAX_PENDING_SHOWN} autre(s).")
    return "\n".join(lines)[:1024]


def results_embed(session: FinderSession, selection: Selection) -> discord.Embed:
    embed = discord.Embed(title="🎯 Résultat Mouse Shape Finder", color=COLOR)
    embed.description = f"{_recap(session)}\n🎚️ Gamme : **{_budget_text(session)}**"

    if not selection.ranked:
        embed.add_field(
            name="Aucun match classable",
            value=(
                "Aucune souris ne peut être classée avec les données vérifiées pour ces critères. "
                "Essayez une autre gamme ou un budget plus élevé."
            ),
            inline=False,
        )
    else:
        top = selection.ranked[0]
        embed.add_field(name="🥇 Le Match Idéal", value=_candidate_text(top), inline=False)
        if len(selection.ranked) > 1:
            embed.add_field(name="🥈 L'Alternative", value=_candidate_text(selection.ranked[1]), inline=False)
        else:
            embed.add_field(name="🥈 L'Alternative", value="Aucune autre souris ne correspond à ces critères.", inline=False)
        embed.add_field(name="🧭 Pourquoi ce choix ?", value=selection.explanation[:1024], inline=False)

    if selection.pending:
        embed.add_field(
            name="⏳ À vérifier (non classées)",
            value=_pending_text(selection.pending),
            inline=False,
        )
    embed.set_footer(text=SCORE_DISCLAIMER)
    return embed


def expired_embed() -> discord.Embed:
    return discord.Embed(
        title="⏱️ Session expirée",
        description="Cliquez sur **Start Mouse Shape Finder** dans le salon pour recommencer.",
        color=discord.Color.orange(),
    )


# ---------------------------------------------------------------------------
# Calcul
# ---------------------------------------------------------------------------
def compute_selection(session: FinderSession) -> Selection:
    if session.grip is None or session.hand_length_mm is None or session.hand_width_mm is None:
        raise ValueError("Session incomplète : grip ou mesures manquants.")
    if session.budget_mode is None:
        raise ValueError("Session incomplète : budget manquant.")
    hand = HandMeasure(session.hand_length_mm, session.hand_width_mm)
    mice = load_catalog(MOUSE_DB_PATH)
    scores = [
        evaluate_mouse(m, hand, session.grip, session.budget_mode, session.max_budget_eur)
        for m in mice
    ]
    return select(scores, session.budget_mode)


# ---------------------------------------------------------------------------
# Views de base
# ---------------------------------------------------------------------------
class FinderView(discord.ui.View):
    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        log.exception("Erreur dans la vue Mouse Shape Finder", exc_info=error)
        await _send_ephemeral(interaction, "⚠️ Une erreur est survenue. Relancez le Mouse Shape Finder.")


class FinderModal(discord.ui.Modal):
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.exception("Erreur dans le modal Mouse Shape Finder", exc_info=error)
        await _send_ephemeral(interaction, "⚠️ Une erreur est survenue. Relancez le Mouse Shape Finder.")


# ---------------------------------------------------------------------------
# Point d'entrée persistant
# ---------------------------------------------------------------------------
class StartView(discord.ui.View):
    """Vue persistante (timeout=None, custom_id fixe) enregistrée au démarrage du bot."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Start Mouse Shape Finder",
        style=discord.ButtonStyle.primary,
        emoji="🖱️",
        custom_id=START_CUSTOM_ID,
    )
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        interaction.client.sessions.start(interaction.user.id)
        await interaction.response.send_message(
            embed=grip_step_embed(), view=GripView(), ephemeral=True
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        log.exception("Erreur sur le message persistant", exc_info=error)
        await _send_ephemeral(interaction, "⚠️ Une erreur est survenue. Réessayez dans un instant.")


# ---------------------------------------------------------------------------
# Étape 1 : Grip
# ---------------------------------------------------------------------------
class GripSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Choisissez votre grip…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=grip.value, description=desc)
                for grip, label, desc in GRIP_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction)
        if session is None:
            return
        session.grip = Grip(self.values[0])
        await interaction.response.edit_message(embed=measure_step_embed(session), view=MeasureView())


class GripView(FinderView):
    def __init__(self) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.add_item(GripSelect())


# ---------------------------------------------------------------------------
# Étape 2 : Mesures (bouton -> modal)
# ---------------------------------------------------------------------------
class MeasureModal(FinderModal):
    def __init__(self) -> None:
        super().__init__(title="Mesure de votre main")
        self.length = discord.ui.TextInput(
            label="Longueur de la main (mm)",
            placeholder="Ex : 180",
            required=True,
            min_length=1,
            max_length=6,
        )
        self.width = discord.ui.TextInput(
            label="Largeur sans le pouce (mm)",
            placeholder="Ex : 90",
            required=True,
            min_length=1,
            max_length=6,
        )
        self.add_item(self.length)
        self.add_item(self.width)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction)
        if session is None:
            return
        try:
            length, width = parse_hand_measures(self.length.value, self.width.value)
        except InputError as exc:
            # Erreur de saisie : on informe sans changer l'étape courante.
            await _send_ephemeral(
                interaction,
                f"❌ **Saisie invalide**\n{exc}\n\nCliquez à nouveau sur **Saisir mes mesures**.",
            )
            return
        session.hand_length_mm = length
        session.hand_width_mm = width
        await interaction.response.edit_message(embed=budget_step_embed(session), view=BudgetView())


class MeasureView(FinderView):
    def __init__(self) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)

    @discord.ui.button(label="Saisir mes mesures", style=discord.ButtonStyle.primary, emoji="📏")
    async def open_measures(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        session = await require_session(interaction)
        if session is None:
            return
        await interaction.response.send_modal(MeasureModal())


# ---------------------------------------------------------------------------
# Étape 3 : Budget (select -> modal si budget personnalisé)
# ---------------------------------------------------------------------------
class BudgetSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Choisissez votre gamme…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=mode.value, description=desc)
                for mode, label, desc in BUDGET_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction)
        if session is None:
            return
        mode = BudgetMode(self.values[0])
        if mode is BudgetMode.CUSTOM:
            # Le modal est la réponse à cette interaction ; la session est mise à jour à la soumission.
            await interaction.response.send_modal(BudgetModal())
            return
        session.budget_mode = mode
        session.max_budget_eur = None
        await _show_results(interaction, session)


class BudgetView(FinderView):
    def __init__(self) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.add_item(BudgetSelect())


class BudgetModal(FinderModal):
    def __init__(self) -> None:
        super().__init__(title="Budget personnalisé")
        self.price = discord.ui.TextInput(
            label="Prix maximum (€)",
            placeholder="Ex : 60",
            required=True,
            min_length=1,
            max_length=8,
        )
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction)
        if session is None:
            return
        try:
            budget = parse_budget(self.price.value)
        except InputError as exc:
            await _send_ephemeral(
                interaction,
                f"❌ **Saisie invalide**\n{exc}\n\nRouvrez le menu « Budget Personnalisé Maximal ».",
            )
            return
        session.budget_mode = BudgetMode.CUSTOM
        session.max_budget_eur = budget
        await _show_results(interaction, session)


# ---------------------------------------------------------------------------
# Résultat final
# ---------------------------------------------------------------------------
async def _show_results(interaction: discord.Interaction, session: FinderSession) -> None:
    selection = compute_selection(session)
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    await interaction.response.edit_message(
        embed=results_embed(session, selection),
        view=ResultsView(selection.ranked, links),
    )


class ResultsView(FinderView):
    def __init__(self, ranked: tuple[MouseScore, ...] | list[MouseScore], links: dict[str, str]) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        for score in ranked:
            url = links.get(score.mouse.id)
            if url:
                self.add_item(
                    discord.ui.Button(
                        label=f"Acheter {score.mouse.label}"[:80],
                        style=discord.ButtonStyle.link,
                        url=url,
                        emoji="🛒",
                    )
                )
            else:
                self.add_item(
                    discord.ui.Button(
                        label=f"Lien bientôt disponible : {score.mouse.label}"[:80],
                        style=discord.ButtonStyle.secondary,
                        disabled=True,
                        custom_id=f"mouse_finder:nolink:{score.mouse.id}",
                    )
                )
        # Ajouté en dernier : le bouton de relance apparaît après les liens d'achat.
        restart = discord.ui.Button(label="Refaire le test", style=discord.ButtonStyle.secondary, emoji="🔄")
        restart.callback = self._restart
        self.add_item(restart)

    async def _restart(self, interaction: discord.Interaction) -> None:
        interaction.client.sessions.start(interaction.user.id)
        await interaction.response.edit_message(embed=grip_step_embed(), view=GripView())
