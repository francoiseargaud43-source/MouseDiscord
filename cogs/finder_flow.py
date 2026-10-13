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
thénar n'est pas posée : 3 étapes). Le thénar sert à lire l'arrière de la souris : **conseil indicatif**,
sans aucun effet sur le score (règle « zéro effet » du MASTER_PROMPT §7.6 : le barème est strictement le
même quel que soit le thénar déclaré). Le mécanisme d'ajustement borné existe mais est en pause, valeurs
neutres (``THENAR_WIDTH_ADJUSTMENT`` dans utils/matcher.py ; méthode : docs/REVERSE_ENGINEERING_OBLIVITY.md).

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
    "Score géométrique provisoire : ni une probabilité d'achat ni une validation biomécanique."
)
# Renvoi vers un bloc qui EXISTE. Le pied de page est posé sur le dernier bloc du message, et le bloc
# « Pourquoi ce choix ? » vit dans les repères de taille : la phrase ne dit donc aucune direction
# (« plus bas » était faux, et le bloc « Comment lire ce résultat » n'existe plus depuis le
# 2026-10-11). Correction autorisée par le propriétaire le 2026-10-13 (point ouvert C27).
EXPLANATION_REFERENCE = " Le calcul est expliqué dans le bloc « 🧭 Pourquoi ce choix ? »."
# Marqueur des souris au score partiel (hauteur des boutons non documentée, décision du propriétaire du
# 2026-10-13) : la note longue n'existe que dans le bloc « 📐 Vos repères de taille », écrit pour le
# MATCH IDÉAL seul — les 2e et 3e places portent donc ce marqueur discret à la fin de leur ligne.
PARTIAL_HINT = "boutons non documentés"
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


# Numéro d'étape par type, selon la prise : Claw insère « claw_variant » en 2, Fingertip saute le thénar.
# Les clés sont EXACTEMENT les valeurs de ``step_kind()`` : c'est ce qui permet de numéroter l'étape
# courante sans table parallèle (défaut trouvé le 2026-10-13 : la table disait « variant » là où
# ``step_kind`` disait « claw_variant », et le titre de cette étape écrivait son numéro en dur).
# Cette table est la SEULE source des numéros d'étapes : le total affiché (« Étape n/N ») en est le
# plus grand numéro, il n'est pas réécrit ailleurs (même famille de défaut, corrigée en C42).
STEP_NUMBERS = {
    Grip.PALM: {"grip": 1, "thenar": 2, "measure": 3, "budget": 4},
    Grip.CLAW: {"grip": 1, "claw_variant": 2, "thenar": 3, "measure": 4, "budget": 5},
    Grip.FINGERTIP: {"grip": 1, "measure": 2, "budget": 3},
}

# L'étape « prise » ouvre tous les parcours : c'est le numéro que la table lui donne pour les trois
# prises. Elle n'affiche pas de dénominateur, la prise n'étant pas encore connue (voir grip_step_embed).
GRIP_STEP_NUMBER = STEP_NUMBERS[Grip.PALM]["grip"]


def _step_number(kind: str, session_or_grip) -> int:
    """Numéro de l'étape demandée pour cette prise.

    Une étape qui n'existe pas pour la prise (le thénar en Fingertip, la variante de Claw hors Claw)
    n'a pas de numéro : le dire clairement plutôt que de laisser remonter un ``KeyError`` muet, qui
    ne dit ni la prise ni l'étape fautive.
    """
    grip = getattr(session_or_grip, "grip", session_or_grip)
    numeros = STEP_NUMBERS.get(grip)
    if numeros is None or kind not in numeros:
        prise = grip.label if isinstance(grip, Grip) else repr(grip)
        etapes = ", ".join(numeros) if numeros else "aucune"
        raise ValueError(f"Étape « {kind} » inexistante en {prise} (étapes de cette prise : {etapes}).")
    return numeros[kind]


