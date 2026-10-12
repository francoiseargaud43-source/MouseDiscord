"""Flux Discord du Mouse Shape Finder : message persistant, étapes éphémères, modals, résultat.

CONFIDENTIALITÉ (tests : tests/test_flow.py, tests/test_privacy.py ; contrôle statique :
tools/privacy_scan.py, testé par tests/test_privacy_scan.py ; limites : docs/audit/AUDIT_CONFIDENTIALITE.md) :
- seul le message d'accueil ``StartView`` est public ; il ne fait qu'ouvrir un parcours privé ;
- toutes les autres réponses sont éphémères : ``send_message(ephemeral=True)``, ``followup.send(ephemeral=True)``
  ou ``edit_message`` sur le message éphémère du parcours ;
- chaque action n'agit que sur le parcours vivant du membre qui clique (identifiant Discord) :
  aucun composant ne peut atteindre le parcours de quelqu'un d'autre.

DURABILITÉ (2026-10-12, après le signalement « le bot cherche dans le vide et dit que ce n'est plus
possible, il faut tout recommencer ») :
- tous les composants des étapes portent des identifiants FIXES, sans délai, et sont enregistrés au
  démarrage (``persistent_views``, appelé par ``bot.py``) : ils continuent de fonctionner après un
  redémarrage du bot. Avant, chaque vue portait un identifiant tiré au hasard : après un
  redémarrage (ou au bout d'une heure), un clic dans une étape n'était plus reconnu par le bot et
  Discord affichait « interaction échouée » — le parcours était à recommencer ;
- les parcours en cours sont conservés dans ``state/sessions.json`` (voir ``utils/session.py``) :
  une mise à jour du bot ne fait plus perdre un questionnaire commencé ;
- ``step_for`` est le SEUL endroit qui décide de l'étape affichée, d'après les réponses déjà
  enregistrées : un clic rejoué ou un ancien message rouvrent le questionnaire là où il en était ;
- toute erreur inattendue est tracée dans le journal ET expliquée à l'utilisateur (``on_error``) ;
  aucune interaction ne reste sans réponse.

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
from typing import Sequence

import discord

from config import COMMERCIAL_LINKS_PATH, IMAGES_CONFIG_PATH, MOUSE_DB_PATH, SESSION_TTL_SECONDS
from utils.assets import load_image_urls
from utils.catalog import CatalogError, load_catalog, load_commercial_links
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
    CLAW_VARIANT_LABELS,
    ClawVariant,
    GRIP_LABELS,
    THENAR_LABELS,
    BudgetMode,
    Grip,
    HandMeasure,
    Thenar,
)
from utils.selection import (
    QUALITE_PRIX_TOLERANCE_POINTS,
    TOLERANCE_BY_MODE,
    Selection,
    _same_shell,
    select,
)
from utils.session import LOOKUP_OK, FinderSession
from utils.validation import InputError, parse_budget, parse_hand_measures

log = logging.getLogger(__name__)

START_CUSTOM_ID = "mouse_finder:start"

# Identifiants FIXES des composants d'étapes (voir DURABILITÉ en tête de fichier) : ils ne doivent
# jamais changer, sinon les messages déjà affichés chez les membres deviendraient muets.
GRIP_CUSTOM_ID = "mouse_finder:grip"
CLAW_VARIANT_CUSTOM_ID = "mouse_finder:claw_variant"
THENAR_CUSTOM_ID = "mouse_finder:thenar"
MEASURE_CUSTOM_ID = "mouse_finder:measures"
BUDGET_CUSTOM_ID = "mouse_finder:budget"
MEASURE_MODAL_CUSTOM_ID = "mouse_finder:measures_modal"
BUDGET_MODAL_CUSTOM_ID = "mouse_finder:budget_modal"

# --- Palette AzeMouse (voir docs/REPORTE_DESIGN.md §4) ---------------------
NAVY = discord.Color.from_rgb(11, 18, 32)        # #0B1220 Nuit  — référencée dans les illustrations
BORDEAUX = discord.Color.from_rgb(138, 35, 66)   # #8A2342 Bordeaux — couleur latérale des embeds
SPARK = discord.Color.from_rgb(240, 196, 60)     # #F0C43C Étincelle — jamais en aplat, images uniquement
COLOR = BORDEAUX
COLOR_EXPIRED = discord.Color.orange()           # seule exception à la charte (session expirée)

SCORE_DISCLAIMER = (
    "Score géométrique provisoire : ni une probabilité d'achat ni une validation biomécanique. "
    "Le calcul est expliqué dans le bloc « Comment lire ce résultat », plus bas."
)
BUTTON_LABEL_MAX = 80

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

# Conseils de forme par prise (vidéo Oblivity et outil de référence) : ils servent au bloc
# « comment lire ce résultat », jamais au calcul — voir docs/REPORTE_DESIGN.md §9.
HUMP_GUIDE = {
    Grip.PALM: ("au milieu ou à l'avant",
                "la bosse suit l'arche naturelle de la paume : la main repose à plat, le poignet reste libre."),
    Grip.CLAW: ("au milieu ou à l'arrière",
                "la bosse soutient l'arche transverse de la main et garde les doigts arqués."),
}
# Bosse conseillée selon la variante de Claw déclarée (l'outil de référence en distingue trois).
CLAW_HUMP_GUIDE = {
    ClawVariant.RELACHEE: ("arrière marquée",
                           "l'arrière de la souris vient remplir la paume : appui franc, main stable."),
    ClawVariant.AGGRESSIVE: ("médiane marquée",
                             "l'appui se fait au-dessus du milieu de la souris, les doigts restent arqués."),
    ClawVariant.PINCEE: ("arrière, flancs peu bombés",
                         "l'auriculaire se pose plus loin, sur un flanc plat : la souris reste « pincée »."),
}
# Forme de coque conseillée selon la prise (la forme de la souris retenue est citée à côté).
SHAPE_GUIDE = {
    Grip.PALM: ("formes **symétriques** comme **ergonomiques** conviennent au palm grip — "
                "une forme **ergonomique** épouse un peu mieux l'arche de la main."),
    Grip.CLAW: ("en claw grip, les formes **symétriques** conviennent aux trois variantes "
                "(une ergonomique basse peut aussi faire l'affaire)."),
}
SHAPE_DISPLAY = {"Symmetrical": "symétrique", "Ergonomic": "ergonomique", "Inconnu": "non vérifiée"}
# Forme affichée en bout de ligne du match idéal / de l'alternative (demande du propriétaire) :
# « tout à droite », lisible d'un coup d'œil. Forme non vérifiée = rien plutôt qu'une mention inutile.
SHAPE_LINE_LABELS = {"Symmetrical": "Symétrique", "Ergonomic": "Ergonomique"}
BUTTON_GUIDE = {
    Grip.PALM: ("hauts",
                "les doigts reposent à plat : des boutons hauts évitent de tirer sur les tendons."),
    Grip.CLAW: ("bas",
                "les doigts restent relâchés : des boutons hauts les obligeraient à tirer vers l'arrière."),
    Grip.FINGERTIP: ("médians à bas",
                     "des boutons hauts poussent les doigts vers le haut et tendent les tendons."),
}
# Variantes de la prise Claw : (illustration T04–T06, libellé, conseil pratique de la variante).
# La bosse attendue, elle, est décrite une seule fois dans CLAW_HUMP_GUIDE.
CLAW_VARIANTS = {
    ClawVariant.RELACHEE: ("illustration_grip_relaxed", "Claw relâchée",
                           "Doigts légèrement arqués et paume posée : cherchez une souris qui remplit la "
                           "main sans forcer, avec une bosse franche sous la paume."),
    ClawVariant.AGGRESSIVE: ("illustration_grip_aggressive", "Claw agressive",
                             "Doigts très arqués : la bosse doit tomber sous le milieu de la paume et "
                             "l'avant de la souris rester bas."),
    ClawVariant.PINCEE: ("illustration_grip_pincer", "Claw pincée",
                         "Souris pincée entre le pouce et l'annulaire : des flancs plats et un arrière "
                         "étroit rendent la prise plus sûre."),
}
# Illustration à montrer dans la recommandation, selon la souris retenue (sa bosse, ses boutons).
HUMP_IMAGE_BY_FAMILY = {"Front": "illustration_hump_front", "Mid": "illustration_hump_mid",
                        "Rear": "illustration_hump_rear"}
BUTTON_IMAGE_BY_HEIGHT = {"High": "illustration_buttons_high", "Mid": "illustration_buttons_mid",
                          "Low": "illustration_buttons_low"}
# Illustration des conseils de forme : elle montre ce qui est conseillé pour la prise, pas la souris.
HUMP_IMAGE_BY_GRIP = {Grip.PALM: "illustration_hump_mid", Grip.CLAW: "illustration_hump_rear"}
BUTTON_IMAGE_BY_GRIP = {Grip.PALM: "illustration_buttons_high", Grip.CLAW: "illustration_buttons_low",
                        Grip.FINGERTIP: "illustration_buttons_mid"}

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
# Étape supplémentaire, posée UNIQUEMENT en Claw (méthode Oblivity : trois variantes de prise).
CLAW_VARIANT_OPTIONS = (
    (ClawVariant.RELACHEE, "Claw relâchée",
     "Main posée, doigts légèrement arqués — l'arrière de la souris remplit la paume"),
    (ClawVariant.AGGRESSIVE, "Claw agressive",
     "Doigts très arqués, paume peu posée — appui au-dessus du milieu de la souris"),
    (ClawVariant.PINCEE, "Claw pincée",
     "Souris pincée, auriculaire posé plus loin sur le flanc"),
)
BUDGET_OPTIONS = (
    (BudgetMode.ECONOMIQUE, "Économique", "Le moins cher de la zone compatible"),
    (BudgetMode.QUALITE_PRIX, "Rapport Qualité/Prix", "Meilleur points/€ (indicatif)"),
    (BudgetMode.HAUT_DE_GAMME, "Haut de Gamme", "Performances documentées les plus élevées"),
    (BudgetMode.PEU_IMPORTE_PRIX, "Peu importe le prix",
     "La forme la plus adaptée, puis les composants les plus actuels"),
    (BudgetMode.CUSTOM, "Budget personnalisé", "Saisir un prix maximum en €"),
)
# Libellés courts utilisés dans le récapitulatif (le catalogue garde ses libellés complets).
BUDGET_RECAP_LABELS = {mode: label for mode, label, _ in BUDGET_OPTIONS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _send_ephemeral(interaction: discord.Interaction, content: str | None = None, *,
                          embed: discord.Embed | None = None,
                          view: discord.ui.View | None = None) -> None:
    """Envoie un message éphémère, en tenant compte de l'état de la réponse.

    Ne lève jamais d'exception : si l'interaction a expiré, l'erreur est journalisée seulement.
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, embed=embed, ephemeral=True, view=view)
        else:
            await interaction.response.send_message(content, embed=embed, ephemeral=True, view=view)
    except (discord.HTTPException, discord.ClientException) as exc:
        log.warning("Impossible de répondre à l'interaction (expirée ?) : %s", exc)


