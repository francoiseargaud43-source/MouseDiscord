"""Hygiène du code livré : résidus d'édition et appels qui n'ont pas leur place dans le bot.

Ces contrôles existent parce qu'un défaut de ce genre a été trouvé en relecture le 2026-10-12 :
``cogs/finder_flow.py`` gardait, à la fin du texte d'une étape, un point, un guillemet de fermeture et
trois guillemets collés (le résidu d'une édition). Il était **invisible** : les chaînes voisines se
concatènent à la compilation (le texte affiché restait juste) et ``pyflakes`` ne dit rien d'une chaîne
vide implicite. Un fichier de test le voit désormais, sur tout le code livré — d'ailleurs ce docstring
a dû être réécrit : écrire le motif en toutes lettres terminait la chaîne de documentation.
"""
from __future__ import annotations

import ast
import os
import py_compile
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))     # les outils du dépôt s'importent comme des modules

import check_bytecode  # noqa: E402  (contrôle de fraîcheur du bytecode, 68e passe)

FICHIERS_PY = sorted(
    [*ROOT.glob("cogs/*.py"), *ROOT.glob("utils/*.py"), *ROOT.glob("tools/*.py"),
     *ROOT.glob("tests/*.py"), ROOT / "bot.py"]
)
FICHIERS_DU_BOT = [*ROOT.glob("cogs/*.py"), *ROOT.glob("utils/*.py"), ROOT / "bot.py"]


def test_le_controle_porte_sur_tout_le_code_livre():
    assert len(FICHIERS_PY) >= 20, [str(p) for p in FICHIERS_PY]
    assert ROOT.joinpath("cogs/finder_flow.py") in FICHIERS_PY


def test_aucun_residu_de_guillemets_dans_un_texte():
    """Une ligne-texte ne commence pas par un guillemet simple pour finir par un triple.

    C'est la signature exacte du défaut trouvé : ``"...calcul).\"\"\"`` — le premier guillemet ferme
    la chaîne, le triple laisse deux guillemets vides collés à la suite.
    """
    residus = []
    for chemin in FICHIERS_PY:
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), start=1):
            texte = ligne.strip()
            if texte.startswith('"') and texte.endswith('"""') and not texte.startswith('"""'):
                residus.append(f"{chemin.relative_to(ROOT)}:{numero}")
    assert residus == [], "résidu de guillemets (chaîne vide implicite) : " + ", ".join(residus)


def test_aucun_appel_a_print_dans_le_bot():
    """Le bot écrit dans le journal (``logging``), jamais sur la sortie standard : un ``print`` ne
    laisse aucune trace horodatée dans ``~/admin/logs/jobs/`` et ne peut donc pas être diagnostiqué."""
    trouves = []
    for chemin in FICHIERS_DU_BOT:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) \
                    and noeud.func.id == "print":
                trouves.append(f"{chemin.relative_to(ROOT)}:{noeud.lineno}")
    assert trouves == [], "print() dans le bot : " + ", ".join(trouves)


# ---------------------------------------------------------------------------
# Un test qui ne vérifie rien n'est pas un test
# ---------------------------------------------------------------------------
# « Assert » (la classe d'un vrai `assert`) et « assert » (les méthodes de simulation,
# `mock.assert_awaited_once()` — leur nom apparaît tel quel dans l'arbre) : les deux comptent.
PREUVES = ("Assert", "assert", "raises", "fail(", "warns", "deprecated_call")


def _tests_sans_verification(chemin: Path) -> list[str]:
    """Les fonctions ``test_*`` du fichier qui ne contiennent aucune vérification.

    Preuves acceptées : une assertion (``assert``), une assertion de simulation
    (``mock.assert_awaited_once()``…), ``pytest.raises`` / ``warns`` / ``deprecated_call`` / ``fail``.
    """
    trouves = []
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not noeud.name.startswith("test_"):
            continue
        source = ast.dump(noeud)
        if not any(motif in source for motif in PREUVES):
            trouves.append(f"{chemin.name}::{noeud.name} (ligne {noeud.lineno})")
    return trouves


