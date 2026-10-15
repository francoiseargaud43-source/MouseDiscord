"""Banc d'essai du parcours : passe TOUTE la grille de profils dans le moteur et rend un rapport.

But : ne jamais découvrir en production un profil qui plante, qui ne renvoie rien du tout ou qui
produit un message hors des limites de Discord. L'outil n'écrit rien et ne modifie aucune donnée.

Usage :
    .venv/bin/python tools/qa_flow_matrix.py           # rapport complet
    .venv/bin/python tools/qa_flow_matrix.py --rapide  # grille réduite (intégration continue)

Contrôles effectués, profil par profil :
- aucune exception ne remonte ;
- le résultat n'est jamais vide (« Aucun match classable ») pour une main plausible ;
- les limites Discord sont respectées (2 à 10 blocs, ≤ 6 000 caractères par bloc, ≤ 25 champs,
  ≤ 1 024 caractères par champ, ≤ 4 096 pour la description, ≤ 5 boutons sur 2 rangées) ;
- le total de points reste dans 0...40 et le pourcentage affiché correspond ;
- deux places du résultat ne montrent jamais la même souris ;
- chaque souris montrée porte bien son NOM, son PRIX, son SCORE et son pourcentage (texte du message) ;
- aucun bouton d'achat pour une souris absente, et un bouton pour chaque souris affichée qui a un lien ;
- en budget personnalisé, aucune souris affichée au-dessus du budget ;
- aucune souris « en attente » (donnée manquante) ni « écartée » (prise faible) n'est affichée ;
- chaque place est contrôlée contre SA fenêtre : le match idéal est la tête du classement du mode,
  l'alternative reste dans la zone du mode ou n'en sort que si aucune autre coque ne s'y trouve (et
  jamais plus chère que le match idéal, hors le repli « même coque » documenté), la troisième place
  reste dans sa fenêtre propre (±5 points) tant que cette fenêtre offre une option, est la moins chère
  des options restantes de cette fenêtre qui ne reprennent pas une coque déjà affichée (préférence
  « jamais deux fois la même coque », appliquée aux trois places le 2026-10-12), et sinon prend la
  meilleure souris restante sous le titre « 🔎 Autre piste » ; dans tous les cas elle porte le bon
  libellé : « 💸 L'économie » si elle est moins chère que tout ce qui est affiché,
  « ➕ L'autre option » sinon (décision du propriétaire du 2026-10-12) ;
- **ordre garanti des pourcentages** (décision du propriétaire, 2026-10-13) : le pourcentage affiché
  ne remonte jamais d'une place à l'autre — la deuxième ne dépasse pas le match idéal, la troisième ne
  dépasse pas la deuxième ;
- **prix non attesté annoncé** : une souris dont le prix n'est pas `verified` affiche « (prix non
  vérifié) » à côté de son prix (décision du propriétaire, 2026-10-13) ;
- **score partiel annoncé** : une souris au score partiel (hauteur des boutons non documentée) affichée
  en 2e ou 3e place porte « boutons non documentés » (décision du propriétaire, 2026-10-13) ; pour le
  match idéal, la note longue du bloc « 📐 Vos repères de taille » en tient lieu ;
- **toutes** les limites Discord, blocs et composants : aucune n'était mesurée avant le 2026-10-14 en
  dehors de cinq limites de bloc sur le seul résultat ; le banc mesure désormais les neuf limites d'un
  bloc et les huit limites d'une vue, sur les écrans fixes, les étapes du profil et le résultat, et
  publie la limite la plus remplie du passage (marge mesurée, jamais supposée) ;
- comptage, sans le compter comme une faute, des profils où DEUX places montrent la même coque :
  c'est le repli documenté (« jamais moins de résultats qu'avant ») quand la zone de tolérance ne
  contient que des variantes de la coque retenue — il est mesuré, pas supposé ;
- comptage, sans le compter comme une faute, des profils où le plafond d'ordre n'a laissé aucun
  candidat : la place reste alors remplie (jamais de trou) et le pourcentage peut remonter.
"""
from __future__ import annotations

import argparse
import contextlib
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discord  # noqa: E402  (types des composants, pour mesurer leurs limites)

from cogs.finder_flow import (BudgetView, ClawVariantView,  # noqa: E402
                              GripView, MeasureView, ResultsView,
                              ThenarView, banner_embed, budget_step_embed, claw_variant_step_embed,
                              compute_selection, grip_step_embed, measure_step_embed,
                              mode_tolerance, result_slots, results_embeds, thenar_step_embed)
from config import COMMERCIAL_LINKS_PATH  # noqa: E402
from utils.catalog import load_commercial_links  # noqa: E402
from utils.matcher import MAX_SCORE, compatibility_percent  # noqa: E402
from utils.models import BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402
from utils.selection import _same_shell  # noqa: E402
from utils.slots import ALTERNATIVE_EXTENSION_POINTS, ECONOMY_SLOT_TOLERANCE_POINTS  # noqa: E402
from utils.session import FinderSession  # noqa: E402

