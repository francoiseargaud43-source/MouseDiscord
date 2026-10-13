"""Outil de mesure de la largeur de prise (tools/measure_grip_width.py) : précision et cas limites."""
import importlib.util
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("measure_grip_width", ROOT / "tools" / "measure_grip_width.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def synthetic_image(path: Path, background=(255, 255, 255), transparent=False) -> Path:
    """Silhouette de 300 px de haut (120 mm) : 40 px de large en haut, 60 px au milieu, 30 px en bas."""
    image = Image.new("RGBA", (120, 300), (*background, 255) if not transparent else (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = (20, 20, 20, 255)
    draw.polygon([(40, 0), (80, 0), (90, 150), (75, 299), (45, 299), (30, 150)], fill=fill)
    image.save(path)
    return path


def test_measure_converts_pixels_to_millimetres(tmp_path):
    image = synthetic_image(tmp_path / "shape.png")
    result = tool.measure(image, length_mm=120.0, at=0.5)
    assert result["hauteur_contour_px"] == 300
    assert result["mm_par_pixel"] == pytest.approx(0.4, abs=1e-3)
    # 60 px au milieu -> 24 mm (tolérance d'un pixel)
    assert result["largeur_au_point_demande_mm"] == pytest.approx(24.0, abs=0.5)
    assert result["largeur_maximale_mm"] == pytest.approx(24.0, abs=0.5)


def test_measure_handles_transparent_background(tmp_path):
    image = synthetic_image(tmp_path / "transparent.png", transparent=True)
    result = tool.measure(image, length_mm=120.0, at=0.1)
    assert result["largeur_au_point_demande_mm"] < result["largeur_maximale_mm"]
    assert result["hauteur_contour_px"] == 300


def test_measure_rejects_empty_or_invalid_inputs(tmp_path):
    empty = tmp_path / "empty.png"
    Image.new("RGBA", (40, 40), (255, 255, 255, 255)).save(empty)
    with pytest.raises(tool.MeasurementError):
        tool.measure(empty, length_mm=120.0)
    image = synthetic_image(tmp_path / "shape.png")
    with pytest.raises(tool.MeasurementError):
        tool.measure(image, length_mm=0.0)
    with pytest.raises(tool.MeasurementError):
        tool.measure(image, length_mm=120.0, at=1.5)


def test_command_line_returns_json(tmp_path, capsys):
    image = synthetic_image(tmp_path / "shape.png")
    assert tool.main([str(image), "--length", "120", "--at", "0.5", "--json"]) == 0
    payload = capsys.readouterr().out
    assert '"largeur_au_point_demande_mm"' in payload and '"profil_mm"' in payload
    # Image absente : phrase sur la sortie d'erreur et code 2 (contrat commun des outils, §26.8 et
    # §26.20). Ce test attendait `return 1` et une phrase sur la sortie standard — l'ancien
    # comportement, corrigé le 2026-10-13.
    with pytest.raises(SystemExit) as sortie:
        tool.main([str(tmp_path / "absent.png"), "--length", "120"])
    assert sortie.value.code == 2
    assert "image introuvable" in capsys.readouterr().err