def _tests_sans_verification_du_depot() -> list[str]:
    return [trouve for chemin in sorted(ROOT.glob("tests/test_*.py"))
            for trouve in _tests_sans_verification(chemin)]


def test_aucun_test_du_depot_ne_passe_sans_rien_verifier():
    """Un test qui se contente d'appeler le code n'échoue jamais : il gonfle la suite sans rien tenir.

    Cas réel trouvé le 2026-10-13 (52e passe) : ``test_send_ephemeral_ne_leve_jamais…`` promettait de
    vérifier deux choses (choisir le bon canal, ne jamais lever) et n'en vérifiait aucune de façon
    lisible — il ne disait ni en privé, ni par ``response`` ou par ``followup``. Le test a été renforcé,
    et ce contrôle empêche la réapparition de la famille.
    """
    sans_verification = _tests_sans_verification_du_depot()
    assert sans_verification == [], "tests sans aucune vérification : " + ", ".join(sans_verification)


# ---------------------------------------------------------------------------
# Une écriture aussitôt écrasée est une écriture morte (2026-10-14, 61e passe)
# ---------------------------------------------------------------------------
# Cas réel trouvé le 2026-10-14 : ce fichier construisait son fichier de contre-épreuve **deux fois de
# suite** (`creux.write_text(...)` puis un second appel identique) — la première écriture était morte,
# écrasée par la seconde, et sa chaîne portait un `\n,` bricolé par un script d'édition resté en
# travers. Rien ne pouvait le voir : l'effet était nul, seul le lecteur perdait son temps. Le contrôle
# ci-dessous refuse deux écritures consécutives sur le **même nom** (``X.write_text`` / ``X.write_bytes``).


def _cible_ecriture(instruction: ast.stmt) -> tuple[str, str] | None:
    """« (nom, méthode) » si l'instruction est un appel ``X.write_text(...)`` / ``X.write_bytes(...)``."""
    if not isinstance(instruction, ast.Expr) or not isinstance(instruction.value, ast.Call):
        return None
    appel = instruction.value
    if not isinstance(appel.func, ast.Attribute) or appel.func.attr not in ("write_text", "write_bytes"):
        return None
    if not isinstance(appel.func.value, ast.Name):
        return None
    return appel.func.value.id, appel.func.attr


def _ecritures_ecrasees(chemin: Path) -> list[str]:
    """Les appels d'écriture consécutifs sur le même nom : le second écrase le premier, sans effet."""
    trouves = []
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        corps = getattr(noeud, "body", None)
        if not isinstance(corps, list):
            continue
        precedent = None
        for instruction in corps:
            cible = _cible_ecriture(instruction)
            if cible is not None and cible == precedent:
                trouves.append(f"{chemin.name}:{instruction.lineno} ({cible[0]}.{cible[1]})")
            precedent = cible
    return trouves


def test_aucune_ecriture_aussitot_ecrasee_dans_le_code_livre():
    ecrasees = [trouve for chemin in FICHIERS_PY for trouve in _ecritures_ecrasees(chemin)]
    assert ecrasees == [], "écritures mortes (écrasées aussitôt) : " + ", ".join(ecrasees)


def test_le_controle_des_ecritures_mortes_sait_reconnaitre_un_ecrasement(tmp_path):
    """Contre-épreuve : deux écritures d'affilée sur le même nom sont signalées, le reste non."""
    exemple = tmp_path / "exemple.py"
    exemple.write_text(
        "a = 1\n"
        "chemin.write_text('un')\n"
        "chemin.write_text('deux')\n"
        "autre.write_text('trois')\n"
        "chemin.read_text()\n"
        "autre.write_bytes(b'quatre')\n",
        encoding="utf-8")

    signalees = _ecritures_ecrasees(exemple)

    assert len(signalees) == 1, signalees
    assert "chemin.write_text" in signalees[0]


