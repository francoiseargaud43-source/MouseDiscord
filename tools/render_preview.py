"""Génère un aperçu visuel (PNG) du parcours et du résultat, sans lancer le bot.

Usage : python tools/render_preview.py
Sortie : docs/apercu_parcours.png et docs/apercu_resultat.png

Le rendu imite le client Discord en thème sombre (fond #313338, carte #2B2D31, barre latérale
bordeaux #8A2342) pour permettre au propriétaire de valider la refonte sans serveur.
Ce n'est PAS un rendu officiel de Discord : la mise en page réelle dépend du client (mobile/desktop).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cogs import finder_flow as flow  # noqa: E402
from utils.assets import IMAGE_KEYS  # noqa: E402
from utils.models import BudgetMode, Grip, Thenar  # noqa: E402
from utils.session import SessionStore  # noqa: E402

# Les images locales sont référencées par un faux domaine : l'aperçu dessine les fichiers de
# assets/illustrations/ sans exiger qu'ils soient déjà publiés en https.
_RAW_IMAGES = json.loads((ROOT / "assets" / "images.json").read_text(encoding="utf-8"))
_FAKE_URLS = {
    key: (f"https://apercu.local/{_RAW_IMAGES[key]}" if _RAW_IMAGES.get(key) else None)
    for key in IMAGE_KEYS
}
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
LISERE = (138, 35, 66)     # #8A2342 Bordeaux
LARGEUR = 620
PAD = 18


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


def _draw_rich(draw, xy, text, font, bold_font, width, fill, line_gap=6):
    """Rend un texte « Discord » : gère le gras (**…**) et le retour à la ligne."""
    x, y = xy
    for paragraph in text.split("\n"):
        segmentos = paragraph.split("**")
        tokens: list[tuple[str, bool]] = []
        for index, segment in enumerate(segmentos):
            if not segment:
                continue
            tokens.append((_plain(segment), index % 2 == 1))
        if not tokens:
            y += font.size + line_gap
            continue
        line, line_bold = "", False
        for token, bold in tokens:
            for word in token.split(" "):
                if word == "" and line:
                    continue
                candidate = f"{line} {word}".strip()
                font_used = bold_font if bold else font
                if font_used.getlength(candidate) <= width or not line:
                    line, line_bold = candidate, bold
                else:
                    draw.text((x, y), line, font=(bold_font if line_bold else font), fill=fill)
                    y += font.size + line_gap
                    line, line_bold = word, bold
        if line:
            draw.text((x, y), line, font=(bold_font if line_bold else font), fill=fill)
            y += font.size + line_gap
    return y


def _embed_height(embed, contenu_largeur: int) -> int:
    """Estimation de hauteur : titre, description, champs, image."""
    font = _font(False, 16)
    height = PAD + 10
    if embed.title:
        height += 30
    if embed.description:
        height += len(_wrap(_plain(embed.description), font, contenu_largeur)) * 22 + 10
    for field in embed.fields:
        height += 26
        height += len(_wrap(_plain(field.value), font, contenu_largeur)) * 22 + 10
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
    cursor = x
    for label, primaire in libelles:
        font = _font(False, 14)
        width = int(font.getlength(label)) + 34
        fill = BOUTON_PRIMAIRE if primaire else BOUTON_SECONDAIRE
        draw.rounded_rectangle([cursor, y, cursor + width, y + 36], radius=8, fill=fill)
        draw.text((cursor + 17, y + 10), label, font=font, fill=WHITE)
        cursor += width + 10
    return y + 52


def nouveau_canvas(hauteur_totale: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", (LARGEUR, hauteur_totale), BG)
    return canvas, ImageDraw.Draw(canvas)


def bandeau(draw, y: int, texte: str) -> int:
    font = _font(True, 13)
    draw.text((PAD + 2, y), texte.upper(), font=font, fill=MUTED)
    return y + 28


def build_parcours() -> Image.Image:
    store = SessionStore(ttl_seconds=600)
    session = store.start(1)
    session.grip, session.hand_length_mm, session.hand_width_mm = Grip.CLAW, 200.0, 110.0
    session.thenar = Thenar.MOYENNE
    etapes = [
        ("Accueil — message persistant (public)", flow.banner_embed(), ["🖱️  Start Mouse Shape Finder"], True),
        ("Étape 1/4 — prise", flow.grip_step_embed(), ["Choisissez votre prise…"], False),
        ("Étape 2/4 — thénar (arrière de la souris)", flow.thenar_step_embed(), ["Choisissez la taille de votre thénar…"], False),
        ("Étape 3/4 — mesures", flow.measure_step_embed(session), ["📏  Saisir mes mesures"], True),
        ("Étape 4/4 — budget", flow.budget_step_embed(session), ["Choisissez votre gamme…"], False),
    ]
    hauteur = sum(_embed_height(e, LARGEUR - 4 * PAD) + 52 + 28 + 16 for _, e, _, _ in etapes) + PAD
    canvas, draw = nouveau_canvas(hauteur)
    y = PAD
    for titre, embed, boutons, primaire in etapes:
        y = bandeau(draw, y, titre)
        y = draw_embed(canvas, draw, embed, y)
        y = draw_boutons(draw, y, [(b, primaire) for b in boutons])
    return canvas


def build_resultat() -> Image.Image:
    store = SessionStore(ttl_seconds=600)
    session = store.start(1)
    session.grip, session.hand_length_mm, session.hand_width_mm = Grip.PALM, 180.0, 100.0
    session.thenar = Thenar.PETITE
    session.budget_mode = BudgetMode.QUALITE_PRIX
    embeds = flow.results_embeds(session, flow.compute_selection(session))
    titres = [
        "Résultat — message éphémère (privé) : la recommandation",
        "Plus bas : les repères de taille (illustrés)",
        "Plus bas : l'arrière étroit, quand le thénar est « Petite »",
        "Plus bas : la bosse conseillée pour la prise",
        "Plus bas : la hauteur des boutons conseillée",
    ]
    hauteur = sum(_embed_height(e, LARGEUR - 4 * PAD) + 28 + 16 for e in embeds) + PAD + 200
    canvas, draw = nouveau_canvas(hauteur)
    y = PAD
    for index, embed in enumerate(embeds):
        y = bandeau(draw, y, titres[index] if index < len(titres) else embed.title)
        y = draw_embed(canvas, draw, embed, y)
        # Aucun bouton interactif : uniquement les liens d'achat (ou « 🔗 Liens à venir »).
        y = draw_boutons(draw, y, [("🛒 Acheter Scyrox V6", False), ("🔗 Liens à venir", False)])
    return canvas


def main() -> int:
    for nom, image in (("apercu_parcours.png", build_parcours()), ("apercu_resultat.png", build_resultat())):
        chemin = ROOT / "docs" / nom
        image.save(chemin, optimize=True)
        print(f"Écrit : {chemin} ({image.width}×{image.height}, {chemin.stat().st_size // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
