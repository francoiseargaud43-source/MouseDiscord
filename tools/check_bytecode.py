"""Contrôle de fraîcheur du bytecode : Python charge-t-il bien le **code livré** ?

    python tools/check_bytecode.py                 # signale ce qui est périmé (sortie 1 s'il y a danger)
    python tools/check_bytecode.py --purge         # supprime les fichiers .pyc périmés
    python tools/check_bytecode.py --dossier DIR   # contrôle un autre dossier que le dépôt

Défaut trouvé le 2026-10-14 (68e passe, C90) : le banc d'essai a publié **10 678 problèmes** et
« 9 768 profils » où l'ordre des pourcentages n'était pas garanti, alors que le moteur livré n'en
produisait **aucun**. La cause n'était pas dans le moteur mais dans un fichier ``.pyc`` : une mutation
d'essai avait modifié ``cogs/finder_flow.py`` (les deux variables de retour de ``result_slots``
échangées), puis la source avait été remise à l'identique — **même taille, même seconde** — si bien que
l'en-tête du bytecode restait valide aux yeux de Python, qui continuait à charger **le code muté**.
Toute mesure faite ensuite portait donc sur un autre moteur que celui du dépôt, sans le moindre signe.

Le contrôle compare, pour chaque ``.pyc`` que Python accepterait, son code à celui de la source. Trois
situations sont distinguées, car elles n'ont pas la même conséquence :

- **périmé sans effet** : l'en-tête ne correspond plus (mtime ou taille) → Python recompile la source,
  aucun danger, le fichier n'est qu'un résidu ;
- **périmé utilisé** : l'en-tête correspond mais le code diffère → Python charge le ``.pyc`` : c'est le
  cas dangereux, celui du 2026-10-14 ;
- **orphelin** : le ``.pyc`` n'a plus de source (module renommé ou supprimé).

Codes de sortie : 0 = rien de dangereux ; 1 = au moins un bytecode « périmé utilisé » ; 2 = entrée
invalide (dossier introuvable), comme les autres outils du dossier.
"""
from __future__ import annotations

import argparse
import importlib.util
import marshal
import struct
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]

# Dossiers jamais visités : environnements et caches d'autres outils. Les `__pycache__`, eux, sont
# visités — ce sont les fichiers à contrôler.
DOSSIERS_IGNORES = (".git", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache",
                    ".ruff_cache", ".tox", "build", "dist", "out", "target")

A_JOUR = "à jour"
PERIME_UTILISE = "périmé utilisé"
PERIME_SANS_EFFET = "périmé sans effet"
ORPHELIN = "orphelin"
ILLISIBLE = "illisible"
DANGEREUX = (PERIME_UTILISE, ILLISIBLE)


class Diagnostic(NamedTuple):
    """Un fichier de bytecode examiné : ce qu'il est, et ce que Python en fait."""

    chemin: Path          # le .pyc
    source: Path | None   # la source correspondante (None si orpheline)
    statut: str
    detail: str


def tag_interpreteur() -> str:
    """Le suffixe des ``.pyc`` de l'interpréteur courant, p. ex. ``cpython-311``.

    Un fichier compilé par un autre interpréteur n'est jamais chargé par celui-ci : le contrôler
    n'aurait pas de sens, et le signaler noierait le vrai danger dans du bruit.
    """
    return f"cpython-{sys.version_info.major}{sys.version_info.minor}"


def empreinte_constante(objet) -> tuple:
    """Empreinte d'une constante, sans jamais se fier à un ordre ni à une adresse.

    Deux pièges rencontrés en écrivant ce contrôle (2026-10-14), tous deux vérifiés par un test :

    - ``repr()`` d'un ``frozenset`` dépend de l'ordre d'itération, donc du **hachage des chaînes**,
      qui change à chaque exécution : deux empreintes du même fichier ne se comparaient pas. Les
      ensembles sont donc triés par leur écriture ;
    - ``repr()`` d'un objet code contient son **adresse mémoire** : un objet code rencontré dans une
      constante (compréhension enveloppée dans un tuple, par exemple) est donc comparé par sa propre
      empreinte, jamais par son écriture.
    """
    if hasattr(objet, "co_code"):
        return ("code", empreinte_code(objet))
    if isinstance(objet, tuple):
        return ("tuple", tuple(empreinte_constante(element) for element in objet))
    if isinstance(objet, frozenset):
        return ("frozenset", tuple(sorted(repr(element) for element in objet)))
    return (type(objet).__name__, objet)


