"""Les points d'entrée des outils répondent-ils **tous** pareil à une entrée invalide ?

Défaut trouvé le 2026-10-13 (chasse aux micro-bugs, §26.20) : après la correction du §26.8 — trois outils
disaient leur erreur en une phrase et sortaient en code 2 —, **quatre autres outils** gardaient un
comportement différent pour la même erreur :

- `measure_button_height.py` remontait une trace `FileNotFoundError` puis `PIL.UnidentifiedImageError`
  (code 1) ;
- `measure_grip_width.py` écrivait sa phrase sur la **sortie standard** en code 1, et une image illisible
  passait à travers sa garde (trace `PIL.UnidentifiedImageError`) ;
- `build_ai_bundle.py` prenait son premier argument pour un nom de fichier **sans contrôle** :
  `build_ai_bundle.py --help` écrivait une archive de 73 Ko nommée `--help` et affichait « Écrit : --help »
  (une faute de frappe dans une option créait donc un fichier au lieu de la signaler) ;
- `check_deployment.py` et `privacy_scan.py` **ignoraient en silence** tout argument (`--help` lançait le
  contrôle, et une option mal orthographiée aussi).

Un appelant qui teste le code de sortie ou lit la sortie d'erreur obtenait donc une réponse différente
selon l'outil, pour la même faute de frappe. Ce fichier remplace la relecture par une **table** : chaque
outil est confronté à une entrée invalide, et le contrat est désormais le même pour tous — une phrase,
sur la sortie d'erreur, code **2**, jamais de trace Python, et **`main(argv)` partout** (condition pour
que le contrôle porte sur tous les outils, y compris ceux qui n'ont aucune option).
"""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

OUTILS = sorted(p.stem for p in (ROOT / "tools").glob("*.py"))
FRAGMENT_OPTION_INCONNUE = "unrecognized arguments"
# Outils dont aucun argument n'est obligatoire : l'option inconnue est alors la SEULE erreur possible,
# donc argparse la nomme. Les autres disent d'abord ce qui manque (« the following arguments are
# required: … »), ce qui est tout aussi juste — le contrat vérifié reste le même.
SANS_ARGUMENT_OBLIGATOIRE = [
    "build_ai_bundle", "build_mouse_db", "check_deployment", "compare_profiles", "flow_effect",
    "image_corpus_check", "privacy_scan", "qa_flow_matrix", "recommendation_stats", "render_preview",
]

# Entrée invalide « métier » : le chemin d'un fichier ou d'un dossier qui n'existe pas.
CAS_ENTREE_INVALIDE = [
    ("image_corpus_check", lambda d: [str(d / "dossier-absent")], "dossier introuvable"),
    ("image_identity_check", lambda d: ["--reference", str(d / "absente.png"),
                                        "--candidate", str(d / "absente2.png")],
     "image introuvable (référence)"),
    ("measure_button_height", lambda d: [str(d / "absente.png"), "--length-mm", "122.5",
                                         "--height-mm", "42.4"],
     "image introuvable"),
    ("measure_grip_width", lambda d: [str(d / "absente.png"), "--length", "118.2"],
     "image introuvable"),
    ("build_ai_bundle", lambda d: [str(d / "dossier-absent" / "pack.zip")],
     "dossier de destination introuvable"),
    ("db_effect", lambda d: ["--avant", str(d / "absent.json"), "--grille", "mini"],
     "catalogue introuvable (AVANT)"),
]


def _outil(nom: str):
    return importlib.import_module(nom)


@pytest.mark.parametrize("nom,construire,fragment", CAS_ENTREE_INVALIDE,
                         ids=[cas[0] for cas in CAS_ENTREE_INVALIDE])
def test_une_entree_invalide_dit_une_phrase_et_sort_en_code_2(nom, construire, fragment, tmp_path, capsys):
    """Le contrat des outils : phrase sur la sortie d'erreur, code 2, aucune trace Python."""
    with pytest.raises(SystemExit) as sortie:
        _outil(nom).main(construire(tmp_path))
    assert sortie.value.code == 2, f"{nom} : code {sortie.value.code} au lieu de 2"
    erreur = capsys.readouterr().err
    assert fragment in erreur, f"{nom} : « {fragment} » absent du message"
    assert "Traceback" not in erreur, f"{nom} : trace Python au lieu d'une phrase"


@pytest.mark.parametrize("nom", OUTILS)
def test_une_option_inconnue_est_refusee_en_code_2(nom, capsys):
    """`--pas-une-option-typo` : refusé partout, jamais écrit dans un fichier, jamais ignoré."""
    with pytest.raises(SystemExit) as sortie:
        _outil(nom).main(["--pas-une-option-typo"])
    assert sortie.value.code == 2, f"{nom} : code {sortie.value.code} au lieu de 2"
    erreur = capsys.readouterr().err
    assert erreur.strip(), f"{nom} : aucune explication sur la sortie d'erreur"
    assert "Traceback" not in erreur


@pytest.mark.parametrize("nom", SANS_ARGUMENT_OBLIGATOIRE)
def test_une_option_inconnue_est_nommee_quand_rien_d_autre_ne_manque(nom, capsys):
    with pytest.raises(SystemExit):
        _outil(nom).main(["--pas-une-option-typo"])
    assert FRAGMENT_OPTION_INCONNUE in capsys.readouterr().err