def _expired_text() -> str:
    """Explique l'expiration avec le vrai délai (aucune durée inventée) et propose la reprise."""
    minutes = max(1, round(SESSION_TTL_SECONDS / 60))
    return (
        f"⏱️ **Ce parcours a expiré** (plus de {minutes} min sans réponse) : pour votre "
        "confidentialité, les réponses ne sont pas conservées.\n\n"
        "Appuyez sur le bouton ci-dessous pour repartir du début : le questionnaire se relance "
        "ici, sans rien chercher dans le salon."
    )


async def _current_session(interaction: discord.Interaction) -> FinderSession | None:
    """Parcours vivant du membre qui clique ; sinon message clair AVEC le bouton de reprise.

    Le rattachement se fait par l'identifiant Discord : un composant ne peut jamais atteindre le
    parcours d'un autre membre (aucune donnée de parcours ne circule dans le message).
    """
    session, status = interaction.client.sessions.current(interaction.user.id)
    if status == LOOKUP_OK and session is not None:
        return session
    # Raison affichée (le délai réel, jamais un texte vague) ET reprise immédiate dans le message.
    await _send_ephemeral(interaction, _expired_text(), embed=expired_embed(), view=StartView())
    return None


def _remember(interaction: discord.Interaction) -> None:
    """Enregistre l'état du parcours tout de suite, après chaque réponse.

    Sans cet appel, une réponse donnée juste avant un redémarrage du bot serait perdue (le fichier
    d'état n'aurait que l'état précédent). L'écriture est atomique et ne peut pas faire échouer le
    parcours : toute erreur de disque est journalisée par le magasin de sessions.
    """
    interaction.client.sessions.save()