LINKS = load_commercial_links(COMMERCIAL_LINKS_PATH)
GRIP_FIELD = {Grip.PALM: "palm_grip_fit", Grip.CLAW: "claw_grip_fit", Grip.FINGERTIP: "fingertip_grip_fit"}


def places_au_prix_non_verifie(slots) -> int:
    """Nombre de places affichées dont le prix n'est pas attesté.

    Chaque place dont la souris n'a pas `price_status == "verified"` porte le marqueur
    « (prix non vérifié) » à côté de son prix : c'est ce total que publient les documents
    (4 373 places le 2026-10-13 à la 35e passe, **3 332** à la 47e, une seule souris non
    attestée). Le chiffre suit les prix du catalogue : seul le banc d'essai fait foi.
    """
    return sum(1 for score in slots
               if score is not None and score.mouse.price_status != "verified")


def prix_fr(price: float) -> str:
    """« 68,95 € » — la virgule décimale française, telle qu'affichée au membre."""
    return f"{price:.2f}".replace(".", ",") + " €"


def message_text(embeds) -> str:
    """Tout le texte visible du résultat (titres, descriptions, champs), pour les contrôles de contenu."""
    morceaux = []
    for embed in embeds:
        morceaux += [embed.title or "", embed.description or "", embed.footer.text or ""]
        for field in embed.fields:
            morceaux += [field.name, field.value]
    return "\n".join(morceaux)


def deux_places_meme_coque(places) -> bool:
    """Vrai dès que **deux** des places affichées partagent une coque.

    Le repli documenté peut concerner **n'importe quelle paire** : le match idéal et l'alternative,
    l'alternative et l'économie, ou le match idéal et l'économie (quand la deuxième place a trouvé une
    autre coque et que la troisième reprend celle du match idéal). Ne regarder que les paires formées
    avec le match idéal sous-comptait : sur la grille du rapport, 966 profils contre **1 367** pour le
    rapport statistique, qui examine, lui, toutes les paires (`itertools.combinations`). Défaut corrigé
    le 2026-10-14 (61e passe) : le banc compte désormais la même chose que le rapport, avec le libellé
    qu'il publie déjà.
    """
    affichees = [s for s in places if s is not None]
    return any(_same_shell(premier, second) for premier, second in itertools.combinations(affichees, 2))


