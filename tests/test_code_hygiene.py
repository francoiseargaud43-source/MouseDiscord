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
