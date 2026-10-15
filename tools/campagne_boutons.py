"""Campagne « hauteur des boutons » sur les profils latéraux d'EloShapes (80e passe, 2026-10-15).

Pourquoi cet outil existe
-------------------------
18 souris sur 36 n'ont pas de hauteur de boutons : elles perdent les points de ce critère (5 sur 40
en Palm et en Claw, 10 en Fingertip) sans que personne sache si elles les méritaient. Mesuré le
2026-10-15 sur les 21 736 profils du banc : selon ce que vaudront ces 18 hauteurs, le match idéal peut
changer pour **5 810 profils (27 %)** et au moins une des trois places pour **14 627 (67 %)**.

L'outil historique (``tools/measure_button_height.py``) bute sur un seul obstacle : il lui faut une vue
de profil **parfaitement de côté**, et sur les sites des fabricants 7 vues sur 11 étaient en
perspective (``docs/audit/MESURE_BOUTONS_2026-10-12.md`` §5). EloShapes dessine toutes ses souris de
profil, à plat, **de la même façon** : c'est la source qu'il faut pour mesurer 36 souris d'un coup
avec une seule méthode.

Ce que fait l'outil
-------------------
1. ``mesurer`` : une image de profil latéral → la silhouette (fond transparent, fond uni ou couleur
   du tracé ; lignes de grille et légendes écartées), puis le **profil complet** du dessus de la coque,
   millimètre par millimètre depuis la pointe avant. Contrôle qualité : le rapport longueur/hauteur de
   la silhouette doit coller aux cotes du catalogue (vue de biais ou image d'une autre souris → refus),
   et la position de la bosse est confrontée à celle du catalogue (alerte d'orientation).
2. ``campagne`` : un manifeste (une ligne par image) → toutes les mesures, puis l'**étalonnage par les
   données** : les souris dont la hauteur de boutons est déjà connue choisissent elles-mêmes la mesure
   qui sépare le mieux « bas », « moyens » et « hauts » (validation en laissant chaque souris de côté à
   tour de rôle), et ses seuils. Les souris inconnues reçoivent une classe **proposée**, ou « non
   tranchée » quand la mesure tombe trop près d'un seuil. Les souris connues que la mesure contredit
   sont signalées « à revoir ».

Ce que l'outil ne fait pas
--------------------------
Il n'écrit **jamais** dans le catalogue : il produit un rapport (Markdown) et un relevé (JSON) qui
disent tout — image, empreinte SHA-256, source, date, valeurs, seuils, accord. Publier une valeur reste
une décision humaine, prise sur ce rapport. Aucune valeur n'est devinée : une image refusée ne produit
rien, une mesure ambiguë reste « non tranchée ».

Usage
-----
    python tools/campagne_boutons.py mesurer IMAGE --id atk_zero --avant droite
    python tools/campagne_boutons.py campagne manifeste.csv --rapport rapport.md --json releve.json

Le manifeste est un CSV à en-tête ``id,image,avant,source,date`` (colonne ``couleur`` facultative,
« #RRGGBB » du tracé quand l'image porte une grille). ``avant`` vaut ``gauche`` ou ``droite`` : le côté
de l'image où se trouve l'avant de la souris (les boutons).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PAR_DEFAUT = ROOT / "data" / "mouse_db.json"

CLASSES = ("Low", "Mid", "High")                 # ordre croissant de hauteur
NOM_CLASSE = {"Low": "bas", "Mid": "moyens", "High": "hauts"}
INCONNU = "Inconnu"

# Vue orthographique : le rapport longueur/hauteur de la silhouette doit coller aux cotes du catalogue.
# EloShapes dessine à plat (écart attendu ~1 %) ; au-delà de 4 %, la vue est de biais ou ce n'est pas
# la bonne souris — la mesure est refusée, rien n'est produit.
TOLERANCE_ASPECT = 0.04
# Alpha minimal d'un pixel de souris sur une image détourée (PNG transparent).
ALPHA_MIN = 40
# Une ligne de grille traverse toute l'image ; la souris, jamais (consigne : laisser une marge autour).
GRILLE_COUVERTURE = 0.98
# Lissage du profil : médiane des colonnes à ± 0,5 mm autour du point demandé.
DEMI_FENETRE_MM = 0.5

# Les mesures candidates. Les « h_ » sont des hauteurs absolues du dessus de la coque (mm, au-dessus du
# tapis), relevées à une distance donnée de la pointe avant ; les « rapport_ » divisent cette hauteur
# par la hauteur maximale de la souris. « rapport_5pct » est la mesure de l'outil historique (5 % de la
# longueur, ``measure_button_height.CLICK_FRACTION``) : elle reste en lice, sans privilège.
METRIQUES = ("rapport_5pct", "h_10mm", "h_20mm", "h_30mm", "rapport_20mm")
# Bruit de mesure de chaque grandeur : une valeur plus proche d'un seuil que ce bruit reste NON TRANCHÉE.
BRUIT = {"rapport_5pct": 0.01, "h_10mm": 0.5, "h_20mm": 0.5, "h_30mm": 0.5, "rapport_20mm": 0.01}
UNITE = {"rapport_5pct": "%", "h_10mm": "mm", "h_20mm": "mm", "h_30mm": "mm", "rapport_20mm": "%"}

# Position attendue de la bosse (fraction de la longueur depuis l'avant) selon le catalogue. Contrôle
# lâche : il sert à repérer une image retournée (avant/arrière inversés), pas à mesurer la bosse.
BOSSE_ATTENDUE = {"Front": (0.0, 0.48), "Mid-Front": (0.2, 0.58), "Mid": (0.3, 0.65),
                  "Mid-Rear": (0.38, 0.8), "Rear": (0.45, 1.0)}


class EntreeInvalide(ValueError):
    """Erreur d'entrée à dire en une phrase (code 2), jamais par une trace Python."""