def check_result_message(session, selection, embeds, ideal, alternative, economy,
                         repli_coque=None, etiquette="", repli_ordre=None) -> list[str]:
    """Contrôles du CONTENU du message : chaque souris montrée doit l'être avec ses vrais chiffres.

    Les trois places sont passées **par rôle** (et non en liste filtrée) : quand l'alternative est
    vide, une liste de souris montrées décale l'économie à sa place et le banc la juge alors comme
    une alternative — c'est la cause des 40 avertissements fantômes du 2026-10-12, corrigée ici.
    """
    problems: list[str] = []
    if ideal is None and alternative is None and economy is None:
        return problems
    texte = message_text(embeds)
    # Ordre garanti (décision du propriétaire, 2026-10-13) : le pourcentage ne remonte JAMAIS d'une
    # place à l'autre. Le moteur l'obtient en plafonnant chaque place par celle du dessus ; le seul
    # cas où il ne peut pas (plafond ne laissant aucun candidat) est compté en « repli », pas
    # sanctionné — comme le repli de coque.
    plafond_ordre = alternative.total if alternative is not None else (ideal.total if ideal is not None else None)
    for premier, second, nom in ((ideal, alternative, "l'alternative"), (alternative, economy, "l'économie")):
        if premier is None or second is None or second.total <= premier.total:
            continue
        ligne = f"{etiquette} : {nom} ({second.mouse.label} {second.total}) mieux notée que la place du dessus ({premier.mouse.label} {premier.total})"
        if repli_ordre is not None:
            repli_ordre.append(ligne)
        else:                                       # pragma: no cover - appel direct hors banc
            problems.append(ligne)
    reference = selection.reference_score if selection.reference_score is not None else ideal.total
    # La tolérance vient du MOTEUR (`mode_tolerance`), jamais d'une valeur recopiée : si la
    # tolérance d'un mode change, le banc d'essai change avec lui (sinon il vérifierait
    # l'ancienne règle et laisserait passer la nouvelle).
    tolerance = mode_tolerance(selection.mode)

    # Zone de chaque place (décision du 2026-10-12) : le match idéal est la tête du classement ;
    # l'alternative reste dans la zone du mode, sauf si cette zone ne contient que des variantes de la
    # coque retenue — elle peut alors venir de la fenêtre d'élargissement, et seulement si elle est
    # moins chère que le match idéal ; l'économie a sa propre fenêtre et un plafond de prix.
    # Le match idéal est la tête du classement DU MODE : en Économique (et en Qualité/Prix), la tête
    # est la souris la moins chère de la zone de tolérance, donc légitimement jusqu'à `tolerance`
    # points sous la meilleure note du mode — c'est l'invariant vérifié dans tests/test_selection.py.
    if ideal is not None and selection.ranked and ideal.mouse.id != selection.ranked[0].mouse.id:
        problems.append(f"le match idéal n'est pas la tête du classement : {ideal.mouse.label}")
    # Dernier palier (décision du propriétaire, 2026-10-12) : quand ni la fenêtre du mode ni « l'autre
    # option » de cette fenêtre ne donnent quelque chose à montrer, la place est remplie par la meilleure
    # souris restante sous le titre « 🔎 Autre piste ». Sa zone est alors le classement entier : ce qu'on
    # vérifie, c'est le TITRE (le message dit-il la vérité ?), plus la fenêtre.
    def _prix(score) -> float:
        return score.mouse.price_eur if score is not None and score.mouse.price_eur is not None else float("inf")

    def hors_de_sa_fenetre(score) -> bool:
        """La troisième place vient-elle du dernier palier (hors de la fenêtre des ±5 points) ?

        Deux cas mènent là : plus rien dans la fenêtre, ou rien d'abordable dans le Budget personnalisé.
        Le banc ne lui applique alors plus la règle de zone — il vérifie son TITRE (le message dit-il la
        vérité ?), comme pour la deuxième place.
        """
        if score is None or ideal is None:
            return False
        return score.total < reference - ECONOMY_SLOT_TOLERANCE_POINTS

    def alternative_est_piste() -> bool:
        """Miroir de la règle du moteur : hors zone du mode ET hors élargissement, ou plus chère."""
        if alternative is None or ideal is None:
            return False
        if alternative.total >= reference - tolerance:
            return False
        return not (alternative.total >= reference - ALTERNATIVE_EXTENSION_POINTS
                    and alternative.mouse.price_eur is not None
                    and ideal.mouse.price_eur is not None
                    and alternative.mouse.price_eur <= ideal.mouse.price_eur)

    hors_fenetre_eco = hors_de_sa_fenetre(economy)
    piste_alt = alternative_est_piste()
    for role, score, marge in (("le match idéal", ideal, tolerance),
                               ("l'alternative", None if piste_alt else alternative,
                                max(tolerance, ALTERNATIVE_EXTENSION_POINTS)),
                               ("l'économie", None if hors_fenetre_eco else economy,
                                ECONOMY_SLOT_TOLERANCE_POINTS)):
        if score is None:
            continue
        mouse = score.mouse
        if mouse.label not in texte:
            problems.append(f"souris montrée mais absente du texte : {mouse.label}")
        if score.is_pending:
            problems.append(f"souris EN ATTENTE affichée : {mouse.label}")
        fit = getattr(mouse, GRIP_FIELD[session.grip])
        if fit == "Faible":
            problems.append(f"souris à prise FAIBLE affichée : {mouse.label}")
        if not 0 <= score.total <= MAX_SCORE:
            problems.append(f"score hors barème pour {mouse.label} : {score.total}")
        if score.total < reference - marge:
            problems.append(f"{role} hors de sa zone ({mouse.label} : {score.total} < {reference - marge})")
        if role == "l'alternative" and score.total < reference - tolerance:
            # Élargissement : interdit si une autre coque était disponible dans la zone du mode, et
            # interdit si la souris proposée est plus chère que le match idéal.
            autres = [s for s in selection.ranked[1:]
                      if s.total >= reference - tolerance and not _same_shell(ideal, s)]
            if autres:
                problems.append(f"alternative hors zone alors qu'une autre coque y est : {mouse.label}")
            if mouse.price_eur is not None and ideal.mouse.price_eur is not None \
                    and mouse.price_eur > ideal.mouse.price_eur and not _same_shell(ideal, score):
                # Exemption : le repli documenté « jamais moins de résultats qu'avant » — quand la zone
                # ne contient QUE des variantes de la coque déjà montrée et qu'aucune n'est moins
                # chère, la place reprend la zone telle quelle. C'est compté ailleurs, pas sanctionné.
                problems.append(f"alternative élargie mais plus chère : {mouse.label}")
        if role == "l'économie" and score is not None:
            plancher = mouse.price_eur if mouse.price_eur is not None else float("inf")
            montrees = {s.mouse.id for s in (ideal, alternative) if s is not None}
            for autre in selection.ranked[1:]:
                if autre.mouse.id in montrees or autre.mouse.price_eur is None:
                    continue
                # Même préférence de coque que le moteur (décision du 2026-10-12) : une variante
                # d'une coque déjà affichée n'est pas « une autre option », elle ne compte donc pas
                # comme un meilleur candidat pour cette place.
                if _same_shell(ideal, autre) or (alternative is not None and _same_shell(alternative, autre)):
                    continue
                # Même plafond que le moteur (décision du 2026-10-13) : une souris mieux notée que la
                # deuxième place n'est pas un candidat légitime pour la troisième, elle ne compte donc
                # pas comme un meilleur candidat — sinon le banc reprocherait au moteur d'appliquer la
                # règle d'ordre.
                if plafond_ordre is not None and autre.total > plafond_ordre:
                    continue
                if autre.total >= reference - ECONOMY_SLOT_TOLERANCE_POINTS \
                        and autre.mouse.price_eur < plancher:
                    problems.append(f"troisième place plus chère qu'une autre option de sa fenêtre : {mouse.label}")
                    break
        if mouse.price_eur is not None and prix_fr(mouse.price_eur) not in texte:
            problems.append(f"prix absent ou faux pour {mouse.label} : attendu {prix_fr(mouse.price_eur)}")
        # Score partiel (décision du propriétaire, 2026-10-13) : la note longue n'existe que pour le
        # match idéal, donc les 2e et 3e places portent « boutons non documentés ». Sans ce marqueur,
        # le pourcentage s'affiche comme un score complet alors qu'il est calculé sans ce critère —
        # toujours SOUS-ESTIMÉ, jamais gonflé (`PARTIAL_HINT` dans `cogs/finder_flow.py`).
        if role != "le match idéal" and score.is_partial and "boutons non documentés" not in texte:
            problems.append(f"{role} au score partiel annoncée sans le dire : {mouse.label}")
        # Prix non attesté : le message doit le dire (décision du propriétaire, 2026-10-13 — le
        # marqueur existait dans le code mais aucun appelant ne l'activait depuis le 2026-10-11).
        if mouse.price_status != "verified" and "prix non vérifié" not in texte:
            problems.append(f"prix non vérifié affiché sans le dire : {mouse.label}")
        if session.budget_mode is BudgetMode.CUSTOM and mouse.price_eur is not None \
                and session.max_budget_eur is not None and mouse.price_eur > session.max_budget_eur:
            problems.append(f"{mouse.label} ({mouse.price_eur} €) au-dessus du budget {session.max_budget_eur} €")

    # Décision du propriétaire du 2026-10-12 : la troisième place porte le titre de son rôle réel —
    # « 💸 L'économie » si elle est moins chère que tout ce qui est affiché (fait vérifiable), sinon
    # « 🔎 Autre piste » si elle vient du dernier palier, sinon « ➕ L'autre option ».
    if economy is not None and ideal is not None:
        plafond = min(_prix(ideal), _prix(alternative))
        if _prix(economy) < plafond:
            attendu = "💸 L'économie"
        elif hors_fenetre_eco:
            attendu = "🔎 Autre piste"
        else:
            attendu = "➕ L'autre option"
        if attendu not in texte:
            problems.append(f"troisième place mal étiquetée : {economy.mouse.label} "
                            f"(attendu « {attendu} »)")
    if piste_alt and alternative is not None and "🔎 Autre piste" not in texte:
        problems.append(f"deuxième place « autre piste » sans le dire : {alternative.mouse.label}")

    attendu_score = f"{ideal.total}/{MAX_SCORE}"
    attendu_pct = f"{compatibility_percent(ideal)} %"
    if attendu_score not in texte:
        problems.append(f"score du match idéal absent du message (attendu {attendu_score})")
    if attendu_pct not in texte:
        problems.append(f"pourcentage du match idéal absent du message (attendu {attendu_pct})")
    for dimension, nom_dimension in ((ideal.mouse.length_mm, "longueur"), (ideal.mouse.width_max_mm, "largeur")):
        if dimension is None:
            continue
        valeur = f"{dimension:g}".replace(".", ",")   # même écriture que _mm() dans le cog
        if valeur not in texte:
            problems.append(f"{nom_dimension} du match idéal absente du message (attendu {valeur} mm)")
    if selection.explanation and selection.explanation not in texte:
        problems.append("justification du choix absente du message")

    if alternative is not None and _same_shell(ideal, alternative):
        # Le plafond d'ordre fait partie de la règle : une souris d'une autre coque qui dépasse le
        # match idéal (donc écartée par le moteur) ne compte pas comme « autre coque disponible ».
        zone = [s for s in selection.ranked[1:]
                if s.total >= reference - tolerance and s.total <= (ideal.total if ideal is not None else 0)]
        if any(not _same_shell(ideal, s) for s in zone):
            problems.append("alternative de la même coque alors qu'une autre coque est disponible")
    # Repli documenté : deux places peuvent montrer la même coque quand la zone n'offre rien d'autre.
    # On le compte pour le suivre (aucune règle n'est cassée), au lieu de le passer sous silence.
    if repli_coque is not None and deux_places_meme_coque((ideal, alternative, economy)):
        repli_coque.append(etiquette)
    identifiants = [s.mouse.id for s in (ideal, alternative, economy) if s is not None]
    if len(identifiants) != len(set(identifiants)):
        problems.append("la même souris est affichée deux fois")

    # Boutons d'achat : un par souris montrée, jamais pour une souris absente, et la bonne adresse.
    view = ResultsView([s for s in (ideal, alternative, economy) if s is not None], LINKS)
    problems.extend(check_view_limits(view))
    boutons = [item for item in view.children]
    for bouton in boutons:
        url = getattr(bouton, "url", None)
        etiquette = getattr(bouton, "label", "") or ""
        if url is None:
            continue                              # bouton informatif « Liens à venir » (désactivé)
        if not any(url == LINKS.get(s.mouse.id) for s in (ideal, alternative, economy) if s is not None):
            problems.append(f"bouton vers une souris absente du message : {url}")
        attendu = next((s.mouse.label for s in (ideal, alternative, economy)
                        if s is not None and LINKS.get(s.mouse.id) == url), None)
        if attendu and attendu.split(" / ")[0][:20] not in etiquette:
            problems.append(f"bouton mal étiqueté : « {etiquette} » pour {attendu}")
    for score in (ideal, alternative, economy):
        if score is None or not LINKS.get(score.mouse.id):
            continue
        if not any(getattr(b, "url", None) == LINKS[score.mouse.id] for b in boutons):
            problems.append(f"aucun bouton d'achat pour {score.mouse.label}")
    return problems

