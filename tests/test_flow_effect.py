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
    """`git show <ref>:…` puis import : le module rechargé expose le calcul des trois places."""
    module = flow_effect.charger_ancienne_version("HEAD")
    assert callable(module.result_slots)


def test_la_version_rechargee_n_est_jamais_le_code_actuel():
    """Piège de la 80e passe : après le découpage, l'ancien ``finder_flow.py`` importe ``result_slots``
    depuis le ``utils/slots.py`` ACTUEL — recharger ce fichier-là aurait comparé le nouveau code à
    lui-même (« 0 changement » quoi qu'on modifie). L'outil recharge donc ``utils/slots.py`` du commit
    quand il existe, et sa fonction n'est pas celle de l'arbre de travail."""
    from utils import slots

    module = flow_effect.charger_ancienne_version("HEAD")
    assert module.result_slots is not slots.result_slots
    assert module.__name__ in {"ancien_slots", "ancien_finder_flow"}
    # Avant le découpage (commit c6a268b), le code vivait dans le cog : il est rechargé de là.
    assert flow_effect.charger_ancienne_version("c6a268b").__name__ == "ancien_finder_flow"


def test_une_reference_inconnue_est_signalee_sans_trace(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["flow_effect.py", "--avant", "pas-une-reference"])
    with pytest.raises(SystemExit) as sortie:
        flow_effect.main()
    assert sortie.value.code == 2
    assert "référence introuvable" in capsys.readouterr().err


def test_le_controle_d_equivalence_voit_un_changement_et_rien_d_autre(monkeypatch):
    """« 0 écart sur 44 776 profils » (80e passe) se rejoue avec ``--aleatoires 40`` ; ce test le fait sur
    la grille réduite : la refonte ne change rien, et un seuil modifié dans ``utils/slots.py`` est vu."""
    from utils import slots

    grille_d_origine = flow_effect.banc.grille
    monkeypatch.setattr(flow_effect.banc, "grille", lambda rapide: grille_d_origine(True))
    ancien = flow_effect.charger_ancienne_version("c6a268b")
    profils, ecarts, _ = flow_effect.equivalence(ancien, 2)
    assert profils == 3 * 576 and ecarts == 0
    monkeypatch.setattr(slots, "ALTERNATIVE_EXTENSION_POINTS", 0)
    assert flow_effect.equivalence(ancien, 0)[1] > 0
