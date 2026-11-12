"""Génère un aperçu visuel (PNG) du parcours, du résultat et du mode « Peu importe le prix ».

Usage : python tools/render_preview.py
Sortie : docs/apercu_parcours.png, docs/apercu_resultat.png, docs/apercu_prix_libre.png

Chaque PNG porte dans ses métadonnées une **empreinte des sources** (catalogue, liens, images et
modules qui décident du rendu) : `tests/test_apercus.py` la relit et refuse un aperçu plus vieux que
les données qu'il montre (« relancez python tools/render_preview.py »). Un aperçu périmé est un
document faux : celui du mode « Peu importe le prix » montrait encore « Z1 V2 Ultra » après le
renommage du 2026-10-13.

Le rendu imite le client Discord en thème sombre (fond #313338, carte #2B2D31, barre latérale
bordeaux #8A2342) pour permettre au propriétaire de valider la refonte sans serveur.
Ce n'est PAS un rendu officiel de Discord : la mise en page réelle dépend du client (mobile/desktop).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cogs import finder_flow as flow  # noqa: E402
from config import VERSIONS_PATH  # noqa: E402
from utils.versions import load_versions  # noqa: E402
from config import COMMERCIAL_LINKS_PATH, MOUSE_DB_PATH  # noqa: E402
from utils.assets import IMAGE_KEYS  # noqa: E402
from utils.catalog import load_commercial_links  # noqa: E402
from utils.models import BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402
from utils.session import SessionStore  # noqa: E402


def _boutons_achat(selection) -> list[tuple[str, bool]]:
    """Les boutons RÉELS du résultat, lus sur la vue que le bot envoie (``flow.ResultsView``).

    Défaut corrigé le 2026-10-15 (80e passe) : cette fonction recalculait les boutons à partir de
    ``selection.ranked`` — le classement interne — alors que le bot les construit sur les souris
    **affichées** (``result_slots``). L'aperçu livré montrait donc « Acheter Pulsar X2 CrazyLight »
    sous une troisième place « VXE MAD R ». Lire la vue elle-même rend tout écart impossible.
    """
    links = load_commercial_links(COMMERCIAL_LINKS_PATH)
    displayed = [score for score in flow.result_slots(selection) if score is not None]
    vue = flow.ResultsView(displayed, links)
    return [(f"{bouton.emoji} {bouton.label}" if bouton.emoji else bouton.label, False)
            for bouton in vue.children]

# Les images locales sont référencées par un faux domaine : l'aperçu dessine les fichiers de
# assets/illustrations/ sans exiger qu'ils soient déjà publiés en https.
_RAW_IMAGES = json.loads((ROOT / "assets" / "images.json").read_text(encoding="utf-8"))
_FAKE_URLS = {
    key: (f"https://apercu.local/{_RAW_IMAGES[key]}" if _RAW_IMAGES.get(key) else None)
    for key in IMAGE_KEYS
}


def images_locales() -> None:
    """Branche ces faux domaines sur le module du bot — à appeler **explicitement**.

    Trouvé le 2026-10-13 : ce détournement était fait à l'import du fichier, donc le simple fait
    d'importer l'outil (test, script, IDE) changeait la résolution des images du bot dans le même
    processus — un test du bot échouait alors selon l'ordre d'exécution. L'outil, lui, l'appelle au
    début de ``main()`` : rien ne change pour l'aperçu.
    """
    flow.load_image_urls = lambda path, base_url=None: dict(_FAKE_URLS)  # type: ignore[assignment]


FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_REG = FONT_DIR / "DejaVuSans.ttf"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"

BG = (49, 51, 56)          # fond Discord sombre
CARD = (43, 45, 49)        # carte d'embed
TEXT = (219, 222, 225)     # texte Discord
MUTED = (148, 155, 164)
WHITE = (255, 255, 255)
BOUTON_PRIMAIRE = (88, 101, 242)
BOUTON_SECONDAIRE = (78, 80, 88)
LISERE = flow.BORDEAUX.to_rgb()   # liseré des embeds : la charte du bot, jamais une copie
LARGEUR = 620
PAD = 18

# Tout ce qui décide de ce qu'on voit dans les aperçus : le catalogue, les liens, les images et les
# modules qui composent le message. Un seul octet de ces fichiers change, et l'aperçu versionné est
# déclaré périmé (métadonnée « azemouse-empreinte », relue par `tests/test_apercus.py`).
CLE_EMPREINTE = "azemouse-empreinte"
FICHIERS_SOURCES = (
    MOUSE_DB_PATH,
    COMMERCIAL_LINKS_PATH,
    ROOT / "assets" / "images.json",
    ROOT / "cogs" / "finder_flow.py",
    ROOT / "utils" / "assets.py",
    ROOT / "utils" / "catalog.py",
    ROOT / "utils" / "matcher.py",
    ROOT / "utils" / "models.py",
    ROOT / "utils" / "selection.py",
    ROOT / "utils" / "slots.py",
    ROOT / "utils" / "session.py",
    ROOT / "utils" / "versions.py",
    ROOT / "data" / "versions.json",
    ROOT / "tools" / "render_preview.py",
)


def empreinte_des_sources() -> str:
    """SHA-256 du contenu des fichiers qui décident du rendu (12 caractères suffisent à le dire)."""
    empreinte = hashlib.sha256()
    for fichier in FICHIERS_SOURCES:
        empreinte.update(fichier.name.encode("utf-8"))
        empreinte.update(fichier.read_bytes())
    return empreinte.hexdigest()[:12]


def lire_empreinte(chemin: Path) -> str | None:
    """L'empreinte inscrite dans un aperçu PNG, ou None s'il n'en porte pas (aperçu d'avant)."""
    with Image.open(chemin) as image:
        return image.text.get(CLE_EMPREINTE)


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def _wrap(text: str, font, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.getlength(test) <= width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _plain(text: str) -> str:
    return text.replace("**", "").replace("*", "").replace("`", "")


def _mots(paragraph: str) -> list[list[tuple[str, bool]]]:
    """Les mots d'un paragraphe « Discord » ; chaque mot est une suite de fragments (texte, gras).

    Un mot peut mêler les deux graisses : dans « **score**. », le point suit le mot en gras sans
    espace. Avant le 2026-11-11, l'aperçu insérait une espace à chaque changement de graisse
    (« petite , moyenne », « le score . ») et dessinait la ligne entière dans la graisse de son
    dernier mot : des défauts d'aperçu, que le propriétaire aurait pu prendre pour des fautes du bot.
    """
    mots: list[list[tuple[str, bool]]] = []
    mot: list[tuple[str, bool]] = []
    for index, segment in enumerate(paragraph.split("**")):
        gras = index % 2 == 1
        for rang, morceau in enumerate(_plain(segment).split(" ")):
            if rang and mot:              # une espace dans la source : le mot en cours est terminé
                mots.append(mot)
                mot = []
            if morceau:
                mot.append((morceau, gras))
    if mot:
        mots.append(mot)
    return mots


def _lignes(paragraph: str, font, bold_font, width: int) -> list[list[tuple[str, bool]]]:
    """Met un paragraphe en lignes, mot à mot, chaque fragment mesuré dans SA graisse."""
    espace = font.getlength(" ")
    lignes: list[list[tuple[str, bool]]] = []
    ligne: list[tuple[str, bool]] = []
    occupe = 0.0
    for mot in _mots(paragraph):
        largeur = sum((bold_font if gras else font).getlength(texte) for texte, gras in mot)
        if ligne and occupe + espace + largeur > width:
            lignes.append(ligne)
            ligne, occupe = [], 0.0
        if ligne:
            ligne.append((" ", False))
            occupe += espace
        ligne.extend(mot)
        occupe += largeur
    lignes.append(ligne)                  # un paragraphe vide occupe une ligne (saut de ligne)
    return lignes


def _draw_rich(draw, xy, text, font, bold_font, width, fill, line_gap=6):
    """Rend un texte « Discord » : gras (**…**) et sous-texte (``-# …``), retour à la ligne."""
    x, y = xy
    for paragraph in text.split("\n"):
        paragraph, font, bold_font, fill, line_gap = _rich_style(paragraph, font, bold_font, fill, line_gap)
        for ligne in _lignes(paragraph, font, bold_font, width):
            curseur = float(x)
            for texte, gras in ligne:
                police = bold_font if gras else font
                draw.text((round(curseur), y), texte, font=police, fill=fill)
                curseur += police.getlength(texte)
            y += font.size + line_gap
    return y


def _rich_style(paragraph, font, bold_font, fill, line_gap):
    """« -# » = sous-texte Discord : plus petit et gris (mise en page de l'aperçu seulement)."""
    if paragraph.startswith("-# "):
        size = max(11, font.size - 3)
        return paragraph[3:], _font(False, size), _font(True, size), MUTED, 4
    return paragraph, font, bold_font, fill, line_gap


def _text_height(text: str, contenu_largeur: int) -> int:
    """Hauteur d'un texte riche : la MÊME mise en lignes que ``_draw_rich`` (corps 15, interligne 6)."""
    height = 0
    for paragraph in text.split("\n"):
        paragraph, font, bold_font, _fill, gap = _rich_style(paragraph, _font(False, 15), _font(True, 15), TEXT, 6)
        height += len(_lignes(paragraph, font, bold_font, contenu_largeur)) * (font.size + gap)
    return height


def _embed_height(embed, contenu_largeur: int) -> int:
    """Estimation de hauteur : titre, description, champs, image."""
    height = PAD + 10
    if embed.title:
        height += 30
    if embed.description:
        height += _text_height(embed.description, contenu_largeur) + 10
    for field in embed.fields:
        height += 26
        height += _text_height(field.value, contenu_largeur) + 10
    if embed.image and embed.image.url:
        path = ROOT / "assets" / "illustrations" / url_basename(embed.image.url)
        if path.is_file():
            with Image.open(path) as img:
                height += int(contenu_largeur * img.height / img.width) + 12
    if embed.footer and embed.footer.text:
        height += len(_wrap(_plain(embed.footer.text), _font(False, 13), contenu_largeur)) * 18 + 10
    return height + PAD


def url_basename(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def draw_embed(canvas, draw, embed, y: int, x: int = PAD, width: int = LARGEUR - 2 * PAD) -> int:
    contenu = width - 2 * PAD
    height = _embed_height(embed, contenu)
    draw.rectangle([x, y, x + width, y + height], fill=CARD)
    draw.rectangle([x, y, x + 5, y + height], fill=LISERE)  # liseré bordeaux (identité AzeMouse)
    cursor = y + PAD
    if embed.title:
        cursor = _draw_rich(draw, (x + PAD, cursor), embed.title, _font(True, 18), _font(True, 18), contenu, WHITE) + 6
    if embed.description:
        cursor = _draw_rich(draw, (x + PAD, cursor), embed.description, _font(False, 15), _font(True, 15), contenu, TEXT) + 8
    for field in embed.fields:
        cursor = _draw_rich(draw, (x + PAD, cursor), field.name, _font(True, 15), _font(True, 15), contenu, WHITE) + 2
        cursor = _draw_rich(draw, (x + PAD, cursor), field.value, _font(False, 15), _font(True, 15), contenu, TEXT) + 12
    if embed.image and embed.image.url:
        path = ROOT / "assets" / "illustrations" / url_basename(embed.image.url)
        if path.is_file():
            with Image.open(path) as img:
                img = img.convert("RGB")
                new_h = int(contenu * img.height / img.width)
                img = img.resize((contenu, new_h), Image.LANCZOS)
                canvas.paste(img, (x + PAD, cursor))
                cursor += new_h + 12
    if embed.footer and embed.footer.text:
        cursor = _draw_rich(draw, (x + PAD, cursor), embed.footer.text, _font(False, 12), _font(False, 12), contenu, MUTED)
    return y + height + 16


def draw_boutons(draw, y: int, libelles: list[tuple[str, bool]], x: int = PAD) -> int:
    """Une rangée de boutons ; comme sur mobile, un bouton qui ne tient plus passe à la ligne."""
    cursor = x
    font = _font(False, 14)
    for label, primaire in libelles:
        width = int(font.getlength(label)) + 34
        if cursor > x and cursor + width > LARGEUR - PAD:
            cursor, y = x, y + 46
        fill = BOUTON_PRIMAIRE if primaire else BOUTON_SECONDAIRE
        draw.rounded_rectangle([cursor, y, cursor + width, y + 36], radius=8, fill=fill)
        draw.text((cursor + 17, y + 10), label, font=font, fill=WHITE)
        cursor += width + 10
    return y + 52


def hauteur_boutons(libelles: list[tuple[str, bool]]) -> int:
    """Hauteur occupée par ``draw_boutons`` (mêmes règles de passage à la ligne)."""
    font = _font(False, 14)
    lignes, cursor = 1, PAD
    for label, _ in libelles:
        width = int(font.getlength(label)) + 34
        if cursor > PAD and cursor + width > LARGEUR - PAD:
            lignes, cursor = lignes + 1, PAD
        cursor += width + 10
    return 52 + 46 * (lignes - 1)


def nouveau_canvas(hauteur_totale: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", (LARGEUR, hauteur_totale), BG)
    return canvas, ImageDraw.Draw(canvas)


def bandeau(draw, y: int, texte: str) -> int:
    font = _font(True, 13)
    draw.text((PAD + 2, y), texte.upper(), font=font, fill=MUTED)
    return y + 28


def _legende_etape(kind: str, session, complement: str) -> str:
    """Légende d'un aperçu : « Étape n/N — … », lue dans la MÊME table que le titre de l'embed.

    Une légende écrite à la main peut contredire l'embed qu'elle coiffe : trouvé le 2026-10-13 dans
    l'aperçu « prix libre », légendé « Étape 5/5 » au-dessus d'un titre « Étape 4/4 ». Ici, numéro et
    total viennent de ``cogs/finder_flow`` : impossible de les désaccorder.
    """
    numero = flow._step_number(kind, session)
    total = flow._steps_total(session)
    return f"Étape {numero}/{total} — {complement}"


def _menu(select: discord.ui.Select) -> list[str]:
    """Le texte d'un menu fermé, lu sur le composant RÉEL du bot (jamais recopié à la main).

    Corrigé le 2026-11-11 : ces textes étaient écrits ici en dur. Le menu du type de griffe a été
    reformulé dans ``cogs/finder_flow`` et l'aperçu aurait continué d'afficher l'ancien libellé.
    """
    return [select.placeholder or ""]


def _bouton(vue_classe: type[discord.ui.View]) -> list[str]:
    """Le libellé du bouton d'une vue, lu sur la déclaration du bouton (sans créer la vue)."""
    for attribut in vars(vue_classe).values():
        reglages = getattr(attribut, "__discord_ui_model_kwargs__", None)
        if reglages and reglages.get("label"):
            emoji = reglages.get("emoji")
            return [f"{emoji}  {reglages['label']}" if emoji else reglages["label"]]
    raise LookupError(f"{vue_classe.__name__} : aucun bouton déclaré")


def etapes_du_parcours(session) -> list[tuple[str, discord.Embed, list[str], bool]]:
    """Cartes de l'aperçu « parcours » : légende, embed, boutons, bouton principal.

    Le parcours montré est celui de la **prise en griffe** (le plus long : 5 étapes). Chaque légende
    est dérivée de la table des étapes et de la même prise que l'embed qu'elle coiffe, donc une
    légende ne peut pas annoncer un numéro que le titre ne dit pas (défaut corrigé le 2026-10-13,
    C43). Les textes des menus et des boutons sont lus sur les composants du bot.

    L'étape des mesures est montrée telle que l'utilisateur la voit : ses mesures ne sont pas encore
    saisies, donc le récapitulatif ne les annonce pas (avant le 2026-11-11, l'aperçu les y affichait).
    """
    avant_mesures = dataclasses.replace(session, hand_length_mm=None, hand_width_mm=None)
    return [
        ("Accueil — message persistant (public)", flow.banner_embed(), _bouton(flow.StartView), True),
        (_legende_etape("grip", session, "prise"),
         flow.grip_step_embed(), _menu(flow.GripSelect()), False),
        (_legende_etape("claw_variant", Grip.CLAW, "type de griffe (aucun effet sur le score)"),
         flow.claw_variant_step_embed(), _menu(flow.ClawVariantSelect()), False),
        (_legende_etape("thenar", session, "éminence thénar (arrière de la souris)"),
         flow.thenar_step_embed(session.grip), _menu(flow.ThenarSelect()), False),
        (_legende_etape("measure", session, "mesures"),
         flow.measure_step_embed(avant_mesures), _bouton(flow.MeasureView), True),
        (_legende_etape("budget", session, "budget"),
         flow.budget_step_embed(session), _menu(flow.BudgetSelect()), False),
    ]


def build_parcours() -> Image.Image:
    store = SessionStore(ttl_seconds=600)
    session = store.start(1)
    session.grip, session.hand_length_mm, session.hand_width_mm = Grip.CLAW, 200.0, 110.0
    # Le récapitulatif de chaque étape reprend les réponses déjà données : ici « Griffe relâchée ».
    session.claw_variant = ClawVariant.RELACHEE
    session.thenar = Thenar.MOYENNE
    etapes = etapes_du_parcours(session)
    hauteur = sum(_embed_height(e, LARGEUR - 4 * PAD) + 52 + 28 + 16 for _, e, _, _ in etapes) + PAD
    canvas, draw = nouveau_canvas(hauteur)
    y = PAD
    for titre, embed, boutons, primaire in etapes:
        y = bandeau(draw, y, titre)
        y = draw_embed(canvas, draw, embed, y)
        y = draw_boutons(draw, y, [(b, primaire) for b in boutons])
    return canvas


def build_resultat() -> Image.Image:
    # Cas le plus complet : Griffe pince + éminence thénar petite → tous les blocs s'affichent.
    store = SessionStore(ttl_seconds=600)
    session = store.start(1)
    session.grip, session.hand_length_mm, session.hand_width_mm = Grip.CLAW, 180.0, 100.0
    session.thenar = Thenar.PETITE
    session.claw_variant = ClawVariant.PINCEE
    session.budget_mode = BudgetMode.QUALITE_PRIX
    selection = flow.compute_selection(session)
    # Comme le vrai bot : les versions de data/versions.json sont montrées sous la recommandation.
    embeds = flow.results_embeds(session, selection, load_versions(VERSIONS_PATH))
    # Légende de chaque bloc, retrouvée par son TITRE (et non par sa position : un bloc ajouté ou
    # retiré décalait toutes les légendes suivantes).
    legendes = {
        "🎯 Votre recommandation": "Résultat — message éphémère (privé) : la recommandation, sans image",
        "🧩 Plusieurs versions de la même souris": "Juste dessous : les versions de la même forme, leur prix et ce qui change",
        "🧭 Pourquoi ce choix ?": "Plus bas : pourquoi ce choix (score, souris en clair, rôle de la gamme)",
        "📐 Vos repères de taille": "Plus bas : les repères de taille, et leur dessin juste dessous",
        "🖐️ Un arrière étroit pour votre thénar": "Plus bas : l'arrière étroit (éminence thénar petite ou moyenne)",
        "⛰️ La bosse et la forme": "Plus bas : la bosse que ce type de griffe appelle, et la forme de coque",
        "🖱️ La hauteur des boutons": "Enfin : la hauteur des boutons conseillée",
    }
    boutons = _boutons_achat(selection)
    hauteur = (sum(_embed_height(e, LARGEUR - 4 * PAD) + 28 + 16 for e in embeds) + PAD
               + 28 + hauteur_boutons(boutons))
    canvas, draw = nouveau_canvas(hauteur)
    y = PAD
    for embed in embeds:
        legende = legendes.get(embed.title) or (
            "Plus bas : le type de griffe déclaré, avec sa photo" if embed.title.startswith("🦾") else embed.title)
        y = bandeau(draw, y, legende)
        y = draw_embed(canvas, draw, embed, y)
    # Discord affiche les composants UNE fois, sous le dernier bloc du message (défaut corrigé le
    # 2026-10-15 : l'aperçu les répétait sous chacun des six blocs). Uniquement des liens d'achat.
    y = bandeau(draw, y, "Sous le message : les liens d'achat des souris affichées")
    draw_boutons(draw, y, boutons)
    return canvas


def draw_menu_options(draw, y: int, options, surligne: int | None = None, x: int = PAD,
                      width: int = LARGEUR - 2 * PAD) -> int:
    """Aperçu du menu déroulant Discord : libellé en gras, description en gris."""
    bold, small = _font(True, 15), _font(False, 13)
    height = sum(28 + len(_wrap(desc, small, width - 2 * PAD + 6)) * 18 for _, _, desc in options) + PAD
    draw.rounded_rectangle([x, y, x + width, y + height], radius=8, fill=(41, 43, 48))
    cursor = y + PAD // 2
    for index, (_, label, desc) in enumerate(options):
        if index == surligne:
            draw.rectangle([x + 1, cursor - 4, x + 5, cursor + 30], fill=LISERE)
        draw.text((x + PAD, cursor), label, font=bold, fill=WHITE if index == surligne else TEXT)
        cursor += 26
        for line in _wrap(desc, small, width - 2 * PAD):
            draw.text((x + PAD, cursor), line, font=small, fill=MUTED)
            cursor += 18
        cursor += 4
    return y + height + 16


def etapes_du_prix_libre(session, selection) -> list[tuple[str, discord.Embed, list[str], bool]]:
    """Cartes de l'aperçu « peu importe le prix » : l'étape budget, puis la ligne de résultat.

    Le nombre d'options annoncé vient de ``flow.BUDGET_OPTIONS`` et le numéro d'étape de la table :
    cette légende-ci avait annoncé « Étape 5/5 » au-dessus d'un titre « Étape 4/4 » (parcours Palm).
    """
    embeds = flow.results_embeds(session, selection)
    return [
        (_legende_etape("budget", session,
                        f"budget : {len(flow.BUDGET_OPTIONS)} options, dont « Peu importe le prix »"),
         flow.budget_step_embed(session), _menu(flow.BudgetSelect()), False),
        ("Résultat « Peu importe le prix » — le prix en tout petit",
         embeds[0], [label for label, _ in _boutons_achat(selection)], True),
    ]


def build_prix_libre() -> Image.Image:
    """« Peu importe le prix » : la nouvelle option du menu, puis la ligne de résultat en petit prix."""
    store = SessionStore(ttl_seconds=600)
    session = store.start(1)
    session.grip, session.hand_length_mm, session.hand_width_mm = Grip.PALM, 180.0, 90.0
    session.thenar = Thenar.PETITE
    session.budget_mode = BudgetMode.PEU_IMPORTE_PRIX
    selection = flow.compute_selection(session)
    etapes = etapes_du_prix_libre(session, selection)
    hauteur = PAD
    for _, embed, _, _ in etapes:
        hauteur += 28 + _embed_height(embed, LARGEUR - 4 * PAD) + 52 + 16
    hauteur += sum(28 + len(_wrap(desc, _font(False, 13), LARGEUR - 4 * PAD + 6)) * 18 for _, _, desc in flow.BUDGET_OPTIONS) + PAD
    canvas, draw = nouveau_canvas(hauteur)
    y = PAD
    for titre, embed, boutons, primaire in etapes:
        y = bandeau(draw, y, titre)
        y = draw_embed(canvas, draw, embed, y)
        y = draw_boutons(draw, y, [(b, primaire) for b in boutons])
        if embed is etapes[0][1]:
            y = draw_menu_options(draw, y, flow.BUDGET_OPTIONS, surligne=3)
    return canvas


def main(argv: list[str] | None = None) -> int:
    """Rend les aperçus PNG des écrans (documents versionnés dans docs/).

    ``--help`` et ``--sortie-dossier`` ont été ajoutés le 2026-10-12 : sans argument, le script
    réécrivait directement les trois aperçus versionnés, sans confirmation. Comportement par défaut
    inchangé.
    """
    parser = argparse.ArgumentParser(description="Rend les aperçus PNG des écrans du bot.")
    parser.add_argument("--sortie-dossier", default=str(ROOT / "docs"),
                        help="dossier où écrire les aperçus (défaut : docs/)")
    args = parser.parse_args(argv)
    images_locales()                       # les faux domaines d'aperçu, branchés ici et pas à l'import
    dossier = Path(args.sortie_dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    empreinte = empreinte_des_sources()
    metadonnees = PngImagePlugin.PngInfo()
    metadonnees.add_text(CLE_EMPREINTE, empreinte)
    for nom, image in (("apercu_parcours.png", build_parcours()), ("apercu_resultat.png", build_resultat()),
                       ("apercu_prix_libre.png", build_prix_libre())):
        chemin = dossier / nom
        image.save(chemin, optimize=True, pnginfo=metadonnees)
        print(f"Écrit : {chemin} ({image.width}×{image.height}, {chemin.stat().st_size // 1024} Ko, "
              f"empreinte {empreinte})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
