"""Validation des saisies des Modals."""
import pytest

from utils.validation import InputError, parse_budget, parse_hand_measures, parse_number


@pytest.mark.parametrize("raw, expected", [("180", 180.0), ("180,5", 180.5), (" 180.25 ", 180.25), ("180 mm", 180.0)])
def test_valid_numbers(raw, expected):
    assert parse_number(raw, "Longueur", (100, 260), "mm") == expected


@pytest.mark.parametrize("raw", ["", "   ", "abc", "1e3", "-5", "12.345", "NaN", "inf", "1,2,3"])
def test_invalid_format(raw):
    with pytest.raises(InputError):
        parse_number(raw, "Longueur", (100, 260), "mm")


def test_out_of_bounds():
    with pytest.raises(InputError, match="hors limites"):
        parse_number("50", "Longueur", (100, 260), "mm")


def test_hand_measures_ok():
    assert parse_hand_measures("180", "90") == (180.0, 90.0)


def test_hand_measures_reports_all_errors_together():
    with pytest.raises(InputError) as exc:
        parse_hand_measures("abc", "900")
    message = str(exc.value)
    assert "Longueur" in message and "Largeur" in message


def test_budget_accepts_euro_sign():
    assert parse_budget("60 €") == 60.0
    assert parse_budget("59,90€") == 59.9


def test_budget_rejects_nonsense():
    with pytest.raises(InputError):
        parse_budget("0")
    with pytest.raises(InputError):
        parse_budget("gratuit")


# --- Chasse aux bugs du 2026-10-12 : espaces insécables/fines et unité en majuscules ---
@pytest.mark.parametrize("raw", ["1\u202f800", "1\u2009800", "1\u00a0800", "1800", "1 800"])
def test_budget_accepts_every_french_space(raw):
    """La barre d'espace française des claviers mobiles est une espace fine (U+202F) : « 1 800 € »
    doit s'accepter, pas produire « n'est pas un nombre valide »."""
    assert parse_budget(raw) == 1800.0


@pytest.mark.parametrize("raw", ["180 mm", "180 MM", "180mm", "180 Mm"])
def test_measure_unit_is_case_insensitive(raw):
    assert parse_number(raw, "Longueur", (100, 260), "mm") == 180.0


def test_non_latin_digits_get_the_clear_message_not_a_crash():
    """Un chiffre non latin doit produire une InputError lisible, jamais une exception technique."""
    with pytest.raises(InputError, match="n'est pas un nombre valide"):
        parse_number("\u0661\u0668\u0660", "Longueur", (100, 260), "mm")
