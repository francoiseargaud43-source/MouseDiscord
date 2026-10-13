"""Mesure l'effet d'une modification de DONNÉES : compare les trois places AVANT / APRÈS.

But : ne jamais annoncer « telle correction change X profils » sans preuve. ``tools/flow_effect.py``
compare deux versions du **code** de l'aiguillage ; cet outil-ci compare deux versions du
**catalogue** (``data/mouse_db.json``) en passant EXACTEMENT la même grille de profils dans les deux.
Le barème, les fenêtres des trois places et la présentation ne sont jamais modifiés : seul le fichier
de données change, donc tout écart mesuré vient des données.

Usage :
    .venv/bin/python tools/db_effect.py --avant /tmp/mouse_db_avant.json                 # grille complète
    .venv/bin/python tools/db_effect.py --avant /tmp/mouse_db_avant.json --grille rapide
    .venv/bin/python tools/db_effect.py --avant /tmp/mouse_db_avant.json --grille mini
    .venv/bin/python tools/db_effect.py --avant ancienne.json --exemples 5
    .venv/bin/python tools/db_effect.py --avant data/mouse_db.json --apres /tmp/sans_rupture.json --retrait

Deux catalogues qui ne listent pas les mêmes souris ne se comparent pas : l'outil refuse (une souris
absente d'un côté fausserait tout). L'option ``--retrait`` lève ce refus **pour une simulation de
retrait** uniquement (catalogue APRÈS = sous-ensemble strict du précédent) : elle mesure alors le
poids des souris sorties (places occupées avant, par souris et au total) et qui reprend leur place.

L'outil n'écrit rien dans le dépôt (les catalogues sont copiés dans un dossier temporaire), ne
modifie aucune donnée et ne touche pas au réseau. Sortie : nombre de profils comparés, nombre de
profils dont le résultat change, répartition par place (idéale, alternative, économie), places
gagnées ou perdues, listes où deux places reprennent la même coque après la modification, et
quelques exemples lisibles (« avant → après »).
"""
from __future__ import annotations

import argparse
import itertools
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import qa_flow_matrix as banc  # noqa: E402  (grille et profil de référence du banc d'essai)
import cogs.finder_flow as flux  # noqa: E402
from utils.catalog import CatalogError, load_catalog  # noqa: E402
from utils.matcher import compatibility_percent  # noqa: E402
from utils.models import BudgetMode, ClawVariant, Grip, Thenar  # noqa: E402


def _mini() -> tuple[list, list, list, list, list, list]:
    """Grille minimale (150 profils) : pour les tests, sans attendre la grille complète.

    Trois prises, trois longueurs, deux largeurs, deux thénars et quatre modes (dont deux budgets
    personnalisés) : assez large pour qu'une modification de données se voie — un test qui ne
    mesurerait aucun changement ne prouverait rien (``tests/test_db_effect.py`` vérifie les deux cas).
    """
    return ([Grip.PALM, Grip.CLAW, Grip.FINGERTIP], [170.0, 180.0, 200.0], [90.0, 110.0],
            [Thenar.PETITE, Thenar.GRANDE],
            [None, BudgetMode.ECONOMIQUE, BudgetMode.HAUT_DE_GAMME, BudgetMode.CUSTOM], [30.0, 60.0])


def grille(nom: str) -> tuple[list, list, list, list, list, list]:
    """(prises, longueurs, largeurs, thénars, modes, budgets) — « complete » par défaut."""
    if nom == "mini":
        return _mini()
    rapide = nom == "rapide"
    return (banc.GRIPS, banc._lengths(rapide), banc._widths(rapide), banc.THENARS,
            banc.MODES, banc._budgets(rapide))


@dataclass
class Rapport:
    profils: int = 0
    changes: list[str] = field(default_factory=list)          # une ligne par profil qui change
    par_place: dict[str, int] = field(default_factory=dict)   # idéal / alternative / économie
    memes_coques: int = 0
    autre_forme: int = 0
    place_gagnee: int = 0
    place_perdue: int = 0
    retirees: list[str] = field(default_factory=list)                  # mode --retrait seulement
    par_souris_retiree: dict[str, int] = field(default_factory=dict)   # places occupées avant
    remplacants: dict[str, int] = field(default_factory=dict)          # qui reprend la place

    @property
    def places_retirees(self) -> int:
        return sum(self.par_souris_retiree.values())

    @property
    def taux(self) -> float:
        return 100.0 * len(self.changes) / self.profils if self.profils else 0.0


