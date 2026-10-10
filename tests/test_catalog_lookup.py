"""Garde-fou : aucune souris du catalogue ne doit contenir une valeur de grip « Élevé » sans source propriétaire."""
from config import MOUSE_DB_PATH
from utils.catalog import load_catalog


def test_only_owner_spec_records_carry_non_unknown_grip_values():
    for m in load_catalog(MOUSE_DB_PATH):
        values = (m.palm_grip_fit, m.claw_grip_fit, m.fingertip_grip_fit)
        if any(v != "Inconnu" for v in values):
            assert m.fit_status == "owner_spec", f"{m.id} : compatibilité non « owner_spec » renseignée"