async def _handle_unexpected_error(interaction: discord.Interaction, error: Exception) -> None:
    """Dernier filet de sécurité : l'erreur est tracée en entier, l'utilisateur est prévenu.

    Sans ce filet, Discord affiche « interaction échouée » et le membre croit le bot cassé.
    """
    log.exception("Erreur inattendue dans le parcours : %s", error, exc_info=error)
    await _send_ephemeral(
        interaction,
        "⚠️ **Une erreur inattendue est survenue.** Rien n'est perdu : refaites l'action, et si cela "
        "se reproduit, relancez le test depuis le bouton **Start Mouse Shape Finder** du salon.",
    )


async def _show_private(interaction: discord.Interaction, **kwargs) -> None:
    """Affiche une étape ou un résultat en PRIVÉ.

    Cas normal : remplace le message éphémère d'origine (bouton, menu ou modal lancé depuis ce message).
    Repli 1 : Discord ne fournit pas le message d'origine (modal non lié à un composant).
    Repli 2 : l'édition est refusée (message supprimé par le membre, interaction déjà répondue) :
    un nouveau message éphémère est alors envoyé. Dans tous les cas, rien n'est publié dans le salon
    et l'utilisateur n'est jamais laissé sans réponse.
    """
    if interaction.message is not None:
        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(**kwargs)
            else:
                await interaction.response.edit_message(**kwargs)
            return
        except (discord.HTTPException, discord.ClientException) as exc:
            log.warning("Message du parcours non modifiable (%s) : envoi d'un nouveau message privé.", exc)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(ephemeral=True, **kwargs)
        else:
            await interaction.response.send_message(ephemeral=True, **kwargs)
    except (discord.HTTPException, discord.ClientException) as exc:
        log.warning("Affichage privé impossible : %s", exc)


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
    """Nombre d'étapes : 3 en Fingertip (pas de thénar), 5 en Claw (variante en plus), 4 sinon."""
    grip = getattr(session_or_grip, "grip", session_or_grip)
    if grip is Grip.FINGERTIP:
        return 3
    if grip is Grip.CLAW:
        return 5
    return 4


# Numéro d'étape par type, selon la prise : Claw insère « variante » en 2, Fingertip saute le thénar.
STEP_NUMBERS = {
    Grip.PALM: {"thenar": 2, "measure": 3, "budget": 4},
    Grip.CLAW: {"variant": 2, "thenar": 3, "measure": 4, "budget": 5},
    Grip.FINGERTIP: {"measure": 2, "budget": 3},
}


def _step_number(kind: str, session_or_grip) -> int:
    grip = getattr(session_or_grip, "grip", session_or_grip)
    return STEP_NUMBERS[grip][kind]


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
        grip = f"✋ **{GRIP_LABELS[session.grip]}**"
        if session.claw_variant is not None:
            # La variante ne s'affiche que pour la prise Claw, sous forme courte (« (relâchée) »).
            grip += f" ({CLAW_VARIANT_LABELS[session.claw_variant].removeprefix('Claw ')})"
        parts.append(grip)
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


def _match_summary(score: MouseScore) -> str:
    """Ce qui colle et ce qui colle moins, en clair : jamais une valeur du barème.

    C'est la phrase qui relie la souris choisie aux repères de taille affichés juste au-dessus.
    """
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
    elif score.is_partial:
        # Critère non documenté (2026-10-12) : la souris est notée sans lui, et on le dit.
        weak.append("hauteur des boutons non documentée : ce critère n'est pas noté")
    sentence = ", ".join(good[:3]) if good else "géométrie proche de votre profil"
    sentence = sentence[0].upper() + sentence[1:]       # première lettre — SANS écraser « Palm Grip »
    sentence += f". À noter : {', '.join(weak[:1])}." if weak else "."
    return sentence[:1024]


def _weight_text(mouse) -> str:
    """Poids documenté (« 54 g ») — chaîne vide s'il n'est pas connu : jamais estimé."""
    return f"{_num(mouse.weight_g)} g" if mouse.weight_g else ""


def _components_text(mouse) -> str:
    """Composants documentés d'une souris : capteur, fréquence, switchs, MCU — rien de déduit.

    Un champ absent n'apparaît pas : une donnée manquante n'est pas un défaut de la souris.
    """
    parts = []
    if mouse.sensor:
        parts.append(mouse.sensor)
    if mouse.polling_hz:
        parts.append(f"{mouse.polling_hz:,}".replace(",", " ") + " Hz")
    if mouse.switches:
        parts.append(mouse.switches)
    if mouse.mcu:
        parts.append(mouse.mcu)
    return " · ".join(parts)


