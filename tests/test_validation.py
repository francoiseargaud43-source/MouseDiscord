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
