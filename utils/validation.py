"""Validation des saisies utilisateur (Modals)."""
from __future__ import annotations

import re

LENGTH_BOUNDS_MM = (100.0, 260.0)
WIDTH_BOUNDS_MM = (50.0, 130.0)
BUDGET_BOUNDS_EUR = (10.0, 5000.0)

# Chiffres ASCII uniquement : un chiffre non latin (ex. « ١٨٠ ») serait refusé par ``float`` juste
# après, avec une erreur technique au lieu du message clair destiné au membre.
_NUMBER_RE = re.compile(r"[0-9]{1,5}(?:\.[0-9]{1,2})?")
_MM_SUFFIX_RE = re.compile(r"(?i)mm$")
_CM_SUFFIX_RE = re.compile(r"(?i)cm$")


class InputError(ValueError):
    """Saisie utilisateur invalide ; le message est destiné à l'utilisateur."""


def parse_number(raw: str | None, label: str, bounds: tuple[float, float], unit: str,
                 *, accept_cm: bool = False) -> float:
    """Nombre borné. Avec ``accept_cm`` (mesures de main), une saisie en centimètres est convertie.

    2026-11-11 : beaucoup de membres mesurent en centimètres (« 18,5 », « 18,5 cm ») et recevaient
    « hors limites » sans comprendre. Une valeur suffixée « cm », ou une valeur nue qui n'a de sens
    qu'en centimètres (sous la borne basse, mais dans les bornes une fois multipliée par 10), est
    convertie en millimètres. Une main de 18 mm n'existe pas : aucune ambiguïté n'est tranchée au hasard.
    """
    if raw is None or not raw.strip():
        raise InputError(f"{label} : la valeur est obligatoire.")
    # Tous les espaces sont ignorés, y compris l'espace fine insécable et l'espace fine que les
    # claviers français insèrent (« 1 800 € » doit s'accepter comme « 1800 € »), ainsi que le suffixe
    # d'unité, quelle que soit sa casse (« 180 mm », « 180 MM »).
    text = "".join(raw.split()).replace("€", "").replace(",", ".")
    in_cm = accept_cm and _CM_SUFFIX_RE.search(text) is not None
    if in_cm:
        text = _CM_SUFFIX_RE.sub("", text)
    else:
        text = _MM_SUFFIX_RE.sub("", text)
    if not _NUMBER_RE.fullmatch(text):
        raise InputError(f"{label} : « {raw.strip()} » n'est pas un nombre valide (ex : 180 ou 180,5).")
    value = float(text)
    low, high = bounds
    if accept_cm and (in_cm or value < low) and low <= value * 10 <= high:
        value = round(value * 10, 1)
    if not low <= value <= high:
        raise InputError(f"{label} : {value:g} {unit} est hors limites ({low:g} à {high:g} {unit}).")
    return value


def parse_hand_measures(length_raw: str | None, width_raw: str | None) -> tuple[float, float]:
    """Valide longueur et largeur ensemble et remonte toutes les erreurs d'un coup."""
    errors: list[str] = []
    length = width = None
    try:
        length = parse_number(length_raw, "Longueur", LENGTH_BOUNDS_MM, "mm", accept_cm=True)
    except InputError as exc:
        errors.append(str(exc))
    try:
        width = parse_number(width_raw, "Largeur", WIDTH_BOUNDS_MM, "mm", accept_cm=True)
    except InputError as exc:
        errors.append(str(exc))
    if errors:
        raise InputError("\n".join(errors))
    assert length is not None and width is not None
    return length, width


def parse_budget(raw: str | None) -> float:
    return parse_number(raw, "Budget maximum", BUDGET_BOUNDS_EUR, "€")