def _slot_text(score: MouseScore, mode: BudgetMode | None = None) -> str:
    """Une souris recommandée : nom · poids · prix · pourcentage · forme, sur une ligne.

    Le poids documenté et la forme de coque (« Symétrique » / « Ergonomique », tout à droite) sont
    mis en avant dès la première ligne (demande du propriétaire, 2026-10-11) : ils permettent de
    comparer le match idéal et l'alternative d'un coup d'œil. Ni score
    brut, ni badge de confiance, ni commentaire : tout cela vit dans les blocs plus bas. Seul le
    mode « Peu importe le prix » ajoute une seconde ligne, en tout petit : le prix (sans effet sur
    ce classement) et les composants documentés, qui départagent les égalités de forme.
    """
    mouse = score.mouse
    parts = [f"**{mouse.label}**"]
    weight = _weight_text(mouse)
    if weight:
        parts.append(weight)
    if mode is not BudgetMode.PEU_IMPORTE_PRIX:
        parts.append(_price_text(score))
    parts.append(f"**{compatibility_percent(score)} %**")
    shape = SHAPE_LINE_LABELS.get(mouse.shape)
    if shape:
        parts.append(shape)          # tout à droite : symétrique ou ergonomique
    line = " · ".join(parts)
    if mode is not BudgetMode.PEU_IMPORTE_PRIX:
        return line
    small = f"-# 💰 {_price_text(score)} — sans effet sur ce classement"
    components = _components_text(mouse)
    if components:
        small += f" · ⚙️ {components}"
    return f"{line}\n{small}"


def _price_or_inf(score: MouseScore) -> float:
    return score.mouse.price_eur if score.mouse.price_eur is not None else float("inf")


def result_slots(selection: Selection) -> tuple[MouseScore | None, MouseScore | None, MouseScore | None]:
    """Trois rôles, dans l'ordre du classement déjà calculé : idéal, alternative, économie.

    (1) **Le match idéal** : la tête du classement du mode (le prix suit, sauf budget contraint).
    (2) **L'alternative** : la souris qui correspond le mieux au profil parmi celles qui restent,
        en préférant une souris un peu moins chère ; sinon la meilleure tout court (son pourcentage
        sert alors à accepter un léger surcoût).
    (3) **L'économie** : la moins chère qui reste dans la zone de compatibilité du mode (tolérance
        ``TOLERANCE_BY_MODE``) et qui est vraiment moins chère que les deux autres ; sinon la ligne
        n'est pas affichée.

    Aucun barème n'est modifié : les trois souris sortent du classement existant, jamais recalculé.
    """
    ordered = list(selection.ranked)
    if not ordered:
        return None, None, None
    ideal = ordered[0]
    # Deux places du résultat ne montrent jamais la MÊME coque (2026-10-12) : proposer
    # « ATK GHOST Ultimate » puis « ATK GHOST Extreme » n'apporte aucun choix — même forme, même
    # prise, seules la finition et le prix changent. On écarte donc, pour l'alternative uniquement,
    # les variantes de la coque déjà retenue ; si la zone n'offre rien d'autre, on reprend la liste
    # complète (jamais moins de résultats qu'avant).
    def not_same_shell(other: MouseScore) -> bool:
        return not _same_shell(ideal, other)

    reference = selection.reference_score if selection.reference_score is not None else ideal.total
    tolerance = TOLERANCE_BY_MODE.get(selection.mode, QUALITE_PRIX_TOLERANCE_POINTS)
    zone = [score for score in ordered[1:] if score.total >= reference - tolerance]

    def best_match(candidates: list[MouseScore]) -> MouseScore | None:
        # Le meilleur profil ; à égalité, la moins chère.
        return max(candidates, key=lambda score: (score.total, -_price_or_inf(score))) if candidates else None

    ideal_price = _price_or_inf(ideal)
    distinct_zone = [score for score in zone if not_same_shell(score)] or zone
    cheaper = [score for score in distinct_zone if _price_or_inf(score) < ideal_price]
    alternative = best_match(cheaper) or best_match(distinct_zone)

    # (3) L'économie : la moins chère de la zone de compatibilité, d'une AUTRE coque si possible, et
    # strictement moins chère que les deux souris déjà montrées. Mesure du 2026-10-12 : cette place
    # n'est remplie que dans 0,1 % des profils, parce que la zone de tolérance du mode (±2 points sur
    # 40) est étroite et que l'alternative, elle, prend déjà la meilleure des souris moins chères.
    # Ce n'est donc pas un bug de calcul mais un effet de seuil : élargir la zone est une décision du
    # propriétaire (voir docs/audit/ROBUSTESSE_2026-10-12.md §5).
    shown_ids = {ideal.mouse.id}
    if alternative is not None:
        shown_ids.add(alternative.mouse.id)
    candidates = [score for score in sorted(zone, key=lambda s: (_price_or_inf(s), -s.total))
                  if score.mouse.id not in shown_ids]
    other_shell = [score for score in candidates if not_same_shell(score)] or candidates

    # Elle doit être moins chère que TOUT ce qui est déjà à l'écran : une souris plus chère que le
    # match idéal ne serait pas « l'économie », et une souris au même prix que l'alternative
    # n'apporterait aucun choix.
    ceiling = min(ideal_price, _price_or_inf(alternative) if alternative is not None else ideal_price)
    economy = next((score for score in other_shell if _price_or_inf(score) < ceiling), None)
    return ideal, alternative, economy


# ---------------------------------------------------------------------------
# Embeds d'accueil et d'étapes
# ---------------------------------------------------------------------------
def banner_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🖱️ AzeMouse — Mouse Shape Finder",
        description=(
            "Trouvez la souris dont la géométrie épouse **votre** main.\n\n"
            "Quelques questions rapides : prise, mesures, budget — thénar et variante de Claw "
            "selon la prise.\n\n"
            "*Réponses privées : seul vous voyez la recommandation.*"
        ),
        color=COLOR,
    )
    return _image(embed, "banner")


def grip_step_embed() -> discord.Embed:
    description = "\n\n".join(f"**{label}** — {desc}" for _, label, desc in GRIP_OPTIONS)
    embed = discord.Embed(
        # Pas de dénominateur : le nombre d'étapes dépend de la prise choisie (3 en Fingertip, 4 sinon).
        title="Étape 1 — Votre prise",
        description=f"Quelle prise utilisez-vous le plus souvent ?\n\n{description}",
        color=COLOR,
    )
    return _image(embed, "step1_grip")


def claw_variant_step_embed() -> discord.Embed:
    description = "\n\n".join(f"**{label}** — {desc}" for _, label, desc in CLAW_VARIANT_OPTIONS)
    embed = discord.Embed(
        title=_step_title(2, Grip.CLAW, "Votre variante de Claw"),
        description=(
            "Les trois variantes de Claw ne placent pas la bosse au même endroit.\n\n"
            f"{description}\n\n"
            "Cette réponse **ne change pas le score** : elle précise le conseil de bosse."
        ),
        color=COLOR,
    )
    return _image(embed, "illustration_grip_relaxed")


