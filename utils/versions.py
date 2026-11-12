"""Versions d'une même souris (2026-11-12) : même coque, autres composants, autre prix.

Une souris du catalogue (``data/mouse_db.json``) est UNE version : par exemple « X1 V2 Ultra Max 2.0 ».
La boutique en vend souvent plusieurs sous le même nom (Ultra Max, Ultimate, Extreme…), avec la même
forme mais un autre capteur, un autre poids, un récepteur 8 000 Hz ou une base de charge. Le moteur
ne note que la forme : la recommandation vaut donc pour toutes. Ce module lit ``data/versions.json``
et prépare le petit tableau affiché sous le résultat, pour que le membre voie d'un coup d'œil ce qui
change et si cela vaut le supplément.

Règles des données du propriétaire, appliquées ici comme dans le catalogue :

- rien n'est inventé : un champ absent n'est pas affiché ;
- prix en euros relevés sur la boutique France, jamais convertis ;
- chaque lien porte le paramètre d'affiliation de sa boutique (même contrôle que les boutons d'achat) ;
- une version épuisée n'est pas proposée.

Le moteur (``utils/matcher.py``, ``selection.py``, ``slots.py``) n'est pas concerné : ce fichier ne
change ni le score ni le classement.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from utils.catalog import _affiliation_manquante, _lien_utilisable

log = logging.getLogger(__name__)

# Écart de poids à partir duquel la différence est signalée (en grammes) : en dessous, elle se sent à
# peine et la mentionner chargerait le tableau pour rien.
POIDS_ECART_NOTABLE_G = 3


@dataclass(frozen=True, slots=True)
class Version:
    nom: str
    prix_eur: float
    lien: str
    capteur: str | None = None
    hz: int | None = None
    poids_g: float | None = None
    switchs: str | None = None      # nom des switchs tel que la fiche l'écrit
    mcu: str | None = None          # puce, telle que la fiche l'écrit
    autonomie_h: int | None = None  # heures d'autonomie annoncées (à 1 000 Hz)
    en_plus: tuple[str, ...] = ()
    resultat: bool = False          # la version décrite par la fiche du catalogue


@dataclass(frozen=True, slots=True)
class Gamme:
    mouse_id: str
    versions: tuple[Version, ...]   # en stock uniquement, du moins cher au plus cher
    releve: str | None = None


def _version(raw: Mapping[str, Any], mouse_id: str) -> Version | None:
    nom = raw.get("nom")
    prix = raw.get("prix_eur")
    lien = raw.get("lien")
    if not (isinstance(nom, str) and nom.strip()):
        log.warning("Version ignorée pour %s : nom absent", mouse_id)
        return None
    if isinstance(prix, bool) or not isinstance(prix, (int, float)) or prix <= 0:
        log.warning("Version %s ignorée pour %s : prix en euros absent", nom, mouse_id)
        return None
    if not (isinstance(lien, str) and _lien_utilisable(lien)) or _affiliation_manquante(lien):
        log.warning("Version %s ignorée pour %s : lien invalide ou sans affiliation", nom, mouse_id)
        return None
    if raw.get("dispo") is not True:
        return None                 # épuisée (ou disponibilité inconnue) : pas proposée
    hz = raw.get("hz")
    poids = raw.get("poids_g")
    capteur = raw.get("capteur")
    switchs = raw.get("switchs")
    mcu = raw.get("mcu")
    autonomie = raw.get("autonomie_h")
    en_plus = raw.get("en_plus") or ()
    return Version(
        nom=nom.strip(),
        prix_eur=float(prix),
        lien=lien,
        capteur=capteur.strip() if isinstance(capteur, str) and capteur.strip() else None,
        hz=hz if isinstance(hz, int) and not isinstance(hz, bool) and hz > 0 else None,
        poids_g=float(poids) if isinstance(poids, (int, float)) and not isinstance(poids, bool) and poids > 0 else None,
        autonomie_h=autonomie if isinstance(autonomie, int) and not isinstance(autonomie, bool) and autonomie > 0 else None,
        mcu=mcu.strip() if isinstance(mcu, str) and mcu.strip() else None,
        switchs=switchs.strip() if isinstance(switchs, str) and switchs.strip() else None,
        en_plus=tuple(x.strip() for x in en_plus if isinstance(x, str) and x.strip()),
        resultat=raw.get("resultat") is True,
    )


def load_versions(path: Path) -> dict[str, Gamme]:
    """Retourne {mouse_id: Gamme}. Fichier absent ou illisible : aucune version, le résultat s'affiche."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log.warning("Fichier des versions illisible (%s) : %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        log.warning("Fichier des versions illisible (objet attendu) : %s", path)
        return {}
    gammes: dict[str, Gamme] = {}
    for mouse_id, entry in raw.items():
        if mouse_id.startswith("_") or not isinstance(entry, dict):
            continue
        items = entry.get("versions")
        if not isinstance(items, list):
            continue
        versions = [v for v in (_version(x, mouse_id) for x in items if isinstance(x, dict)) if v]
        # Une seule version en stock : rien à comparer, le bloc ne s'affiche pas.
        if len(versions) < 2:
            continue
        versions.sort(key=lambda v: (v.prix_eur, v.nom))
        releve = entry.get("releve")
        gammes[mouse_id] = Gamme(mouse_id, tuple(versions), releve if isinstance(releve, str) else None)
    return gammes