def _steps_total(session_or_grip) -> int:
    """Nombre d'étapes de la prise : le plus grand numéro de ``STEP_NUMBERS``.

    Dérivé de la table, jamais écrit en clair : ajouter ou retirer une étape dans ``STEP_NUMBERS``
    suffit alors à corriger le « /N » affiché. Un total écrit en dur formait une seconde table — et un
    total faux reste plausible, donc invisible (même famille de défaut que C41).
    """
    grip = getattr(session_or_grip, "grip", session_or_grip)
    numeros = STEP_NUMBERS.get(grip)
    if not numeros:
        prise = grip.label if isinstance(grip, Grip) else repr(grip)
        raise ValueError(f"Prise « {prise} » : aucune étape déclarée, donc aucun total à afficher.")
    return max(numeros.values())


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
    """Prix lisible. ``verified_hint`` ajoute « (prix non vérifié) » quand le prix n'est pas attesté.

    Le marqueur est **actif dans le résultat** depuis la décision du propriétaire du 2026-10-13 : le
    master prompt le montre dans ses exemples (« 74.90 € (prix non vérifié) »), mais l'onglet
    « Détails » qui le portait a été retiré le 2026-10-11 et aucun appelant ne l'activait plus — un
    prix non attesté s'affichait donc exactement comme un prix vérifié, sur 17 % des résultats. Les
    lignes de place l'activent désormais (`_slot_text`), y compris la petite ligne de prix du mode
    « Peu importe le prix », où c'est le seul endroit où le prix apparaît.
    """
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
        # Le sens de l'écart (trop long / trop court) n'est pas porté par le score : la phrase
        # reste donc neutre. Avant, elle affirmait « en léger retrait » même pour une souris plus
        # longue que la cible (correctif du 2026-10-12).
        weak.append("longueur un peu hors de la cible")
    if score.breakdown.width_pts == WIDTH_PTS_IN_RANGE:
        good.append("largeur de prise dans la cible")
    elif score.breakdown.width_pts > 0:
        weak.append("largeur de prise proche de la cible")
    else:
        # Idem : « un peu large » était faux pour une souris PLUS ÉTROITE que la cible, cas réel
        # dès qu'une grande main cherche une souris fine (mesuré au banc d'essai).
        weak.append("largeur de prise un peu hors de la cible")
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


def _slot_text(score: MouseScore, mode: BudgetMode | None = None, *, partial_hint: bool = False) -> str:
    """Une souris recommandée : nom · poids · prix · pourcentage · forme, sur une ligne.

    Le poids documenté et la forme de coque (« Symétrique » / « Ergonomique », tout à droite) sont
    mis en avant dès la première ligne (demande du propriétaire, 2026-10-11) : ils permettent de
    comparer le match idéal et l'alternative d'un coup d'œil. Ni score
    brut, ni badge de confiance, ni commentaire : tout cela vit dans les blocs plus bas. Seul le
    mode « Peu importe le prix » ajoute une seconde ligne, en tout petit : le prix (sans effet sur
    ce classement) et les composants documentés, qui départagent les égalités de forme.

    ``partial_hint`` ajoute « boutons non documentés » à la fin de la ligne (décision du propriétaire,
    2026-10-13) : la note complète du bloc « 📐 Vos repères de taille » n'est écrite que pour le match
    idéal, donc une souris au score partiel en 2e ou 3e place affichait son pourcentage — calculé SANS
    le critère des boutons, donc sous-estimé — sans que rien ne le dise (**8 187 places** sur 27 170
    profils, mesuré le 2026-10-13). Le marqueur ne touche ni le score ni le classement.
    """
    mouse = score.mouse
    parts = [f"**{mouse.label}**"]
    weight = _weight_text(mouse)
    if weight:
        parts.append(weight)
    if mode is not BudgetMode.PEU_IMPORTE_PRIX:
        parts.append(_price_text(score, verified_hint=True))
    parts.append(f"**{compatibility_percent(score)} %**")
    shape = SHAPE_LINE_LABELS.get(mouse.shape)
    if shape:
        parts.append(shape)          # tout à droite : symétrique ou ergonomique
    if partial_hint and score.is_partial:
        parts.append(PARTIAL_HINT)   # score calculé sans les boutons : le dire (2026-10-13)
    line = " · ".join(parts)
    if mode is not BudgetMode.PEU_IMPORTE_PRIX:
        return line
    small = f"-# 💰 {_price_text(score, verified_hint=True)} — sans effet sur ce classement"
    components = _components_text(mouse)
    if components:
        small += f" · ⚙️ {components}"
    return f"{line}\n{small}"