def thenar_step_embed(grip: Grip = Grip.PALM) -> discord.Embed:
    embed = discord.Embed(
        title=_step_title(_step_number("thenar", grip), grip, "Votre éminence thénar"),
        description=(
            "Votre réponse indique l'arrière de souris qui vous convient : un petit thénar préfère un "
            "arrière étroit, un grand thénar est soutenu par un arrière marqué.\n\n"
            "Effet **borné à ±2 points** sur le score, et **uniquement** pour les souris à bosse "
            "arrière marquée — sinon le score ne change pas."
        ),
        color=COLOR,
    )
    return _image(embed, "step2_thenar")


def measure_step_embed(session: FinderSession) -> discord.Embed:
    embed = discord.Embed(
        title=_step_title(_step_number("measure", session), session, "Vos mesures"),
        description=(
            f"{_recap(session)}\n\n"
            "Avec une règle :\n\n"
            "• **Longueur** : pli du poignet → bout du majeur.\n"
            "• **Largeur** : articulations, **sans le pouce**."
        ),
        color=COLOR,
    )
    return _image(embed, "step2_measure")


def budget_step_embed(session: FinderSession) -> discord.Embed:
    embed = discord.Embed(
        title=_step_title(_step_number("budget", session), session, "Budget et gamme"),
        description=f"{_recap(session)}\n\nChoisissez votre gamme de prix.",
        color=COLOR,
    )
    return _image(embed, "step3_budget")


def _hump_family(mouse) -> str | None:
    """Famille de bosse d'une souris : « Front », « Mid », « Rear » — None si inconnue."""
    tokens = set((mouse.hump_position or "").split("-"))
    for family in ("Rear", "Front", "Mid"):
        if family in tokens:
            return family
    return None


def result_image_key(winner: MouseScore | None, grip: Grip | None) -> str | None:
    """Illustration la plus utile : la bosse d'abord (ressenti), les boutons ensuite. Une seule image."""
    if winner is None:
        return None
    mouse = winner.mouse
    if grip in (Grip.PALM, Grip.CLAW):
        family = _hump_family(mouse)
        if family:
            return HUMP_IMAGE_BY_FAMILY[family]
    return BUTTON_IMAGE_BY_HEIGHT.get(mouse.button_height)


def _hand_of(session: FinderSession) -> HandMeasure | None:
    """Mesures de la main, ou ``None`` tant qu'elles ne sont pas saisies (jamais de valeur par défaut)."""
    if not session.has_measures:
        return None
    return HandMeasure(float(session.hand_length_mm), float(session.hand_width_mm))


def _dimensions_embed(session: FinderSession, ideal: MouseScore,
                      explanation: str) -> discord.Embed | None:
    """Bloc « repères de taille » : les plages cibles, la souris retenue en clair, le pourquoi du choix.

    ``None`` si le parcours est incomplet : aucun repère n'est alors inventé.
    """
    hand = _hand_of(session)
    if session.grip is None or hand is None:
        return None
    ranges = compute_target_ranges(hand, session.grip)
    length = (
        f"jusqu'à {_num(ranges.length_max, 1)} mm"
        if session.grip is Grip.FINGERTIP
        else f"{_num(ranges.length_min, 1)}–{_num(ranges.length_max, 1)} mm"
    )
    embed = discord.Embed(
        title="📐 Vos repères de taille",
        description=(
            f"**Longueur cible : {length}**\n"
            "du talon arrière de la souris à la pointe avant.\n\n"
            f"**Largeur de prise : {_num(ranges.width_min, 1)}–{_num(ranges.width_max, 1)} mm**\n"
            "souris retournée, à hauteur du capteur.\n\n"
            f"Score : **{ideal.total}/{MAX_SCORE} — {compatibility_percent(ideal)} %** du maximum théorique\n"
            "(longueur, largeur de prise, compatibilité de prise, bosse, boutons)."
            + (
                "\n\n**Hauteur des boutons non documentée** pour cette souris : ce critère n'est pas "
                "noté (aucun point inventé) ; elle est classée sur les critères disponibles."
                if ideal.is_partial else ""
            )
        ),
        color=COLOR,
    )
    embed.add_field(
        name=f"🔎 {ideal.mouse.label} en clair",
        value=f"{_size_text(ideal.mouse)} · {_price_text(ideal)}\n{_match_summary(ideal)}"[:1024],
        inline=False,
    )
    embed.add_field(name="🧭 Pourquoi ce choix ?", value=explanation[:1024], inline=False)
    return _image(embed, "illustration_mouse_dimensions")


def _narrow_rear_embed() -> discord.Embed:
    """Bloc « arrière étroit », affiché seulement si le thénar déclaré est « Petite » (Palm/Claw)."""
    embed = discord.Embed(
        title="🖐️ Un arrière étroit pour votre thénar",
        description=(
            "Votre thénar est **Petite** : un arrière étroit, en « pilule », laisse la main se poser "
            "sans forcer.\n\n"
            "Une souris à bosse arrière marquée est **pénalisée à la marge** dans le score."
        ),
        color=COLOR,
    )
    return _image(embed, "illustration_rear_narrow")


