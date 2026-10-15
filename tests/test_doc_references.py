"""Cohérence des renvois documentaires : chemins cités existants, titres de section exacts.

Ne vérifie pas le sens du texte (cela reste une relecture humaine), mais empêche les renvois morts
(fichier renommé, section renumérotée, titre modifié) de revenir silencieusement.
"""
import json
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
CODE_FILES = ["utils/models.py", "utils/selection.py", "utils/slots.py", "utils/matcher.py",
              "cogs/finder_flow.py"]

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
# Renvois de section : un numéro cité doit exister (2026-10-14, 61e passe)
# ---------------------------------------------------------------------------
# Deux renvois morts trouvés à la relecture : le « 7.5 » cité par le tableau 8.1 désignait une section
# déjà occupée par un autre sujet (« le point ouvert : le prix de l'A9 Plus »), et quatre renvois vers
# « 21.6 » — écrits quand la 33e passe devait être une sous-section de la 32e — pointaient dans le vide
# depuis que ce passage est devenu la section 22 (ce commentaire les cite sans « § » pour ne pas se
# dénoncer lui-même : la règle ci-dessous balaie ce fichier comme les autres). Le lecteur qui suit un
# renvoi tombait sur une section inexistante, ou sur la mauvaise. Aucun test ne relisait les numéros cités : ce contrôle le fait, sur les trois
# plages sans ambiguïté du dépôt — « §19.x » à « §26.x » n'existent que dans ROBUSTESSE_2026-10-12.md,
# « §12.x » que dans le guide de déploiement, et « C## » que dans AUDIT.md.


def _sections(rel: str) -> set[str]:
    return set(re.findall(r"^#{2,3} (\d{1,2}\.\d+)", _read(rel), re.M))


def test_chaque_numero_de_section_cite_existe_dans_le_document_qu_il_vise():
    robustesse = _sections("docs/audit/ROBUSTESSE_2026-10-12.md")
    deploiement = {n for n in _sections("docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md") if n.startswith("12.")}
    constats = set(re.findall(r"^\| (C\d+) \|", _read("docs/audit/AUDIT.md"), re.M))

    # 89 fichiers : documents, notes des données, et tout le code — une citation nue (§26.8 dans
    # `tools/measure_grip_width.py`) n'est attrapée ni par le test 37e (qui exige un nom de fichier
    # accolé) ni par un balayage limité aux documents.
    motifs = ("README.md", "docs/**/*.md", "tests/*.py", "tools/*.py", "utils/*.py", "cogs/*.py",
              "bot.py", "config.py", "data/*.json")
    fichiers = sorted({p.relative_to(ROOT).as_posix() for motif in motifs for p in ROOT.glob(motif)})
    morts = []
    for rel in fichiers:
        texte = _read(rel)
        for majeur, mineur in re.findall(r"§(\d{1,2})\.(\d+)", texte):
            numero = f"{majeur}.{mineur}"
            if int(majeur) >= 19 and numero not in robustesse:
                morts.append(f"{rel} → §{numero} (absent de ROBUSTESSE_2026-10-12.md)")
            elif majeur == "12" and rel != "docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md" and numero not in deploiement:
                morts.append(f"{rel} → §{numero} (absent du guide de déploiement)")
        if rel != "docs/audit/AUDIT.md":
            for code in re.findall(r"(?<![A-Za-z0-9])C(\d{2,3})(?!\d)", texte):
                if f"C{code}" not in constats:
                    morts.append(f"{rel} → C{code} (absent de docs/audit/AUDIT.md)")
    assert morts == [], "renvois de section morts : " + " ; ".join(morts)


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


def _renvois_morts(texte: str) -> list[str]:
    """Les renvois « un document .md + un numéro de section », quand la section n'existe pas."""
    morts = []
    for motif, (groupe_nom, groupe_num) in CITATION_PATTERNS:
        for trouve in motif.finditer(texte):
            nom = trouve.group(groupe_nom).rsplit("/", 1)[-1]
            if nom not in _DOC_INDEX:
                continue        # fichier cité absent du dépôt : l'autre test s'en charge
            numero = trouve.group(groupe_num)
            if numero not in _sections_of(nom):
                morts.append(f"{nom} §{numero} (« {trouve.group(0)[:60]} »)")
    return morts


@pytest.mark.parametrize("rel", _CITATION_FILES)
def test_les_renvois_de_section_pointent_sur_une_section_existante(rel):
    morts = _renvois_morts(_read(rel))
    assert morts == [], f"renvois de section introuvables dans {rel} : {sorted(set(morts))}"


