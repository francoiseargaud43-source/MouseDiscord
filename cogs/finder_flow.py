"""Flux Discord du Mouse Shape Finder : message persistant, étapes éphémères, modals, résultat.

CONFIDENTIALITÉ (tests : tests/test_flow.py, tests/test_privacy.py ; contrôle statique :
tools/privacy_scan.py, testé par tests/test_privacy_scan.py ; limites : docs/audit/AUDIT_CONFIDENTIALITE.md) :
- seul le message d'accueil ``StartView`` est public ; il ne fait qu'ouvrir un parcours privé ;
- toutes les autres réponses sont éphémères : ``send_message(ephemeral=True)``, ``followup.send(ephemeral=True)``
  ou ``edit_message`` sur le message éphémère du parcours ;
- chaque vue et chaque modal porte le ``session_id`` du parcours ; chaque action vérifie l'identifiant ET le propriétaire.

Parcours : 1/4 prise -> 2/4 thénar -> 3/4 mesures de la main -> 4/4 budget (en Fingertip, la question du
thénar n'est pas posée : 3 étapes). Le thénar sert à lire l'arrière de la souris : ajustement **borné**
(±2 points au maximum) du sous-score de largeur, appliqué **uniquement** aux souris à bosse arrière
marquée et jamais en Fingertip (``THENAR_WIDTH_ADJUSTMENT`` dans utils/matcher.py ; méthode :
docs/REVERSE_ENGINEERING_OBLIVITY.md). Sans thénar renseigné (ou thénar moyen), le barème est inchangé.

CHARTE AZEMOUSE (voir docs/REPORTE_DESIGN.md) :
- **Bordeaux #8A2342** = couleur latérale de tous les embeds (identité) ; seul « session expirée » reste orange ;
- **Nuit #0B1220 / Encre #070B14** portent le fond des illustrations (assets/images/T*.png) ;
- **Étincelle #F0C43C** est un highlight présent uniquement dans les images (jamais en aplat) ;
- **Crème #F6F1EA** n'apparaît que dans les illustrations, jamais dans un embed.
Limites Discord prises en compte : pas de police personnalisée dans le texte natif (hiérarchie rendue par le
Markdown), une seule image par embed, 25 champs maximum, 5 boutons par rangée, 1024 caractères par champ.
Le résultat tient en **deux embeds** : la recommandation, puis les repères de taille — jamais les points internes.
"""
from __future__ import annotations

import logging

import discord

from config import COMMERCIAL_LINKS_PATH, IMAGES_CONFIG_PATH, MOUSE_DB_PATH
from utils.assets import load_image_urls
from utils.catalog import load_catalog, load_commercial_links
from utils.matcher import (
    LENGTH_PTS_IN_RANGE,
    MAX_SCORE,
    WIDTH_PTS_IN_RANGE,
    MouseScore,
    compatibility_percent,
    compute_target_ranges,
    evaluate_mouse,
)
from utils.models import (
    BUDGET_LABELS,
    GRIP_LABELS,
    THENAR_LABELS,
    BudgetMode,
    Grip,
    HandMeasure,
    Thenar,
)
from utils.selection import Selection, performance_index, select
from utils.session import LOOKUP_FORBIDDEN, LOOKUP_OK, FinderSession
from utils.validation import InputError, parse_budget, parse_hand_measures

log = logging.getLogger(__name__)

VIEW_TIMEOUT = 900
START_CUSTOM_ID = "mouse_finder:start"

# --- Palette AzeMouse (voir docs/REPORTE_DESIGN.md §4) ---------------------
NAVY = discord.Color.from_rgb(11, 18, 32)        # #0B1220 Nuit  — référencée dans les illustrations
BORDEAUX = discord.Color.from_rgb(138, 35, 66)   # #8A2342 Bordeaux — couleur latérale des embeds
SPARK = discord.Color.from_rgb(240, 196, 60)     # #F0C43C Étincelle — jamais en aplat, images uniquement
COLOR = BORDEAUX
COLOR_EXPIRED = discord.Color.orange()           # seule exception à la charte (session expirée)

SCORE_DISCLAIMER = (
    "Score géométrique provisoire : ni une probabilité d'achat ni une validation biomécanique. "
    "Données, limites et souris écartées : bouton 🔍 Détails."
)
PENDING_DOC_REFERENCE = "docs/audit/matrice_profils.md"
BUTTON_LABEL_MAX = 80
MAX_PENDING_SHOWN = 5      # au-delà : décompte sans liste (le poids visuel reste au winner)
MAX_PENDING_LISTED = 8     # au-delà : une phrase de synthèse, sans nommer les souris
ALTERNATIVE_PRICE_RATIO = 0.70       # au moins 30 % moins cher
ALTERNATIVE_WIDTH_DELTA_MM = 2.0     # largeur de prise sensiblement différente
ALTERNATIVE_LENGTH_DELTA_MM = 4.0    # longueur sensiblement différente