def _price_or_inf(score: MouseScore) -> float:
    return score.mouse.price_eur if score.mouse.price_eur is not None else float("inf")


# ---------------------------------------------------------------------------
# Fenêtres des trois places (décision du propriétaire, 2026-10-12 : l'expérience utilisateur prime)
# ---------------------------------------------------------------------------
# Mesures d'origine (grille de 27 170 profils) : avec une zone unique de ±2 points, 4 472 profils
# (16,5 %) affichaient deux fois la même coque et la troisième place « Économie » ne sortait que dans
# 0,3 % des cas — deux effets de seuil, pas des bugs.
# Décision retenue :
#   • l'ALTERNATIVE garde la zone étroite du mode (±2) ; si cette zone ne contient que des variantes de
#     la coque déjà montrée, la recherche s'élargit UNE fois à ±5 points pour proposer une vraie autre
#     forme ; si rien n'existe, la variante est conservée (jamais moins de résultats qu'avant) ;
#   • l'ÉCONOMIE dispose de sa propre fenêtre (±5 points) : une option moins chère mérite d'être montrée
#     même si elle perd quelques points, à condition d'être strictement moins chère que les deux autres
#     et, si possible, d'une autre coque ;
#   • ORDRE GARANTI (décision du propriétaire, 2026-10-13) : le pourcentage ne remonte jamais d'une
#     place à l'autre — la 2e ne dépasse pas le match idéal, la 3e ne dépasse pas la 2e. La règle
#     s'applique à la sélection de chaque place (``sous_plafond``), pas à l'affichage : le score n'est
#     jamais retouché, c'est la souris choisie qui change. Repli documenté : si le plafond ne laisse
#     aucun candidat, la place reste remplie (jamais de trou) et le banc compte ces profils.
ALTERNATIVE_EXTENSION_POINTS = 5
ECONOMY_SLOT_TOLERANCE_POINTS = 5
# Dernier palier (décision du propriétaire, 2026-10-12) : quand ni « l'économie » ni « l'autre option »
# de la fenêtre ne donnent quelque chose à montrer — Budget personnalisé serré, ou souris suivante très
# loin derrière — la place reste remplie par la **meilleure souris restante du classement**, affichée
# sous son vrai nom : « 🔎 Autre piste ». Son pourcentage reste affiché tel quel, donc le membre voit
# immédiatement que la piste est loin. Le classement n'est jamais franchi vers une souris hors budget :
# en Budget personnalisé, le plafond reste la règle. Mesuré sur le banc du parcours : 2 747 profils
# (10,1 % de la grille, 13,6 % des profils avec un résultat) avaient une place vide avec au moins une
# souris abordable — comblement possible, budget respecté.
PISTE_TITLE = "🔎 Autre piste"


def mode_tolerance(mode: BudgetMode | None) -> int:
    """Tolérance du mode (la zone dans laquelle une souris reste « comparable » au match idéal)."""
    return TOLERANCE_BY_MODE.get(mode, QUALITE_PRIX_TOLERANCE_POINTS)