GRIPS = list(Grip)
THENARS = [None, *Thenar]
MODES = [None, *BudgetMode]


def _lengths(fast: bool) -> list[float]:
    if fast:
        return [160.0, 180.0, 200.0]
    return [float(v) for v in range(140, 235, 5)]


def _widths(fast: bool) -> list[float]:
    if fast:
        return [70.0, 90.0, 110.0]
    return [float(v) for v in range(60, 125, 5)]


def _budgets(fast: bool) -> list[float]:
    return [30.0, 60.0, 120.0] if fast else [10.0, 25.0, 45.0, 60.0, 90.0, 150.0]


def profile(mode: BudgetMode | None, budget: float | None) -> FinderSession:
    session = FinderSession(user_id=7)
    session.budget_mode = mode
    session.max_budget_eur = budget if mode is BudgetMode.CUSTOM else None
    return session


# Limites Discord, valeurs documentées (docs/partie « limits ») — une seule source pour le banc.
# Le banc ne les vérifiait qu'en partie jusqu'au 2026-10-14 : cinq des neuf limites d'un bloc, et
# **aucune** des huit limites d'une vue. Or discord.py ne refuse à la construction que le nombre
# d'enfants d'une vue (25) et les rangées (0 à 4) : un libellé trop long, une adresse trop longue, un
# `custom_id` trop long et un menu à plus de 25 options **passent** la construction et sont refusés par
# Discord **à l'envoi** — le membre ne verrait alors aucun résultat, sans erreur lisible.
LIMITES_BLOC = {"blocs": 10, "titre": 256, "description": 4096, "champs": 25, "nom_de_champ": 256,
                "valeur_de_champ": 1024, "pied": 2048, "auteur": 256, "total": 6000}
