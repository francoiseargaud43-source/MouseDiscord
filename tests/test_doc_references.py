"""Cohérence des renvois documentaires : chemins cités existants, titres de section exacts.

Ne vérifie pas le sens du texte (cela reste une relecture humaine), mais empêche les renvois morts
(fichier renommé, section renumérotée, titre modifié) de revenir silencieusement.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_FILES = [
    "README.md",
    "docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md",
    "docs/audit/AUDIT.md",
    "docs/audit/AUDIT_CONFIDENTIALITE.md",
    "docs/audit/CATALOGUE_ATK.md",
    "docs/audit/DEPLOIEMENT_AUDIT.md",
    "docs/audit/RAPPORT_FINAL.md",
    "docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md",
]
CODE_FILES = ["utils/models.py", "utils/selection.py", "utils/matcher.py", "cogs/finder_flow.py"]

PATH_RE = re.compile(r"`((?:docs|tests|utils|cogs|data|assets|tools)/[\w./-]+\.(?:md|py|json|txt|ini))`")

# Titres de section réellement cités (texte exact tel qu'écrit dans le fichier, sans les « # »).
EXPECTED_HEADINGS = {
    "docs/audit/RAPPORT_FINAL.md": [
        "## 4. Tests réellement exécutés",
        "## 7. Points ouverts et entrées nécessaires du propriétaire",
        "## 8. Vérifications Discord manuelles (non exécutées)",
    ],
    "docs/audit/AUDIT.md": [
        "## 2. Constats et corrections",
        "## 8. Points ouverts (propriétaire)",
        "## 9. Vérifications Discord",
    ],
    "docs/audit/DEPLOIEMENT_AUDIT.md": [
        "### F.1 Vérifications NON réalisées (nécessitent votre hébergement ou Discord)",
        "## Livrable H — Diagnostic des prérequis d'hébergement (Alwaysdata)",
    ],
    "docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md": [
        "### 2.2 Arborescence finale attendue sur le serveur",
        "### 2.3 Tableau de tri des fichiers du dépôt",
        "### 2.4 Le fichier `.env` : secret, à ne jamais publier",
        "### 2.5 Les liens d'achat : point d'attention avant mise en ligne publique",
        "### 5.1 Créer la connexion",
        "### 5.3 Transférer le contenu du dépôt",
        "### 5.4 Vérifier le transfert",
        "### 6.5 Créer le fichier `.env` sur le serveur",
        "## 7. Démarrage permanent : Alwaysdata « Services »",
        "### 7.1 Déclarer le service",
        "### 7.2 Vérifier le démarrage",
        "### 8.3 Salon dédié, `FINDER_CHANNEL_ID` et verrouillage",
        "### 10.3 Dans Discord (manuel, à effectuer par vous)",
        "### 11.1 Où lire les erreurs",
        "### 12.1 Ce qui ne doit JAMAIS être écrasé",
        "### 12.2 Procédure pas à pas",
    ],
}


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", [f for f in DOC_FILES + CODE_FILES if (ROOT / f).exists()])
def test_backticked_repo_paths_exist(rel):
    missing = []
    for match in PATH_RE.finditer(_read(rel)):
        target = match.group(1)
        if not (ROOT / target).exists():
            missing.append(target)
    assert missing == [], f"chemins cités absents du dépôt dans {rel} : {missing}"


@pytest.mark.parametrize("rel", sorted(EXPECTED_HEADINGS))
def test_cited_section_titles_exist_exactly(rel):
    headings = {line.rstrip() for line in _read(rel).splitlines() if line.startswith("#")}
    missing = [h for h in EXPECTED_HEADINGS[rel] if h not in headings]
    assert missing == [], f"titres introuvables dans {rel} : {missing}"


def test_no_citation_of_nonexistent_audit_section():
    # Ancienne citation erronée : « Points non vérifiés » n'existe pas dans DEPLOIEMENT_AUDIT.md
    assert "Points non vérifiés" not in _read("docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md")
    # « AUDIT.md §3.3 » n'existe pas (la séparation des largeurs est au constat C2, §2)
    assert "AUDIT.md, §3.3" not in _read("utils/models.py")