def result_slots(selection: Selection) -> tuple[MouseScore | None, MouseScore | None, MouseScore | None]:
    """Trois rôles, dans l'ordre du classement déjà calculé : idéal, alternative, économie.

    (1) **Le match idéal** : la tête du classement du mode (le prix suit, sauf budget contraint).
    (2) **L'alternative** : la souris qui correspond le mieux au profil parmi celles qui restent,
        en préférant une souris un peu moins chère ; sinon la meilleure tout court (son pourcentage
        sert alors à accepter un léger surcoût). Elle reste dans la zone du mode ; elle n'en sort que
        si cette zone ne contient rien d'autre que la coque déjà montrée (élargissement unique). Si
        même cet élargissement ne donne rien, la place prend la meilleure souris restante et s'intitule
        « Autre piste » (``alternative_slot_title``) : jamais de ligne vide au milieu du résultat.
    (3) **L'économie** : la moins chère de sa propre fenêtre (``ECONOMY_SLOT_TOLERANCE_POINTS``) qui
        est vraiment moins chère que les deux autres. À défaut, depuis la décision du propriétaire du
        2026-10-12, l'option la moins chère restante de cette fenêtre — même un peu plus chère que le
        match idéal — et la ligne s'intitule alors « L'autre option ». Si la fenêtre elle-même est
        vide, la place prend la meilleure souris restante du classement (``PISTE_TITLE``, « Autre
        piste ») : jamais une ligne blanche quand une souris est montrable dans le budget.

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
    tolerance = mode_tolerance(selection.mode)

    def in_window(score: MouseScore, margin: int) -> bool:
        return score.total >= reference - margin

    zone = [score for score in ordered[1:] if in_window(score, tolerance)]
    distinct_zone = [score for score in zone if not_same_shell(score)]

    def best_match(candidates: list[MouseScore]) -> MouseScore | None:
        # Le meilleur profil ; à égalité, la moins chère.
        return max(candidates, key=lambda score: (score.total, -_price_or_inf(score))) if candidates else None

    def sous_plafond(candidates: list[MouseScore], plafond: int) -> list[MouseScore]:
        """Candidats d'une place : jamais mieux notés que la place du dessus (décision du 2026-10-13).

        Le pourcentage affiché ne remonte donc jamais d'une ligne à l'autre : la deuxième place ne
        peut pas dépasser le match idéal, la troisième ne peut pas dépasser la deuxième. Avant, cela
        arrivait — **1 622 profils (6,0 %)** montraient une deuxième place mieux notée que le match
        idéal (en mode Économique, le match idéal est la souris la MOINS CHÈRE de la zone : une souris
        mieux notée mais plus chère le dépassait donc en deuxième ligne), et la troisième place
        dépassait la deuxième sur 24 à 128 profils selon le mode. Le membre lisait alors un « idéal »
        moins bien noté que la ligne du dessous : cela ressemble à une erreur de calcul.

        Filtre STRICT : quand le plafond ne laisse aucun candidat dans la fenêtre de la place, le
        moteur élargit sa recherche SOUS le plafond (classement entier) avant de renoncer à l'ordre —
        voir les derniers paliers de chaque place. Le seul cas où l'ordre cède est celui où aucune
        souris du classement ne passe sous le plafond : la place reste alors remplie (règle du
        2026-10-12 : jamais de trou dans le résultat) et le banc d'essai compte ces profils sous le nom
        « ordre non garanti » — mesuré, jamais supposé.

        Le plafond porte sur les points du barème (sur 40) : comme le pourcentage affiché est
        proportionnel à ces points (``compatibility_percent`` = points × 100 / 40, arrondi), il ne peut
        pas remonter quand les points ne remontent pas — la garantie vaut donc aussi pour le nombre
        affiché, sans second plafond. Vérifié sur la grille complète : 84 violations en points = 84 en
        pourcentages, aucune divergence.
        """
        return [score for score in candidates if score.total <= plafond]

    ideal_price = _price_or_inf(ideal)
    plafond_ideal = ideal.total
    zone = sous_plafond(zone, plafond_ideal)
    distinct_zone = [score for score in zone if not_same_shell(score)]
    if distinct_zone:
        # Cas normal : une autre coque est déjà dans la zone du mode. On préfère la moins chère
        # (c'est le rôle de cette place) ; à défaut, la mieux notée de la zone.
        cheaper = [score for score in distinct_zone if _price_or_inf(score) < ideal_price]
        alternative = best_match(cheaper) or best_match(distinct_zone)
    else:
        # Zone composée uniquement de variantes de la coque déjà montrée : élargissement UNIQUE
        # (2026-10-12) à ``ALTERNATIVE_EXTENSION_POINTS``, et seulement vers une souris qui ne coûte
        # pas plus cher que le match idéal — jamais une souris à la fois moins bien notée et plus
        # chère. Sans candidat, on reprend la zone telle quelle : jamais moins de résultats qu'avant.
        extension = [score for score in ordered[1:]
                     if in_window(score, ALTERNATIVE_EXTENSION_POINTS) and not_same_shell(score)]
        extension = sous_plafond(extension, plafond_ideal)
        alternative = best_match([score for score in extension if _price_or_inf(score) <= ideal_price]) \
            or best_match(zone)

    if alternative is None:
        # Dernier palier appliqué à la DEUXIÈME place (même décision du 2026-10-12) : la zone du mode
        # est vide ou ne contient que des variantes de la coque retenue, et l'élargissement n'a rien
        # donné de moins cher. La deuxième ligne reste alors remplie par la meilleure souris restante,
        # montrée sous le titre « 🔎 Autre piste » (``third_slot_title``) — le résultat ne comporte
        # jamais de trou au milieu, et son pourcentage dit à lui seul que la piste est loin.
        restants = [score for score in ordered[1:] if not_same_shell(score)]
        alternative = best_match(sous_plafond(restants, plafond_ideal)) or best_match(restants)

    # (3) La troisième place : la moins chère de sa propre fenêtre (``ECONOMY_SLOT_TOLERANCE_POINTS``)
    # qui est vraiment moins chère que les deux autres (« l'économie ») ; **à défaut**, depuis la
    # décision du propriétaire du 2026-10-12, l'option la moins chère restante de la fenêtre, même un
    # peu plus chère que le match idéal — sans quoi la place disparaissait quand le match idéal était
    # déjà la souris la moins chère du catalogue (VXE V3 à 13,95 € : 594 profils passaient de trois
    # places à deux, mesuré). Le libellé suit la réalité du prix (``third_slot_title``).
    shown_ids = {ideal.mouse.id}
    if alternative is not None:
        shown_ids.add(alternative.mouse.id)
    # Plafond de la troisième place : le score de la DEUXIÈME (ou du match idéal si elle manque),
    # par la même règle d'ordre (décision du propriétaire, 2026-10-13).
    plafond_economie = alternative.total if alternative is not None else plafond_ideal
    economy_window = [score for score in ordered[1:] if in_window(score, ECONOMY_SLOT_TOLERANCE_POINTS)]
    candidates = sous_plafond(
        [score for score in sorted(economy_window, key=lambda s: (_price_or_inf(s), -s.total))
         if score.mouse.id not in shown_ids],
        plafond_economie)

    # Elle doit être moins chère que TOUT ce qui est déjà à l'écran : une souris plus chère que le
    # match idéal ne serait pas « l'économie », et une souris au même prix que l'alternative
    # n'apporterait aucun choix.
    ceiling = min(ideal_price, _price_or_inf(alternative) if alternative is not None else ideal_price)
    below = [score for score in candidates if _price_or_inf(score) < ceiling]
    # « d'une AUTRE coque si possible » : la préférence s'applique PARMI les souris sous le plafond,
    # jamais au prix de la place elle-même. Correctif du 2026-10-12 : en filtrant d'abord sur la
    # coque, la place disparaissait dès que la moins chère d'une autre coque dépassait le plafond
    # (mesure sur 1 029 profils : 2 profils au lieu de 4) — l'inverse de la règle annoncée.
    def other_shell(score: MouseScore) -> bool:
        """Aucune des deux places déjà affichées ne partage sa coque avec cette souris.

        Le principe « deux places du résultat ne montrent jamais la même coque » (décision du
        2026-10-12) vaut pour les TROIS places : une troisième ligne qui reprend la coque du match
        idéal ou de l'alternative n'offre aucun choix de forme.
        """
        if _same_shell(ideal, score):
            return False
        return alternative is None or not _same_shell(alternative, score)

    different_shell = [score for score in below if other_shell(score)]
    economy = (different_shell or below)[0] if (different_shell or below) else None
    if economy is None and candidates:
        # Aucune souris moins chère que le plafond : décision du propriétaire (2026-10-12), la place
        # reste remplie par l'option la MOINS CHÈRE de la fenêtre du mode — donc « un peu plus chère »
        # au minimum possible. À prix comparable, une autre coque passe devant : mesuré sur la grille
        # de référence, 2 175 profils (15,84 % des trois places) montraient une variante d'une coque
        # déjà affichée, dont 1 338 avec une autre coque disponible (surcoût médian +4,00 €, 61 % sous
        # +10 €) et 837 sans aucune autre coque dans la fenêtre.
        autre_coque = [score for score in candidates if other_shell(score)]
        economy = (autre_coque or candidates)[0]
    if economy is None:
        # Dernier palier (décision du propriétaire, 2026-10-12) : ni la fenêtre du mode ni « l'autre
        # option » de cette fenêtre ne donnent quoi que ce soit — soit le mode est un Budget
        # personnalisé si serré que le plafond a tout écarté, soit la souris suivante est très loin
        # derrière (10 à 25 points mesurés sur le banc). La place reste remplie par la meilleure souris
        # restante : la ligne dit alors « 🔎 Autre piste » avec son pourcentage, donc jamais une
        # promesse exagérée. Le budget reste la règle : en Budget personnalisé, le classement ne
        # contient déjà que des souris conformes au plafond (``evaluate_mouse`` les écarte sinon).
        restants = [score for score in ordered[1:] if score.mouse.id not in shown_ids]
        sous_plafond_restants = sous_plafond(restants, plafond_economie)
        autre_coque = [score for score in sous_plafond_restants if other_shell(score)]
        # Dernier recours (ordre non garanti, compté par le banc) : aucune souris du classement ne
        # passe sous le plafond de la deuxième place — la ligne reste remplie quand même.
        economy = best_match(autre_coque or sous_plafond_restants) or best_match(restants)
    return ideal, alternative, economy


def alternative_slot_title(alternative: MouseScore, ideal: MouseScore,
                           reference: int | None = None, tolerance: int | None = None) -> str:
    """Titre de la deuxième place : « 🥈 L'alternative » ou, si elle vient du dernier palier, « Autre piste ».

    Le titre ne fait que **redire la règle du moteur** : une alternative comparable est dans la zone du
    mode (``tolerance``) ou dans l'élargissement unique à ``ALTERNATIVE_EXTENSION_POINTS`` sans coûter
    plus cher que le match idéal. Tout le reste est une piste — la meilleure souris restante, choisie
    pour ne pas laisser de ligne vide (décision du propriétaire, 2026-10-12).

    Sans ``reference`` ni ``tolerance`` (appel direct dans un test ou un outil), le titre reste celui de
    la place : le moteur ne produit une piste que dans les cas décrits ci-dessus.
    """
    if reference is None or tolerance is None:
        return "🥈 L'alternative"
    if alternative.total >= reference - tolerance:
        return "🥈 L'alternative"
    if alternative.total >= reference - ALTERNATIVE_EXTENSION_POINTS \
            and _price_or_inf(alternative) <= _price_or_inf(ideal):
        return "🥈 L'alternative"
    return PISTE_TITLE


def third_slot_title(economy: MouseScore, ideal: MouseScore,
                     alternative: MouseScore | None = None,
                     reference: int | None = None) -> str:
    """Titre de la troisième place : le rôle réel, jamais un rôle supposé.

    Trois cas, dans l'ordre (décisions du propriétaire, 2026-10-12) :

    1. ``💸 L'économie`` — elle est *strictement moins chère* que tout ce qui est affiché : c'est un
       fait sur le prix, vérifiable d'un coup d'œil, et c'est le rôle premier de cette ligne ;
    2. ``🔎 Autre piste`` — elle n'est pas moins chère **et** se situe hors de la fenêtre de la place
       (plus de ``ECONOMY_SLOT_TOLERANCE_POINTS`` sous le meilleur score) : c'est le dernier palier,
       elle n'est comparable ni au match idéal ni à l'alternative, et le titre le dit ;
    3. ``➕ L'autre option`` — elle est dans la fenêtre mais plus chère (ou au même prix) : le libellé
       reste honnête.

    ``reference`` est le meilleur score du mode, tel que ``Selection.reference_score`` : sans lui
    (appel direct dans un test ou un outil), la distinction « piste » n'est pas faite et le titre
    reste celui du prix. Le reste de la ligne (nom · prix · % du maximum théorique) ne change pas.
    """
    plafond = _price_or_inf(ideal)
    if alternative is not None:
        plafond = min(plafond, _price_or_inf(alternative))
    if _price_or_inf(economy) < plafond:
        # Le prix d'abord : « l'économie » est un fait vérifiable (574 profils de la grille, soit 1,8 %
        # des trois places, l'affichent alors même qu'elle est hors de la fenêtre des ±5 points).
        return "💸 L'économie"
    if reference is not None and economy.total < reference - ECONOMY_SLOT_TOLERANCE_POINTS:
        return PISTE_TITLE
    return "➕ L'autre option"


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
        # Pas de dénominateur : le nombre d'étapes dépend de la prise choisie (3 en Fingertip,
        # 4 en Palm, 5 en Claw) et la prise n'est pas encore connue à cette étape. Le numéro, lui,
        # vient de la table (GRIP_STEP_NUMBER) : il n'est pas réécrit ici.
        title=f"Étape {GRIP_STEP_NUMBER} — Votre prise",
        description=f"Quelle prise utilisez-vous le plus souvent ?\n\n{description}",
        color=COLOR,
    )
    return _image(embed, "step1_grip")


def claw_variant_step_embed() -> discord.Embed:
    description = "\n\n".join(f"**{label}** — {desc}" for _, label, desc in CLAW_VARIANT_OPTIONS)
    embed = discord.Embed(
        title=_step_title(_step_number("claw_variant", Grip.CLAW), Grip.CLAW, "Votre variante de Claw"),
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
            "**Information seule : le thénar ne modifie pas le score** (recommandation morphologique "
            "indicative, non prise en compte dans le calcul)."
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
            "Votre éminence thénar est **petite** : un arrière étroit, en « pilule », laisse la main se "
            "poser sans forcer.\n\n"
            "**Information seule** : le thénar ne modifie pas le score — c'est un repère "
            "morphologique, pas un critère de calcul."
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
            # Le message nomme ce que le membre a fourni (prise, mesures, gamme ou budget) et rien
            # d'autre : l'ancien texte — « avec les données vérifiées pour ces critères » — accusait
            # le catalogue dans les trois cas réels où cette carte s'affiche (mesures hors de la
            # plage des 36 souris, budget trop serré, gamme sans candidat), alors que des souris
            # classables existent. Corrigé le 2026-10-13 (46e passe, C59).
            value=(
                "Aucune souris ne peut être retenue avec ces critères. "
                "Essayez une autre gamme ou un budget plus élevé."
            ),
            inline=False,
        )
        main.set_footer(text=SCORE_DISCLAIMER)
        return [main]

    main.add_field(name="🥇 Le match idéal", value=_slot_text(ideal, session.budget_mode), inline=False)
    if alternative is not None:
        main.add_field(name=alternative_slot_title(alternative, ideal, selection.reference_score,
                                                  mode_tolerance(selection.mode)),
                       value=_slot_text(alternative, session.budget_mode, partial_hint=True), inline=False)
    if economy is not None:
        main.add_field(name=third_slot_title(economy, ideal, alternative, selection.reference_score),
                       value=_slot_text(economy, session.budget_mode, partial_hint=True), inline=False)
    image_key = result_image_key(ideal, session.grip)
    if image_key:
        main = _image(main, image_key)

    if session.grip is None or not session.has_measures:
        # Parcours incomplet : rien à expliquer, et surtout aucune valeur inventée — et donc aucun
        # renvoi vers un bloc qui n'est pas là.
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
    # Le renvoi n'est ajouté que si le bloc « Pourquoi ce choix ? » est bien dans le message.
    embeds[-1].set_footer(
        text=SCORE_DISCLAIMER + (EXPLANATION_REFERENCE if dimensions is not None else ""))
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
            # Réémission de la MÊME interaction (double appui sur mobile, interaction rejouée par
            # Discord) : la réponse est déjà partie, on ne répond pas deux fois et rien ne s'affiche en
            # double. Le parcours créé juste au-dessus remplace l'éventuel précédent du même membre :
            # il n'y en a jamais deux vivants (vérifié par
            # tests/test_flow.py::test_deux_appuis_sur_le_panneau_ne_laissent_qu_un_parcours_vivant).
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
# Étape 3 : éminence thénar (informative : THENAR_WIDTH_ADJUSTMENT est en pause à 0 / 0 / 0)
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
        session.thenar = Thenar(self.values[0])  # stocké et affiché ; aucun effet sur le score
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