def test_le_controle_de_verification_sait_reconnaitre_un_test_creux(tmp_path):
    """Contre-épreuve : le contrôle doit signaler un test vide **et** accepter les vraies preuves."""
    creux = tmp_path / "test_creux.py"
    creux.write_text(
        "import pytest\n"
        "from unittest.mock import AsyncMock\n"
        "\n"
        "def test_qui_ne_verifie_rien():\n"
        "    {'a': 1}.get('a')\n"
        "\n"
        "def test_avec_assertion():\n"
        "    assert 1 == 1\n"
        "\n"
        "def test_avec_assertion_de_simulation():\n"
        "    suivi = AsyncMock()\n"
        "    suivi.assert_not_awaited()\n"
        "\n"
        "def test_avec_leve_attendue():\n"
        "    with pytest.raises(ValueError):\n"
        "        int('x')\n",
        encoding="utf-8")

    signales = _tests_sans_verification(creux)

    assert len(signales) == 1 and "test_qui_ne_verifie_rien" in signales[0]


# ---------------------------------------------------------------------------
# Bytecode : Python exécute-t-il bien le code LIVRÉ ?
# ---------------------------------------------------------------------------
def _paquet_avec_bytecode_perime(dossier: Path) -> tuple[Path, Path]:
    """Reproduit le piège du 2026-10-14 : la source change, le ``.pyc`` reste « valide ».

    Un module est compilé normalement, puis sa source est réécrite **avec la même taille** et on lui
    rend sa date de modification : l'en-tête du ``.pyc`` correspond toujours, donc Python continue de
    charger l'ancien code. C'est exactement ce qui est arrivé à ``cogs/finder_flow.py`` quand la
    source d'une mutation d'essai a été remise à l'identique — même taille, même seconde.
    """
    paquet = dossier / "paquet"
    paquet.mkdir()
    (paquet / "__init__.py").write_text("", encoding="utf-8")
    source = paquet / "moteur.py"
    source.write_text("def places():\n    return 'ideal', 'economie', 'alternative'\n", encoding="utf-8")
    py_compile.compile(str(source), doraise=True)
    etat = source.stat()
    source.write_text("def places():\n    return 'ideal', 'alternative', 'economie'\n", encoding="utf-8")
    os.utime(source, (etat.st_atime, etat.st_mtime))
    return source, next((paquet / "__pycache__").glob("moteur.*.pyc"))


def _charge(racine: Path):
    """Importe ``paquet.moteur`` depuis ``racine`` et rend le module (nettoyé après usage)."""
    import importlib

    sys.path.insert(0, str(racine))
    importlib.invalidate_caches()
    try:
        for nom in ("paquet.moteur", "paquet"):
            sys.modules.pop(nom, None)
        return importlib.import_module("paquet.moteur")
    finally:
        sys.path.remove(str(racine))


def test_aucun_bytecode_perime_n_est_charge_dans_le_depot():
    """Le contrôle de référence : Python doit charger le code livré, dans le dépôt tel qu'il est.

    Défaut trouvé le 2026-10-14 (68e passe, C90) : le banc a publié 10 678 problèmes et « 9 768
    profils » où l'ordre des pourcentages n'était pas garanti, alors que le moteur livré n'en
    produisait **aucun** — un ``.pyc`` gardait la mutation d'essai de ``result_slots``. Sans ce
    contrôle, la mesure suivante repartait sur le même moteur fantôme.
    """
    perimes = check_bytecode.dangereux(check_bytecode.controle(ROOT))

    assert perimes == [], ("bytecode périmé chargé par Python : "
                           + ", ".join(f"{d.chemin} (source {d.source})" for d in perimes)
                           + " — lancez `python tools/check_bytecode.py --purge`")


def test_le_controle_du_bytecode_reconnait_le_piege_et_le_prouve(tmp_path):
    """Le contrôle nomme le ``.pyc`` périmé utilisé, et Python rend bien l'ancien code."""
    _, pyc = _paquet_avec_bytecode_perime(tmp_path)

    diagnostic = check_bytecode.examine(pyc)

    assert diagnostic.statut == check_bytecode.PERIME_UTILISE, diagnostic
    assert diagnostic.source is not None and diagnostic.source.name == "moteur.py"
    assert "moteur" in check_bytecode.phrase_de_synthese([diagnostic])
    # La preuve que le piège est réel : Python exécute le .pyc, pas la source livrée.
    assert _charge(tmp_path).places() == ("ideal", "economie", "alternative")


