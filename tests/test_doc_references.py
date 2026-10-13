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


# ---------------------------------------------------------------------------
# Règles du moteur recopiées dans les documents normatifs (2026-10-12)
# ---------------------------------------------------------------------------
# Bug de la 28e passe : quatre documents (dont ce README et le prompt de référence) annonçaient
# « Claw → {Low, Mid} · Fingertip → {Low} », alors que `utils/matcher.py` applique l'inverse depuis le
# reverse engineering de l'outil Oblivity. Un document qui décrit une règle du moteur est un document
# qui peut se périmer : ces quatre-là portent désormais la MÊME phrase de référence, et le test
# ci-dessous la compare au moteur. Changer la règle sans changer la phrase fait échouer la suite.
RULE_DOCUMENTS = [
    "README.md",
    "docs/MASTER_PROMPT_AZEMOUSE.md",
    "docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md",
    "docs/PROMPT_RECHERCHE_SOURIS_ATK.md",
]


def _canonical_button_sentence() -> str:
    from utils.matcher import BUTTON_IDEAL
    from utils.models import Grip
    parts = [f"{grip.name.capitalize()} → {{{', '.join(sorted(BUTTON_IDEAL[grip]))}}}"
             for grip in (Grip.PALM, Grip.CLAW, Grip.FINGERTIP)]
    return " · ".join(parts)


@pytest.mark.parametrize("rel", RULE_DOCUMENTS)
def test_button_rule_sentence_is_the_same_in_every_normative_document(rel):
    sentence = _canonical_button_sentence()
    assert sentence == "Palm → {High} · Claw → {Low} · Fingertip → {Low, Mid}", (
        "la phrase de référence du test ne correspond plus au moteur : mettre à jour les quatre "
        f"documents normatifs et ce test dans le même commit (moteur : {sentence})"
    )
    assert sentence in _read(rel), (
        f"{rel} n'annonce pas la règle des boutons du moteur ({sentence})"
    )


def test_no_document_announces_the_retired_button_rule():
    """Les formulations périmées ne doivent pas revenir (hors mention historique explicite)."""
    retired = ("Claw→{Low,Mid}", "Claw→{Low, Mid}", "Claw : Low ou Mid", "Claw -> {Low, Mid}",
               "Fingertip→{Low}", "Claw → {Low, Mid}")
    offenders = []
    for path in sorted(ROOT.glob("*.md")) + sorted(ROOT.glob("docs/**/*.md")):
        text = path.read_text(encoding="utf-8")
        # `docs/REVERSE_ENGINEERING_OBLIVITY.md` §4 conserve l'ancienne règle comme HISTORIQUE daté
        # (journal de décision) : c'est le seul endroit autorisé à la citer.
        if path.name == "REVERSE_ENGINEERING_OBLIVITY.md":
            continue
        for phrase in retired:
            if phrase in text:
                offenders.append(f"{path.relative_to(ROOT)} : « {phrase} »")
    assert offenders == [], "formulations de la règle boutons périmée : " + " ; ".join(offenders)


# ---------------------------------------------------------------------------
# Renvois « fichier + §numéro » : la section visée doit exister (37e passe)
# ---------------------------------------------------------------------------
# Bug réel trouvé le 2026-10-13 : deux renvois de `ROBUSTESSE_2026-10-12.md` citaient « §6.6 » et
# « §6.8 » d'un document qui n'a ni 6.6 ni 6.8 (les faits visés étaient les points 6 et 8 du §3).
# Un renvoi mort ne casse rien à l'exécution : il envoie seulement le lecteur dans le vide. Le test
# ci-dessous vérifie que CHAQUE citation « <fichier>.md §N » (ou « §N de <fichier>.md ») désigne une
# section qui existe vraiment dans le fichier visé.
CITATION_PATTERNS = (
    # `docs/audit/X.md` §24.4
    (re.compile(r"`([A-Za-z0-9_./-]+\.md)`\s*§\s*(\d+(?:\.\d+)?)"), (1, 2)),
    # §24.4 de `X.md` / §7 du fichier `X.md`
    (re.compile(r"§\s*(\d+(?:\.\d+)?)\s*(?:du|de|des|d'|d’|—|-|:)?\s*`?([A-Za-z0-9_./-]+\.md)"), (2, 1)),
    # X.md §24.4 (sans guillemets)
    (re.compile(r"([A-Za-z0-9_./-]+\.md)\s*§\s*(\d+(?:\.\d+)?)"), (1, 2)),
)

_CITATION_FILES = sorted(
    {
        str(p.relative_to(ROOT))
        for motif in ("*.md", "docs/**/*.md", "tests/*.py", "tools/*.py", "utils/*.py", "cogs/*.py")
        for p in ROOT.glob(motif)
        # Ce fichier-ci cite volontairement un renvoi mort (« AUDIT.md, §3.3 ») comme contre-exemple.
        if p.name != "test_doc_references.py"
    }
)

_DOC_INDEX = {
    p.name: p
    for p in list(ROOT.glob("*.md")) + list(ROOT.glob("docs/**/*.md"))
}


def _sections_of(nom: str) -> set[str]:
    """Numéros de titre du document (ex. {« 24 », « 24.4 », « 12.19 »})."""
    sections = set()
    for ligne in _DOC_INDEX[nom].read_text(encoding="utf-8").splitlines():
        trouve = re.match(r"^#{1,4}\s+(\d+(?:\.\d+)?)[.\s]", ligne)
        if trouve:
            sections.add(trouve.group(1))
    return sections


@pytest.mark.parametrize("rel", _CITATION_FILES)
def test_les_renvois_de_section_pointent_sur_une_section_existante(rel):
    texte = _read(rel)
    morts = []
    for motif, (groupe_nom, groupe_num) in CITATION_PATTERNS:
        for trouve in motif.finditer(texte):
            nom = trouve.group(groupe_nom).rsplit("/", 1)[-1]
            if nom not in _DOC_INDEX:
                continue        # fichier cité absent du dépôt : l'autre test s'en charge
            numero = trouve.group(groupe_num)
            if numero not in _sections_of(nom):
                morts.append(f"{nom} §{numero} (« {trouve.group(0)[:60]} »)")
    assert morts == [], f"renvois de section introuvables dans {rel} : {sorted(set(morts))}"