CONFIDENCE_BADGES = {"élevée": "🟢", "moyenne": "🟡", "faible": "🔴"}

# Affichage : noms français des positions de bosse et des hauteurs de boutons (le catalogue garde
# ses valeurs anglaises, seules les phrases montrées à l'utilisateur sont traduites).
HUMP_DISPLAY = {
    "Front": "à l'avant",
    "Mid-Front": "au milieu-avant",
    "Mid": "au milieu",
    "Mid-Rear": "au milieu-arrière",
    "Rear": "à l'arrière",
}
BUTTON_DISPLAY = {"High": "hauts", "Mid": "médians", "Low": "bas"}

GRIP_OPTIONS = (
    (Grip.PALM, "Palm Grip", "Paume posée sur la coque"),
    (Grip.CLAW, "Claw Grip", "Doigts arqués, pulpes en contact"),
    (Grip.FINGERTIP, "Fingertip Grip", "Bout des doigts — parcours raccourci"),
)
THENAR_OPTIONS = (
    (Thenar.PETITE, "Petite", "Thénar peu développé"),
    (Thenar.MOYENNE, "Moyenne", "Thénar dans la moyenne"),
    (Thenar.GRANDE, "Grande", "Thénar bien développé"),
)
BUDGET_OPTIONS = (
    (BudgetMode.ECONOMIQUE, "Économique", "Le moins cher de la zone compatible"),
    (BudgetMode.QUALITE_PRIX, "Rapport Qualité/Prix", "Meilleur points/€ (indicatif)"),
    (BudgetMode.HAUT_DE_GAMME, "Haut de Gamme", "Performances documentées les plus élevées"),
    (BudgetMode.CUSTOM, "Budget personnalisé", "Saisir un prix maximum en €"),
)
# Libellés courts utilisés dans le récapitulatif (le catalogue garde ses libellés complets).
BUDGET_RECAP_LABELS = {mode: label for mode, label, _ in BUDGET_OPTIONS}


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


async def require_session(interaction: discord.Interaction, session_id: str) -> FinderSession | None:
    """Retourne la session si elle est active ET appartient à l'utilisateur ; sinon informe en privé."""
    session, status = interaction.client.sessions.lookup(session_id, interaction.user.id)
    if status == LOOKUP_OK:
        return session
    if status == LOOKUP_FORBIDDEN:
        # Ne révèle rien sur le parcours d'un autre membre et ne modifie rien.
        await _send_ephemeral(interaction, "🔒 Cette action n'est pas disponible pour votre compte.")
    else:
        await _send_ephemeral(
            interaction,
            "⏱️ Ce parcours n'est plus actif (expiré ou remplacé par un nouveau test). "
            "Cliquez à nouveau sur **Start Mouse Shape Finder**.",
        )
    return None


async def _show_private(interaction: discord.Interaction, **kwargs) -> None:
    """Affiche une étape ou un résultat en PRIVÉ.

    Cas normal : remplace le message éphémère d'origine (bouton, menu ou modal lancé depuis ce message).
    Repli : si Discord ne fournit pas le message d'origine (modal non lié à un composant),
    envoi d'un nouveau message éphémère. Dans les deux cas, rien n'est publié dans le salon.
    """
    if interaction.message is not None:
        await interaction.response.edit_message(**kwargs)
    else:
        await interaction.response.send_message(ephemeral=True, **kwargs)


def _image(embed: discord.Embed, key: str) -> discord.Embed:
    """Attache l'illustration de ``key`` (assets/images.json) si une URL https est disponible."""
    url = load_image_urls(IMAGES_CONFIG_PATH).get(key)
    if url:
        embed.set_image(url=url)
    return embed


def _num(value: float, decimals: int = 0) -> str:
    """Nombre à la française : virgule décimale, sans zéro inutile (« 118,8 », « 59,95 », « 127 »)."""
    return (f"{value:.{decimals}f}" if decimals else f"{value:g}").replace(".", ",")


def _mm(value: float) -> str:
    """« 127 mm » plutôt que « 127.0 mm » (lisibilité mobile)."""
    return f"{_num(value)} mm"


def _size_text(mouse) -> str:
    parts = []
    if mouse.length_mm is not None:
        parts.append(f"long. {_mm(mouse.length_mm)}")
    if mouse.width_max_mm is not None:
        parts.append(f"larg. {_mm(mouse.width_max_mm)} (coque)")
    return " · ".join(parts)


def _steps_total(session_or_grip) -> int:
    """Nombre d'étapes du parcours : 3 en Fingertip (l'étape thénar n'est pas proposée), 4 sinon."""
    grip = getattr(session_or_grip, "grip", session_or_grip)
    return 3 if grip is Grip.FINGERTIP else 4


def _step_title(index: int, session_or_grip, label: str) -> str:
    return f"Étape {index}/{_steps_total(session_or_grip)} — {label}"