def empreinte_code(code) -> tuple:
    """Empreinte **récursive** d'un objet code : le bytecode, les noms, les constantes.

    Les numéros de ligne en sont volontairement exclus : un commentaire déplacé change le ``.pyc``
    sans changer une seule instruction, et l'accuser ferait crier le contrôle à tort. Ce qui compte
    ici, c'est le **comportement** : deux empreintes égales = le même code s'exécute.
    """
    morceaux: list = [code.co_code, code.co_names, code.co_varnames, code.co_flags, code.co_argcount]
    morceaux.extend(empreinte_constante(constante) for constante in code.co_consts)
    return tuple(morceaux)


def source_du_pyc(pyc: Path) -> Path | None:
    """La source d'un ``<dossier>/__pycache__/<nom>.<tag>.pyc``, ou ``None`` si elle n'existe plus."""
    if pyc.parent.name != "__pycache__":
        return None
    nom = pyc.name.split(".")[0]
    source = pyc.parent.parent / f"{nom}.py"
    return source if source.is_file() else None


def _en_tete_valide(donnees: bytes, source: Path) -> bool:
    """Le fichier serait-il chargé par Python **à la place** de la source ?

    C'est la question exacte que le contrôle doit trancher : un ``.pyc`` dont l'en-tête ne correspond
    plus est inoffensif (Python recompile), un ``.pyc`` dont l'en-tête correspond est chargé tel quel.
    """
    drapeaux = int.from_bytes(donnees[4:8], "little")
    if drapeaux & 0b11:      # bytecode basé sur une empreinte (PEP 552)
        return donnees[8:16] == importlib.util.source_hash(source.read_bytes())
    mtime, taille = struct.unpack("<II", donnees[8:16])
    etat = source.stat()
    return mtime == int(etat.st_mtime) and taille == etat.st_size


def examine(pyc: Path) -> Diagnostic:
    """Ce que Python ferait de ce ``.pyc`` : inoffensif, dangereux, orphelin ou illisible."""
    source = source_du_pyc(pyc)
    if source is None:
        return Diagnostic(pyc, None, ORPHELIN, "le module source n'existe plus")
    try:
        donnees = pyc.read_bytes()
    except OSError as exc:                                    # pragma: no cover - disque en défaut
        return Diagnostic(pyc, source, ILLISIBLE, f"lecture impossible : {exc}")
    if len(donnees) < 16 or donnees[:4] != importlib.util.MAGIC_NUMBER:
        return Diagnostic(pyc, source, PERIME_SANS_EFFET,
                          "compilé par un autre interpréteur : Python recompile la source")
    try:
        chargé = _en_tete_valide(donnees, source)
    except OSError as exc:                                    # pragma: no cover - disque en défaut
        return Diagnostic(pyc, source, ILLISIBLE, f"source illisible : {exc}")
    if not chargé:
        return Diagnostic(pyc, source, PERIME_SANS_EFFET,
                          "l'en-tête ne correspond plus (mtime ou taille) : Python recompile la source")
    try:
        code_pyc = marshal.loads(donnees[16:])
        # `dont_inherit=True` : sans lui, la comparaison hérite des `from __future__ import …` de CE
        # fichier — un module qui n'a pas cet import était alors déclaré « périmé » à tort (le drapeau
        # d'annotations diffère). Défaut trouvé le 2026-10-14 en vérifiant le contrôle lui-même.
        code_source = compile(source.read_text(encoding="utf-8"), str(source), "exec", dont_inherit=True)
    except (ValueError, SyntaxError, EOFError, OSError) as exc:
        return Diagnostic(pyc, source, ILLISIBLE, f"comparaison impossible : {type(exc).__name__} {exc}")
    if empreinte_code(code_pyc) != empreinte_code(code_source):
        return Diagnostic(pyc, source, PERIME_UTILISE,
                          "l'en-tête correspond mais le code diffère : Python charge le .pyc, "
                          "pas la source livrée")
    return Diagnostic(pyc, source, A_JOUR, "identique à sa source")