def _places(chemin: Path, profils: list[tuple]) -> list[list[tuple[str, int]]]:
    """Trois places (identifiant, pourcentage) de chaque profil, le catalogue ``chemin`` étant chargé."""
    ancien = flux.MOUSE_DB_PATH
    flux.MOUSE_DB_PATH = chemin
    try:
        resultats: list[list[tuple[str, int]]] = []
        for grip, length, width, thenar, mode, budget in profils:
            session = banc.profile(mode, budget)
            session.grip = grip
            session.hand_length_mm = length
            session.hand_width_mm = width
            session.thenar = thenar if grip is not Grip.FINGERTIP else None
            if grip is Grip.CLAW:
                session.claw_variant = ClawVariant.RELACHEE
            selection = flux.compute_selection(session)
            resultats.append([
                (score.mouse.id, compatibility_percent(score))
                for score in flux.result_slots(selection) if score is not None
            ])
        return resultats
    finally:
        flux.MOUSE_DB_PATH = ancien


def _libelle(grip, length, width, thenar, mode, budget) -> str:
    nom_mode = mode.value if mode is not None else "aucun-mode"
    return (f"{grip.value} {length:.0f}x{width:.0f} thénar={thenar.value if thenar else '—'} "
            f"mode={nom_mode} budget={budget if budget is not None else '—'}")


def comparer(chemin_avant: Path | str, chemin_apres: Path | str, grille_nom: str = "complete", *,
             retrait: bool = False) -> Rapport:
    """Compare les trois places des deux catalogues sur toute la grille. Ne modifie aucun fichier.

    Avec ``retrait=True``, le catalogue APRÈS peut être un **sous-ensemble strict** du précédent :
    l'écart mesure alors ce que pèsent les souris sorties (et qui reprend leur place).
    """
    prise, longueurs, largeurs, thenars, modes, budgets = grille(grille_nom)
    combinaisons = [
        (grip, length, width, thenar, mode, budget)
        for grip, length, width, thenar in itertools.product(prise, longueurs, largeurs, thenars)
        if grip is Grip.CLAW or thenar is not None   # même règle de grille que le banc d'essai
        for mode in modes
        for budget in (budgets if mode is BudgetMode.CUSTOM else [None])
    ]
    if not combinaisons:                                     # pragma: no cover - garde-fou
        raise ValueError("grille vide : la comparaison ne prouverait rien")

    with tempfile.TemporaryDirectory() as dossier:
        temporaires = []
        for source in (chemin_avant, chemin_apres):
            copie = Path(dossier) / f"mouse_db_{len(temporaires)}.json"
            shutil.copyfile(source, copie)
            temporaires.append(copie)
        catalogue_avant = load_catalog(temporaires[0])
        catalogue_apres = load_catalog(temporaires[1])
        par_id = {m.id: m for m in catalogue_avant}
        ids_avant = set(par_id)
        ids_apres = {m.id for m in catalogue_apres}
        retirees = sorted(ids_avant - ids_apres)
        ajoutees = sorted(ids_apres - ids_avant)
        if (retirees or ajoutees) and not (retrait and retirees and not ajoutees):
            raise ValueError("les deux catalogues ne contiennent pas les mêmes souris")

        resultats_avant = _places(temporaires[0], combinaisons)
        resultats_apres = _places(temporaires[1], combinaisons)

    rapport = Rapport(profils=len(combinaisons), retirees=retirees)
    for cas, avant, apres in zip(combinaisons, resultats_avant, resultats_apres):
        identifiants_avant = {identifiant for identifiant, _ in avant}
        for identifiant, _pourcentage in avant:                     # poids réel des souris sorties
            if identifiant in rapport.retirees:
                rapport.par_souris_retiree[identifiant] = rapport.par_souris_retiree.get(identifiant, 0) + 1
        if avant == apres:
            continue
        rapport.changes.append(f"{_libelle(*cas)} : {avant} → {apres}")
        for identifiant, _pourcentage in apres:                     # qui reprend la place laissée libre
            if identifiant not in identifiants_avant:
                rapport.remplacants[identifiant] = rapport.remplacants.get(identifiant, 0) + 1
        # Nature du changement : même coque ou vraie autre forme, place gagnée ou perdue.
        if len(apres) > len(avant):
            rapport.place_gagnee += 1
        elif len(apres) < len(avant):
            rapport.place_perdue += 1
        for index, place in enumerate(("ideal", "alternative", "economie")):
            if avant[index:index + 1] != apres[index:index + 1]:
                rapport.par_place[place] = rapport.par_place.get(place, 0) + 1
        couples = list(itertools.combinations(apres, 2))
        memes = any(_same_shell_par_id(par_id, a, b) for a, b in couples)
        rapport.memes_coques += int(memes)
        rapport.autre_forme += int(bool(couples) and not memes)
    return rapport