def _budget_text(session: FinderSession) -> str:
    if session.budget_mode is BudgetMode.CUSTOM and session.max_budget_eur is not None:
        return f"Budget max {_num(session.max_budget_eur, 2)} €"
    if session.budget_mode is not None:
        return BUDGET_RECAP_LABELS.get(session.budget_mode, BUDGET_LABELS[session.budget_mode])
    return "—"


def _recap(session: FinderSession) -> str:
    """Récapitulatif d'une ligne (mobile) : prise, thénar, main, gamme — seules les données connues."""
    parts = []
    if session.grip:
        parts.append(f"✋ **{GRIP_LABELS[session.grip]}**")
    if session.thenar:
        parts.append(f"🖐️ Thénar **{THENAR_LABELS[session.thenar]}**")
    if session.hand_length_mm and session.hand_width_mm:
        parts.append(f"📏 **{_num(session.hand_length_mm)} × {_num(session.hand_width_mm)} mm**")
    if session.budget_mode is not None:
        parts.append(f"🎚️ **{_budget_text(session)}**")
    return "  •  ".join(parts)


def _price_text(score: MouseScore, *, verified_hint: bool = False) -> str:
    """Prix lisible ; le statut « non vérifié » n'apparaît que dans l'onglet Détails."""
    mouse = score.mouse
    if mouse.price_eur is None:
        return "prix non renseigné"
    text = f"{_num(mouse.price_eur, 2)} €"
    if verified_hint and mouse.price_status != "verified":
        text += " (prix non vérifié)"
    return text


def _confidence_line(score: MouseScore) -> str:
    """Badge de confiance en trois mots (jamais une couleur seule) : explication dans l'onglet Détails."""
    level = score.confidence or "faible"
    badge = CONFIDENCE_BADGES.get(level, "🔴")
    return f"{badge} Confiance {level}"


def _confidence_detail(score: MouseScore) -> str:
    """Pourquoi cette confiance (onglet Détails) : jamais affiché dans le résumé."""
    level = score.confidence or "faible"
    badge = CONFIDENCE_BADGES.get(level, "🔴")
    reason = {
        "élevée": "dimensions vérifiées et largeur de prise mesurée",
        "moyenne": "dimensions vérifiées, largeur de prise encore estimée (coque − 3 mm, provisoire)",
        "faible": "données d'une seule source ou compatibilité non confirmée",
    }.get(level, "données partielles")
    return f"{badge} **{level.capitalize()}** — {reason}."


def _match_summary(score: MouseScore) -> str:
    """Phrase humaine (sans points internes) : ce qui colle, ce qui colle moins."""
    mouse = score.mouse
    good, weak = [], []
    if score.breakdown.length_pts == LENGTH_PTS_IN_RANGE:
        good.append("longueur dans la cible")
    elif score.breakdown.length_pts > 0:
        weak.append("longueur à quelques millimètres de la cible")
    else:
        weak.append("longueur en léger retrait")
    if score.breakdown.width_pts == WIDTH_PTS_IN_RANGE:
        good.append("largeur de prise dans la cible")
    elif score.breakdown.width_pts > 0:
        weak.append("largeur de prise proche de la cible")
    else:
        weak.append("largeur de prise un peu large")
    if score.breakdown.grip_pts > 0:
        good.append(f"prise {score.grip.label} bien soutenue")
    if score.breakdown.thenar_pts > 0:
        good.append("arrière marqué qui soutient votre thénar")
    elif score.breakdown.thenar_pts < 0:
        weak.append("arrière large peu adapté à un petit thénar")
    if mouse.hump_position != "Inconnu" and score.grip is not Grip.FINGERTIP:
        # En Fingertip, la bosse est ignorée par le barème : ne pas la présenter comme un défaut.
        (good if score.breakdown.hump_pts > 0 else weak).append(
            f"bosse {HUMP_DISPLAY.get(mouse.hump_position, mouse.hump_position)} "
            + ("adaptée" if score.breakdown.hump_pts > 0 else "moins adaptée")
        )
    if mouse.button_height != "Inconnu":
        (good if score.breakdown.button_pts > 0 else weak).append(
            f"boutons {BUTTON_DISPLAY.get(mouse.button_height, mouse.button_height)} "
            + ("adaptés" if score.breakdown.button_pts > 0 else "moins adaptés")
        )
    sentence = ", ".join(good[:3]).capitalize() if good else "Géométrie proche de votre profil"
    if weak:
        sentence += f". À noter : {', '.join(weak[:1])}."
    else:
        sentence += "."
    return sentence[:300]


def _candidate_text(score: MouseScore) -> str:
    """Match idéal en deux lignes : souris + prix, puis pourcentage et confiance (le reste : 🔍 Détails)."""
    return (
        f"**{score.mouse.label}** · {_price_text(score)}\n"
        f"**{compatibility_percent(score)} %** du maximum théorique · {_confidence_line(score)}"
    )[:1024]