def _hump_guide_embed(session: FinderSession, ideal: MouseScore) -> discord.Embed | None:
    """Bloc « la bosse et la forme » : où placer la bosse et quelle coque choisir pour la prise choisie.

    Rien en Fingertip : cette prise n'utilise ni l'arrière ni la bosse (barème et outil de référence
    sont d'accord là-dessus).
    """
    grip = session.grip
    if grip not in HUMP_GUIDE:
        return None
    if grip is Grip.CLAW and session.claw_variant is not None:
        # La variante déclarée précise la bosse attendue (Claw relâchée ≠ agressive ≠ pincée).
        position, why = CLAW_HUMP_GUIDE[session.claw_variant]
        entete = f"**{CLAW_VARIANT_LABELS[session.claw_variant]} → bosse {position}.**"
    else:
        position, why = HUMP_GUIDE[grip]
        entete = f"**{grip.label} → bosse {position}.**"
    shape = SHAPE_DISPLAY.get(ideal.mouse.shape, SHAPE_DISPLAY["Inconnu"])
    embed = discord.Embed(
        title="⛰️ La bosse et la forme",
        description=(
            f"{entete}\n\n{why[0].upper()}{why[1:]}\n\n"
            f"**Forme** — {SHAPE_GUIDE[grip]}\n\n"
            f"La souris retenue est **{shape}**."
        ),
        color=COLOR,
    )
    # L'image montre la bosse conseillée pour la prise (la souris retenue, elle, illustre le bloc du haut).
    return _image(embed, HUMP_IMAGE_BY_GRIP[grip])


def _claw_variant_embeds(session: FinderSession) -> list[discord.Embed]:
    """La variante de Claw déclarée, illustrée (T04–T06). Affichée pour cette prise seulement.

    Repli : si la variante n'a pas été demandée (parcours ouvert avant l'ajout de l'étape), les trois
    variantes sont présentées, faute de savoir laquelle s'applique.
    """
    if session.grip is not Grip.CLAW:
        return []
    if session.claw_variant is None:
        # Repli : les trois variantes, avec la bosse attendue pour chacune.
        embeds = []
        for variant, (image_key, title, _) in CLAW_VARIANTS.items():
            position, why = CLAW_HUMP_GUIDE[variant]
            embeds.append(_image(
                discord.Embed(title=f"🦾 {title}", description=f"Bosse **{position}** : {why}", color=COLOR),
                image_key,
            ))
        return embeds
    image_key, title, tip = CLAW_VARIANTS[session.claw_variant]
    embed = discord.Embed(title=f"🦾 {title}",
                          description=f"**Votre variante.** {tip}",
                          color=COLOR)
    return [_image(embed, image_key)]


def _buttons_guide_embed(session: FinderSession) -> discord.Embed | None:
    """Bloc « la hauteur des boutons » : le niveau conseillé pour la prise choisie.

    ``None`` si la prise n'est pas encore connue (aucun conseil inventé).
    """
    grip = session.grip
    if grip not in BUTTON_GUIDE:
        return None
    level, why = BUTTON_GUIDE[grip]
    embed = discord.Embed(
        title="🖱️ La hauteur des boutons",
        description=f"**{grip.label} → boutons {level}.**\n\n{why[0].upper()}{why[1:]}",
        color=COLOR,
    )
    return _image(embed, BUTTON_IMAGE_BY_GRIP[grip])


def results_embeds(session: FinderSession, selection: Selection) -> list[discord.Embed]:
    """Résultat en un seul message, jamais en onglet : la recommandation, puis l'explication plus bas.

    Bloc 1 — **la recommandation** : la ligne du parcours, puis le match idéal, l'alternative et, si
    elle existe, l'économie (nom · prix · pourcentage du maximum théorique). Rien d'autre à l'écran :
    ni score, ni badge, ni terme technique.

    Puis les blocs de compréhension, dans l'ordre de l'outil de référence : repères de taille,
    arrière (thénar « Petite »), bosse — et ses trois variantes en Claw —, hauteur des boutons.
    Chaque bloc porte son illustration (assets/images.json) ; aucun n'est affiché « pour rien ».
    """
    main = discord.Embed(title="🎯 Votre recommandation", color=COLOR)
    header = _recap(session)
    if session.budget_mode is None:
        # Mode absent : le récapitulatif ne porte pas la gamme, on l'indique explicitement.
        header = f"{header}  •  🎚️ **Classement morphologique**"
    main.description = header[:4096]

    ideal, alternative, economy = result_slots(selection)
    if ideal is None:
        main.add_field(
            name="Aucun match classable",
            value=(
                "Aucune souris ne peut être classée avec les données vérifiées pour ces critères. "
                "Essayez une autre gamme ou un budget plus élevé."
            ),
            inline=False,
        )
        main.set_footer(text=SCORE_DISCLAIMER)
        return [main]

    main.add_field(name="🥇 Le match idéal", value=_slot_text(ideal, session.budget_mode), inline=False)
    if alternative is not None:
        main.add_field(name="🥈 L'alternative", value=_slot_text(alternative, session.budget_mode), inline=False)
    if economy is not None:
        main.add_field(name="💸 L'économie", value=_slot_text(economy, session.budget_mode), inline=False)
    image_key = result_image_key(ideal, session.grip)
    if image_key:
        main = _image(main, image_key)

    if session.grip is None or not session.has_measures:
        # Parcours incomplet : rien à expliquer, et surtout aucune valeur inventée.
        main.set_footer(text=SCORE_DISCLAIMER)
        return [main]

    embeds = [main]
    dimensions = _dimensions_embed(session, ideal, selection.explanation)
    if dimensions is not None:
        embeds.append(dimensions)
    if session.thenar is Thenar.PETITE and session.grip is not Grip.FINGERTIP:
        embeds.append(_narrow_rear_embed())
    hump = _hump_guide_embed(session, ideal)
    if hump is not None:
        embeds.append(hump)
    embeds.extend(_claw_variant_embeds(session))
    buttons = _buttons_guide_embed(session)
    if buttons is not None:
        embeds.append(buttons)
    embeds[-1].set_footer(text=SCORE_DISCLAIMER)
    return embeds


def expired_embed() -> discord.Embed:
    """Embed orange du message d'expiration (seule exception à la charte) ; la reprise est dessous."""
    minutes = max(1, round(SESSION_TTL_SECONDS / 60))
    return discord.Embed(
        title="⏱️ Session expirée",
        description=(
            f"Plus de {minutes} min sans réponse : pour votre confidentialité, les réponses ne sont "
            "pas conservées.\n\n"
            "Le bouton **ci-dessous** relance le questionnaire ici même, sans rien chercher dans le salon."
        ),
        color=COLOR_EXPIRED,
    )


