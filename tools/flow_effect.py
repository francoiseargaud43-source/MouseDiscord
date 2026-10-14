"""Mesure l'effet d'une modification du parcours : compare les trois places AVANT / APRÈS.

But : ne jamais annoncer « ça change X profils » sans preuve. L'outil recharge l'ancienne version de
``cogs/finder_flow.py`` depuis un commit du dépôt (``git show``), la met à côté de la version en cours
et passe EXACTEMENT la même grille de profils dans les deux (même sélection : seul l'aiguillage des
places change, le barème n'est jamais recalculé).

Usage :
    .venv/bin/python tools/flow_effect.py                 # grille complète vs HEAD
    .venv/bin/python tools/flow_effect.py --rapide        # grille réduite
    .venv/bin/python tools/flow_effect.py --avant cd977a6 # référence explicite

L'outil n'écrit rien dans le dépôt, ne modifie aucune donnée et ne touche pas au réseau.
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import qa_flow_matrix as banc  # noqa: E402  (réutilise la grille du banc d'essai)
from cogs.finder_flow import compute_selection, result_slots  # noqa: E402
from utils.models import ClawVariant, Grip  # noqa: E402
from utils.selection import _same_shell  # noqa: E402


def charger_ancienne_version(ref: str):
    """Importe ``cogs/finder_flow.py`` tel qu'il était au commit ``ref`` (copie temporaire)."""
    source = subprocess.run(
        ["git", "show", f"{ref}:cogs/finder_flow.py"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    with tempfile.TemporaryDirectory() as dossier:
        chemin = Path(dossier) / "ancien_finder_flow.py"
        chemin.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("ancien_finder_flow", chemin)
        module = importlib.util.module_from_spec(spec)
        sys.modules["ancien_finder_flow"] = module      # sinon les décorateurs échouent
        spec.loader.exec_module(module)
    return module


def montrees(places) -> list[str]:
    """Les identifiants des souris montrées, place par place (une place vide n'apparaît pas)."""
    return [score.mouse.id for score in places if score is not None]


def meme_coque(places) -> bool:
    """Vrai si deux places du résultat montrent des variantes de la même coque."""
    for premier, second in itertools.combinations([s for s in places if s is not None], 2):
        if _same_shell(premier, second):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Effet d'une modification du parcours (avant/après)")
    parser.add_argument("--avant", default="HEAD", help="commit de référence pour l'ancienne version")
    parser.add_argument("--rapide", action="store_true", help="grille réduite")
    args = parser.parse_args(argv)

    try:
        ancien = charger_ancienne_version(args.avant)
    except subprocess.CalledProcessError:
        # Référence inconnue : `git show` échoue. Le dire en une ligne plutôt que de laisser
        # remonter un `CalledProcessError` brut (trouvé le 2026-10-13, chasse aux micro-bugs).
        parser.error(
            f"référence introuvable dans ce dépôt : {args.avant!r} "
            "(attendu : un commit, une branche ou HEAD)"
        )
    reference = args.avant
    if reference == "HEAD":
        reference = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   check=True, capture_output=True, text=True).stdout.strip()
    print(f"Ancienne version : {reference} · nouvelle version : arbre de travail\n")

    profils = 0
    ideaux_changes: list[str] = []
    alternatives_changees: list[str] = []
    places_avant: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    places_apres: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    meme_coque_avant = 0
    meme_coque_apres = 0
    pire_baisse = 0
    pire_baisse_exemple = ""
    economies_perdues: list[str] = []
    troisieme_avant_gagnee: list[str] = []
    troisiemes_changees: list[str] = []
    ordre_avant: list[str] = []                 # profils où le % remontait d'une place à l'autre
    ordre_apres: list[str] = []

    # La grille vient du banc d'essai, sans copie : une seule définition pour les trois outils.
    # La grille vient du banc d'essai, sans copie : une seule définition, pour les trois outils.
    for grip, length, width, thenar, mode, budget in banc.grille(args.rapide):
        session = banc.profile(mode, budget)
        session.grip = grip
        session.hand_length_mm = length
        session.hand_width_mm = width
        session.thenar = thenar          # la grille donne déjà None en Fingertip (testé au banc)
        if grip is Grip.CLAW:
            session.claw_variant = ClawVariant.RELACHEE
        selection = compute_selection(session)
        anciennes = ancien.result_slots(selection)
        nouvelles = result_slots(selection)
        if all(score is None for score in anciennes + nouvelles):
            continue
        profils += 1
        ou = f"{grip.value}/{length:.0f}x{width:.0f}/thenar={thenar}/mode={mode}/{budget}"
        places_avant[len(montrees(anciennes))] += 1
        places_apres[len(montrees(nouvelles))] += 1
        if meme_coque(anciennes):
            meme_coque_avant += 1
        if meme_coque(nouvelles):
            meme_coque_apres += 1

        if montrees(anciennes)[:1] != montrees(nouvelles)[:1]:
            ideaux_changes.append(ou)
        if montrees(anciennes)[2:3] != montrees(nouvelles)[2:3]:
            troisiemes_changees.append(ou)
        for places, compteur in ((anciennes, ordre_avant), (nouvelles, ordre_apres)):
            montrees_ici = [s for s in places if s is not None]
            if any(b.total > a.total for a, b in zip(montrees_ici, montrees_ici[1:])):
                compteur.append(ou)
        if montrees(anciennes)[1:2] != montrees(nouvelles)[1:2]:
            alternatives_changees.append(ou)
            avant_alt, apres_alt = anciennes[1], nouvelles[1]
            if avant_alt is not None and apres_alt is not None:
                baisse = avant_alt.total - apres_alt.total
                if baisse > pire_baisse:
                    pire_baisse = baisse
                    pire_baisse_exemple = (f"{ou} : {avant_alt.mouse.label} {avant_alt.total}/40 → "
                                           f"{apres_alt.mouse.label} {apres_alt.total}/40")
        if anciennes[2] is not None and nouvelles[2] is None:
            economies_perdues.append(f"{ou} : {anciennes[2].mouse.label} "
                                     f"(déjà montrées : {montrees(anciennes)[:2]})")
        if anciennes[2] is None and nouvelles[2] is not None:
            troisieme_avant_gagnee.append(ou)

    print(f"Profils comparés : {profils}")
    print(f"Match idéal : {len(ideaux_changes)} profil(s) changé(s)")
    print(f"Troisième place : {len(troisiemes_changees)} profil(s) changé(s)"
          + (f"  ·  ex. {troisiemes_changees[0]}" if troisiemes_changees else ""))
    print(f"Ordre des pourcentages violé AVANT : {len(ordre_avant)} · APRÈS : {len(ordre_apres)}")
    print(f"Alternative : {len(alternatives_changees)} profil(s) changé(s)"
          + (f"  ·  ex. {alternatives_changees[0]}" if alternatives_changees else ""))
    print("Places remplies AVANT : " + " · ".join(f"{n} place(s) : {places_avant[n]}" for n in (0, 1, 2, 3)))
    print("Places remplies APRÈS : " + " · ".join(f"{n} place(s) : {places_apres[n]}" for n in (0, 1, 2, 3)))
    print(f"Deux places sur la même coque AVANT : {meme_coque_avant}")
    print(f"Deux places sur la même coque APRÈS : {meme_coque_apres}")
    print(f"Pire baisse de score pour l'alternative : {pire_baisse} point(s)"
          + (f"  ({pire_baisse_exemple})" if pire_baisse_exemple else ""))
    print(f"Économie gagnée : {len(troisieme_avant_gagnee)} profil(s)"
          + (f"  ·  ex. {troisieme_avant_gagnee[0]}" if troisieme_avant_gagnee else ""))
    print(f"Économie perdue : {len(economies_perdues)} profil(s)")
    for ligne in economies_perdues[:5]:
        print(f"  · {ligne}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
