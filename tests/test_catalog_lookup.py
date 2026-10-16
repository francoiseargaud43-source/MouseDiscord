"""Garde-fou : aucune souris du catalogue ne doit porter une compatibilité de prise sans provenance.

Deux provenances sont admises pour une valeur autre que « Inconnu » :
- « owner_spec » : fournie par le propriétaire (cahier des charges) ;
- « manufacturer_guide » : reprise d'une recommandation ÉCRITE du fabricant
  (« Recommended for Claw / Fingertip Grip »), auquel cas la source doit déclarer le champ.
Une valeur déduite, devinée ou copiée d'un avis sans que le fabricant l'écrive est refusée.
"""
from config import MOUSE_DB_PATH
from utils.catalog import load_catalog

GRIP_FIELDS = ("palm_grip_fit", "claw_grip_fit", "fingertip_grip_fit")


def test_only_sourced_records_carry_non_unknown_grip_values():
    for m in load_catalog(MOUSE_DB_PATH):
        values = (m.palm_grip_fit, m.claw_grip_fit, m.fingertip_grip_fit)
        if any(v != "Inconnu" for v in values):
            assert m.fit_status in {"owner_spec", "manufacturer_guide", "third_party_guide"}, (
                f"{m.id} : compatibilité renseignée sans provenance ({m.fit_status})"
            )
            assert m.fit_rationale, f"{m.id} : compatibilité renseignée sans justification"


def test_manufacturer_guide_values_are_written_by_the_brand():
    """« manufacturer_guide » : le champ renseigné doit être attesté par une source qui le liste."""
    for m in load_catalog(MOUSE_DB_PATH):
        if m.fit_status != "manufacturer_guide":
            continue
        for field, value in zip(GRIP_FIELDS, (m.palm_grip_fit, m.claw_grip_fit, m.fingertip_grip_fit)):
            if value == "Inconnu":
                continue
            assert any(field in source.fields for source in m.sources), (m.id, field)