LIMITES_VUE = {"composants": 25, "rangees": 5, "libelle_bouton": 80, "url_bouton": 512,
               "custom_id": 100, "options": 25, "libelle_option": 100, "description_option": 100}


# Marges observées pendant le passage (plus grande valeur vue, limite) — pour la ligne de synthèse :
# « 0 dépassement » ne dit pas si l'on passe à un cheveu de la limite ou si l'on a de la place.
MARGES: dict[str, tuple[int, int]] = {}


def _noter_marge(nom: str, valeur: int, limite: int) -> None:
    if nom not in MARGES or valeur > MARGES[nom][0]:
        MARGES[nom] = (valeur, limite)


def resume_des_marges() -> str:
    """La limite la plus remplie du passage, en clair (rejouable, jamais devinée).

    On compare des **fractions de limite** (un compte d'options et une longueur de texte ne se
    soustraient pas) : c'est le composant le plus proche de son plafond qui compte pour la suite.
    """
    if not MARGES:
        return "Limites Discord : aucune mesure (banc interrompu ?)"
    nom, (valeur, limite) = max(MARGES.items(), key=lambda item: item[1][0] / item[1][1])
    return (f"Limites Discord : la plus remplie est « {nom} » — {valeur}/{limite} "
            f"({100 * valeur / limite:.0f} % de la limite), sur les blocs et les vues du parcours entier")