def test_aide_disponible_sur_tous_les_outils_et_sans_ecriture(tmp_path, capsys, monkeypatch):
    """`--help` doit afficher l'aide : avant, trois outils l'ignoraient (dont un qui ÉCRIVAIT un fichier).

    Le contrôle tourne dans un dossier temporaire vide (dossier de travail du processus changé) : si un
    outil écrit quelque chose pendant `--help`, il laisse une trace derrière lui.
    """
    monkeypatch.chdir(tmp_path)
    for nom in OUTILS:
        with pytest.raises(SystemExit) as sortie:
            _outil(nom).main(["--help"])
        assert sortie.value.code == 0, f"{nom} : code {sortie.value.code} pour --help"
        assert "usage:" in capsys.readouterr().out, f"{nom} : pas d'aide affichée"
    assert list(tmp_path.iterdir()) == [], "un outil a écrit un fichier pendant --help"


def test_une_image_sans_souris_detectable_dit_une_phrase_et_sort_en_code_2(tmp_path, capsys):
    """Cas réel : le propriétaire vise une capture vide (ou un fond uni) — la mesure doit le dire."""
    from PIL import Image

    vide = tmp_path / "vide.png"
    Image.new("RGB", (400, 200), (255, 255, 255)).save(vide)

    with pytest.raises(SystemExit) as sortie:
        _outil("measure_button_height").main([str(vide), "--length-mm", "122.5", "--height-mm", "42.4"])
    assert sortie.value.code == 2
    erreur = capsys.readouterr().err
    assert "mesure impossible" in erreur
    assert "aucune souris détectée" in erreur
    assert "Traceback" not in erreur

    with pytest.raises(SystemExit) as sortie:
        _outil("measure_grip_width").main([str(vide), "--length", "118.2"])
    assert sortie.value.code == 2
    erreur = capsys.readouterr().err
    assert "mesure impossible" in erreur
    assert "aucun contour détecté" in erreur
    assert "Traceback" not in erreur


def test_une_image_illisible_dit_une_phrase_et_sort_en_code_2(tmp_path, capsys):
    """Un fichier qui n'est pas une image (téléchargement raté) : phrase, pas `UnidentifiedImageError`."""
    faux = tmp_path / "pas_une_image.png"
    faux.write_text("ceci n'est pas une image", encoding="utf-8")

    for nom, argv in (("measure_button_height", [str(faux), "--length-mm", "122.5",
                                                 "--height-mm", "42.4"]),
                      ("measure_grip_width", [str(faux), "--length", "118.2"])):
        with pytest.raises(SystemExit) as sortie:
            _outil(nom).main(argv)
        assert sortie.value.code == 2, nom
        erreur = capsys.readouterr().err
        assert "image illisible" in erreur, nom
        assert "Traceback" not in erreur, nom


def test_tous_les_outils_acceptent_argv_et_sont_donc_couverts():
    """Complétude : un outil dont `main` n'accepte pas `argv` échapperait à tout ce fichier.

    C'était le cas de cinq outils avant le 2026-10-13 (ils lisaient `sys.argv` directement ou pas du
    tout). L'invariant est désormais vérifié plutôt qu'espéré : `main(argv=None)` sur les quatorze.
    """
    sans_argv = [nom for nom in OUTILS
                 if "argv" not in inspect.signature(_outil(nom).main).parameters]
    assert sans_argv == [], f"outils non testables en l'état : {sans_argv}"
    assert len(OUTILS) >= 14, f"le dossier ne contient plus les outils attendus : {OUTILS}"

# ---------------------------------------------------------------------------
# Un outil de mesure ne doit pas remplacer un rapport de référence sans le dire
# ---------------------------------------------------------------------------
def test_rapide_n_ecrase_pas_le_rapport_statistique_du_depot(tmp_path, capsys):
    """Défaut trouvé le 2026-10-13 (46e passe, C61) : l'exemple du module invitait à écraser.

    `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` est l'artefact de référence — grille
    complète, 18 522 profils ; la grille resserrée en compte 420. Le module montrait `--rapide` **sans**
    `--sortie` : suivre l'exemple remplaçait donc le rapport de référence par un rapport d'une autre
    grille, sans avertissement. Le contrôle rapide écrit maintenant ailleurs, et le rapport du dépôt
    n'est plus touché (vérifié ici en le relisant avant/après).
    """
    from tools import recommendation_stats as stats

    rapport = stats.SORTIE_PAR_DEFAUT
    avant = rapport.read_bytes()

    assert stats.main(["--rapide"]) == 2                       # refusé, code 2
    erreur = capsys.readouterr().err
    assert "--sortie" in erreur and "Erreur" in erreur          # la phrase dit quoi faire
    assert rapport.read_bytes() == avant                        # le rapport de référence est intact

    assert stats.main(["--rapide", "--sortie", str(tmp_path / "rapide.md")]) == 0
    assert "## Résultats vides et repli de coque" in (tmp_path / "rapide.md").read_text(encoding="utf-8")
