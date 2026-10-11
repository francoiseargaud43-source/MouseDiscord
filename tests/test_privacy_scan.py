"""Contrôle statique de confidentialité : détection des violations, absence de faux positifs évidents.

Chaque cas de violation est une VARIANTE d'appel différente (kwargs, alias, defer, salon, getattr…),
pour éviter qu'un contrôle trop simple ne soit contourné par une réécriture triviale.
"""
from pathlib import Path

import pytest

from tools import privacy_scan as ps

ROOT = Path(__file__).resolve().parents[1]
FLOW = "cogs/finder_flow.py"


def rules(source: str, relpath: str = FLOW) -> list[str]:
    return [f.rule for f in ps.scan_source(source, relpath)]


# ---------------------------------------------------------------------------
# 1. Le dépôt réel est conforme (et le contrôle ne dépend pas d'une liste vide)
# ---------------------------------------------------------------------------
def test_current_project_has_no_violation():
    assert ps.scan_project(ROOT) == []


def test_scanner_really_inspects_interaction_calls():
    # Sans cette vérification, un scanner qui ne lit rien passerait le test ci-dessus.
    source = (ROOT / FLOW).read_text(encoding="utf-8")
    import ast

    sensitive_calls = [
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in {"send_message", "defer", "edit_message", "send"}
    ]
    # Inventaire exact des 5 appels sensibles actuels : StartView.start, _send_ephemeral (x2 : send_message
    # et followup.send), _show_private (edit + repli send_message).
    # Toute évolution de ce nombre doit être relue par rapport à EDIT_ALLOWED_FUNCTIONS.
    assert len(sensitive_calls) == 5


# ---------------------------------------------------------------------------
# 2. Cas valides : aucun signalement
# ---------------------------------------------------------------------------
VALID = {
    "send_message éphémère littéral": "async def f(i):\n    await i.response.send_message('x', ephemeral=True)\n",
    "defer éphémère": "async def f(i):\n    await i.response.defer(ephemeral=True)\n",
    "followup éphémère": "async def f(i):\n    await i.followup.send('x', ephemeral=True)\n",
    "edit dans fonction autorisée": "async def _show_private(i, **kw):\n    await i.response.edit_message(**kw)\n",
    "fallback ephemeral dans _show_private": (
        "async def _show_private(i, **kw):\n"
        "    if i.message is not None:\n        await i.response.edit_message(**kw)\n"
        "    else:\n        await i.response.send_message(ephemeral=True, **kw)\n"
    ),
}


@pytest.mark.parametrize("name", sorted(VALID))
def test_valid_patterns_are_not_reported(name):
    assert rules(VALID[name]) == []


def test_public_send_allowed_in_admin_command_only():
    source = "async def setup_finder(self, ctx):\n    await ctx.send('ok')\n"
    assert rules(source, "cogs/mouse_finder.py") == []
    assert rules(source, FLOW) == ["R3"]


# ---------------------------------------------------------------------------
# 3. Violations : chaque variante doit être détectée
# ---------------------------------------------------------------------------
VIOLATIONS = {
    "R1 send_message sans ephemeral": ("async def f(i):\n    await i.response.send_message('x')\n", "R1"),
    "R1 ephemeral=False": ("async def f(i):\n    await i.response.send_message('x', ephemeral=False)\n", "R1"),
    "R1 ephemeral variable": ("async def f(i, flag):\n    await i.response.send_message('x', ephemeral=flag)\n", "R1"),
    "R1 contournement **kwargs": ("async def f(i, opts):\n    await i.response.send_message(**opts)\n", "R1"),
    "R1 defer public": ("async def f(i):\n    await i.response.defer()\n", "R1"),
    "R2 followup public": ("async def f(i):\n    await i.followup.send('x')\n", "R2"),
    "R2 followup ephemeral=False": ("async def f(i):\n    await i.followup.send('x', ephemeral=False)\n", "R2"),
    "R3 salon de l'interaction": ("async def f(i):\n    await i.channel.send('résultat')\n", "R3"),
    "R3 reply sur un message": ("async def f(m):\n    await m.reply('résultat')\n", "R3"),
    "R4 edit hors fonction autorisée": (
        "async def leak(i, embed):\n    await i.response.edit_message(embed=embed)\n", "R4"),
    "R4 edit_original_response": (
        "async def leak(i, embed):\n    await i.edit_original_response(embed=embed)\n", "R4"),
    "R5 alias de méthode d'envoi": (
        "async def f(i):\n    send = i.response.send_message\n    await send('x')\n", "R5"),
    "R6 getattr sur la réponse": (
        "async def f(i, name):\n    await getattr(i.response, name)('x')\n", "R6"),
    "R6 getattr littéral sensible": (
        "async def f(i):\n    await getattr(i.response, 'send_message')('x')\n", "R6"),
}


@pytest.mark.parametrize("name", sorted(VIOLATIONS))
def test_violation_variants_are_detected(name):
    source, expected = VIOLATIONS[name]
    assert expected in rules(source), f"{name} non détecté"


# ---------------------------------------------------------------------------
# 4. Échec sur une violation réelle injectée dans le vrai fichier, puis réussite après restauration
# ---------------------------------------------------------------------------
def test_injected_violation_in_real_flow_module_is_reported(tmp_path):
    original = (ROOT / FLOW).read_text(encoding="utf-8")
    injected = original + (
        "\n\nasync def _debug_leak(interaction, session):\n"
        "    await interaction.channel.send(f'Résultat de {session.user_id}')\n"
    )
    findings = ps.scan_source(injected, FLOW)
    assert any(f.rule == "R3" for f in findings)
    # Restauration : le fichier réel d'origine n'a aucune violation
    assert ps.scan_source(original, FLOW) == []


def test_scan_project_reports_a_violation_in_a_copy(tmp_path):
    for rel in ps.SCANNED_FILES:
        src = ROOT / rel
        if src.is_file():
            dst = tmp_path / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    flow = tmp_path / FLOW
    flow.write_text(flow.read_text(encoding="utf-8") +
                    "\n\nasync def leak(i):\n    await i.response.send_message('x')\n", encoding="utf-8")
    assert any(f.rule == "R1" and f.file == FLOW for f in ps.scan_project(tmp_path))
    flow.write_text(flow.read_text(encoding="utf-8").rsplit("\n\nasync def leak", 1)[0] + "\n", encoding="utf-8")
    assert ps.scan_project(tmp_path) == []