def _alternative_reason(top: MouseScore, alt: MouseScore) -> str:
    """Explique en une phrase pourquoi l'alternative mérite un coup d'œil."""
    if top.mouse.price_eur and alt.mouse.price_eur and alt.mouse.price_eur <= top.mouse.price_eur * ALTERNATIVE_PRICE_RATIO:
        saving = round((1 - alt.mouse.price_eur / top.mouse.price_eur) * 100)
        return f"Prix inférieur d'environ {saving} % pour une compatibilité équivalente."
    if performance_index(alt.mouse) != performance_index(top.mouse):
        if performance_index(alt.mouse) > performance_index(top.mouse):
            return "Performances documentées supérieures (polling ≥ 8000 Hz et/ou capteur haut de gamme)."
        return "Performances documentées différentes (moins de caractéristiques haut de gamme)."
    if top.mouse.hump_position != alt.mouse.hump_position or top.mouse.button_height != alt.mouse.button_height:
        return (
            f"Géométrie différente : bosse {alt.mouse.hump_position}, boutons {alt.mouse.button_height} "
            f"contre {top.mouse.hump_position} / {top.mouse.button_height}."
        )
    return "Dimensions sensiblement différentes de celles du match idéal."


def _alternative_is_relevant(top: MouseScore | None, alt: MouseScore | None) -> bool:
    """Une alternative ne s'affiche que si elle apporte une vraie différence (prix, performance, géométrie)."""
    if top is None or alt is None:
        return False
    if top.mouse.hump_position != alt.mouse.hump_position or top.mouse.button_height != alt.mouse.button_height:
        return True
    if performance_index(alt.mouse) != performance_index(top.mouse):
        return True
    if top.mouse.price_eur and alt.mouse.price_eur and alt.mouse.price_eur <= top.mouse.price_eur * ALTERNATIVE_PRICE_RATIO:
        return True
    if (top.mouse.length_mm and alt.mouse.length_mm
            and abs(top.mouse.length_mm - alt.mouse.length_mm) >= ALTERNATIVE_LENGTH_DELTA_MM):
        return True
    return bool(
        top.width_used_mm and alt.width_used_mm
        and abs(top.width_used_mm - alt.width_used_mm) >= ALTERNATIVE_WIDTH_DELTA_MM
    )


def _alternative_reason_short(top: MouseScore, alt: MouseScore) -> str:
    """Différence utile en quelques mots (la version chiffrée reste dans l'onglet Détails)."""
    if alt.total == top.total:
        # Égalité parfaite : la gamme a choisi le moins cher, l'alternative est donc plus chère.
        return "Même score, un peu plus chère."
    if (top.mouse.price_eur and alt.mouse.price_eur
            and alt.mouse.price_eur <= top.mouse.price_eur * ALTERNATIVE_PRICE_RATIO):
        saving = round((1 - alt.mouse.price_eur / top.mouse.price_eur) * 100)
        return f"Environ {saving} % moins chère."
    if performance_index(alt.mouse) > performance_index(top.mouse):
        return "Performances documentées supérieures."
    if (top.mouse.hump_position != alt.mouse.hump_position
            or top.mouse.button_height != alt.mouse.button_height):
        return "Forme différente de celle du match idéal."
    return "Dimensions différentes."


def _alternative_text(top: MouseScore | None, alt: MouseScore | None) -> str:
    """Alternative en deux lignes : souris + prix, puis pourcentage, confiance et différence utile."""
    if not _alternative_is_relevant(top, alt):
        return "Aucune alternative pertinente dans la gamme choisie (mêmes géométrie, prix et performances documentées)."
    assert alt is not None and top is not None
    return (
        f"**{alt.mouse.label}** · {_price_text(alt)}\n"
        f"**{compatibility_percent(alt)} %** du maximum théorique · {_confidence_line(alt)}\n"
        f"{_alternative_reason_short(top, alt)}"
    )[:1024]


def _pending_reason(score: MouseScore) -> str:
    """Raison courte et lisible — jamais de score partiel ni de « /25 pts » (détails dans la matrice)."""
    missing = " ".join(score.missing)
    if "compatibilité" in missing:
        return f"compatibilité {score.grip.label} non vérifiée"
    if "longueur" in missing or "conflit" in missing:
        return "dimensions non vérifiées"
    if score.mouse.price_eur is None:
        return "prix non renseigné"
    if "bosse" in missing:
        return "position de la bosse non vérifiée"
    if "boutons" in missing:
        return "hauteur des boutons non vérifiée"
    return "données incomplètes"


PENDING_BUCKETS = {
    "compatibilité": "sans compatibilité de prise",
    "bosse": "sans hauteur de bosse",
    "boutons": "sans hauteur de boutons",
    "dimensions": "sans dimensions vérifiées",
    "prix": "sans prix renseigné",
}