# ---------------------------------------------------------------------------
# Calcul
# ---------------------------------------------------------------------------
def compute_selection(session: FinderSession) -> Selection:
    """Lecture à chaud du catalogue (les données ne sont jamais mises en cache)."""
    if session.grip is None or not session.has_measures:
        raise ValueError("Parcours incomplet : la prise et les mesures de la main sont nécessaires.")
    mice = load_catalog(MOUSE_DB_PATH)
    hand = HandMeasure(session.hand_length_mm, session.hand_width_mm)
    scores = [
        evaluate_mouse(mouse, hand, session.grip, session.budget_mode, session.max_budget_eur,
                       thenar=session.thenar)
        for mouse in mice
    ]
    # top_n = toutes les souris classées : la présentation en choisit trois (match idéal,
    # alternative, économie) sans jamais recalculer ni modifier les scores.
    return select(scores, session.budget_mode, top_n=len(scores))


# ---------------------------------------------------------------------------
# Vues et modals
# ---------------------------------------------------------------------------
class FinderView(discord.ui.View):
    """Base des vues du parcours : aucune donnée n'est publiée dans le salon."""

    def __init__(self) -> None:
        super().__init__(timeout=None)          # composant durable : jamais désactivé par le temps

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        await _handle_unexpected_error(interaction, error)


