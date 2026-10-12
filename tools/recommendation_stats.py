"""Étude statistique des recommandations : combien de fois chaque souris sort, pour toutes les mains.

Usage (depuis la racine du dépôt) :
    python tools/recommendation_stats.py                 # grille complète (~2 min)
    python tools/recommendation_stats.py --rapide        # grille resserrée (contrôle rapide)
    python tools/recommendation_stats.py --sortie chemin.md

Le script n'introduit AUCUNE donnée : il applique le moteur (utils/matcher.py), la sélection
(utils/selection.py) et exactement la même mise en places que l'écran de résultat
(cogs.finder_flow.result_slots) — donc il mesure ce que le membre voit vraiment.

Domaine balayé (bornes réellement acceptées par le questionnaire, utils/validation.py) :
longueur de main de 140 à 240 mm, largeur de 60 à 125 mm, les trois prises, les trois tailles de
thénar (sautées en Fingertip, comme dans le parcours), les cinq modes, et cinq budgets personnalisés.

Sortie : docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md
"""
from __future__ import annotations

import argparse
import itertools
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import MOUSE_DB_PATH  # noqa: E402
from cogs.finder_flow import compute_selection, result_slots  # noqa: E402
from utils.catalog import load_catalog  # noqa: E402
from utils.matcher import evaluate_mouse  # noqa: E402
from utils.models import THENAR_LABELS, BudgetMode, ClawVariant, Grip, HandMeasure, Thenar  # noqa: E402
from utils.selection import _same_shell  # noqa: E402
from utils.session import FinderSession  # noqa: E402

# --- Vitesse : on ne relit le catalogue qu'une fois ; chaque profil est évalué par le moteur réel.
LENGTHS_FULL = tuple(range(140, 245, 5))       # 140 → 240 mm
WIDTHS_FULL = tuple(range(60, 130, 5))         #  60 → 125 mm
LENGTHS_FAST = (160, 175, 190, 205)
WIDTHS_FAST = (75, 90, 105)
BUDGETS_FULL = (25.0, 45.0, 60.0, 90.0, 150.0)
BUDGETS_FAST = (60.0,)
MODES = (BudgetMode.ECONOMIQUE, BudgetMode.QUALITE_PRIX, BudgetMode.HAUT_DE_GAMME,
         BudgetMode.PEU_IMPORTE_PRIX, BudgetMode.CUSTOM)
BUDGET_LABELS = {
    BudgetMode.ECONOMIQUE: "Économique",
    BudgetMode.QUALITE_PRIX: "Qualité/Prix",
    BudgetMode.HAUT_DE_GAMME: "Haut de gamme",
    BudgetMode.PEU_IMPORTE_PRIX: "Peu importe le prix",
    BudgetMode.CUSTOM: "Budget personnalisé",
}


def profiles(fast: bool):
    """Tous les profils du domaine : (prise, thénar, longueur, largeur, mode, budget)."""
    lengths = LENGTHS_FAST if fast else LENGTHS_FULL
    widths = WIDTHS_FAST if fast else WIDTHS_FULL
    budgets = BUDGETS_FAST if fast else BUDGETS_FULL
    for grip, length, width, thenar in itertools.product(Grip, lengths, widths, Thenar):
        if grip is Grip.FINGERTIP and thenar is not Thenar.MOYENNE:
            continue                        # le parcours ne pose pas la question en Fingertip
        combos = [(mode, None) for mode in MODES if mode is not BudgetMode.CUSTOM]
        combos += [(BudgetMode.CUSTOM, budget) for budget in budgets]
        for mode, budget in combos:
            yield grip, thenar, float(length), float(width), mode, budget


def make_session(grip, thenar, length, width, mode, budget) -> FinderSession:
    session = FinderSession(user_id=1)
    session.grip = grip
    session.thenar = None if grip is Grip.FINGERTIP else thenar
    session.claw_variant = ClawVariant.RELACHEE if grip is Grip.CLAW else None
    session.hand_length_mm = length
    session.hand_width_mm = width
    session.budget_mode = mode
    session.max_budget_eur = budget
    return session