def check_embed_limits(embeds) -> list[str]:
    """Toutes les limites d'un bloc Discord, mesurées : aucune n'est supposée."""
    problems: list[str] = []
    L = LIMITES_BLOC
    if not 1 <= len(embeds) <= L["blocs"]:
        problems.append(f"nombre de blocs hors limites : {len(embeds)}")
    # Discord compte les 6 000 caractères sur TOUS les blocs d'un message réunis, pas bloc par bloc
    # (trou du banc trouvé le 2026-10-15, 80e passe : seule la limite par bloc était mesurée, alors que
    # le résultat porte jusqu'à huit blocs). Un dépassement fait refuser l'envoi entier.
    message = sum(len(e.title or "") + len(e.description or "")
                  + sum(len(f.name) + len(f.value) for f in e.fields)
                  + len(e.footer.text or "") + len(e.author.name or "") for e in embeds)
    _noter_marge("total d'un message", message, L["total"])
    if message > L["total"]:
        problems.append(f"message : {message} caractères sur l'ensemble des blocs (> {L['total']})")
    images = [e.image.url for e in embeds if e.image and e.image.url]
    if len(images) != len(set(images)):
        problems.append("la même illustration apparaît deux fois dans le message")
    for index, embed in enumerate(embeds, start=1):
        total = len(embed.title or "") + len(embed.description or "")
        total += sum(len(f.name) + len(f.value) for f in embed.fields)
        total += len(embed.footer.text or "") + len(embed.author.name or "")
        _noter_marge("total d'un bloc", total, L["total"])
        if total > L["total"]:
            problems.append(f"bloc {index} : {total} caractères (> {L['total']})")
        _noter_marge("titre de bloc", len(embed.title or ""), L["titre"])
        if len(embed.title or "") > L["titre"]:
            problems.append(f"bloc {index} : titre {len(embed.title or '')} (> {L['titre']})")
        _noter_marge("description de bloc", len(embed.description or ""), L["description"])
        if len(embed.description or "") > L["description"]:
            problems.append(f"bloc {index} : description {len(embed.description or '')} "
                            f"(> {L['description']})")
        _noter_marge("pied de bloc", len(embed.footer.text or ""), L["pied"])
        if len(embed.footer.text or "") > L["pied"]:
            problems.append(f"bloc {index} : pied {len(embed.footer.text or '')} (> {L['pied']})")
        _noter_marge("auteur de bloc", len(embed.author.name or ""), L["auteur"])
        if len(embed.author.name or "") > L["auteur"]:
            problems.append(f"bloc {index} : auteur {len(embed.author.name or '')} (> {L['auteur']})")
        _noter_marge("champs d'un bloc", len(embed.fields), L["champs"])
        if len(embed.fields) > L["champs"]:
            problems.append(f"bloc {index} : {len(embed.fields)} champs (> {L['champs']})")
        for f in embed.fields:
            _noter_marge("nom de champ", len(f.name), L["nom_de_champ"])
            _noter_marge("valeur de champ", len(f.value), L["valeur_de_champ"])
            if len(f.name) > L["nom_de_champ"] or len(f.value) > L["valeur_de_champ"]:
                problems.append(f"bloc {index} : champ « {f.name} » hors limites")
    return problems


def check_ecrans_fixes() -> list[str]:
    """Les écrans fixes du parcours — panneau, étapes de choix — blocs **et** vues, mesurés une fois.

    Ils ne dépendaient d'aucun profil, donc aucun contrôle par profil ne pouvait les couvrir : leurs
    limites Discord n'étaient mesurées nulle part avant le 2026-10-14.
    """
    problems: list[str] = []
    blocs = {"panneau": banner_embed(), "prise": grip_step_embed(), "variante": claw_variant_step_embed()}
    for grip in (Grip.PALM, Grip.CLAW):     # Fingertip saute le thénar (garde de _step_number)
        blocs[f"thénar/{grip.value}"] = thenar_step_embed(grip)
    for nom, embed in blocs.items():
        problems.extend(f"{nom} : {p}" for p in check_embed_limits([embed]))
    vues = {"prise": GripView(), "variante": ClawVariantView(), "thénar": ThenarView(),
            "mesures": MeasureView(), "budget": BudgetView()}
    for nom, vue in vues.items():
        problems.extend(f"{nom} : {p}" for p in check_view_limits(vue))
    return problems


def check_view_limits(view) -> list[str]:
    """Toutes les limites Discord d'une vue : enfants, rangées, libellés, adresses, options.

    Les deux premières sont aussi refusées par discord.py à la construction (25 enfants, rangées 0 à
    4) : les mesurer ici garde la limite écrite noir sur blanc, et les autres — celles que discord.py
    laisse passer et que Discord refuse **à l'envoi** — n'étaient mesurées nulle part avant le
    2026-10-14.
    """
    problems: list[str] = []
    L = LIMITES_VUE
    enfants = [item for item in view.children]
    if not enfants:
        problems.append("vue vide : un envoi sans composant n'a pas de sens ici")
        return problems
    _noter_marge("composants d'une vue", len(enfants), L["composants"])
    if len(enfants) > L["composants"]:
        problems.append(f"vue : {len(enfants)} composants (> {L['composants']})")
    rangees = {item.row for item in enfants if item.row is not None}
    if rangees and (min(rangees) < 0 or max(rangees) >= L["rangees"]):
        problems.append(f"vue : rangées {sorted(rangees)} hors de 0 à {L['rangees'] - 1}")
    for item in enfants:
        if isinstance(item, discord.ui.Button):
            _noter_marge("libellé de bouton", len(item.label or ""), L["libelle_bouton"])
            if len(item.label or "") > L["libelle_bouton"]:
                problems.append(f"vue : libellé de bouton {len(item.label or '')} "
                                f"(> {L['libelle_bouton']}) : « {item.label} »")
            _noter_marge("adresse de bouton", len(item.url or ""), L["url_bouton"])
            if item.url is not None and len(item.url) > L["url_bouton"]:
                problems.append(f"vue : adresse de bouton {len(item.url)} (> {L['url_bouton']})")
            if item.custom_id is not None and not 1 <= len(item.custom_id) <= L["custom_id"]:
                problems.append(f"vue : custom_id de {len(item.custom_id)} caractères "
                                f"(attendu 1 à {L['custom_id']})")
        elif isinstance(item, discord.ui.Select):
            _noter_marge("options d'un menu", len(item.options), L["options"])
            if len(item.options) > L["options"]:
                problems.append(f"vue : menu à {len(item.options)} options (> {L['options']})")
            for option in item.options:
                _noter_marge("libellé d'option", len(option.label or ""), L["libelle_option"])
                if len(option.label or "") > L["libelle_option"]:
                    problems.append(f"vue : libellé d'option {len(option.label or '')} "
                                    f"(> {L['libelle_option']}) : « {option.label} »")
                _noter_marge("description d'option", len(option.description or ""), L["description_option"])
                if len(option.description or "") > L["description_option"]:
                    problems.append(f"vue : description d'option {len(option.description or '')} "
                                    f"(> {L['description_option']}) : « {option.description} »")
    return problems


