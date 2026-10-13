"""Le mesureur d'effet du parcours (``tools/flow_effect.py``).

Il recharge la version antérieure de ``cogs/finder_flow.py`` depuis un commit et compare les trois
places avant/après. Deux exigences : le rechargement fonctionne (sinon la mesure est impossible), et
une référence inconnue se dit en **une ligne** — avant le 2026-10-13 elle remontait une trace
`CalledProcessError` de `subprocess`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import flow_effect  # noqa: E402


def test_la_version_anterieure_se_recharge():
    """`git show <ref>:cogs/finder_flow.py` puis import : le module doit exposer le même contrat."""
    module = flow_effect.charger_ancienne_version("HEAD")
    for nom in ("result_slots", "_slot_text", "compute_selection"):
        assert hasattr(module, nom), nom


def test_une_reference_inconnue_est_signalee_sans_trace(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["flow_effect.py", "--avant", "pas-une-reference"])
    with pytest.raises(SystemExit) as sortie:
        flow_effect.main()
    assert sortie.value.code == 2
    assert "référence introuvable" in capsys.readouterr().err