# ---------------------------------------------------------------------------
# Texte affiché
# ---------------------------------------------------------------------------

def _prix(v: float) -> str:
    return f"{v:.2f}".replace(".", ",") + " €"


def _hz(v: int) -> str:
    return f"{v:,}".replace(",", " ") + " Hz"


def _grammes(v: float) -> str:
    return (f"{v:.1f}".rstrip("0").rstrip(".")).replace(".", ",") + " g"


def type_de_clic(switchs: str | None) -> str | None:
    """« ATK Lightblade Mechanical » → « clics mécaniques » ; « Omron Optical » → « clics optiques »."""
    if not switchs:
        return None
    nom = switchs.lower()
    if "optical" in nom or "optique" in nom:
        return "clics optiques"
    if "mechanical" in nom or "mécanique" in nom:
        return "clics mécaniques"
    return None


# Une autonomie annoncée inférieure d'au moins un quart à celle de la base est signalée : c'est le
# prix caché des versions « Extreme » (puce plus rapide, batterie qui tient deux à quatre fois moins).
AUTONOMIE_PERTE_NOTABLE = 0.75


def moins_d_autonomie(version: Version, base: Version) -> bool:
    return bool(version.autonomie_h and base.autonomie_h
                and version.autonomie_h <= base.autonomie_h * AUTONOMIE_PERTE_NOTABLE)


def ce_qui_change(version: Version, base: Version) -> list[str]:
    """Ce que ``version`` apporte de plus que ``base`` (la moins chère), en mots simples."""
    gains = []
    if version.capteur and base.capteur and version.capteur != base.capteur:
        gains.append(f"capteur {version.capteur}")
    if version.hz and base.hz and version.hz > base.hz:
        gains.append(f"{_hz(version.hz)} au lieu de {_hz(base.hz)}")
    if version.poids_g and base.poids_g and base.poids_g - version.poids_g >= POIDS_ECART_NOTABLE_G:
        gains.append(f"{_grammes(base.poids_g - version.poids_g)} plus légère")
    elif version.poids_g and base.poids_g and version.poids_g - base.poids_g >= POIDS_ECART_NOTABLE_G:
        gains.append(f"{_grammes(version.poids_g - base.poids_g)} plus lourde")
    if version.mcu and base.mcu and version.mcu != base.mcu:
        gains.append(f"puce plus rapide ({version.mcu})" if "54H20" in version.mcu else f"puce {version.mcu}")
    if moins_d_autonomie(version, base):
        gains.append(f"⚠️ autonomie {version.autonomie_h} h au lieu de {base.autonomie_h} h")
    clic, clic_base = type_de_clic(version.switchs), type_de_clic(base.switchs)
    if clic and clic_base and clic != clic_base:
        gains.append(clic)
    gains.extend(x for x in version.en_plus if x not in base.en_plus)
    return gains