def _pending_bucket(score: MouseScore) -> str:
    """Regroupe une souris non classée par donnée manquante (pour un décompte compact)."""
    missing = " ".join(score.missing)
    for key, label in PENDING_BUCKETS.items():
        if key in missing:
            return label
    return "données incomplètes"


def _pending_breakdown(pending: tuple[MouseScore, ...]) -> str:
    """« 12 sans compatibilité · 5 sans hauteur de boutons » — ordre décroissant, sans points internes."""
    counts: dict[str, int] = {}
    for score in pending:
        bucket = _pending_bucket(score)
        counts[bucket] = counts.get(bucket, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return " · ".join(f"{count} {label}" for label, count in ordered)


def _pending_text(pending: tuple[MouseScore, ...]) -> str:
    """Décompte compact par raison, puis au maximum 5 noms (jamais de score partiel)."""
    header = f"{len(pending)} souris écartées du classement — {_pending_breakdown(pending)}."
    if len(pending) > MAX_PENDING_LISTED:
        return f"{header}\nDétail par souris : `{PENDING_DOC_REFERENCE}`."[:1024]
    lines = [f"• **{s.mouse.label}** — {_pending_reason(s)}" for s in pending[:MAX_PENDING_SHOWN]]
    if len(pending) > MAX_PENDING_SHOWN:
        lines.append(f"… +{len(pending) - MAX_PENDING_SHOWN} — `{PENDING_DOC_REFERENCE}`.")
    else:
        lines.append(f"Détail par souris : `{PENDING_DOC_REFERENCE}`.")
    return f"{header}\n" + "\n".join(lines)[:1024]


# ---------------------------------------------------------------------------
# Embeds d'accueil et d'étapes
# ---------------------------------------------------------------------------
def banner_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🖱️ AzeMouse — Mouse Shape Finder",
        description=(
            "Trouvez la souris dont la géométrie épouse **votre** main.\n"
            "4 questions rapides : prise, thénar, mesures, budget.\n"
            "*Réponses privées : seul vous voyez la recommandation.*"
        ),
        color=COLOR,
    )
    return _image(embed, "banner")


def grip_step_embed() -> discord.Embed:
    description = "\n".join(f"**{label}** — {desc}" for _, label, desc in GRIP_OPTIONS)
    embed = discord.Embed(
        # Pas de dénominateur : le nombre d'étapes dépend de la prise choisie (3 en Fingertip, 4 sinon).
        title="Étape 1 — Votre prise",
        description=f"Quelle prise utilisez-vous le plus souvent ?\n{description}",
        color=COLOR,
    )
    return _image(embed, "step1_grip")


def thenar_step_embed() -> discord.Embed:
    embed = discord.Embed(
        title=_step_title(2, Grip.PALM, "Votre éminence thénar"),
        description=(
            "Votre réponse indique l'arrière de souris qui vous convient : un petit thénar préfère un "
            "arrière étroit, un grand thénar est soutenu par un arrière marqué.\n"
            "Effet **borné à ±2 points** sur le score, et **uniquement** pour les souris à bosse "
            "arrière marquée — sinon le score ne change pas."
        ),
        color=COLOR,
    )
    return _image(embed, "step2_thenar")


def measure_step_embed(session: FinderSession) -> discord.Embed:
    embed = discord.Embed(
        title=_step_title(2 if session.grip is Grip.FINGERTIP else 3, session, "Vos mesures"),
        description=(
            f"{_recap(session)}\n\n"
            "Avec une règle :\n"
            "• **Longueur** : pli du poignet → bout du majeur.\n"
            "• **Largeur** : articulations, **sans le pouce**."
        ),
        color=COLOR,
    )
    return _image(embed, "step2_measure")


def budget_step_embed(session: FinderSession) -> discord.Embed:
    embed = discord.Embed(
        title=_step_title(3 if session.grip is Grip.FINGERTIP else 4, session, "Budget et gamme"),
        description=f"{_recap(session)}\nChoisissez votre gamme de prix.",
        color=COLOR,
    )
    return _image(embed, "step3_budget")


def _target_line(session: FinderSession) -> str:
    """Plage cible expliquée en une phrase (jamais de détail de points)."""
    hand = HandMeasure(session.hand_length_mm, session.hand_width_mm)
    assert session.grip is not None
    ranges = compute_target_ranges(hand, session.grip)
    length = (
        f"jusqu'à {_num(ranges.length_max, 1)} mm"
        if session.grip is Grip.FINGERTIP
        else f"{_num(ranges.length_min, 1)}–{_num(ranges.length_max, 1)} mm"
    )
    return (f"Longueur cible : **{length}** · largeur de prise : "
            f"**{_num(ranges.width_min, 1)}–{_num(ranges.width_max, 1)} mm**.")


