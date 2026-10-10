"""Contrôle statique de confidentialité du Mouse Shape Finder (défense complémentaire aux tests).

Objectif : détecter, dans le code du bot, les chemins d'envoi susceptibles de rendre PUBLIC
un message contenant des données individuelles du questionnaire (grip, mesures, budget, résultat).

Seul le message d'accueil (``StartView``) est public. Toute autre réponse liée à une interaction doit être :
- ``response.send_message(..., ephemeral=True)``   (réponse immédiate, visible par le seul utilisateur) ;
- ``response.defer(ephemeral=True)``                (réponse différée, idem) ;
- ``followup.send(..., ephemeral=True)``            (suivi, idem) ;
- ``response.edit_message(...)`` / ``edit_original_response(...)`` UNIQUEMENT dans les fonctions
  listées dans ``EDIT_ALLOWED_FUNCTIONS`` (message éphémère du parcours, déjà contrôlé par propriétaire).

Règles (AST, pas de simple recherche de texte) :
- R1  ``send_message`` / ``defer`` : un argument ``ephemeral=True`` littéral est OBLIGATOIRE.
      Les arguments ``**kwargs`` ne sont PAS acceptés comme preuve.
- R2  ``followup.send`` : ``ephemeral=True`` littéral obligatoire.
- R3  ``send`` / ``reply`` / ``respond`` sur tout autre objet (salon, message, contexte) : interdit, sauf
      dans les fonctions de ``PUBLIC_ALLOWLIST`` (commande d'administration ``!setup_finder``, publication du panneau).
- R4  ``edit_message`` / ``edit_original_response`` : interdit hors ``EDIT_ALLOWED_FUNCTIONS``.
- R5  Référence non appelée à une méthode sensible (alias : ``f = interaction.response.send_message``) : interdite.
- R6  ``getattr`` / ``setattr`` / ``partial`` visant une méthode sensible, par nom littéral ou sur un objet
      d'interaction : interdits (contournement dynamique).

Limites connues (voir docs/audit/AUDIT_CONFIDENTIALITE.md) : analyse locale à chaque fichier, sans suivi
inter-modules ; un appel construit par concaténation de chaînes ou importé sous un autre nom peut échapper
à la détection. Le contrôle ne remplace pas les tests fonctionnels ni la vérification sur serveur Discord.

Usage : ``python tools/privacy_scan.py`` (code de sortie 1 si une violation est trouvée).
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCANNED_FILES = ("bot.py", "config.py", "cogs/finder_flow.py", "cogs/mouse_finder.py", "cogs/__init__.py",
                 "utils/session.py", "utils/assets.py", "utils/catalog.py", "utils/validation.py",
                 "utils/matcher.py", "utils/selection.py", "utils/models.py")

SEND_METHODS_REQUIRING_EPHEMERAL = frozenset({"send_message", "defer"})   # R1
EDIT_METHODS = frozenset({"edit_message", "edit_original_response"})        # R4
PUBLIC_SEND_METHODS = frozenset({"send", "reply", "respond"})               # R3
SENSITIVE_NAMES = frozenset(SEND_METHODS_REQUIRING_EPHEMERAL | EDIT_METHODS | PUBLIC_SEND_METHODS | {"followup"})
DYNAMIC_ACCESSORS = frozenset({"getattr", "setattr", "partial"})            # R6
INTERACTION_HINTS = ("interaction", "response", "followup", "channel", "message", "ctx")

# Fonctions autorisées à éditer un message : parcours privé ou résultat appartenant au propriétaire vérifié.
EDIT_ALLOWED_FUNCTIONS = {
    "cogs/finder_flow.py": {"_show_private", "_close", "_restart"},
}
# Fonctions autorisées à publier : commande d'administration et panneau public, jamais de données individuelles.
PUBLIC_ALLOWLIST = {
    "cogs/mouse_finder.py": {"setup_finder", "setup_finder_error", "_edit_existing"},
}


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.rule}] {self.message}"


def _receiver_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - sécurité
        return ""


def _is_true_literal(value: ast.AST | None) -> bool:
    return isinstance(value, ast.Constant) and value.value is True


def _ephemeral_keyword(call: ast.Call) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == "ephemeral":
            return kw.value
    return None


class _Scanner(ast.NodeVisitor):
    def __init__(self, relpath: str) -> None:
        self.relpath = relpath
        self.findings: list[Finding] = []
        self.function_stack: list[str] = []
        self.parents: dict[ast.AST, ast.AST] = {}

    # -- utilitaires ----------------------------------------------------------
    @property
    def current_function(self) -> str:
        return self.function_stack[-1] if self.function_stack else "<module>"

    def _add(self, node: ast.AST, rule: str, message: str) -> None:
        self.findings.append(Finding(self.relpath, getattr(node, "lineno", 0), rule, message))

    def _allowed(self, table: dict[str, set[str]]) -> bool:
        return self.current_function in table.get(self.relpath, set())

    # -- parcours -------------------------------------------------------------
    def visit(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            self.parents[child] = node
        super().visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            self._check_method_call(node, func)
        elif isinstance(func, ast.Name) and func.id in DYNAMIC_ACCESSORS:
            self._check_dynamic_accessor(node, func.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # R5 : référence à une méthode sensible utilisée sans être appelée (alias).
        if node.attr in SENSITIVE_NAMES and isinstance(node.ctx, ast.Load):
            parent = self.parents.get(node)
            is_called = isinstance(parent, ast.Call) and parent.func is node
            is_followup_container = node.attr == "followup"  # ``interaction.followup`` seul est accepté
            if not is_called and not is_followup_container:
                self._add(node, "R5", f"référence non appelée à « {node.attr} » (alias possible)")
        self.generic_visit(node)

    # -- règles d'appel -------------------------------------------------------
    def _check_method_call(self, node: ast.Call, func: ast.Attribute) -> None:
        name = func.attr
        receiver = _receiver_text(func.value)
        is_followup = receiver.endswith("followup")

        if name == "send_message" or (name == "defer" and "response" in receiver):
            if not _is_true_literal(_ephemeral_keyword(node)):
                self._add(node, "R1", f"{receiver}.{name} sans ephemeral=True littéral")
        elif name == "send" and is_followup:
            if not _is_true_literal(_ephemeral_keyword(node)):
                self._add(node, "R2", f"{receiver}.send sans ephemeral=True littéral")
        elif name in PUBLIC_SEND_METHODS:
            if not self._allowed(PUBLIC_ALLOWLIST):
                self._add(node, "R3", f"envoi public possible : {receiver}.{name}(…) dans « {self.current_function} »")
        elif name in EDIT_METHODS:
            if not self._allowed(EDIT_ALLOWED_FUNCTIONS):
                self._add(node, "R4", f"édition de message hors fonctions autorisées : {receiver}.{name}(…) "
                                      f"dans « {self.current_function} »")

    def _check_dynamic_accessor(self, node: ast.Call, name: str) -> None:
        if len(node.args) < 2:
            return
        target_text = _receiver_text(node.args[0])
        attr = node.args[1]
        literal_sensitive = isinstance(attr, ast.Constant) and attr.value in SENSITIVE_NAMES
        interaction_target = any(hint in target_text.lower() for hint in INTERACTION_HINTS)
        if literal_sensitive or interaction_target:
            self._add(node, "R6", f"{name}() dynamique sur « {target_text} » : contournement possible")


def scan_source(source: str, relpath: str) -> list[Finding]:
    """Analyse le code source d'un fichier. ``relpath`` sert à appliquer les listes d'exceptions."""
    tree = ast.parse(source, filename=relpath)
    scanner = _Scanner(relpath)
    scanner.visit(tree)
    return scanner.findings


def scan_project(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for rel in SCANNED_FILES:
        path = root / rel
        if path.is_file():
            findings.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return findings


def main() -> int:
    findings = scan_project()
    for finding in findings:
        print(finding)
    print(f"{len(findings)} violation(s) de confidentialité détectée(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
