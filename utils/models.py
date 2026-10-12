"""Types métier partagés : grips, modes de sélection, souris et métadonnées de données.

Séparation des largeurs (voir docs/audit/AUDIT.md, §2, constat C2) :
- ``width_max_mm``   : largeur maximale documentée de la coque (donnée catalogue) ;
- ``grip_width_mm``  : largeur de prise réellement mesurée (None tant qu'aucune mesure n'existe) ;
- l'estimation ``width_max_mm - GRIP_WIDTH_ESTIMATE_OFFSET_MM`` n'est utilisée qu'à défaut de mesure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

UNKNOWN = "Inconnu"  # valeur explicite pour une donnée non vérifiée (ni Faible, ni Moyen, ni Élevé)

FIT_LEVELS = frozenset({"Élevé", "Moyen", "Faible", UNKNOWN})
BUTTON_HEIGHTS = frozenset({"Low", "Mid", "High", UNKNOWN})
HUMP_POSITIONS = frozenset({"Front", "Mid", "Rear", "Mid-Front", "Mid-Rear", "Any", UNKNOWN})
# Forme générale de la coque (bloc « la bosse et la forme » du résultat, méthode Oblivity).
SHAPES = frozenset({"Symmetrical", "Ergonomic", UNKNOWN})

DIMENSION_STATUSES = frozenset({"verified", "single_source", "conflicting", "owner_spec", "owner_spec_unverified"})
PRICE_STATUSES = frozenset({"owner_spec_unverified", "verified", "unknown"})
# Provenance des compatibilités de prise (palm / claw / fingertip) :
# - « owner_spec »         : valeurs fournies par le propriétaire (cahier des charges) ;
# - « manufacturer_guide » : valeurs reprises d'une recommandation ÉCRITE du fabricant
#                            (« Recommended for Claw / Fingertip Grip ») — jamais d'une déduction :
#                            une prise absente des recommandations reste « Inconnu » ;
# - « third_party_guide »  : valeurs reprises d'une recommandation ÉCRITE d'une source tierce
#                            AUTORISÉE par le propriétaire (mouseshape.com), uniquement pour une prise
#                            que le fabricant ne publie pas, et uniquement « Élevé » (« Recommended »)
#                            ou « Moyen » (« Okay »). « Not ideal » n'est JAMAIS converti en « Faible » :
#                            l'élimination reste réservée au fabricant et au propriétaire — la source
#                            tierce contredit d'ailleurs le fabricant sur certaines prises, donc elle
#                            ne peut pas servir à écarter une souris. Une valeur fabricant n'est jamais
#                            remplacée par une valeur tierce ;
# - « unverified »         : aucune compatibilité renseignée (toutes « Inconnu »).
FIT_STATUSES = frozenset({"owner_spec", "manufacturer_guide", "third_party_guide", "unverified"})


class Grip(Enum):
    PALM = "palm"
    CLAW = "claw"
    FINGERTIP = "fingertip"

    @property
    def label(self) -> str:
        return GRIP_LABELS[self]


GRIP_LABELS = {
    Grip.PALM: "Palm Grip",
    Grip.CLAW: "Claw Grip",
    Grip.FINGERTIP: "Fingertip Grip",
}


class BudgetMode(Enum):
    ECONOMIQUE = "economique"
    QUALITE_PRIX = "qualite_prix"
    HAUT_DE_GAMME = "haut_de_gamme"
    PEU_IMPORTE_PRIX = "peu_importe_prix"
    CUSTOM = "custom"

    @property
    def label(self) -> str:
        return BUDGET_LABELS[self]


BUDGET_LABELS = {
    BudgetMode.ECONOMIQUE: "Économique",
    BudgetMode.QUALITE_PRIX: "Rapport Qualité/Prix",
    BudgetMode.HAUT_DE_GAMME: "Haut de Gamme (Max Perf)",
    BudgetMode.PEU_IMPORTE_PRIX: "Peu importe le prix",
    BudgetMode.CUSTOM: "Budget Personnalisé Maximal",
}


class Thenar(Enum):
    """Taille de l'éminence thénar : collectée et affichée, **sans effet sur le score**.

    Règle du propriétaire (2026-10-11, confirmée le 2026-10-12) : le thénar est une information
    morphologique, pas un critère de notation — « zéro effet » sur les équations, les seuils, les
    points, le score, le classement et les exclusions (``MASTER_PROMPT_AZEMOUSE.md`` §7.6).
    Le reverse engineering de l'outil Oblivity (dossier ``Reverse/``) l'utilise seulement pour
    conseiller une forme d'arrière (« arrière étroit en pilule » pour un thénar petit ou moyen).
    Le mécanisme d'ajustement existe toujours (``THENAR_WIDTH_ADJUSTMENT`` dans ``utils/matcher.py``)
    mais ses trois valeurs sont neutres : pour l'activer, voir
    ``docs/REVERSE_ENGINEERING_OBLIVITY.md`` §3. En Fingertip, la question n'est jamais posée.
    """

    PETITE = "petite"
    MOYENNE = "moyenne"
    GRANDE = "grande"

    @property
    def label(self) -> str:
        return THENAR_LABELS[self]


THENAR_LABELS = {
    Thenar.PETITE: "Petite",
    Thenar.MOYENNE: "Moyenne",
    Thenar.GRANDE: "Grande",
}


class ClawVariant(Enum):
    """Variante de la prise Claw : collectée UNIQUEMENT en Claw, et jamais utilisée dans un calcul.

    Elle précise le conseil de bosse (méthode Oblivity) : une bosse arrière pour la Claw relâchée,
    médiane pour l'agressive, arrière à flancs plats pour la pincée. Aucun point, aucun classement
    ne change : le barème reste identique pour les trois variantes.
    """

    RELACHEE = "relachee"
    AGGRESSIVE = "aggressive"
    PINCEE = "pincee"

    @property
    def label(self) -> str:
        return CLAW_VARIANT_LABELS[self]


CLAW_VARIANT_LABELS = {
    ClawVariant.RELACHEE: "Claw relâchée",
    ClawVariant.AGGRESSIVE: "Claw agressive",
    ClawVariant.PINCEE: "Claw pincée",
}


@dataclass(frozen=True)
class HandMeasure:
    length_mm: float
    width_mm: float  # largeur sans le pouce

    def __post_init__(self) -> None:
        if self.length_mm <= 0 or self.width_mm <= 0:
            raise ValueError("Les mesures de la main doivent être strictement positives.")


GRIP_FIT_FIELDS = {
    Grip.PALM: "palm_grip_fit",
    Grip.CLAW: "claw_grip_fit",
    Grip.FINGERTIP: "fingertip_grip_fit",
}


@dataclass(frozen=True)
class Source:
    label: str
    url: str
    fields: tuple[str, ...]          # champs couverts par la source (ex. "length_mm", "price_eur")
    date_checked: str                # AAAA-MM-JJ de la vérification

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Source":
        return cls(
            label=str(raw["label"]),
            url=str(raw["url"]),
            fields=tuple(raw.get("fields", ())),
            date_checked=str(raw["date_checked"]),
        )


@dataclass(frozen=True)
class Mouse:
    id: str
    brand: str
    model: str
    budget_tier: str
    width_max_mm: float
    hump_position: str
    button_height: str
    palm_grip_fit: str
    claw_grip_fit: str
    fingertip_grip_fit: str
    fit_rationale: str
    # Géométrie : None = non vérifiée / en conflit (ne doit pas être comblée par défaut)
    length_mm: float | None = None
    height_mm: float | None = None
    shape: str = UNKNOWN                      # "Symmetrical" | "Ergonomic" | "Inconnu"
    grip_width_mm: float | None = None        # largeur de prise MESURÉE uniquement
    dimension_status: str = "owner_spec_unverified"
    conflicts: dict[str, Any] = field(default_factory=dict)  # ex. {"length_mm": {"values": [...], "sources": [...]}}
    shell_id: str | None = None               # même coque => dimensions partagées
    # Commercial / indicatif (ne modifient jamais le score géométrique)
    price_eur: float | None = None
    price_status: str = "owner_spec_unverified"
    price_note: str = ""
    weight_g: float | None = None
    sensor: str | None = None
    polling_hz: int | None = None
    switches: str = ""                        # type de switchs documenté (texte libre, jamais deviné)
    mcu: str = ""                             # microcontrôleur documenté (texte libre)
    # Métadonnées de compatibilité
    fit_status: str = "owner_spec"
    family: str = ""
    category: str = "ATK"                     # marque du produit (ATK ou autre)
    sources: tuple[Source, ...] = ()
    notes: str = ""

    @property
    def label(self) -> str:
        return f"{self.brand} {self.model}"

    def fit_for(self, grip: Grip) -> str:
        return getattr(self, GRIP_FIT_FIELDS[grip])

    @property
    def is_price_known(self) -> bool:
        return self.price_eur is not None