def result_image_key(winner: MouseScore | None, grip: Grip | None) -> str | None:
    """Illustration la plus utile : la bosse d'abord (ressenti), les boutons ensuite. Une seule image."""
    if winner is None:
        return None
    mouse = winner.mouse
    if grip in (Grip.PALM, Grip.CLAW) and mouse.hump_position != "Inconnu":
        tokens = set(mouse.hump_position.split("-"))
        if "Rear" in tokens:
            return "illustration_hump_rear"
        if "Front" in tokens:
            return "illustration_hump_front"
        if "Mid" in tokens:
            return "illustration_hump_mid"
    return {
        "High": "illustration_buttons_high",
        "Mid": "illustration_buttons_mid",
        "Low": "illustration_buttons_low",
    }.get(mouse.button_height)


def results_embeds(session: FinderSession, selection: Selection) -> list[discord.Embed]:
    """Résultat en deux embeds : (1) la recommandation, (2) les repères de taille. Jamais de points internes."""
    main = discord.Embed(title="🎯 Votre recommandation", color=COLOR)
    header = _recap(session)
    if session.budget_mode is None:
        # Mode absent : le récapitulatif ne porte pas la gamme, on l'indique explicitement.
        header = f"{header}  •  🎚️ **Classement morphologique**"
    main.description = header[:4096]

    if not selection.ranked:
        main.add_field(
            name="Aucun match classable",
            value=(
                "Aucune souris ne peut être classée avec les données vérifiées pour ces critères. "
                "Essayez une autre gamme ou un budget plus élevé."
            ),
            inline=False,
        )
    else:
        top = selection.ranked[0]
        alt = selection.ranked[1] if len(selection.ranked) > 1 else None
        main.add_field(name="🥇 Le Match Idéal", value=_candidate_text(top), inline=False)
        main.add_field(name="🥈 L'Alternative", value=_alternative_text(top, alt), inline=False)
        main.add_field(name="🧭 Pourquoi ce choix ?", value=selection.explanation[:1024], inline=False)
        if selection.pending:
            main.add_field(
                name="⏳ Non classées",
                value=(f"**{len(selection.pending)}** souris écartées du classement, faute de données vérifiées.\n"
                       "Détail souris par souris : bouton **🔍 Détails**."),
                inline=False,
            )
        image_key = result_image_key(top, session.grip)
        if image_key:
            main = _image(main, image_key)

    main.set_footer(text=SCORE_DISCLAIMER)
    embeds = [main]

    if selection.ranked and session.grip is not None:
        top = selection.ranked[0]
        details = discord.Embed(title="📐 Repères de taille", color=COLOR)
        # Autoportant : le rappel de la prise et des mesures permet de lire cet embed seul (partage, capture).
        details.description = (
            f"{_recap(session)}\n{_target_line(session)}\n"
            f"Score : **{top.total}/{MAX_SCORE} — {compatibility_percent(top)} % du maximum théorique**.\n"
            "Barème : longueur, largeur de prise (ajustement thénar borné à ±2), compatibilité de prise, "
            "bosse, boutons."
        )
        details.add_field(
            name="🧩 Le match en clair",
            value=(f"{_size_text(top.mouse)} · {_price_text(top, verified_hint=True)}\n"
                   f"{_match_summary(top)}")[:1024],
            inline=False,
        )
        details.add_field(name="🔎 Confiance", value=_confidence_detail(top), inline=False)
        if selection.pending:
            details.add_field(name="⏳ Souris écartées", value=_pending_text(selection.pending), inline=False)
        if session.thenar is Thenar.PETITE and session.grip is not Grip.FINGERTIP:
            details.add_field(
                name="🖐️ Thénar Petite",
                value=("Arrière étroit en « pilule » conseillé (méthode Oblivity) ; "
                       "une souris à bosse arrière marquée est **pénalisée à la marge** dans le score."),
                inline=False,
            )
            details = _image(details, "illustration_rear_narrow")
        else:
            details = _image(details, "illustration_mouse_dimensions")
        embeds.append(details)
    return embeds


def expired_embed() -> discord.Embed:
    return discord.Embed(
        title="⏱️ Session expirée",
        description="Cliquez sur **Start Mouse Shape Finder** dans le salon pour recommencer.",
        color=COLOR_EXPIRED,
    )


# ---------------------------------------------------------------------------
# Calcul
# ---------------------------------------------------------------------------
def compute_selection(session: FinderSession) -> Selection:
    """Lecture à chaud du catalogue (les données ne sont jamais mises en cache)."""
    mice = load_catalog(MOUSE_DB_PATH)
    hand = HandMeasure(session.hand_length_mm, session.hand_width_mm)
    assert session.grip is not None
    scores = [
        evaluate_mouse(mouse, hand, session.grip, session.budget_mode, session.max_budget_eur,
                       thenar=session.thenar)
        for mouse in mice
    ]
    return select(scores, session.budget_mode)