def test_les_donnees_du_catalogue_ne_citent_pas_de_section_morte():
    """Le catalogue et les liens renvoient à leurs preuves écrites (« docs/… §3 (point 6) »).

    Défaut trouvé le 2026-10-13 (49e passe) : la note de prix du U2 V2 Mini renvoyait au §6.6 de
    `VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`, une section qui n'a jamais existé — la réponse est au
    §3 (point 6). Les documents étaient relus par un test, les données non : un renvoi mort y dormait.
    """
    morts = []
    fichiers = sorted(ROOT.glob("data/*.json"))
    assert fichiers, "aucun fichier de données trouvé : le test ne contrôlerait rien"
    for fichier in fichiers:
        texte = fichier.read_text(encoding="utf-8")
        json.loads(texte)           # une donnée illisible est un autre problème, dit ailleurs
        morts += [f"{fichier.name} → {mort}" for mort in _renvois_morts(texte)]
    assert morts == [], f"renvois de section introuvables dans data/ : {morts}"


def test_le_readme_cite_tous_les_fichiers_de_tests_et_tous_les_outils():
    """Le README est l'index du dépôt : un fichier ajouté sans y être décrit redevient invisible.

    Défaut trouvé le 2026-10-13 : huit fichiers de tests et quatre outils existaient sans être cités
    dans le README, et la description de `tests/test_db_effect.py` avait été coupée en deux par le
    « copier-coller » d'un fichier de test dans la liste (la fin de sa phrase servait de corps au
    suivant). Ce contrôle tient les deux bouts : tout fichier de `tests/` et de `tools/` est cité, et
    toute citation pointe sur un fichier qui existe (le contrôle des chemins cités le vérifie déjà).
    """
    texte = (ROOT / "README.md").read_text(encoding="utf-8")
    cites = set(re.findall(r"(tests/test_[a-z_0-9]+\.py|tools/[a-z_0-9]+\.py)", texte))
    attendus = {f"tests/{f.name}" for f in (ROOT / "tests").glob("test_*.py")}
    attendus |= {f"tools/{f.name}" for f in (ROOT / "tools").glob("*.py")}
    absents = sorted(attendus - cites)
    assert absents == [], f"fichiers absents du README : {absents}"
    morts = sorted(cites - attendus)
    assert morts == [], f"le README cite des fichiers qui n'existent pas : {morts}"

# ---------------------------------------------------------------------------
# Tableau des images du README : une clé décrite UNE fois, et toutes décrites
# ---------------------------------------------------------------------------
def test_le_tableau_des_images_du_readme_decrit_chaque_cle_une_seule_fois():
    """Défaut trouvé le 2026-10-13 : `illustration_grip_relaxed` était décrit **deux fois**.

    Deux lignes pour la même clé, avec deux textes différents (« étape et résultat » / « résultat ») :
    l'exploitant qui personnalise une illustration ne sait plus laquelle est la bonne, et une clé
    ajoutée à `assets/images.json` peut rester invisible. Le contrôle compare le tableau au fichier,
    dans les deux sens, et vérifie que le fichier cité existe vraiment.
    """
    lignes = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    entete = next(i for i, l in enumerate(lignes) if l.startswith("| Clé | Affichée à |"))
    tableau = []
    for ligne in lignes[entete + 2:]:
        if not ligne.startswith("|"):
            break
        tableau.append(ligne)

    cles = [re.match(r"^\| `([a-z0-9_]+)` \|", l).group(1) for l in tableau]
    assert len(cles) == len(set(cles)), f"clé décrite plusieurs fois : {sorted(cles)}"

    images = json.loads((ROOT / "assets" / "images.json").read_text(encoding="utf-8"))
    images = {k: v for k, v in images.items() if not k.startswith("_")}
    assert set(cles) == set(images), (f"clés absentes du tableau : {sorted(set(images) - set(cles))} ; "
                                      f"clés du tableau absentes du fichier : {sorted(set(cles) - set(images))}")

    livrees = {f.name for f in (ROOT / "assets" / "illustrations").iterdir() if f.is_file()}
    for ligne, cle in zip(tableau, cles):
        cellules = [c.strip() for c in ligne.strip("|").split("|")]
        fichier = cellules[2].strip("`")
        if fichier and fichier != "*(vide)*":
            assert fichier in livrees, f"{cle} cite {fichier}, absent de assets/illustrations/"
        if images[cle]:
            assert fichier and fichier != "*(vide)*", f"{cle} a une image mais le tableau dit « vide »"
        else:
            assert fichier == "*(vide)*", f"{cle} n'a pas d'image mais le tableau cite {fichier!r}"


# Rapports **datés** : ils citent les noms de la suite de leur jour, et c'est leur sujet.
# - `RAPPORT_FINAL.md` (2026-10-10) est le rapport de migration : chaque ligne dit ce que le test cité
#   est devenu (« Supprimé », « Devient … », « remplacé par … »).
# - `REPORTE_DESIGN.md` (2026-10-11) décrit le design tel qu'il était et cite les tests qui le
#   vérifiaient alors — dont la liste « À vérifier », retirée depuis.
# Les autres documents sont tenus à jour : un nom de test qui n'existe plus y est un renvoi mort.
REGISTRE = ROOT / "docs/audit/NOMS_DE_TESTS_RETIRES.md"
RAPPORTS_DATES = {"docs/audit/RAPPORT_FINAL.md", "docs/REPORTE_DESIGN.md"}
NOM_DE_TEST = re.compile(r"(?<![/\w])(test_\w{10,})")


