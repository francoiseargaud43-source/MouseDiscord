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

DIMENSION_STATUSES = frozenset({"verified", "single_source", "conflicting", "owner_spec", "owner_spec_unverified"})
PRICE_STATUSES = frozenset({"owner_spec_unverified", "verified", "unknown"})
FIT_STATUSES = frozenset({"owner_spec", "unverified"})


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
    CUSTOM = "custom"

    @property
    def label(self) -> str:
        return BUDGET_LABELS[self]


BUDGET_LABELS = {
    BudgetMode.ECONOMIQUE: "Économique",
    BudgetMode.QUALITE_PRIX: "Rapport Qualité/Prix",
    BudgetMode.HAUT_DE_GAMME: "Haut de Gamme (Max Perf)",
    BudgetMode.CUSTOM: "Budget Personnalisé Maximal",
}


class Thenar(Enum):
    """Taille de l'éminence thénar : collectée, affichée, et utilisée pour UN seul ajustement.

    Depuis le reverse engineering de l'outil Oblivity (2026-10-11, dossier ``Reverse/``), le thénar
    sert à trancher la forme de l'arrière (« arrière étroit en pilule » pour un thénar petit ou
    moyen, aucune contrainte pour un grand). Il ne modifie donc que le sous-score de largeur, et
    uniquement pour les souris à bosse arrière marquée (``THENAR_WIDTH_ADJUSTMENT`` dans
    ``utils/matcher.py``). En Fingertip, la question n'est jamais posée, donc jamais appliquée.
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