# ---------------------------------------------------------------------------
# Silhouette
# ---------------------------------------------------------------------------
def lire_couleur(texte: str | None) -> tuple[int, int, int] | None:
    """« #RRGGBB » ou « R,G,B » → triplet ; ``None`` si rien n'est donné."""
    if not texte:
        return None
    texte = texte.strip()
    try:
        if texte.startswith("#") and len(texte) == 7:
            return tuple(int(texte[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
        r, g, b = (int(v) for v in texte.split(","))
        return r, g, b
    except ValueError as exc:
        raise EntreeInvalide(f"couleur illisible : « {texte} » (attendu #RRGGBB ou R,G,B)") from exc


def _masque(img: Image.Image, couleur: tuple[int, int, int] | None, tolerance: int) -> bytearray:
    """1 = pixel de souris. Trois lectures, dans l'ordre : couleur du tracé, transparence, fond uni."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    # ``tobytes`` (RGBA, 4 octets par pixel) : identique sur toutes les versions de Pillow, là où
    # ``getdata`` est annoncé retiré pour Pillow 14 et son remplaçant absent des versions anciennes.
    octets = rgba.tobytes()

    def pixel(i: int) -> tuple[int, int, int, int]:
        return tuple(octets[4 * i:4 * i + 4])  # type: ignore[return-value]

    bord = [pixel(i) for i in (0, w - 1, (h - 1) * w, h * w - 1, w // 2, (h - 1) * w + w // 2)]
    transparent = sum(1 for p in bord if p[3] < 250) >= 4
    masque = bytearray(w * h)
    r_, g_, b_, a_ = octets[0::4], octets[1::4], octets[2::4], octets[3::4]
    if couleur is not None:
        cr, cg, cb = couleur
        for i in range(w * h):
            if a_[i] > ALPHA_MIN and abs(r_[i] - cr) + abs(g_[i] - cg) + abs(b_[i] - cb) <= tolerance:
                masque[i] = 1
    elif transparent:
        for i in range(w * h):
            if a_[i] > ALPHA_MIN:
                masque[i] = 1
    else:
        bord.sort()
        fr, fg, fb = bord[len(bord) // 2][:3]
        for i in range(w * h):
            if abs(r_[i] - fr) + abs(g_[i] - fg) + abs(b_[i] - fb) > tolerance:
                masque[i] = 1
    return masque


def _blocs(indices: list[int]) -> list[tuple[int, int]]:
    """Regroupe des indices consécutifs : [3, 4, 9] → [(3, 4), (9, 9)] (une ligne épaisse = un bloc)."""
    blocs: list[tuple[int, int]] = []
    for i in indices:
        if blocs and i == blocs[-1][1] + 1:
            blocs[-1] = (blocs[-1][0], i)
        else:
            blocs.append((i, i))
    return blocs


def _retirer_grille(masque: bytearray, w: int, h: int) -> None:
    """Efface les lignes et colonnes de grille : un tracé continu d'un bord à l'autre de l'image.

    Une ligne de grille traverse aussi la souris quand celle-ci est pleine : effacer la rangée entière
    la couperait en tranches. Sur la rangée (ou le bloc de rangées) d'une ligne de grille, un pixel est
    donc RÉTABLI quand la souris est présente juste au-dessus ET juste au-dessous du bloc (même règle,
    à gauche et à droite, pour une colonne) : la grille disparaît, la souris reste d'un seul tenant.
    """
    def plus_long_trait(indices) -> int:
        meilleur = courant = 0
        for i in indices:
            courant = courant + 1 if masque[i] else 0
            meilleur = max(meilleur, courant)
        return meilleur

    rangees = [y for y in range(h) if plus_long_trait(range(y * w, (y + 1) * w)) >= GRILLE_COUVERTURE * w]
    colonnes = [x for x in range(w) if plus_long_trait(range(x, w * h, w)) >= GRILLE_COUVERTURE * h]
    for y0, y1 in _blocs(rangees):
        for x in range(w):
            pont = 0 < y0 and y1 < h - 1 and masque[(y0 - 1) * w + x] and masque[(y1 + 1) * w + x]
            for y in range(y0, y1 + 1):
                masque[y * w + x] = 1 if pont else 0
    for x0, x1 in _blocs(colonnes):
        for y in range(h):
            pont = 0 < x0 and x1 < w - 1 and masque[y * w + x0 - 1] and masque[y * w + x1 + 1]
            for x in range(x0, x1 + 1):
                masque[y * w + x] = 1 if pont else 0


def _plus_grande_composante(masque: bytearray, w: int, h: int) -> list[int]:
    """La souris est le plus grand ensemble de pixels connexes : légendes, cotes et poussières écartées."""
    vu = bytearray(w * h)
    meilleure: list[int] = []
    for depart in range(w * h):
        if not masque[depart] or vu[depart]:
            continue
        vu[depart] = 1
        composante, file = [], deque([depart])
        while file:
            i = file.popleft()
            composante.append(i)
            x, y = i % w, i // w
            for yy in (y - 1, y, y + 1):
                if 0 <= yy < h:
                    for xx in (x - 1, x, x + 1):
                        if 0 <= xx < w:
                            j = yy * w + xx
                            if masque[j] and not vu[j]:
                                vu[j] = 1
                                file.append(j)
        if len(composante) > len(meilleure):
            meilleure = composante
    return meilleure


@dataclass(frozen=True)
class Silhouette:
    x_min: int
    x_max: int
    y_haut: int                     # point le plus haut du dessus
    y_base: int                     # point le plus bas (le tapis)
    dessus: dict[int, int]          # colonne → première rangée de la souris

    @property
    def longueur_px(self) -> int:
        return self.x_max - self.x_min + 1

    @property
    def hauteur_px(self) -> int:
        return self.y_base - self.y_haut + 1


def silhouette(img: Image.Image, couleur: tuple[int, int, int] | None = None, tolerance: int = 40) -> Silhouette:
    w, h = img.size
    masque = _masque(img, couleur, tolerance)
    _retirer_grille(masque, w, h)
    pixels = _plus_grande_composante(masque, w, h)
    if len(pixels) < 50:
        raise EntreeInvalide("aucune souris détectée : le fond et la souris se confondent "
                             "(essayez --couleur avec la couleur du tracé)")
    dessus: dict[int, int] = {}
    dessous: dict[int, int] = {}
    for i in pixels:
        x, y = i % w, i // w
        if y < dessus.get(x, h):
            dessus[x] = y
        if y > dessous.get(x, -1):
            dessous[x] = y
    return Silhouette(min(dessus), max(dessus), min(dessus.values()), max(dessous.values()), dessus)


# ---------------------------------------------------------------------------
# Profil et mesures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Profil:
    longueur_mm: float
    hauteur_mm: float
    ecart_aspect: float             # |rapport L/H mesuré − rapport du catalogue| / rapport du catalogue
    hauteurs: tuple[float, ...]     # hauteur du dessus (mm) à 0, 1, 2… mm de la pointe avant
    position_bosse: float           # centre du sommet, en fraction de la longueur depuis l'avant

    def hauteur_a(self, distance_mm: float) -> float:
        """Hauteur du dessus à ``distance_mm`` de la pointe avant (interpolation linéaire)."""
        d = min(max(distance_mm, 0.0), len(self.hauteurs) - 1.0)
        i = int(d)
        if i >= len(self.hauteurs) - 1:
            return self.hauteurs[-1]
        return self.hauteurs[i] + (self.hauteurs[i + 1] - self.hauteurs[i]) * (d - i)

    def metriques(self) -> dict[str, float]:
        sommet = max(self.hauteurs)
        return {
            "rapport_5pct": self.hauteur_a(0.05 * self.longueur_mm) / sommet,
            "h_10mm": self.hauteur_a(10.0),
            "h_20mm": self.hauteur_a(20.0),
            "h_30mm": self.hauteur_a(30.0),
            "rapport_20mm": self.hauteur_a(20.0) / sommet,
        }


def profil(sil: Silhouette, longueur_mm: float, hauteur_mm: float, avant: str) -> Profil:
    """Le dessus de la coque, millimètre par millimètre depuis la pointe avant."""
    if avant not in ("gauche", "droite"):
        raise EntreeInvalide(f"côté avant inconnu : « {avant} » (gauche ou droite)")
    echelle_x = longueur_mm / sil.longueur_px        # mm par pixel, dans le sens de la longueur
    echelle_y = hauteur_mm / sil.hauteur_px          # mm par pixel, dans le sens de la hauteur
    rapport_mesure = sil.longueur_px / sil.hauteur_px
    rapport_catalogue = longueur_mm / hauteur_mm
    ecart = abs(rapport_mesure - rapport_catalogue) / rapport_catalogue
    demi = max(1, round(DEMI_FENETRE_MM / echelle_x))
    hauteurs = []
    for d in range(int(longueur_mm) + 1):
        decalage = round(d / echelle_x)
        x = sil.x_min + decalage if avant == "gauche" else sil.x_max - decalage
        voisins = [sil.dessus[c] for c in range(x - demi, x + demi + 1) if c in sil.dessus]
        if not voisins:
            raise EntreeInvalide(f"profil interrompu à {d} mm de l'avant (tracé incomplet)")
        hauteurs.append((sil.y_base - statistics.median(voisins)) * echelle_y)
    sommet = max(hauteurs)
    plateau = [d for d, v in enumerate(hauteurs) if v >= sommet - 0.3]
    position = statistics.median(plateau) / longueur_mm
    return Profil(longueur_mm, hauteur_mm, ecart, tuple(round(v, 2) for v in hauteurs), round(position, 3))


def ouvrir_image(chemin: Path) -> Image.Image:
    if not chemin.is_file():
        raise EntreeInvalide(f"image introuvable : {chemin}")
    try:
        with Image.open(chemin) as img:
            img.load()
            return img.copy()
    except (OSError, UnidentifiedImageError) as exc:
        raise EntreeInvalide(f"image illisible : {chemin} ({exc})") from exc


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
def charger_catalogue(chemin: Path) -> dict[str, dict]:
    if not chemin.is_file():
        raise EntreeInvalide(f"catalogue introuvable : {chemin}")
    try:
        souris = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EntreeInvalide(f"catalogue illisible : {chemin} ({exc})") from exc
    return {m["id"]: m for m in souris}


def fiche(catalogue: dict[str, dict], ident: str) -> dict:
    souris = catalogue.get(ident)
    if souris is None:
        raise EntreeInvalide(f"souris inconnue du catalogue : « {ident} »")
    if souris.get("length_mm") is None or souris.get("height_mm") is None:
        raise EntreeInvalide(f"{ident} : longueur ou hauteur absente du catalogue, aucune échelle possible")
    return souris


def alerte_bosse(position: float, bosse_catalogue: str) -> str | None:
    """Une bosse mesurée loin de celle du catalogue trahit le plus souvent une image retournée."""
    plage = BOSSE_ATTENDUE.get(bosse_catalogue)
    if plage is None or plage[0] <= position <= plage[1]:
        return None
    return (f"sommet mesuré à {position * 100:.0f} % de la longueur depuis l'avant, alors que le "
            f"catalogue annonce une bosse « {bosse_catalogue} » : vérifier le côté avant (--avant) "
            "et l'identité de l'image")


# ---------------------------------------------------------------------------
# Étalonnage par les données
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Etalonnage:
    metrique: str
    seuil_bas: float                # frontière « bas / moyens »
    seuil_haut: float               # frontière « moyens / hauts »
    erreurs: int                    # souris connues mal classées par ces seuils
    loo_justes: int                 # validation en laissant chaque souris de côté
    effectif: int
    marge: float                    # plus petite distance d'une souris connue à un seuil


def _classer(valeur: float, seuil_bas: float, seuil_haut: float) -> str:
    if valeur < seuil_bas:
        return "Low"
    if valeur < seuil_haut:
        return "Mid"
    return "High"


def _seuils(echantillons: list[tuple[str, float]]) -> tuple[float, float, int, float]:
    """Les deux seuils qui classent le mieux les souris connues (puis la plus grande marge).

    Recherche exhaustive : chaque seuil candidat est un milieu entre deux valeurs voisines. Avec
    36 souris au plus, c'est quelques centaines de couples — exact, sans approximation.
    """
    valeurs = sorted({v for _, v in echantillons})
    candidats = ([valeurs[0] - 1.0] + [(a + b) / 2 for a, b in zip(valeurs, valeurs[1:])]
                 + [valeurs[-1] + 1.0])
    meilleur = None
    for i, bas in enumerate(candidats):
        for haut in candidats[i:]:
            erreurs = sum(_classer(v, bas, haut) != c for c, v in echantillons)
            marge = min(min(abs(v - bas), abs(v - haut)) for _, v in echantillons)
            cle = (erreurs, -marge)
            if meilleur is None or cle < meilleur[0]:
                meilleur = (cle, bas, haut)
    (erreurs, moins_marge), bas, haut = meilleur  # type: ignore[misc]
    return bas, haut, erreurs, -moins_marge


def etalonner(metrique: str, connues: list[tuple[str, str, float]]) -> Etalonnage:
    """Seuils d'une mesure, ajustés sur les souris connues, et leur validation croisée."""
    echantillons = [(classe, valeur) for _, classe, valeur in connues]
    bas, haut, erreurs, marge = _seuils(echantillons)
    justes = 0
    for k, (classe, valeur) in enumerate(echantillons):
        autres = echantillons[:k] + echantillons[k + 1:]
        if len({c for c, _ in autres}) < len(CLASSES):
            continue                 # sans les trois classes, aucun seuil n'est ajustable : non compté
        b, h, _, _ = _seuils(autres)
        justes += _classer(valeur, b, h) == classe
    return Etalonnage(metrique, bas, haut, erreurs, justes, len(echantillons), marge)


def choisir(etalonnages: list[Etalonnage]) -> Etalonnage:
    """La mesure retenue : la meilleure validation croisée, puis la marge la plus large (en bruits)."""
    return max(etalonnages, key=lambda e: (e.loo_justes, -e.erreurs, e.marge / BRUIT[e.metrique]))


# ---------------------------------------------------------------------------
# Campagne
# ---------------------------------------------------------------------------
@dataclass
class Releve:
    ident: str
    image: str
    source: str
    date: str
    avant: str
    sha256: str = ""
    classe_catalogue: str = INCONNU
    metriques: dict[str, float] = field(default_factory=dict)
    ecart_aspect: float | None = None
    position_bosse: float | None = None
    refus: str | None = None
    alertes: list[str] = field(default_factory=list)
    classe_proposee: str | None = None
    verdict: str = ""


def mesurer_ligne(ligne: dict[str, str], dossier: Path, catalogue: dict[str, dict]) -> Releve:
    ident = (ligne.get("id") or "").strip()
    releve = Releve(ident, (ligne.get("image") or "").strip(), (ligne.get("source") or "").strip(),
                    (ligne.get("date") or "").strip(), (ligne.get("avant") or "").strip())
    try:
        souris = fiche(catalogue, ident)
        releve.classe_catalogue = souris.get("button_height", INCONNU)
        chemin = dossier / releve.image
        img = ouvrir_image(chemin)
        releve.sha256 = empreinte(chemin)
        sil = silhouette(img, lire_couleur(ligne.get("couleur")), int(ligne.get("tolerance") or 40))
        prof = profil(sil, float(souris["length_mm"]), float(souris["height_mm"]), releve.avant)
    except EntreeInvalide as exc:
        releve.refus = str(exc)
        return releve
    releve.ecart_aspect = round(prof.ecart_aspect, 4)
    releve.position_bosse = prof.position_bosse
    if prof.ecart_aspect > TOLERANCE_ASPECT:
        releve.refus = (f"vue refusée : rapport longueur/hauteur à {prof.ecart_aspect * 100:.1f} % des "
                        f"cotes du catalogue (tolérance {TOLERANCE_ASPECT * 100:.0f} %) — vue de biais "
                        "ou image d'une autre souris")
        return releve
    releve.metriques = {k: round(v, 4) for k, v in prof.metriques().items()}
    alerte = alerte_bosse(prof.position_bosse, souris.get("hump_position", INCONNU))
    if alerte:
        releve.alertes.append(alerte)
    return releve


def lire_manifeste(chemin: Path) -> list[dict[str, str]]:
    if not chemin.is_file():
        raise EntreeInvalide(f"manifeste introuvable : {chemin}")
    with chemin.open(encoding="utf-8-sig", newline="") as fh:
        lignes = list(csv.DictReader(fh))
    manquantes = {"id", "image", "avant"} - set(lignes[0].keys() if lignes else ())
    if not lignes or manquantes:
        raise EntreeInvalide(f"manifeste sans les colonnes {sorted(manquantes) or ['id', 'image', 'avant']}")
    return lignes


def conclure(releves: list[Releve]) -> tuple[Etalonnage | None, list[Etalonnage]]:
    """Étalonne chaque mesure sur les souris connues, retient la meilleure, classe les autres."""
    mesurees = [r for r in releves if r.refus is None]
    connues = [r for r in mesurees if r.classe_catalogue in CLASSES]
    if len({r.classe_catalogue for r in connues}) < len(CLASSES):
        for r in mesurees:
            r.verdict = "étalonnage impossible : il faut au moins une souris connue de chaque classe"
        return None, []
    etalonnages = [etalonner(m, [(r.ident, r.classe_catalogue, r.metriques[m]) for r in connues])
                   for m in METRIQUES]
    retenu = choisir(etalonnages)
    bruit = BRUIT[retenu.metrique]
    for r in mesurees:
        valeur = r.metriques[retenu.metrique]
        distance = min(abs(valeur - retenu.seuil_bas), abs(valeur - retenu.seuil_haut))
        classe = _classer(valeur, retenu.seuil_bas, retenu.seuil_haut)
        if distance < bruit:
            r.classe_proposee = None
            r.verdict = "non tranchée (trop près d'un seuil)"
        elif r.classe_catalogue in CLASSES:
            r.classe_proposee = classe
            r.verdict = "accord" if classe == r.classe_catalogue else "À REVOIR : la mesure contredit le catalogue"
        else:
            r.classe_proposee = classe
            r.verdict = "classe proposée"
    return retenu, etalonnages


def _fmt(metrique: str, valeur: float) -> str:
    texte = f"{valeur * 100:.1f} %" if UNITE[metrique] == "%" else f"{valeur:.1f} mm"
    return texte.replace(".", ",")


def rapport_markdown(releves: list[Releve], retenu: Etalonnage | None, etalonnages: list[Etalonnage]) -> str:
    lignes = ["# Campagne « hauteur des boutons » — profils latéraux", ""]
    mesurees = [r for r in releves if r.refus is None]
    lignes.append(f"Images : **{len(releves)}** · mesurées : **{len(mesurees)}** · refusées : "
                  f"**{len(releves) - len(mesurees)}**.")
    lignes.append("")
    if retenu is None:
        lignes.append("**Étalonnage impossible** : il faut au moins une souris connue de chaque classe.")
    else:
        lignes += [
            f"Mesure retenue par les données : **{retenu.metrique}** — seuils "
            f"{_fmt(retenu.metrique, retenu.seuil_bas)} (bas/moyens) et {_fmt(retenu.metrique, retenu.seuil_haut)} "
            f"(moyens/hauts) ; validation croisée **{retenu.loo_justes}/{retenu.effectif}** souris connues "
            f"retrouvées, {retenu.erreurs} contradiction(s) avec tous les seuils ajustés.",
            "",
            "Prudence : la mesure retenue est choisie parmi plusieurs candidates sur le même petit échantillon ; "
            "sa validation croisée est donc un peu optimiste.",
            "",
            "## Mesures candidates",
            "",
            "| Mesure | Validation croisée | Contradictions | Seuil bas/moyens | Seuil moyens/hauts | Marge |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for e in sorted(etalonnages, key=lambda e: (-e.loo_justes, e.erreurs)):
            lignes.append(f"| {e.metrique}{' ✅' if e is retenu else ''} | {e.loo_justes}/{e.effectif} | "
                          f"{e.erreurs} | {_fmt(e.metrique, e.seuil_bas)} | {_fmt(e.metrique, e.seuil_haut)} | "
                          f"{_fmt(e.metrique, e.marge)} |")
    for titre, filtre in (("Souris dont la hauteur est connue (contrôle)", lambda r: r.classe_catalogue in CLASSES),
                          ("Souris sans hauteur de boutons (proposition)", lambda r: r.classe_catalogue not in CLASSES)):
        groupe = [r for r in mesurees if filtre(r)]
        if not groupe:
            continue
        lignes += ["", f"## {titre}", "",
                   "| Souris | Catalogue | " + " | ".join(METRIQUES) + " | Proposée | Verdict |",
                   "| --- | --- | " + " | ".join("---" for _ in METRIQUES) + " | --- | --- |"]
        for r in sorted(groupe, key=lambda r: r.ident):
            valeurs = " | ".join(_fmt(m, r.metriques[m]) for m in METRIQUES)
            lignes.append(f"| `{r.ident}` | {NOM_CLASSE.get(r.classe_catalogue, '—')} | {valeurs} | "
                          f"{NOM_CLASSE.get(r.classe_proposee or '', '—')} | {r.verdict} |")
    refusees = [r for r in releves if r.refus is not None]
    alertes = [r for r in mesurees if r.alertes]
    if refusees or alertes:
        lignes += ["", "## Refus et alertes", ""]
        lignes += [f"- `{r.ident or '?'}` ({r.image}) : **refusée** — {r.refus}" for r in refusees]
        lignes += [f"- `{r.ident}` : alerte — {a}" for r in alertes for a in r.alertes]
    lignes += ["", "## Traçabilité", "", "| Souris | Image | SHA-256 (12) | Avant | Source | Date |",
               "| --- | --- | --- | --- | --- | --- |"]
    lignes += [f"| `{r.ident}` | {r.image} | {r.sha256[:12] or '—'} | {r.avant} | {r.source or '—'} | {r.date or '—'} |"
               for r in releves]
    return "\n".join(lignes) + "\n"


def releve_json(releves: list[Releve], retenu: Etalonnage | None) -> dict:
    return {
        "outil": "tools/campagne_boutons.py",
        "mesure_retenue": None if retenu is None else {
            "metrique": retenu.metrique, "seuil_bas": round(retenu.seuil_bas, 4),
            "seuil_haut": round(retenu.seuil_haut, 4), "validation_croisee": f"{retenu.loo_justes}/{retenu.effectif}",
            "contradictions": retenu.erreurs},
        "releves": [{
            "id": r.ident, "image": r.image, "sha256": r.sha256, "source": r.source, "date": r.date,
            "avant": r.avant, "classe_catalogue": r.classe_catalogue, "metriques": r.metriques,
            "ecart_aspect": r.ecart_aspect, "position_bosse": r.position_bosse, "refus": r.refus,
            "alertes": r.alertes, "classe_proposee": r.classe_proposee, "verdict": r.verdict,
        } for r in releves],
    }


# ---------------------------------------------------------------------------
# Ligne de commande
# ---------------------------------------------------------------------------
def _parseur() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hauteur des boutons mesurée sur des profils latéraux (EloShapes).")
    sous = parser.add_subparsers(dest="commande", required=True)
    un = sous.add_parser("mesurer", help="mesurer une image de profil")
    un.add_argument("image")
    un.add_argument("--id", required=True, help="identifiant du catalogue (ex. atk_zero)")
    un.add_argument("--avant", required=True, choices=("gauche", "droite"))
    un.add_argument("--couleur", help="couleur du tracé (#RRGGBB) quand l'image porte une grille")
    un.add_argument("--tolerance", type=int, default=40)
    un.add_argument("--catalogue", default=str(CATALOGUE_PAR_DEFAUT))
    tous = sous.add_parser("campagne", help="mesurer toutes les images d'un manifeste CSV, puis étalonner")
    tous.add_argument("manifeste")
    tous.add_argument("--dossier", help="dossier des images (par défaut : celui du manifeste)")
    tous.add_argument("--rapport", help="fichier Markdown à écrire (sinon : affiché)")
    tous.add_argument("--json", dest="json_sortie", help="relevé JSON à écrire")
    tous.add_argument("--catalogue", default=str(CATALOGUE_PAR_DEFAUT))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parseur()
    args = parser.parse_args(argv)
    try:
        catalogue = charger_catalogue(Path(args.catalogue))
        if args.commande == "mesurer":
            souris = fiche(catalogue, args.id)
            img = ouvrir_image(Path(args.image))
            sil = silhouette(img, lire_couleur(args.couleur), args.tolerance)
            prof = profil(sil, float(souris["length_mm"]), float(souris["height_mm"]), args.avant)
            print(f"{souris['brand']} {souris['model']} — {args.image}")
            print(f"Rapport longueur/hauteur : écart de {prof.ecart_aspect * 100:.1f} % aux cotes du catalogue "
                  f"({'accepté' if prof.ecart_aspect <= TOLERANCE_ASPECT else 'REFUSÉ : vue de biais ou autre souris'})")
            print(f"Sommet à {prof.position_bosse * 100:.0f} % de la longueur depuis l'avant")
            alerte = alerte_bosse(prof.position_bosse, souris.get("hump_position", INCONNU))
            if alerte:
                print(f"⚠️ {alerte}")
            for nom, valeur in prof.metriques().items():
                print(f"  {nom:13} {_fmt(nom, valeur)}")
            print("Profil (mm depuis l'avant → hauteur) : " + " · ".join(
                f"{d}→{prof.hauteur_a(d):.1f}" for d in range(0, int(prof.longueur_mm) + 1, 10)))
            return 0
        manifeste = Path(args.manifeste)
        lignes = lire_manifeste(manifeste)
        dossier = Path(args.dossier) if args.dossier else manifeste.parent
        if not dossier.is_dir():
            raise EntreeInvalide(f"dossier des images introuvable : {dossier}")
    except EntreeInvalide as exc:
        parser.error(str(exc))
    releves = [mesurer_ligne(ligne, dossier, catalogue) for ligne in lignes]
    retenu, etalonnages = conclure(releves)
    texte = rapport_markdown(releves, retenu, etalonnages)
    if args.rapport:
        Path(args.rapport).write_text(texte, encoding="utf-8")
        print(f"Rapport écrit : {args.rapport}")
    else:
        print(texte)
    if args.json_sortie:
        Path(args.json_sortie).write_text(json.dumps(releve_json(releves, retenu), ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        print(f"Relevé écrit : {args.json_sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
