"""Types métier partagés : grips, budgets, zones thénar et souris."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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

    @property
    def tier(self) -> str | None:
        """Valeur de `budget_tier` du catalogue correspondant (tie-break)."""
        return BUDGET_TIERS[self]


BUDGET_LABELS = {
    BudgetMode.ECONOMIQUE: "Économique",
    BudgetMode.QUALITE_PRIX: "Rapport Qualité/Prix",
    BudgetMode.HAUT_DE_GAMME: "Haut de Gamme (Max Perf)",
    BudgetMode.CUSTOM: "Budget Personnalisé Maximal",
}

BUDGET_TIERS = {
    BudgetMode.ECONOMIQUE: "Économique",
    BudgetMode.QUALITE_PRIX: "Qualité-Prix",
    BudgetMode.HAUT_DE_GAMME: "Haut de Gamme",
    BudgetMode.CUSTOM: None,
}


class Thenar(Enum):
    """Muscle thénar : collecté pour l'UX, n'entre PAS dans l'équation."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    @property
    def label(self) -> str:
        return self.name.capitalize()


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
class Mouse:
    id: str
    brand: str
    model: str
    price_eur: float
    budget_tier: str
    length_mm: float
    width_max_mm: float
    hump_position: str
    button_height: str
    palm_grip_fit: str
    claw_grip_fit: str
    fingertip_grip_fit: str
    fit_rationale: str

    @property
    def label(self) -> str:
        return f"{self.brand} {self.model}"

    def fit_for(self, grip: Grip) -> str:
        return getattr(self, GRIP_FIT_FIELDS[grip])