def _same_shell_par_id(par_id: dict, premier: tuple[str, int], second: tuple[str, int]) -> bool:
    """« Même coque » (``shell_id``) entre deux places décrites par (id, pourcentage)."""
    a, b = par_id[premier[0]], par_id[second[0]]
    return a.id == b.id or bool(a.shell_id) and a.shell_id == b.shell_id


def main() -> int:
    analyseur = argparse.ArgumentParser(description="Effet d'une modification de données sur les 3 places.")
    analyseur.add_argument("--avant", required=True, help="catalogue AVANT (JSON)")
    analyseur.add_argument("--apres", default=str(flux.MOUSE_DB_PATH), help="catalogue APRÈS (défaut : le dépôt)")
    analyseur.add_argument("--grille", choices=("complete", "rapide", "mini"), default="complete")
    analyseur.add_argument("--exemples", type=int, default=8, help="nombre d'exemples affichés")
    analyseur.add_argument("--retrait", action="store_true",
                           help="simulation de retrait : autorise un catalogue APRÈS réduit (sous-ensemble)")
    options = analyseur.parse_args()

    # Fichier absent ou illisible : le dire en une ligne plutôt que de laisser remonter un
    # FileNotFoundError brut (trouvé le 2026-10-13, chasse aux micro-bugs).
    for etiquette, chemin in (("AVANT", options.avant), ("APRÈS", options.apres)):
        if not Path(chemin).is_file():
            analyseur.error(f"catalogue introuvable ({etiquette}) : {chemin}")
    try:
        rapport = comparer(options.avant, options.apres, options.grille, retrait=options.retrait)
    except (CatalogError, ValueError, OSError) as exc:
        analyseur.error(f"catalogue illisible ou incohérent : {exc}")
    print(f"Grille « {options.grille} » — profils comparés : {rapport.profils}")
    if rapport.retirees:
        detail = ", ".join(f"{identifiant} {n}" for identifiant, n in
                           sorted(rapport.par_souris_retiree.items(), key=lambda item: -item[1]))
        print(f"Souris retirées : {len(rapport.retirees)} ({', '.join(rapport.retirees)})")
        print(f"Places qu'elles occupaient AVANT : {rapport.places_retirees} — {detail or 'aucune place'}")
    print(f"Profils dont le résultat change : {len(rapport.changes)} ({rapport.taux:.2f} %)")
    if rapport.changes:
        if rapport.remplacants:
            top = sorted(rapport.remplacants.items(), key=lambda item: (-item[1], item[0]))[:5]
            print("  places reprises par : " + ", ".join(f"{identifiant} {n}" for identifiant, n in top))
        print("  par place : " + ", ".join(f"{place} {n}" for place, n in sorted(rapport.par_place.items())))
        print(f"  place gagnée : {rapport.place_gagnee} · place perdue : {rapport.place_perdue}")
        print(f"  nouvelle liste sans deux fois la même coque : {rapport.autre_forme}")
        print(f"  nouvelle liste avec deux fois la même coque (repli documenté) : {rapport.memes_coques}")
        for ligne in rapport.changes[:options.exemples]:
            print(f"  · {ligne}")
        if len(rapport.changes) > options.exemples:
            print(f"  · … et {len(rapport.changes) - options.exemples} autre(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