def ligne(version: Version, base: Version) -> str:
    """« **Ultimate 2.0** · 59,98 € (+18 €) · capteur PAW3955 · [voir](lien) »"""
    morceaux = [f"**{version.nom}**"]
    prix = _prix(version.prix_eur)
    if version is not base:
        prix += f" (+{_prix(version.prix_eur - base.prix_eur)})"
    morceaux.append(prix)
    if version is base:
        detail = [x for x in (version.capteur, _hz(version.hz) if version.hz else None,
                              _grammes(version.poids_g) if version.poids_g else None,
                              type_de_clic(version.switchs),
                              f"{version.autonomie_h} h d'autonomie" if version.autonomie_h else None) if x]
        morceaux.append(" · ".join(detail) if detail else "version de base")
    else:
        gains = ce_qui_change(version, base)
        morceaux.append(", ".join(gains) if gains else "mêmes composants documentés")
    texte = " · ".join(morceaux)
    if version.resultat:
        texte += " ← celle du résultat"
    return f"• {texte} · [voir]({version.lien})"


def conseil(gamme: Gamme) -> str:
    """La phrase « Ça vaut le coup ? », tirée des seules différences relevées.

    Elle ne juge que ce qui est documenté : la forme est la même (donc le confort aussi), et chaque
    supplément est rattaché à ce qu'il achète. Aucune note, aucun avis inventé.
    """
    base = gamme.versions[0]
    autres = gamme.versions[1:]
    plus_capteur = any(v.capteur and base.capteur and v.capteur != base.capteur for v in autres)
    plus_hz = any(v.hz and base.hz and v.hz > base.hz for v in autres)
    plus_leger = any(v.poids_g and base.poids_g and base.poids_g - v.poids_g >= POIDS_ECART_NOTABLE_G
                     for v in autres)
    autre_clic = any(type_de_clic(v.switchs) and type_de_clic(base.switchs)
                     and type_de_clic(v.switchs) != type_de_clic(base.switchs) for v in autres)
    phrases = ["Même forme pour toutes : le confort et la recommandation ne changent pas."]
    if plus_leger:
        phrases.append("Quelques grammes en moins se sentent quand on vise vite : c'est le supplément "
                       "le plus utile.")
    if plus_capteur or plus_hz:
        phrases.append("Un capteur plus récent ou une fréquence plus haute changent très peu en jeu : "
                       "pas une raison de payer plus.")
    if any(v.mcu and base.mcu and v.mcu != base.mcu for v in autres):
        if any(moins_d_autonomie(v, base) for v in autres):
            phrases.append("La puce plus rapide gagne un peu de latence, qu'on ne sent quasiment pas, et "
                           "la batterie tient bien moins longtemps : ça ne vaut pas le supplément.")
        else:
            phrases.append("La puce plus rapide gagne un peu de latence, qu'on ne sent quasiment pas.")
    elif any(moins_d_autonomie(v, base) for v in autres):
        phrases.append("Attention à l'autonomie annoncée, plus courte sur certaines versions.")
    if autre_clic:
        phrases.append("Clics mécaniques ou optiques : une affaire de sensation, pas de niveau.")
    phrases.append(f"La moins chère ({base.nom}) suffit pour la plupart des joueurs.")
    return " ".join(phrases)


def champs(gamme: Gamme, limite: int = 1024) -> list[str]:
    """Le texte des champs d'embed d'une gamme : les lignes, puis le conseil en petit.

    Un champ Discord tient 1 024 caractères et chaque lien en prend environ 150 : au-delà de cinq ou six
    versions, la suite passe dans un second champ plutôt que d'être coupée.
    """
    base = gamme.versions[0]
    morceaux = [ligne(v, base) for v in gamme.versions] + [f"-# 💡 {conseil(gamme)}"]
    valeurs, courant = [], ""
    for morceau in morceaux:
        morceau = morceau[:limite]
        if courant and len(courant) + 1 + len(morceau) > limite:
            valeurs.append(courant)
            courant = morceau
        else:
            courant = f"{courant}\n{morceau}" if courant else morceau
    valeurs.append(courant)
    return valeurs