def grille(fast: bool):
    """Les entrées du banc : un profil **distinct** par itération, dans l'ordre d'affichage.

    Règle du parcours : le thénar est **toujours demandé** en Palm et en Claw, et **jamais** en
    Fingertip (l'étape est sautée — `step_kind`). Le banc suit cette règle pour construire ses entrées.

    Défaut corrigé le 2026-10-14 (61e passe) : la boucle itérait les trois tailles de thénar **aussi**
    en Fingertip, où le parcours force `session.thenar = None`. Les trois itérations produisaient donc
    la **même entrée moteur** : 5 434 des 27 170 profils annoncés — 20,0 % — étaient le même profil
    mesuré trois fois, et chaque pourcentage publié « sur 27 170 » portait un dénominateur gonflé
    d'un cinquième. Le garde-fou de `tests/test_qa_flow_matrix.py` refuse désormais toute entrée
    dupliquée.
    """
    for grip, length, width, thenar in itertools.product(GRIPS, _lengths(fast), _widths(fast), THENARS):
        if grip is Grip.FINGERTIP:
            if thenar is not None:
                continue            # question non posée : un seul profil par couple taille/prise
        elif grip is not Grip.CLAW and thenar is None:
            continue                # le thénar est toujours demandé en Palm ; en Claw, None reste testé
        for mode in MODES:
            for budget in (_budgets(fast) if mode is BudgetMode.CUSTOM else [None]):
                yield grip, length, width, thenar, mode, budget
def verifier_bytecode() -> str | None:
    """Refuse la mesure si Python chargerait un code **différent** de celui qui est livré.

    Défaut trouvé le 2026-10-14 (68e passe, C90) : le banc a publié **10 678 problèmes**, dont
    « 9 768 profils » où l'ordre des pourcentages n'était pas garanti, alors que le moteur livré n'en
    produisait aucun. La faute n'était pas dans le moteur mais dans un fichier ``.pyc`` : une mutation
    d'essai avait échangé les deux variables de retour de ``result_slots``, la source avait été remise
    à l'identique — **même taille, même seconde** — et Python continuait donc de charger le code muté.
    Toute la mesure portait sur un autre moteur que celui du dépôt, sans le moindre signe extérieur.

    Un banc qui mesure un autre code que le code livré ne vaut rien : mieux vaut refuser la mesure et
    le dire, avec la commande qui répare. Le contrôle lui-même vit dans ``tools/check_bytecode.py``.
    """
    try:
        from check_bytecode import controle, dangereux
    except ImportError:                                     # pragma: no cover - outil déplacé
        return None
    perimes = dangereux(controle(ROOT))
    if not perimes:
        return None
    coupables = ", ".join(str(d.source) for d in perimes[:5])
    return (f"mesure refusée : Python chargerait un bytecode périmé ({coupables}) — "
            "lancez `python tools/check_bytecode.py --purge`, puis relancez le banc")


@contextlib.contextmanager
def illustrations_actives():
    """Le banc rend chaque résultat AVEC ses illustrations, comme sur le serveur.

    Hors serveur, ``IMAGES_BASE_URL`` est vide et aucun bloc ne porte d'image : la règle « une même
    illustration une seule fois par message » (80e passe) n'aurait alors jamais été vérifiée. Chaque
    clé reçoit ici une adresse fictive distincte ; l'état d'origine est rétabli en sortie.
    """
    import cogs.finder_flow as flow
    from utils.assets import IMAGE_KEYS
    origine = flow.load_image_urls
    flow.load_image_urls = lambda path, base_url=None: {cle: f"https://banc.local/{cle}.png" for cle in IMAGE_KEYS}
    try:
        yield
    finally:
        flow.load_image_urls = origine


