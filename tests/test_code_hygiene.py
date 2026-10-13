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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
        "def test_avec_assertion_de_simulation()\n,\n".replace("\n,", ""),
        encoding="utf-8")
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