# ---------------------------------------------------------------------------
# Vues et modals
# ---------------------------------------------------------------------------
class FinderView(discord.ui.View):
    """Base des vues du parcours : aucune donnée n'est publiée dans le salon."""

    def __init__(self, timeout: float | None = VIEW_TIMEOUT) -> None:
        super().__init__(timeout=timeout)


class FinderModal(discord.ui.Modal):
    def __init__(self, title: str) -> None:
        super().__init__(title=title)


# ---------------------------------------------------------------------------
# Accueil (vue persistante : custom_id fixe, enregistrée au démarrage du bot)
# ---------------------------------------------------------------------------
class StartView(FinderView):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Start Mouse Shape Finder",
        style=discord.ButtonStyle.primary,
        emoji="🖱️",
        custom_id=START_CUSTOM_ID,
    )
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        session = interaction.client.sessions.start(interaction.user.id)
        await interaction.response.send_message(
            embed=grip_step_embed(), view=GripView(session.session_id), ephemeral=True
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        log.exception("Erreur sur le message persistant", exc_info=error)
        await _send_ephemeral(interaction, "⚠️ Une erreur est survenue. Réessayez dans un instant.")


# ---------------------------------------------------------------------------
# Étape 1 : prise (grip)
# ---------------------------------------------------------------------------
class GripSelect(discord.ui.Select):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(
            placeholder="Choisissez votre prise…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=grip.value, description=desc)
                for grip, label, desc in GRIP_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction, self.session_id)
        if session is None:
            return
        session.grip = Grip(self.values[0])
        if session.grip is Grip.FINGERTIP:
            # L'arrière de la souris n'est pas utilisé dans cette prise (bosse ignorée par le barème,
            # thénar non collecté) : l'étape thénar est sautée et aucune note « arrière étroit » ne s'affiche.
            session.thenar = None
            await _show_private(interaction, embed=measure_step_embed(session), view=MeasureView(self.session_id))
            return
        await _show_private(interaction, embed=thenar_step_embed(), view=ThenarView(self.session_id))


class GripView(FinderView):
    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.add_item(GripSelect(session_id))


# ---------------------------------------------------------------------------
# Étape 2 : éminence thénar (ajustement borné du sous-score de largeur : THENAR_WIDTH_ADJUSTMENT)
# ---------------------------------------------------------------------------
class ThenarSelect(discord.ui.Select):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(
            placeholder="Choisissez la taille de votre thénar…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=thenar.value, description=desc)
                for thenar, label, desc in THENAR_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction, self.session_id)
        if session is None:
            return
        session.thenar = Thenar(self.values[0])  # stocké et affiché uniquement
        await _show_private(interaction, embed=measure_step_embed(session), view=MeasureView(self.session_id))


class ThenarView(FinderView):
    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.add_item(ThenarSelect(session_id))


# ---------------------------------------------------------------------------
# Étape 3 : mesures (bouton -> modal)
# ---------------------------------------------------------------------------
class MeasureModal(FinderModal):
    def __init__(self, session_id: str) -> None:
        super().__init__(title="Mesure de votre main")
        self.session_id = session_id
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
        session = await require_session(interaction, self.session_id)
        if session is None:
            return
        try:
            length, width = parse_hand_measures(self.length.value, self.width.value)
        except InputError as exc:
            # Erreur de saisie : message PRIVÉ, étape courante inchangée, données non enregistrées.
            await _send_ephemeral(
                interaction,
                f"❌ **Saisie invalide**\n{exc}\n\nCliquez à nouveau sur **Saisir mes mesures**.",
            )
            return
        session.hand_length_mm = length
        session.hand_width_mm = width
        await _show_private(interaction, embed=budget_step_embed(session), view=BudgetView(self.session_id))


class MeasureView(FinderView):
    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id

    @discord.ui.button(label="Saisir mes mesures", style=discord.ButtonStyle.primary, emoji="📏")
    async def open_measures(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        session = await require_session(interaction, self.session_id)
        if session is None:
            return
        await interaction.response.send_modal(MeasureModal(self.session_id))


# ---------------------------------------------------------------------------
# Étape 4 : budget (select -> modal si budget personnalisé)
# ---------------------------------------------------------------------------
class BudgetSelect(discord.ui.Select):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
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
        session = await require_session(interaction, self.session_id)
        if session is None:
            return
        mode = BudgetMode(self.values[0])
        if mode is BudgetMode.CUSTOM:
            # Le modal est la réponse à cette interaction ; la session est mise à jour à la soumission.
            await interaction.response.send_modal(BudgetModal(self.session_id))
            return
        session.budget_mode = mode
        session.max_budget_eur = None
        await _show_results(interaction, session)


class BudgetView(FinderView):
    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.add_item(BudgetSelect(session_id))


class BudgetModal(FinderModal):
    def __init__(self, session_id: str) -> None:
        super().__init__(title="Budget personnalisé")
        self.session_id = session_id
        self.price = discord.ui.TextInput(
            label="Prix maximum (€)",
            placeholder="Ex : 60",
            required=True,
            min_length=1,
            max_length=8,
        )
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = await require_session(interaction, self.session_id)
        if session is None:
            return
        try:
            budget = parse_budget(self.price.value)
        except InputError as exc:
            await _send_ephemeral(
                interaction,
                f"❌ **Saisie invalide**\n{exc}\n\nRouvrez le menu « Budget personnalisé ».",
            )
            return
        session.budget_mode = BudgetMode.CUSTOM
        session.max_budget_eur = budget
        await _show_results(interaction, session)


# ---------------------------------------------------------------------------
# Résultat final (privé) et fermeture
# ---------------------------------------------------------------------------
async def _show_results(interaction: discord.Interaction, session: FinderSession) -> None:
    selection = compute_selection(session)
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    owner_id = session.user_id
    embeds = results_embeds(session, selection)
    # Minimisation : les réponses ne servent plus une fois le résultat produit.
    interaction.client.sessions.discard(session.session_id)
    # À l'écran : le résumé seul. Les repères, la confiance et les souris écartées sont dans 🔍 Détails.
    await _show_private(interaction, embeds=embeds[:1], view=ResultsView(owner_id, selection.ranked, links, embeds))


class ResultsView(FinderView):
    """Boutons du résultat privé : achats réels, Liens à venir si aucun lien, Fermer, Refaire (propriétaire)."""

    def __init__(self, owner_id: int, ranked: tuple[MouseScore, ...] | list[MouseScore], links: dict[str, str],
                 embeds: list[discord.Embed] | None = None) -> None:
        super().__init__()
        self.owner_id = owner_id
        self.embeds = list(embeds or [])   # [résumé, détails] — le résumé seul est envoyé au départ
        self.showing_details = False
        purchases = 0
        for score in ranked[:2]:
            url = links.get(score.mouse.id)
            if url:
                self.add_item(
                    discord.ui.Button(
                        label=f"Acheter {score.mouse.label}"[:BUTTON_LABEL_MAX],
                        style=discord.ButtonStyle.link,
                        url=url,
                        emoji="🛒",
                        row=0,
                    )
                )
                purchases += 1
        if purchases == 0:
            # Plus un bouton grisé par souris : un seul bouton informatif, jamais de lien inventé.
            self.add_item(
                discord.ui.Button(
                    label="Liens à venir",
                    style=discord.ButtonStyle.secondary,
                    emoji="🔗",
                    disabled=True,
                    custom_id="mouse_finder:nolink",
                    row=0,
                )
            )
        close = discord.ui.Button(label="Fermer", style=discord.ButtonStyle.secondary, emoji="✖️", row=1)
        close.callback = self._close
        self.add_item(close)
        # Ajouté en dernier : le bouton de relance apparaît après les liens d'achat.
        restart = discord.ui.Button(label="Refaire le test", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
        restart.callback = self._restart
        self.add_item(restart)
        # Bascule résumé <-> détails : le second embed ne s'affiche que si l'utilisateur le demande.
        self.details_button: discord.ui.Button | None = None
        if len(self.embeds) > 1:
            self.details_button = discord.ui.Button(
                label="Détails", style=discord.ButtonStyle.secondary, emoji="🔍", row=1
            )
            self.details_button.callback = self._toggle_details
            self.add_item(self.details_button)

    async def _toggle_details(self, interaction: discord.Interaction) -> None:
        """Affiche (ou masque) l'embed technique, toujours dans le message privé d'origine."""
        if not await self._check_owner(interaction):
            return
        self.showing_details = not self.showing_details
        if self.details_button is not None:
            self.details_button.label = "Résumé" if self.showing_details else "Détails"
            self.details_button.emoji = "↩️" if self.showing_details else "🔍"
        embeds = self.embeds if self.showing_details else self.embeds[:1]
        await _show_private(interaction, embeds=embeds, view=self)

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await _send_ephemeral(interaction, "🔒 Cette action n'est pas disponible pour votre compte.")
            return False
        return True

    async def _close(self, interaction: discord.Interaction) -> None:
        if not await self._check_owner(interaction):
            return
        # Retire le résultat du message privé ; aucun message n'est publié.
        await interaction.response.edit_message(
            content="✅ Résultat fermé. Cliquez sur **Start Mouse Shape Finder** dans le salon pour un nouveau test.",
            embed=None,
            embeds=None,
            view=None,
        )

    async def _restart(self, interaction: discord.Interaction) -> None:
        if not await self._check_owner(interaction):
            return
        session = interaction.client.sessions.start(interaction.user.id)
        await interaction.response.edit_message(embed=grip_step_embed(), embeds=None, view=GripView(session.session_id))
