"""Le moteur est-il encore celui de la preuve primaire ? Les 10 sorties de `Reverse/` le disent.

`docs/REVERSE_ENGINEERING_OBLIVITY.md` commence par « Aucun écart » et `docs/audit/AUDIT.md` note que
les **10 sorties datées du dossier `Reverse/`** ont servi à vérifier les équations du moteur. Or, jusqu'au
2026-10-13, **aucun test ne relisait ces fichiers** : la preuve était citée par trois documents, jamais
revérifiée. C'est `tests/test_matcher.py` qui tenait les constantes, sur des valeurs recopiées.

Ce fichier referme la boucle : il **relit les fichiers de référence** produits le 2026-10-11 par l'outil
d'origine (10 profils : trois prises, longueurs 150/180/210 mm, largeurs 75/90/110 mm, thénar
Small/Medium/Large) et exige que le moteur les reproduise **exactement** :

| Ce que dit le fichier de référence | Ce qui doit le reproduire |
|---|---|
| « Optimal Mouse Length: 118.8mm - 123.8mm » (ou « max. 123.8mm » en Fingertip) | `compute_target_ranges()` — au centième de millimètre |
| « Optimal Mouse Width: 55.6mm - 59.6mm » | `compute_target_ranges()` — la plage ne dépend pas de la prise |
| « Hump Placement: Mid-to-Front / Mid-to-Back » | `HUMP_IDEAL` (bosse ignorée en Fingertip, où la section est absente) |
| « Button Height: Elevated / Low / Mid-to-Low » | `BUTTON_IDEAL` |
| « Relaxed Claw → prominent back hump », « Aggressive → prominent middle hump », « Pincer → back hump and less curvature » | `CLAW_HUMP_GUIDE` |
| « Narrow Rear » pour Small **et** Medium, rien pour Large | `_narrow_rear_embed` : **Petite seulement** — écart **assumé et daté** (voir plus bas) |
| Largeur « measured with the mouse upside down, at the sensor position » | `grip_width_for_scoring()` : correctif d'estimation, documenté comme provisoire |

**Les fichiers de référence ne sont jamais modifiés** : ils sont la preuve. Seul le moteur bouge.

**Ce que ce fichier ne remplace pas** : la valeur exacte des constantes (les fichiers de référence sont
arrondis au dixième de millimètre, un changement de 0,0001 sur la pente y est invisible) — c'est
`tests/test_matcher.py` qui les verrouille au chiffre près. Ce fichier-ci tient ce que le code **veut dire** :
les équations, les règles de forme et les conseils du bot sont-ils toujours ceux de l'outil d'origine ?
Contre-épreuves du 2026-10-13 : pente +0,0001 et correctif 3,0 → 3,5 mm détectés par `test_matcher` ;
base Fingertip +0,1, ancienne règle de boutons en Claw ({Low, Mid}), bosse Palm {Rear}, perte de « flancs »
dans la variante pincée et arrière étroit ouvert au thénar moyen → détectés **ici**.

Écart connu, écrit ici pour qu'il ne se perde pas : l'outil d'origine conseille l'arrière étroit au thénar
**Petite *ou* Moyenne** ; le bot ne l'affiche que pour **Petite**, et le `MASTER_PROMPT_AZEMOUSE.md` §7.6
le prescrit ainsi (« Si thénar Small → arrière étroit conseillé »). Le test ci-dessous **grave les deux
règles** : il refuse que le code s'écarte du prompt, et il refuse que le prompt devienne silencieux.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataclasses import replace  # noqa: E402

from cogs import finder_flow as flow  # noqa: E402
from config import MOUSE_DB_PATH  # noqa: E402
from utils.catalog import load_catalog  # noqa: E402
from utils.matcher import (  # noqa: E402
    BUTTON_IDEAL,
    HUMP_IDEAL,
    compute_target_ranges,
    grip_width_for_scoring,
)
from utils.models import BudgetMode, ClawVariant, Grip, HandMeasure, Thenar  # noqa: E402
from utils.session import FinderSession  # noqa: E402

REFERENCE = ROOT / "Reverse"
TOLERANCE_MM = 0.051        # les fichiers publient des dixièmes : 118,8 doit tomber juste, pas « à peu près »

# Traductions du vocabulaire de l'outil d'origine vers les valeurs du catalogue (utils/models.py).
HUMP_PAR_LIBELLE = {"Mid-to-Front": {"Front", "Mid"}, "Mid-to-Back": {"Mid", "Rear"}}
BOUTONS_PAR_LIBELLE = {"Elevated": {"High"}, "Low": {"Low"}, "Mid-to-Low": {"Low", "Mid"}}
VARIANTE_PAR_LIBELLE = {
    "Relaxed Claw Grip": ClawVariant.RELACHEE,
    "Aggressive Claw Grip": ClawVariant.AGGRESSIVE,
    "Pincer Claw Grip": ClawVariant.PINCEE,
}
GRIP_PAR_LIBELLE = {"Palm": Grip.PALM, "Claw": Grip.CLAW, "Fingertip": Grip.FINGERTIP}
THENAR_PAR_LIBELLE = {"Small": Thenar.PETITE, "Medium": Thenar.MOYENNE, "Large": Thenar.GRANDE}


def _bloc(texte: str, titre: str) -> str | None:
    """Contenu d'une section du fichier de référence, ou ``None`` si elle est absente.

    Deux formes selon la section : le titre et son contenu dans le même bloc (« Hand Dimensions: 180mm… »)
    ou le titre seul sur sa ligne (« ✋Your Profile »). Les deux sont acceptées.
    """
    for bloc in texte.split("\n\n"):
        nu = bloc.strip()
        premiere = nu.split("\n")[0]
        if nu.startswith(f"{titre}:") or premiere == titre:
            return " ".join(nu.split())
    return None


def _nombre(motif: str, texte: str, defaut=None) -> float | None:
    trouve = re.search(motif, texte)
    return float(trouve.group(1)) if trouve else defaut


def _libelle(bloc: str | None, titre: str) -> str | None:
    """Le mot-clé qui suit un titre de section (« Button Height » → « Low »), ou ``None``.

    Dans les fichiers de référence, le titre occupe sa propre ligne et le mot-clé la suivante :
    « Button Height\nLow: Claw grippers benefit… ». Après mise à plat, le mot-clé est donc ce qui
    précède le premier deux-points, une fois le titre retiré.
    """
    if bloc is None:
        return None
    reste = bloc[len(titre):].lstrip()
    if reste.startswith(":"):                  # forme « Thenar Muscle: Small »
        reste = reste[1:].lstrip()
    return reste.split(":")[0].strip()


def lire_reference(chemin: Path) -> dict:
    """Un fichier de `Reverse/` mis à plat : prise, main, thénar, plages, sections brutes."""
    texte = chemin.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    entete = _bloc(texte, "✋Your Profile") or ""
    mesures = _bloc(texte, "Hand Dimensions") or ""
    prise = re.search(r"Grip: (\w+)", entete)
    main = re.search(r"Hand Dimensions: ([\d.]+)mm \(L\) x ([\d.]+)mm \(W\)", mesures)
    assert prise and main, f"en-tête illisible dans {chemin.name} : le fichier de référence a-t-il changé ?"
    longueur = _bloc(texte, "Optimal Mouse Length") or ""
    largeur = _bloc(texte, "Optimal Mouse Width") or ""
    fin_largeur = _nombre(r"Optimal Mouse Width: [\d.]+mm - ([\d.]+)mm", largeur)
    return {
        "nom": chemin.name,
        "grip": GRIP_PAR_LIBELLE[prise.group(1)],
        "longueur_main": float(main.group(1)),
        "largeur_main": float(main.group(2)),
        "thenar": _libelle(_bloc(texte, "Thenar Muscle"), "Thenar Muscle"),
        "long_min": _nombre(r"Optimal Mouse Length: ([\d.]+)mm - ", longueur),
        "long_max": (_nombre(r"Optimal Mouse Length: [\d.]+mm - ([\d.]+)mm", longueur)
                     or _nombre(r"Optimal Mouse Length: max\. ([\d.]+)mm", longueur)),
        "sans_minimum": "max." in longueur,
        "larg_min": _nombre(r"Optimal Mouse Width: ([\d.]+)mm - ", largeur),
        "larg_max": fin_largeur,
        "bosse": _libelle(_bloc(texte, "Hump Placement"), "Hump Placement"),
        "boutons": _libelle(_bloc(texte, "Button Height"), "Button Height"),
        "arriere": _libelle(_bloc(texte, "Rear Design"), "Rear Design"),
        "variantes": _bloc(texte, "Claw Grip Variants"),
        "forme": _bloc(texte, "Mouse Design"),
        "texte": texte,
    }


def toutes_les_references() -> list[dict]:
    fichiers = sorted(REFERENCE.glob("*.txt"))
    return [lire_reference(chemin) for chemin in fichiers]


REFERENCES = toutes_les_references()
PRISES = [ref["grip"] for ref in REFERENCES]
SANS_MINIMUM = [ref for ref in REFERENCES if ref["sans_minimum"]]


def test_les_dix_fichiers_de_reference_sont_lisibles_et_complets():
    """Le socle de la vérification : 10 profils, trois prises, toutes les sections attendues.

    Sans ce contrôle, une section renommée dans un fichier de référence rendrait les tests suivants
    **muets** (ils parcourent ce qu'ils trouvent) au lieu d'échouer — le piège exact que ce fichier
    existe pour fermer.
    """
    assert len(REFERENCES) == 10, f"{len(REFERENCES)} fichiers de référence au lieu de 10"
    assert set(PRISES) == set(Grip), f"prises couvertes : {sorted(g.name for g in PRISES)}"
    assert {ref["thenar"] for ref in REFERENCES if ref["grip"] is not Grip.FINGERTIP} == {"Small", "Medium", "Large"}
    assert len(SANS_MINIMUM) == 3 and all(ref["grip"] is Grip.FINGERTIP for ref in SANS_MINIMUM)

    manquantes = []
    for ref in REFERENCES:
        for cle in ("bosse", "boutons", "forme"):
            if ref[cle] is None and ref["grip"] is not Grip.FINGERTIP:
                manquantes.append(f"{ref['nom']} : section « {cle} » absente")
        if ref["grip"] is Grip.CLAW and ref["variantes"] is None:
            manquantes.append(f"{ref['nom']} : section « Claw Grip Variants » absente")
        if ref["grip"] is not Grip.FINGERTIP and ref["thenar"] is None:
            manquantes.append(f"{ref['nom']} : thénar absent")
    assert manquantes == [], "fichiers de référence incomplets : " + " ; ".join(manquantes)


@pytest.mark.parametrize("ref", REFERENCES, ids=lambda ref: ref["nom"][:42])
def test_les_plages_ciblees_sont_exactement_celles_de_l_outil_d_origine(ref):
    """Longueur et largeur : les équations du moteur reproduisent la référence au dixième près.

    Le fichier donne des plages arrondies au dixième (« 118.8mm - 123.8mm ») : une tolérance de
    0,051 mm accepte l'arrondi **et rien d'autre**. **Résolution de la preuve**, mesurée : un
    changement de 0,0001 sur la pente (0,2633) ne déplace la borne que de 0,018 mm à 210 mm de main —
    sous l'arrondi du fichier, donc invisible ici, et c'est normal : c'est `tests/test_matcher.py`
    qui tient la valeur exacte des constantes, ce fichier-ci tient le **lien avec la preuve**.
    En Fingertip, l'outil n'écrit pas de minimum (« max. 123.8mm ») : le moteur le traduit
    par `length_min = 0.0`.
    """
    plages = compute_target_ranges(HandMeasure(ref["longueur_main"], ref["largeur_main"]), ref["grip"])

    assert plages.length_max == pytest.approx(ref["long_max"], abs=TOLERANCE_MM), ref["nom"]
    if ref["long_min"] is None:
        assert ref["grip"] is Grip.FINGERTIP
        assert plages.length_min == 0.0, "Fingertip : l'outil d'origine ne fixe aucun minimum de longueur"
    else:
        assert plages.length_min == pytest.approx(ref["long_min"], abs=TOLERANCE_MM), ref["nom"]
    assert plages.width_min == pytest.approx(ref["larg_min"], abs=TOLERANCE_MM), ref["nom"]
    assert plages.width_max == pytest.approx(ref["larg_max"], abs=TOLERANCE_MM), ref["nom"]


def test_la_largeur_ne_depend_que_de_la_main_et_de_la_base_de_prise():
    """Deux enseignements que la référence rend visibles, et que le moteur doit reproduire.

    1. **La largeur ne dépend pas de la prise** : les fichiers de référence donnent la même plage pour
       toutes les mains de même largeur (55,6–59,6 mm pour 90 mm, quelle que soit la prise, la longueur
       et le thénar) — vérifié ici sur les trois largeurs de main documentées.
    2. **La base, elle, change en Fingertip** (47,3 contre 48,4) : les fichiers Fingertip donnent des
       plages plus étroites de 1,1 mm pour la même main, et le moteur reproduit exactement cet écart.
    """
    par_groupe = {}
    for ref in REFERENCES:
        # Fingertip a sa propre base de largeur : c'est justement l'écart à mesurer, pas une anomalie.
        groupe = (ref["largeur_main"], "fingertip" if ref["grip"] is Grip.FINGERTIP else "palm_claw")
        par_groupe.setdefault(groupe, set()).add((ref["larg_min"], ref["larg_max"]))
    assert {largeur for largeur, _ in par_groupe} == {75.0, 90.0, 110.0}
    for (largeur_main, base), plages in par_groupe.items():
        assert len(plages) == 1, f"main {largeur_main} ({base}) : la référence se contredit ({plages})"
        (larg_min, larg_max), = plages
        prises = (Grip.FINGERTIP,) if base == "fingertip" else (Grip.PALM, Grip.CLAW)
        for grip in prises:
            plage = compute_target_ranges(HandMeasure(180.0, largeur_main), grip)
            assert plage.width_min == pytest.approx(larg_min, abs=TOLERANCE_MM), f"{base} {largeur_main}"
            assert plage.width_max == pytest.approx(larg_max, abs=TOLERANCE_MM), f"{base} {largeur_main}"

    referentiel = [ref for ref in REFERENCES if ref["grip"] is Grip.FINGERTIP and ref["largeur_main"] == 90.0][0]
    paume = compute_target_ranges(HandMeasure(180.0, 90.0), Grip.PALM)
    fingertip = compute_target_ranges(HandMeasure(180.0, 90.0), Grip.FINGERTIP)
    assert fingertip.width_min < paume.width_min, "la base Fingertip doit être plus basse que celle de Palm/Claw"
    assert fingertip.width_min == pytest.approx(referentiel["larg_min"], abs=TOLERANCE_MM)
    assert referentiel["larg_min"] == pytest.approx(paume.width_min - 1.1, abs=0.051)


@pytest.mark.parametrize("ref", REFERENCES, ids=lambda ref: ref["nom"][:42])
def test_la_regle_de_bosse_du_moteur_est_celle_de_la_reference(ref):
    """« Mid-to-Front » en Palm, « Mid-to-Back » en Claw, section absente (et bosse ignorée) en Fingertip."""
    if ref["grip"] is Grip.FINGERTIP:
        assert ref["bosse"] is None, "l'outil d'origine ne mentionne pas la bosse en Fingertip"
        assert ref["grip"] not in HUMP_IDEAL, "la bosse ne doit pas être notée en Fingertip"
        return
    assert ref["bosse"] in HUMP_PAR_LIBELLE, f"libellé de bosse inattendu : {ref['bosse']}"
    assert HUMP_IDEAL[ref["grip"]] == HUMP_PAR_LIBELLE[ref["bosse"]], ref["nom"]


@pytest.mark.parametrize("ref", REFERENCES, ids=lambda ref: ref["nom"][:42])
def test_la_regle_de_hauteur_des_boutons_est_celle_de_la_reference(ref):
    """« Elevated » en Palm, « Low » en Claw, « Mid-to-Low » en Fingertip — la règle alignée le 2026-10-12."""
    assert ref["boutons"] in BOUTONS_PAR_LIBELLE, f"libellé de hauteur inattendu : {ref['boutons']}"
    assert BUTTON_IDEAL[ref["grip"]] == BOUTONS_PAR_LIBELLE[ref["boutons"]], ref["nom"]


def test_les_trois_variantes_de_claw_suivent_la_bosse_decrirte_par_la_reference():
    """« Relaxed → prominent back hump », « Aggressive → prominent middle hump », « Pincer → back + flancs plats ».

    La référence situe chaque variante « Best paired with … » : le conseil du bot doit dire la même chose,
    avec ses mots à lui (c'est ce texte-là que les membres lisent).
    """
    phrases = {}
    for ref in REFERENCES:
        if ref["grip"] is not Grip.CLAW:
            assert ref["variantes"] is None, f"{ref['nom']} : section de variantes hors Claw"
            continue
        for libelle, variante in VARIANTE_PAR_LIBELLE.items():
            trouve = re.search(rf"{re.escape(libelle)}[^:]*: Best paired with ([^A-Z]+)", ref["variantes"])
            assert trouve, f"« {libelle} » introuvable dans {ref['nom']}"
            phrases.setdefault(variante, set()).add(" ".join(trouve.group(1).split()).lower())

    assert set(phrases) == set(ClawVariant)
    attendu = {
        ClawVariant.RELACHEE: "a prominent back hump",
        ClawVariant.AGGRESSIVE: "a prominent middle hump",
        ClawVariant.PINCEE: "a back hump and less curvature on the sides",
    }
    for variante, motif in attendu.items():
        assert phrases[variante] == {motif}, f"{variante.value} : la référence dit {phrases[variante]}"

    # Et le texte du bot dit la même chose : arrière marquée / médiane marquée / arrière à flancs plats.
    assert "arrière" in flow.CLAW_HUMP_GUIDE[ClawVariant.RELACHEE][0]
    assert "médiane" in flow.CLAW_HUMP_GUIDE[ClawVariant.AGGRESSIVE][0]
    assert "flancs" in flow.CLAW_HUMP_GUIDE[ClawVariant.PINCEE][0]


def test_l_arriere_etroit_reste_reserve_au_thenar_petite_malgre_la_reference():
    """Écart **assumé et daté** : la référence conseille l'arrière étroit à Petite *et* Moyenne.

    Le bot ne l'affiche que pour **Petite**, comme le prescrit `docs/MASTER_PROMPT_AZEMOUSE.md` §7.6.
    Deux garanties sont gravées ici : le code s'en tient au prompt, et le prompt continue de le dire —
    si l'un des deux change sans l'autre, ce test tombe.
    """
    conseils = {ref["thenar"] for ref in REFERENCES if ref["arriere"]}
    assert conseils == {"Small", "Medium"}, "la référence doit conseiller l'arrière étroit pour Small ET Medium"
    # La section est présente exactement pour ces deux thénars, et elle dit toujours « Narrow Rear ».
    for ref in REFERENCES:
        attendu = ref["thenar"] in {"Small", "Medium"}
        assert (ref["arriere"] is not None) is attendu, f"{ref['nom']} : section arrière = {ref['arriere']!r}"
        if attendu:
            assert ref["arriere"] == "Narrow Rear", ref["nom"]

    prompt = (ROOT / "docs" / "MASTER_PROMPT_AZEMOUSE.md").read_text(encoding="utf-8")
    assert "Si thénar Small → arrière étroit conseillé" in prompt, "la règle du prompt a changé : réviser le bloc"

    # Le code, mesuré sur le message réel : l'arrière étroit pour « Petite » seulement, jamais en Fingertip.
    def session_pour(grip: Grip, thenar: Thenar | None) -> FinderSession:
        session = FinderSession(user_id=1)
        session.grip = grip
        session.thenar = thenar
        session.hand_length_mm = 180.0
        session.hand_width_mm = 90.0
        session.budget_mode = BudgetMode.QUALITE_PRIX
        return session

    titre = "🖐️ Un arrière étroit pour votre thénar"
    assert flow._narrow_rear_embed() is not None               # le bloc existe (jamais supprimé par erreur)
    for thenar, attendu in ((Thenar.PETITE, True), (Thenar.MOYENNE, False), (Thenar.GRANDE, False)):
        session = session_pour(Grip.PALM, thenar)
        embeds = flow.results_embeds(session, flow.compute_selection(session))
        affiche = titre in [embed.title for embed in embeds]
        assert affiche is attendu, f"thénar {thenar.label} : arrière étroit affiché = {affiche}"
    fingertip = flow.results_embeds(session_pour(Grip.FINGERTIP, None),
                                    flow.compute_selection(session_pour(Grip.FINGERTIP, None)))
    assert titre not in [embed.title for embed in fingertip]  # la prise ne pose pas la question du thénar


def test_la_largeur_de_prise_est_le_correctif_documente_dans_l_attente_d_une_mesure():
    """La référence impose la mesure « souris retournée, au niveau du capteur » — pas la largeur maximale.

    Sans mesure, le moteur applique le correctif provisoire de 3 mm, et le dit (« estimated ») ; le jour où
    une souris porte une mesure, celle-ci prend la main **sans changer de code** — c'est ce que ce test
    vérifie sur une souris réelle du catalogue, dans ses deux états. C'est la règle qui rend l'attente
    sûre : aucune souris du catalogue du 2026-10-13 ne porte de mesure (`grip_width_mm` absent).
    Le **nombre** (3,0 mm) est verrouillé par `tests/test_matcher.py` ; ici, c'est la priorité et le lien
    avec la méthode de la référence qui sont tenus (mutation de 3,0 à 3,5 mm : détectée là-bas).
    """
    from utils.matcher import GRIP_WIDTH_ESTIMATE_OFFSET_MM

    assert "upside down, at the sensor position" in (REFERENCE / "Palm  Longueur 180  Largeur 90  Thenar Small.txt").read_text(
        encoding="utf-8-sig")

    # Une souris du catalogue, dans ses deux états : sans mesure (aujourd'hui) et avec.
    souris = replace(load_catalog(MOUSE_DB_PATH)[0], grip_width_mm=None)
    largeur, source = grip_width_for_scoring(souris)
    assert source == "estimated"
    assert largeur == pytest.approx(souris.width_max_mm - GRIP_WIDTH_ESTIMATE_OFFSET_MM)

    mesuree = replace(souris, grip_width_mm=56.4)
    largeur, source = grip_width_for_scoring(mesuree)
    assert source == "measured" and largeur == 56.4

    # Aucune souris du catalogue ne porte de mesure aujourd'hui : c'est le correctif qui travaille.
    assert all(m.grip_width_mm is None for m in load_catalog(MOUSE_DB_PATH))

    # La référence elle-même : « 55.6mm - 59.6mm » pour 180 × 90 — la mesure de prise, pas la largeur max.
    ref = lire_reference(REFERENCE / "Palm  Longueur 180  Largeur 90  Thenar Small.txt")
    assert ref["larg_min"] < 60.0 - GRIP_WIDTH_ESTIMATE_OFFSET_MM < ref["larg_max"]