class FinderModal(discord.ui.Modal):
    def __init__(self, title: str, custom_id: str) -> None:
        super().__init__(title=title, custom_id=custom_id, timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await _handle_unexpected_error(interaction, error)


def step_kind(session: FinderSession) -> str:
    """Étape du questionnaire d'après les réponses DÉJÀ enregistrées (jamais un état inventé)."""
    if session.grip is None:
        return "grip"
    if session.grip is Grip.CLAW and session.claw_variant is None:
        return "claw_variant"
    if session.grip is not Grip.FINGERTIP and session.thenar is None:
        return "thenar"
    if not session.has_measures:
        return "measure"
    return "budget"


def step_for(session: FinderSession) -> tuple[discord.Embed, discord.ui.View]:
    """Étape à afficher, avec ses composants, pour l'état actuel du parcours.

    Seul endroit qui décide de l'étape : chaque réponse enregistre sa donnée puis redemande
    l'étape courante. Un clic rejoué, un ancien message ou une relance du bot rouvrent donc le
    questionnaire exactement là où il en était, au lieu de le casser.
    """
    kind = step_kind(session)
    if kind == "grip":
        return grip_step_embed(), GripView()
    if kind == "claw_variant":
        return claw_variant_step_embed(), ClawVariantView()
    if kind == "thenar":
        grip = session.grip if session.grip is not None else Grip.PALM
        return thenar_step_embed(grip), ThenarView()
    if kind == "measure":
        return measure_step_embed(session), MeasureView()
    return budget_step_embed(session), BudgetView()


async def _show_step(interaction: discord.Interaction, session: FinderSession) -> None:
    """Affiche l'étape courante : utilisé par TOUTES les réponses du questionnaire."""
    embed, view = step_for(session)
    await _show_private(interaction, embed=embed, view=view)


# ---------------------------------------------------------------------------
# Accueil (vue persistante : custom_id fixe, enregistrée au démarrage du bot)
# ---------------------------------------------------------------------------
class StartView(FinderView):
    @discord.ui.button(
        label="Start Mouse Shape Finder",
        style=discord.ButtonStyle.primary,
        emoji="🖱️",
        custom_id=START_CUSTOM_ID,
    )
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Nouveau parcours : il remplace le précédent du même membre (un seul parcours vivant).
        session = interaction.client.sessions.start(interaction.user.id)
        step_embed, step_view = step_for(session)
        try:
            await interaction.response.send_message(embed=step_embed, view=step_view, ephemeral=True)
        except discord.InteractionResponded:
            # Double appui (fréquent sur mobile) : la première réponse est déjà partie et le parcours
            # est ouvert. Aucune erreur affichée, aucune seconde session créée.
            return


# ---------------------------------------------------------------------------
# Étape 1 : prise (grip)
# ---------------------------------------------------------------------------
class GripSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            custom_id=GRIP_CUSTOM_ID,
            placeholder="Choisissez votre prise…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=grip.value, description=desc)
                for grip, label, desc in GRIP_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await _current_session(interaction)
        if session is None:
            return
        grip = Grip(self.values[0])
        if session.grip is not grip:
            # Changer de prise remet à zéro les questions qui en dépendent (variante, thénar).
            session.thenar = None
            session.claw_variant = None
        session.grip = grip
        if grip is Grip.FINGERTIP:
            # L'arrière de la souris n'est pas utilisé dans cette prise : ni variante, ni thénar,
            # et aucune note « arrière étroit » (bosse ignorée par le barème).
            session.thenar = None
            session.claw_variant = None
        _remember(interaction)
        await _show_step(interaction, session)


class GripView(FinderView):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(GripSelect())


# ---------------------------------------------------------------------------
# Étape 2 (Claw uniquement) : variante de la prise — n'entre dans aucun calcul, précise le conseil
# ---------------------------------------------------------------------------
class ClawVariantSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            custom_id=CLAW_VARIANT_CUSTOM_ID,
            placeholder="Choisissez votre variante de Claw…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=variant.value, description=desc)
                for variant, label, desc in CLAW_VARIANT_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await _current_session(interaction)
        if session is None:
            return
        session.claw_variant = ClawVariant(self.values[0])   # stocké et affiché uniquement
        _remember(interaction)
        await _show_step(interaction, session)


class ClawVariantView(FinderView):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(ClawVariantSelect())


# ---------------------------------------------------------------------------
# Étape 3 : éminence thénar (ajustement borné du sous-score de largeur : THENAR_WIDTH_ADJUSTMENT)
# ---------------------------------------------------------------------------
class ThenarSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            custom_id=THENAR_CUSTOM_ID,
            placeholder="Choisissez la taille de votre thénar…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=thenar.value, description=desc)
                for thenar, label, desc in THENAR_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await _current_session(interaction)
        if session is None:
            return
        session.thenar = Thenar(self.values[0])  # stocké ; ajustement borné au calcul du score
        _remember(interaction)
        await _show_step(interaction, session)


class ThenarView(FinderView):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(ThenarSelect())


# ---------------------------------------------------------------------------
# Mesures (bouton -> modal)
# ---------------------------------------------------------------------------
class MeasureModal(FinderModal):
    def __init__(self) -> None:
        super().__init__(title="Mesure de votre main", custom_id=MEASURE_MODAL_CUSTOM_ID)
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
        session = await _current_session(interaction)
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
        _remember(interaction)
        await _show_step(interaction, session)


class MeasureView(FinderView):
    @discord.ui.button(label="Saisir mes mesures", style=discord.ButtonStyle.primary, emoji="📏",
                       custom_id=MEASURE_CUSTOM_ID)
    async def open_measures(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        session = await _current_session(interaction)
        if session is None:
            return
        if step_kind(session) != "measure":
            # Le questionnaire n'est pas à cette étape (ancien message, clic rejoué) : on réaffiche
            # l'étape réelle plutôt que d'ouvrir un formulaire qui n'a plus de sens.
            await _show_step(interaction, session)
            return
        try:
            await interaction.response.send_modal(MeasureModal())
        except discord.InteractionResponded:
            # Double appui (fréquent sur mobile) : le premier formulaire est déjà ouvert.
            return


# ---------------------------------------------------------------------------
# Budget (select -> modal si budget personnalisé)
# ---------------------------------------------------------------------------
class BudgetSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            custom_id=BUDGET_CUSTOM_ID,
            placeholder="Choisissez votre gamme…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=mode.value, description=desc)
                for mode, label, desc in BUDGET_OPTIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        session = await _current_session(interaction)
        if session is None:
            return
        mode = BudgetMode(self.values[0])
        if mode is BudgetMode.CUSTOM:
            # Le modal est la réponse à cette interaction ; la session est mise à jour à la soumission.
            try:
                await interaction.response.send_modal(BudgetModal())
            except discord.InteractionResponded:
                return          # double appui : un formulaire est déjà ouvert
            return
        session.budget_mode = mode
        session.max_budget_eur = None
        _remember(interaction)
        await _show_results(interaction, session)


class BudgetView(FinderView):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(BudgetSelect())


class BudgetModal(FinderModal):
    def __init__(self) -> None:
        super().__init__(title="Budget personnalisé", custom_id=BUDGET_MODAL_CUSTOM_ID)
        self.price = discord.ui.TextInput(
            label="Prix maximum (€)",
            placeholder="Ex : 60",
            required=True,
            min_length=1,
            max_length=8,
        )
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        session = await _current_session(interaction)
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
        _remember(interaction)
        await _show_results(interaction, session)


# ---------------------------------------------------------------------------
# Résultat final (privé) et fermeture
# ---------------------------------------------------------------------------
async def _show_results(interaction: discord.Interaction, session: FinderSession) -> None:
    """Calcule et affiche le résultat ; ne laisse jamais le membre sans réponse."""
    if session.grip is None or not session.has_measures:
        # Parcours incomplet (relance, interaction rejouée) : on reprend à l'étape manquante.
        await _show_step(interaction, session)
        return
    try:
        selection = compute_selection(session)
    except (CatalogError, OSError, ValueError) as exc:
        log.exception("Catalogue illisible : %s", exc)
        await _send_ephemeral(
            interaction,
            "⚠️ **Les données des souris sont momentanément illisibles.** Réessayez dans un instant ; "
            "si le problème persiste, prévenez la personne qui gère le bot.",
        )
        return
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    embeds = results_embeds(session, selection)
    # Les boutons d'achat suivent EXACTEMENT les souris affichées (match idéal, alternative,
    # économie). Avant, ils suivaient les deux premiers du classement interne — qui ne sont pas
    # toujours les souris montrées : le membre voyait une souris sans bouton, et un bouton pour une
    # souris absente du message.
    displayed = [score for score in result_slots(selection) if score is not None]
    # Minimisation : le parcours est TERMINÉ (ses réponses sont retirées du fichier d'état) ; il
    # reste quelques minutes en mémoire pour qu'un clic rejoué par Discord reçoive le même résultat
    # au lieu du message « ce parcours n'est plus actif ».
    interaction.client.sessions.finish(session.session_id)
    # Les deux blocs sont toujours affichés : la recommandation, puis l'explication plus bas.
    await _show_private(interaction, embeds=embeds, view=ResultsView(displayed, links))


def persistent_views() -> tuple[discord.ui.BaseView, ...]:
    """Composants durables à enregistrer au démarrage du bot (``bot.add_view``).

    Sans cet enregistrement, Discord continue d'afficher les menus mais le bot ne reconnaît plus les
    clics après un redémarrage : c'est exactement la panne corrigée le 2026-10-12.
    """
    return (StartView(), GripView(), ClawVariantView(), ThenarView(), MeasureView(), BudgetView(),
            MeasureModal(), BudgetModal())


class ResultsView(discord.ui.View):
    """Boutons d'achat du résultat : des LIENS, gérés par Discord, jamais par le bot.

    « Fermer », « Refaire le test » et « Détails » ont été retirés le 2026-10-11 : ces boutons
    interactifs pouvaient cesser de répondre après un redémarrage du bot (« AzeMouse n'a pas
    répondu à temps »). Un lien, lui, ne dépend pas du bot et fonctionne toujours ; le message
    éphémère se ferme avec la croix du client Discord, et un nouveau test se lance depuis le
    panneau du salon. Conséquence : plus aucun bouton du résultat ne peut rester muet.
    """

    def __init__(self, displayed: Sequence[MouseScore], links: dict[str, str]) -> None:
        """``displayed`` : les souris MONTREÉES dans le message, dans l'ordre (match idéal,
        alternative, économie). Un bouton par souris affichée — jamais pour une souris absente."""
        super().__init__(timeout=None)
        purchases = 0
        seen: set[str] = set()
        for score in displayed:
            if score.mouse.id in seen:
                continue
            seen.add(score.mouse.id)
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