def run(fast: bool) -> int:
    gene = verifier_bytecode()
    if gene is not None:
        print(gene, file=sys.stderr)
        return 2
    with illustrations_actives():
        return _run(fast)


def _run(fast: bool) -> int:
    cases = 0
    problems: list[str] = []
    empties: list[str] = []
    vides_par_cause: dict[str, int] = {}      # d'où vient un résultat vide (80e passe)
    partials = 0
    marques_prix = 0
    places = {0: 0, 1: 0, 2: 0, 3: 0}          # nombre de places réellement remplies dans le message
    same_shell_slots: list[str] = []            # profils où deux places partagent la même coque (repli)
    ordre_repli: list[str] = []                 # profils où le plafond d'ordre n'a laissé aucun candidat
    MARGES.clear()                          # un passage = un relevé de marges
    problems.extend(check_ecrans_fixes())
    for grip, length, width, thenar, mode, budget in grille(fast):
        cases += 1
        where = f"{grip.value}/{length:.0f}x{width:.0f}/thenar={thenar}/mode={mode}/{budget}"
        session = profile(mode, budget)
        session.grip = grip
        session.hand_length_mm = length
        session.hand_width_mm = width
        session.thenar = thenar          # déjà None en Fingertip : la règle est dans grille()
        if grip is Grip.CLAW:
            session.claw_variant = ClawVariant.RELACHEE
        try:
            selection = compute_selection(session)
            embeds = results_embeds(session, selection)
        except Exception as exc:  # noqa: BLE001 - le banc d'essai doit tout attraper
            problems.append(f"{where} : EXCEPTION {type(exc).__name__} : {exc}")
            continue
        problems.extend(f"{where} : {p}" for p in check_embed_limits(embeds))
        # Les étapes montrées par le parcours : leurs blocs portaient des limites Discord jamais
        # vérifiées avant le 2026-10-14 (seul le résultat l'était).
        problems.extend(f"{where} : {p}" for p in check_embed_limits([measure_step_embed(session)]))
        problems.extend(f"{where} : {p}" for p in check_embed_limits([budget_step_embed(session)]))
        ideal, alternative, economy = result_slots(selection)
        places[len([s for s in (ideal, alternative, economy) if s is not None])] += 1
        problems.extend(f"{where} : {p}"
                        for p in check_result_message(session, selection, embeds, ideal, alternative,
                                                     economy, same_shell_slots, where,
                                                     repli_ordre=ordre_repli))
        if ideal is None:
            empties.append(where)
            cause = (f"budget personnalisé de {budget:g} €" if mode is BudgetMode.CUSTOM
                     else f"mode {mode.value if mode else 'aucun'}")
            vides_par_cause[cause] = vides_par_cause.get(cause, 0) + 1
        else:
            if ideal.is_partial:
                partials += 1
            marques_prix += places_au_prix_non_verifie((ideal, alternative, economy))
            for score in (ideal, alternative, economy):
                if score is None:
                    continue
                if not 0 <= score.total <= MAX_SCORE:
                    problems.append(f"{where} : total {score.total} hors barème")
            if alternative is not None and alternative.mouse.id == ideal.mouse.id:
                problems.append(f"{where} : alternative identique au match idéal")
            if economy is not None and economy.mouse.id in {
                ideal.mouse.id,
                alternative.mouse.id if alternative else None,
            }:
                problems.append(f"{where} : économie déjà montrée plus haut")
    print(f"Profils testés : {cases}")
    print(f"Profils sans aucun résultat : {len(empties)}"
          + (" (" + " · ".join(f"{cause} : {n}" for cause, n in sorted(vides_par_cause.items())) + ")"
             if vides_par_cause else ""))
    for where in empties[:15]:
        print(f"  · {where}")
    print(f"Profils où le match idéal est partiel (boutons non documentés) : {partials}")
    print(f"Profils où deux places montrent la même coque (repli documenté) : {len(same_shell_slots)}"
          + (f"  ·  ex. {same_shell_slots[0]}" if same_shell_slots else ""))
    print(f"Profils où l'ordre des pourcentages n'est pas garanti (plafond sans candidat) : {len(ordre_repli)}"
          + (f"  ·  ex. {ordre_repli[0]}" if ordre_repli else ""))
    print("Places remplies dans le résultat : "
          + " · ".join(f"{n} place(s) : {places[n]}" for n in (0, 1, 2, 3))
          + f"  (3 places = {100 * places[3] / cases:.2f} % des profils)" if cases else "")
    print(f"Places portant « (prix non vérifié) » : {marques_prix}"
          + (f"  ({100 * marques_prix / cases:.2f} % des profils)" if cases else ""))
    print(resume_des_marges())
    print(f"Problèmes détectés : {len(problems)}")
    for problem in problems[:40]:
        print(f"  ! {problem}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Banc d'essai du parcours")
    parser.add_argument("--rapide", action="store_true", help="grille réduite")
    args = parser.parse_args(argv)
    return run(args.rapide)


if __name__ == "__main__":
    raise SystemExit(main())