def _noms_de_tests_definis() -> tuple[set[str], set[str]]:
    fonctions, fichiers = set(), set()
    for chemin in (ROOT / "tests").rglob("*.py"):
        fichiers.add(chemin.stem)
        fonctions |= set(re.findall(r"def (test_\w+)\(", chemin.read_text(encoding="utf-8")))
    return fonctions, fichiers


def test_chaque_nom_de_test_cite_en_document_existe_dans_la_suite():
    """Un document qui cite un test doit citer un test **existant** (2026-10-14, 66e passe).

    Constat : quinze citations de tests n'existaient plus dans la suite — dans l'audit de
    confidentialité (6), le protocole de validation en conditions réelles (2), `AUDIT.md` (2), le
    master prompt (4) et le rapport de design (1). Les noms avaient existé : `git log -S` les retrouve,
    et le renommage est tracé (par exemple `test_p11_persistent_panel_works_after_restart_in_fresh_bot_instance`
    est devenu `test_p11_a_restart_keeps_the_running_parcours_and_its_components`, et les tests du bouton
    « Terminer » ont disparu avec le bouton). Un renvoi mort envoie le lecteur — ou la personne qui
    exécute le protocole de confidentialité — chercher une preuve qui n'existe pas.

    Deux formes sont écartées, parce qu'elles ne sont pas des renvois : un nom de **fichier** de test
    (`test_session`, `test_catalog_lookup`, y compris suivi de « .py ») et une **abréviation** assumée
    (le nom finit par « _ », ou est suivi de « … » : `test_p07_…`). Un nom mort **en fin de phrase** est
    attrapé comme les autres : la première version du contrôle l'excusait, la mutation l'a montré.

    Mutation jouée : remettre un nom mort dans `AUDIT.md` → 1 échec. Les deux rapports datés
    (`RAPPORT_FINAL.md`, `REPORTE_DESIGN.md`) sont hors périmètre : ils citent les noms de leur jour, et
    le rapport de migration parle même *des* renommages.
    """
    fonctions, fichiers = _noms_de_tests_definis()
    retires, _ = _colonnes_du_registre()
    morts = []
    for chemin in sorted(ROOT.rglob("*.md")):
        if ".venv" in chemin.parts or ".git" in chemin.parts:
            continue
        relatif = chemin.relative_to(ROOT).as_posix()
        if relatif in RAPPORTS_DATES:
            continue
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), start=1):
            for nom in NOM_DE_TEST.findall(ligne):
                if (nom in fonctions or nom in retires or nom.rstrip("_") in fichiers
                        or nom.endswith("_")):
                    continue
                suivant = ligne[ligne.find(nom) + len(nom):][:3]
                if suivant.startswith("…") or suivant.startswith(".py"):
                    continue          # abréviation, ou ancien nom de fichier (« ex-`test_x.py` »)
                morts.append(f"{relatif}:{numero} → {nom}")
    assert morts == [], "citations de tests qui n'existent pas :\n  " + "\n  ".join(morts)


def _colonnes_du_registre() -> tuple[set[str], set[str]]:
    """(noms retirés, renvois cités) lus dans `docs/audit/NOMS_DE_TESTS_RETIRES.md`."""
    retires, renvois = set(), set()
    for ligne in REGISTRE.read_text(encoding="utf-8").splitlines():
        if not ligne.startswith("|") or ligne.startswith("|---") or ligne.startswith("| Nom retiré"):
            continue
        cellules = [c.strip() for c in ligne.strip("|").split("|")]
        if len(cellules) < 2:
            continue
        retires |= set(re.findall(r"`(test_\w+)`", cellules[0]))
        for cellule in cellules[1:]:
            renvois |= set(re.findall(r"`(test_\w+)`", cellule))
    return retires, renvois


def test_le_registre_des_noms_retires_ne_contient_que_des_renvois_valides():
    """Le registre ne peut pas pourrir : chaque renvoi doit vivre, chaque nom retiré doit être mort.

    Un ancien nom qui revient comme test vivant voudrait dire que le registre raconte l'inverse de la
    vérité ; un renvoi vers un test qui n'existe pas serait un renvoi mort de plus, dans le fichier censé
    les répertorier.
    """
    fonctions, _ = _noms_de_tests_definis()
    retires, renvois = _colonnes_du_registre()
    assert len(retires) >= 12, f"registre vide ou illisible : {len(retires)} nom(s) retiré(s)"
    assert len(renvois) >= 12, f"aucun renvoi lu dans le registre : {len(renvois)}"
    vivants_parmi_les_retires = sorted(retires & fonctions)
    assert vivants_parmi_les_retires == [], f"noms retirés qui existent encore : {vivants_parmi_les_retires}"
    renvois_morts = sorted(renvois - fonctions)
    assert renvois_morts == [], f"renvois du registre vers des tests inexistants : {renvois_morts}"