def run(fast: bool = False):
    """Passe toute la grille et renvoie les comptages + l'état d'éligibilité de chaque souris."""
    mice = load_catalog(MOUSE_DB_PATH)
    shell_of = {mouse.id: mouse.shell_id for mouse in mice}    # coque partagée (mêmes dimensions)
    counter = {mouse.id: Counter() for mouse in mice}          # ideal / alternative / economie
    by_mode: dict[str, Counter] = defaultdict(Counter)
    by_grip: dict[str, Counter] = defaultdict(Counter)
    by_thenar: dict[str, Counter] = defaultdict(Counter)
    statuses = {mouse.id: Counter() for mouse in mice}         # scored / pending / excluded
    scores_seen: dict[str, list[int]] = defaultdict(list)      # points obtenus quand la souris est notée
    in_zone: Counter = Counter()                              # présent dans la zone de tolérance du mode
    same_shell_pairs: Counter = Counter()                     # deux places, une seule coque (repli documenté)
    dominated_by: dict[str, Counter] = defaultdict(Counter)    # qui remporte l'idéal quand la souris est notée
    twin_ahead: dict[str, Counter] = defaultdict(Counter)      # coque jumelle classée devant (structurel)
    empty_causes: Counter = Counter()
    total = 0
    empty = 0
    empty_with_unusable = 0
    same_shell_profiles = 0
    for grip, thenar, length, width, mode, budget in profiles(fast):
        session = make_session(grip, thenar, length, width, mode, budget)
        selection = compute_selection(session)
        total += 1
        for score in selection.ranked:
            scores_seen[score.mouse.id].append(score.total)
            in_zone[score.mouse.id] += 1
        for score in selection.pending:
            statuses[score.mouse.id]["pending"] += 1
        ideal, alternative, economy = result_slots(selection)
        if ideal is None:
            empty += 1
            if selection.pending:
                empty_with_unusable += 1
            # Pourquoi ce profil est vide : on sépare « aucune souris ne convient à cette main »
            # de « les souris qui conviennent coûtent plus cher que le budget demandé ». Un profil
            # en budget personnalisé n'a plus AUCUNE souris classable dès que le filtre de prix a
            # écarté tout le monde : sans cette seconde évaluation (hors budget), les deux causes
            # seraient confondues dans le rapport.
            sans_budget = [evaluate_mouse(m, HandMeasure(length, width), grip) for m in mice]
            classables = [s for s in sans_budget if s.is_scored]
            if not classables:
                empty_causes["aucune souris ne convient à cette main et à cette prise"] += 1
            elif budget is not None and all(s.mouse.price_eur is None or s.mouse.price_eur > budget
                                            for s in classables):
                empty_causes["budget inférieur à la souris qui convient la moins chère"] += 1
            else:
                empty_causes["autre cause (exclusion de prise, de longueur ou de largeur)"] += 1
        else:
            places = [s for s in (ideal, alternative, economy) if s is not None]
            for premier, second in itertools.combinations(places, 2):
                if _same_shell(premier, second):
                    same_shell_profiles += 1
                    same_shell_pairs[tuple(sorted((premier.mouse.id, second.mouse.id)))] += 1
                    break
        for role, score in (("ideal", ideal), ("alternative", alternative), ("economie", economy)):
            if score is None:
                continue
            counter[score.mouse.id][role] += 1
            counter[score.mouse.id]["total"] += 1
            by_mode[mode.value][score.mouse.id] += 1
            by_grip[grip.value][score.mouse.id] += 1
            key = "—" if session.thenar is None else session.thenar.value
            by_thenar[key][score.mouse.id] += 1
        shown = {s.mouse.id for s in (ideal, alternative, economy) if s is not None}
        positions = {s.mouse.id: i for i, s in enumerate(selection.ranked)}
        evaluated = {s.mouse.id: s for s in (*selection.ranked, *selection.pending)}
        for mouse in mice:
            score = evaluated.get(mouse.id)
            if score is None:
                statuses[mouse.id]["excluded"] += 1
            elif score.is_pending:
                pass                                  # déjà compté en « en attente » ci-dessus
            elif mouse.id not in shown:
                statuses[mouse.id]["scored-not-shown"] += 1
                if ideal is not None:
                    # Pourquoi cette souris ne sort pas ALORS QU'elle est notée : on enregistre qui
                    # occupe la première place sur ces profils (réponse mesurée, pas supposée).
                    dominated_by[mouse.id][ideal.mouse.id] += 1
                # Deuxième cause, structurelle : une souris de la MÊME coque (mêmes dimensions, même
                # pièce) est classée devant elle. Mesuré dans l'ordre réel du classement.
                coque = shell_of.get(mouse.id)
                rang = positions.get(mouse.id)
                if coque and rang is not None:
                    devant = [autre for autre, j in positions.items()
                              if j < rang and autre != mouse.id and shell_of.get(autre) == coque]
                    if devant:
                        twin_ahead[mouse.id][devant[0]] += 1
    return {
        "mice": mice, "counter": counter, "by_mode": by_mode, "by_grip": by_grip, "by_thenar": by_thenar,
        "statuses": statuses, "scores": scores_seen, "in_zone": in_zone,
        "total": total, "empty": empty, "fast": fast,
        "empty_causes": empty_causes, "empty_with_unusable": empty_with_unusable,
        "dominated_by": dominated_by, "twin_ahead": twin_ahead,
        "same_shell_profiles": same_shell_profiles, "same_shell_pairs": same_shell_pairs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Statistiques de recommandation sur toute la grille de mains.")
    parser.add_argument("--rapide", action="store_true", help="grille resserrée (contrôle rapide)")
    parser.add_argument("--sortie", default=str(ROOT / "docs" / "audit" / "STATISTIQUES_RECOMMANDATIONS_2026-10-12.md"),
                        help="fichier Markdown à écrire")
    args = parser.parse_args(argv)

    data = run(fast=args.rapide)
    mice = data["mice"]
    counter = data["counter"]
    total = data["total"]
    ranked = sorted(mice, key=lambda m: (-counter[m.id]["total"], m.label))
    never = [m for m in ranked if counter[m.id]["total"] == 0]

    lines: list[str] = []
    add = lines.append
    add("# Statistiques de recommandation — 2026-10-12\n")
    add(f"Grille : **{total:,} profils** (longueurs 140–240 mm, largeurs 60–125 mm, trois prises, "
        "trois thénars (sauté en Fingertip), cinq modes et cinq budgets personnalisés).\n".replace(",", " "))
    add("Une « recommandation » = une souris affichée dans le résultat, à l'une des trois places "
        "(match idéal, alternative, économie). Comptage fait avec le moteur et la sélection réels, "
        "sans aucune donnée ajoutée pour l'étude.\n")

    add("## Résultats vides et repli de coque (2026-10-12)\n")
    empty = data["empty"]
    add(f"- **Profils sans aucun résultat : {empty}** sur {total} ({100 * empty / total:.1f} %).")
    for cause, nombre in data["empty_causes"].most_common():
        add(f"  - {cause} : {nombre}")
    add(f"  - dont profils où au moins une souris est « à vérifier » faute d'une donnée publiée "
        f"(compatibilité de prise) : **{data['empty_with_unusable']}**")
    add(f"- **Profils où DEUX places montrent la même coque : {data['same_shell_profiles']}** "
        f"({100 * data['same_shell_profiles'] / total:.1f} %).")
    add("  C'est le repli documenté de `result_slots()` : quand la zone de tolérance du mode ne contient "
        "que des variantes de la coque retenue, la deuxième place reprend la même coque plutôt que de "
        "disparaître. Les paires concernées, par fréquence :")
    for (premier, second), nombre in data["same_shell_pairs"].most_common(6):
        add(f"  - `{premier}` + `{second}` : {nombre} profils")
    add("  Depuis la décision du 2026-10-12, l'alternative est déjà élargie une fois au-delà de la "
        "zone du mode (±5 points) — mais uniquement vers une souris qui ne coûte pas plus cher que le "
        "match idéal, et seulement quand la zone du mode ne contient que des variantes de la coque "
        "retenue. Le repli ci-dessus ne subsiste donc que là où même cet élargissement ne trouve pas "
        "d'autre coque à prix égal ou inférieur.\n")
    add("## Nombre de fois où chaque souris est recommandée\n")
    add("| Souris | Idéal | Alternative | Économie | Total | % des profils |")
    add("|---|---:|---:|---:|---:|---:|")
    for mouse in ranked:
        c = counter[mouse.id]
        share = f"{100 * c['total'] / total:.1f} %" if total else "—"
        add(f"| {mouse.label} | {c['ideal']} | {c['alternative']} | {c['economie']} | {c['total']} | {share} |")

    add("\n## Souris jamais recommandées\n")
    if not never:
        add("Aucune : toutes les souris du catalogue sortent au moins une fois.")
    else:
        add(f"**{len(never)} souris sur {len(mice)}** ne sortent jamais sur cette grille :\n")
        for mouse in never:
            add(f"- **{mouse.label}** (`{mouse.id}`)")
        add("\n### Pourquoi elles ne sortent pas\n")
        add("| Souris | Notée | En attente (donnée manquante) | Écartée | Motif principal |")
        add("|---|---:|---:|---:|---|")
        labels = {m.id: m.label for m in mice}
        for mouse in never:
            st = data["statuses"][mouse.id]
            scored = st["scored-not-shown"]
            pending = st["pending"]
            excluded = st["excluded"]
            motifs = []
            if mouse.price_eur is None:
                motifs.append("aucun prix EUR (les modes à prix l'écartent d'office)")
            # Ce qui manque vraiment : chaque champ non renseigné est nommé (le statut de provenance
            # `fit_status` n'est PAS une donnée manquante — `manufacturer_guide` ou `owner_spec`
            # veulent dire que la prise est renseignée, pas qu'elle est absente).
            missing = []
            if mouse.hump_position == "Inconnu":
                missing.append("position de la bosse")
            if mouse.button_height == "Inconnu":
                missing.append("hauteur des boutons")
            for value, label in ((mouse.palm_grip_fit, "prise Palm"),
                                 (mouse.claw_grip_fit, "prise Claw"),
                                 (mouse.fingertip_grip_fit, "prise Fingertip")):
                if value == "Inconnu":
                    missing.append(label)
            if mouse.length_mm is None:
                missing.append("longueur")
            if missing:
                motifs.append("donnée absente : " + ", ".join(missing))
            if scored > 0:
                top = data["dominated_by"][mouse.id].most_common(1)
                if top:
                    dominante, combien = top[0]
                    motifs.append(f"notée, jamais affichée : la 1re place revient à "
                                  f"**{labels.get(dominante, dominante)}** sur {combien} des {scored} "
                                  "profils où elle reste éligible")
                else:
                    motifs.append("notée, jamais retenue (classement dominé)")
                jumelles = data["twin_ahead"][mouse.id]
                if jumelles:
                    # Cause structurelle mesurée : une variante de SA coque est classée devant elle.
                    # Le compte est la somme sur toutes les variantes de la coque (une souris peut
                    # avoir plusieurs jumelles), et le nom cité est le plus fréquent.
                    autre, combien = jumelles.most_common(1)[0]
                    total = sum(jumelles.values())
                    precisions = "" if len(jumelles) == 1 else f", dont {combien} avec {labels.get(autre, autre)}"
                    motifs.append(f"**une variante de sa coque ({labels.get(autre, autre)}) est classée "
                                  f"devant elle sur {total} des {scored} profils où elle est notée**"
                                  f"{precisions} — coque identique, prix différent")
            elif pending > 0:
                motifs.append("en attente sur toute la grille : aucune place tant qu'une donnée manque")
            else:
                motifs.append("jamais notée : écartée par une règle éliminatoire, un budget ou un prix")
            add(f"| {mouse.label} | {scored} | {pending} | {excluded} | {' · '.join(motifs) or '—'} |")

    add("\n## Par mode (nombre de sorties)\n")
    add("| Souris | " + " | ".join(BUDGET_LABELS[mode] for mode in MODES) + " |")
    add("|---" * (len(MODES) + 1) + "|")
    for mouse in ranked:
        add(f"| {mouse.label} | " + " | ".join(str(data['by_mode'][mode.value][mouse.id]) for mode in MODES) + " |")

    add("\n## Par prise (nombre de sorties)\n")
    add("| Souris | Palm | Claw | Fingertip |")
    add("|---|---:|---:|---:|")
    for mouse in ranked:
        add(f"| {mouse.label} | {data['by_grip']['palm'][mouse.id]} | {data['by_grip']['claw'][mouse.id]} "
            f"| {data['by_grip']['fingertip'][mouse.id]} |")

    add("\n## Par taille de thénar (nombre de sorties)\n")
    add("Le thénar n'est pas posé en Fingertip : la colonne « — » compte ces profils.\n")
    add("| Souris | " + " | ".join(THENAR_LABELS[t] for t in Thenar) + " | — (Fingertip) |")
    add("|---" * (len(Thenar) + 2) + "|")
    for mouse in ranked:
        cellules = " | ".join(str(data["by_thenar"][t.value][mouse.id]) for t in Thenar)
        add(f"| {mouse.label} | {cellules} | {data['by_thenar']['—'][mouse.id]} |")

    add("\n## Points obtenus quand la souris est classée\n")
    add("| Souris | Score moyen | Meilleur | Pire | Fois classée dans la zone |")
    add("|---|---:|---:|---:|---:|")
    for mouse in ranked:
        values = data["scores"].get(mouse.id, [])
        if not values:
            add(f"| {mouse.label} | — | — | — | 0 |")
            continue
        add(f"| {mouse.label} | {sum(values) / len(values):.1f}/40 | {max(values)}/40 | {min(values)}/40 "
            f"| {data['in_zone'][mouse.id]} |")

    output = Path(args.sortie)
    output.parent.mkdir(parents=True, exist_ok=True)
    # --- Plan d'action : ce qui manque, souris par souris. Calculé depuis le catalogue (aucune
    # valeur inventée) : ces trois familles de données sont les seules causes d'inéligibilité.
    add("\n## Ce qui manque, souris par souris (à trouver, jamais à inventer)\n")
    sans_prise = [m for m in ranked if m.fit_status == "unverified"]
    sans_bosse = [m for m in ranked if m.hump_position == "Inconnu"]
    sans_boutons = [m for m in ranked if m.button_height == "Inconnu"]
    add(f"- **Sans aucune compatibilité de prise publiée ({len(sans_prise)} souris)** : jamais "
        "classables, donc jamais proposées, quel que soit le profil. Seule une publication du "
        "fabricant (ou une source tierce explicitement autorisée) peut les faire entrer.")
    for mouse in sans_prise:
        prix = f"{mouse.price_eur:.2f} €".replace(".", ",") if mouse.price_eur else "prix inconnu"
        add(f"  - {mouse.label} (`{mouse.id}`) — {prix}")
    add(f"- **Sans position de bosse publiée ({len(sans_bosse)} souris)** : « à vérifier » dès que la "
        "prise utilise la bosse (Palm et Claw) ; sortent seulement en Fingertip.")
    for mouse in sans_bosse:
        add(f"  - {mouse.label} (`{mouse.id}`)")
    add(f"- **Sans hauteur de boutons documentée ({len(sans_boutons)} souris)** : classées "
        "partiellement, donc désavantagées au classement (le critère manquant ne peut pas leur "
        "rapporter les points que les autres gagnent).")
    add("\nCompléter ces trois familles est la seule façon de faire sortir les souris listées plus "
        "haut ; aucune valeur ne peut être devinée. Depuis le 2026-10-12, les sources tierces sont "
        "autorisées pour les données que le fabricant ne publie pas.\n")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Profils passés : {total}")
    print(f"Profils sans aucun résultat : {data['empty']}")
    print(f"Souris jamais recommandées : {len(never)}")
    for mouse in never:
        print(f"  · {mouse.label} ({mouse.id})")
    print(f"Rapport écrit : {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