def test_la_purge_rend_le_code_livre(tmp_path):
    """Après purge, Python recompile la source : le code exécuté redevient celui du fichier."""
    _, pyc = _paquet_avec_bytecode_perime(tmp_path)

    retires = check_bytecode.purge(check_bytecode.controle(tmp_path))

    assert [chemin.name for chemin in retires] == [pyc.name]
    assert not pyc.exists()
    assert _charge(tmp_path).places() == ("ideal", "alternative", "economie")
    assert check_bytecode.dangereux(check_bytecode.controle(tmp_path)) == []


def test_le_controle_ne_signale_pas_un_ensemble_de_constantes(tmp_path):
    """Contre-épreuve du faux positif trouvé en écrivant le contrôle : un ``frozenset`` n'est pas un écart.

    ``repr()`` d'un ensemble dépend de l'ordre d'itération, donc du hachage des chaînes, qui change à
    chaque exécution : comparer les écritures déclarait « périmé » un module pourtant identique.
    """
    source = tmp_path / "constantes.py"
    source.write_text("STATUTS = frozenset({'verified', 'unknown', 'owner_spec_unverified'})\n",
                      encoding="utf-8")
    py_compile.compile(str(source), doraise=True)

    diagnostic = check_bytecode.examine(next((tmp_path / "__pycache__").glob("constantes.*.pyc")))

    assert diagnostic.statut == check_bytecode.A_JOUR, diagnostic


CHAMPS_SANS_LECTEUR_DANS_LE_BOT = {
    # champ du catalogue → (phrase vraie exigée dans le README, phrase périmée interdite)
    "budget_tier": ("aucun module du bot ne la lit", "départage visuel uniquement"),
    "fit_rationale": ("le bot ne l'affiche pas", "Texte affiché dans le résultat"),
}


@pytest.mark.parametrize("champ, phrases", sorted(CHAMPS_SANS_LECTEUR_DANS_LE_BOT.items()))
def test_les_champs_du_catalogue_sans_lecteur_sont_dits_tels_quels(champ, phrases):
    """Un champ que rien ne lit doit être **décrit** comme tel, jamais autrement.

    Défaut trouvé le 2026-10-14, deux fois dans la même heure : le README annonçait `budget_tier`
    comme un « départage visuel » (et le constat d'audit le disait « affiché ») alors qu'aucun module
    ne le lit ; puis il annonçait `fit_rationale` comme un « texte affiché dans le résultat » alors
    que le bloc « 🧭 Pourquoi ce choix ? » vient du calcul (`selection.explanation`) — le texte du
    catalogue n'apparaît dans **aucun** message, pour aucune des 36 souris. Dans les deux cas, le seul
    code qui touche le champ est le schéma (`utils/catalog.py`) et la dataclass (`utils/models.py`).

    Le contrôle tient le document et le code ensemble : le jour où le bot lira l'un de ces champs, ce
    test tombera et forcera la mise à jour du README — dans ce sens-là.
    """
    phrase_vraie, phrase_perimee = phrases
    lecteurs_autorises = {"utils/catalog.py", "utils/models.py"}
    lecteurs = {
        chemin.relative_to(ROOT).as_posix()
        for chemin in FICHIERS_DU_BOT
        if champ in chemin.read_text(encoding="utf-8")
    }
    assert lecteurs == lecteurs_autorises, (
        f"un module du bot lit `{champ}` : mettre le README à jour et élargir ce contrôle — "
        f"lecteurs trouvés : {sorted(lecteurs)}"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert phrase_vraie in readme, f"le README ne dit pas que `{champ}` n'est pas lu"
    assert phrase_perimee not in readme, f"le README garde la description périmée : {phrase_perimee!r}"