def controle(dossier: Path = ROOT) -> list[Diagnostic]:
    """Tous les ``.pyc`` de l'interpréteur courant sous ``dossier``, avec ce que Python en ferait."""
    tag = tag_interpreteur()
    diagnostics = []
    for pyc in sorted(dossier.rglob(f"*.{tag}.pyc")):
        if any(partie in DOSSIERS_IGNORES for partie in pyc.parts):
            continue
        diagnostics.append(examine(pyc))
    return diagnostics


def dangereux(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in diagnostics if d.statut in DANGEREUX]


def a_purger(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    """Tout ce qui n'est pas « à jour » : bytecode dangereux, résidus et orphelins."""
    return [d for d in diagnostics if d.statut != A_JOUR]


def purge(diagnostics: list[Diagnostic]) -> list[Path]:
    """Supprime les fichiers de :func:`a_purger` ; rend la liste de ceux qui ont pu l'être."""
    retires = []
    for diagnostic in a_purger(diagnostics):
        try:
            diagnostic.chemin.unlink()
        except OSError:                                       # pragma: no cover - disque en défaut
            continue
        retires.append(diagnostic.chemin)
    return retires


def phrase_de_synthese(diagnostics: list[Diagnostic]) -> str:
    """La ligne de conclusion du contrôle, en clair et sans jargon."""
    if not diagnostics:
        return "Bytecode : aucun fichier compilé à contrôler pour cet interpréteur"
    perimes = dangereux(diagnostics)
    if perimes:
        noms = ", ".join(str(d.chemin) for d in perimes[:5])
        return (f"Bytecode : {len(perimes)} fichier(s) périmé(s) UTILISÉ(S) — Python charge un autre "
                f"code que celui livré ({noms}) : lancez `python tools/check_bytecode.py --purge`")
    autres = len(a_purger(diagnostics))
    return (f"Bytecode : {len(diagnostics)} fichier(s) examiné(s), aucun périmé utilisé"
            + (f" ({autres} résidu(s) ou orphelin(s) sans effet)" if autres else ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Contrôle de fraîcheur du bytecode (fichiers .pyc)")
    parser.add_argument("--dossier", default=str(ROOT), help="dossier à contrôler (défaut : le dépôt)")
    parser.add_argument("--purge", action="store_true", help="supprime les fichiers .pyc périmés")
    args = parser.parse_args(argv)

    dossier = Path(args.dossier)
    if not dossier.is_dir():
        parser.error(f"dossier introuvable : {dossier}")

    diagnostics = controle(dossier)
    if args.purge:
        retires = purge(diagnostics)
        print(f"Bytecode : {len(retires)} fichier(s) .pyc supprimé(s) (ils seront recompilés au besoin)")
        return 0

    for diagnostic in diagnostics:
        if diagnostic.statut == A_JOUR:
            continue
        marque = "✘" if diagnostic.statut in DANGEREUX else "·"
        source = diagnostic.source if diagnostic.source is not None else "(sans source)"
        print(f"  {marque} {diagnostic.chemin} : {diagnostic.statut} — {diagnostic.detail}")
        if diagnostic.statut in DANGEREUX:
            print(f"    source : {source}")
    print(phrase_de_synthese(diagnostics))
    if dangereux(diagnostics):
        print("Correction : python tools/check_bytecode.py --purge", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
