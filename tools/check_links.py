"""Contrôle de cohérence des liens d'achat avec le catalogue (réseau requis).

Pourquoi cet outil existe : la question « le lien du bouton ouvre-t-il **le** modèle annoncé, à **son**
prix ? » se vérifiait à la main, lien par lien, et la réponse n'était écrite que dans un tableau
(`docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` §8). Deux défauts réels sont nés de ce contrôle
manuel le 2026-10-13 : un prix publié (45,00 €) qui n'était pas celui de la variante ouverte par le
bouton (27,95 €), et trois noms de modèles qui ne se retrouvaient pas sur la page ouverte. Ici, la
vérification est mécanique et refaisable : pour chaque souris, l'outil ouvre la fiche de la boutique
au format JSON public — `products/<handle>.json?country=FR` —, y cherche le produit, puis, quand le
lien fige une variante (`?variant=<id>`), **cette variante exacte** ; il compare le prix affiché au
prix publié par `data/mouse_db.json`.

Ce que l'outil ne fait pas : il n'écrit rien, ne modifie aucune donnée, ne devine aucun lien. Une
fiche en dollars (cas des Scyrox) est signalée « hors comparaison » — aucune conversion n'est faite.

Où regarder la référence : l'inventaire daté des 36 liens est le §8 de
`docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` ; il est verrouillé par `tests/test_liens_achat.py`.
Quand ce contrôle-ci signale un écart, c'est cet inventaire et `data/mouse_db.json` qu'il faut mettre à
jour — avec le relevé du jour.

Réseau : l'outil a besoin de joindre les boutiques (`atk.store`, `eu.pulsar.gg`, `scyrox.com`). Depuis
un réseau qui les bloque, il ne peut rien comparer : il le dit et sort en code **2**, jamais en code 1
(un blocage réseau ne veut pas dire que le catalogue est faux).

Usage :
    .venv/bin/python tools/check_links.py                                   # les 36 souris
    .venv/bin/python tools/check_links.py --souris atk_a9_plus pulsar_x2_v3_mini
    .venv/bin/python tools/check_links.py --delai 20

Codes de sortie : 0 tout est cohérent · 1 au moins une fiche contredit le catalogue · 2 entrée
invalide (souris inconnue, lien inexploitable) ou réseau indisponible.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import COMMERCIAL_LINKS_PATH, MOUSE_DB_PATH  # noqa: E402
from utils.catalog import CatalogError, load_catalog, load_commercial_links  # noqa: E402

AGENT = "AzeMouse-controle-liens/1.0"
DELAI_PAR_DEFAUT = 15.0
OK = "✅ cohérent"
PRIX_DIFFERENT = "🔧 prix différent"
VARIANTE_ABSENTE = "❌ variante introuvable"
HORS_COMPARAISON = "⚠️ monnaie ≠ EUR (hors comparaison)"
INACCESSIBLE = "❌ fiche inaccessible"
LIEN_INEXPLOITABLE = "❌ lien inexploitable"
SANS_CATALOGUE = "❌ souris absente du catalogue"
ECHECS = frozenset({PRIX_DIFFERENT, VARIANTE_ABSENTE, INACCESSIBLE, LIEN_INEXPLOITABLE, SANS_CATALOGUE})


class EntreeInvalide(ValueError):
    """Lien d'achat inexploitable : on le dit, on ne devine rien."""


@dataclass(frozen=True)
class Fiche:
    """La réponse d'une boutique pour un lien donné."""

    libelle: str
    prix: float
    devise: str


@dataclass(frozen=True)
class Verdict:
    """Le statut est stocké à part du détail : c'est le STATUT qui décide du verdict final.

    Défaut trouvé par le test du 2026-10-13 : les statuts composés (« ❌ variante introuvable — variante
    absente de la fiche ») n'étaient plus reconnus comme des échecs, parce que la comparaison portait sur
    la phrase entière. Le code de sortie aurait donc rendu 0 sur une variante disparue.
    """

    souris: str
    handle: str
    variante: str
    fiche: Fiche | None
    prix_publie: float | None
    statut: str
    detail: str = ""

    @property
    def verdict(self) -> str:
        return f"{self.statut} — {self.detail}" if self.detail else self.statut

    @property
    def echec(self) -> bool:
        return self.statut in ECHECS


def extraire(url: str) -> tuple[str, str, str, str | None]:
    """(hôte, préfixe, handle, variante) — refuse tout ce qui n'est pas une fiche produit Shopify."""
    parties = urlsplit(url)
    if not parties.scheme.startswith("http") or not parties.netloc:
        raise EntreeInvalide(f"lien inexploitable : {url!r}")
    if "/products/" not in parties.path:
        raise EntreeInvalide(f"lien sans fiche produit « /products/ » : {url!r}")
    avant, handle = parties.path.split("/products/", 1)
    handle = handle.strip("/")
    if not handle:
        raise EntreeInvalide(f"lien sans identifiant de produit : {url!r}")
    variante = parse_qs(parties.query).get("variant", [None])[0]
    return parties.netloc, avant.rstrip("/"), handle, variante


def url_fiche(hote: str, prefixe: str, handle: str) -> str:
    return f"https://{hote}{prefixe}/products/{handle}.json?country=FR"


def telecharger_json(url: str, delai: float = DELAI_PAR_DEFAUT) -> dict:
    """Ouvre une fiche boutique et rend son JSON — aucune donnée n'est écrite, rien n'est modifié."""
    requete = Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    with urlopen(requete, timeout=delai) as reponse:  # noqa: S310 (URL construite à partir du dépôt)
        return json.loads(reponse.read().decode("utf-8"))


def lire_fiche(donnees: dict, variante: str | None) -> Fiche:
    """Le libellé et le prix de la variante figée — ou, sans variante figée, du modèle le moins cher."""
    produit = donnees.get("product")
    if not isinstance(produit, dict):
        raise EntreeInvalide("réponse sans objet « product » (fiche changée de format ?)")
    variantes = [v for v in produit.get("variants") or [] if isinstance(v, dict)]
    if not variantes:
        raise EntreeInvalide("réponse sans variante : fiche vide ou dépubliée")
    if variante is not None:
        choisies = [v for v in variantes if str(v.get("id")) == str(variante)]
        if not choisies:
            raise EntreeInvalide("variante absente de la fiche")
        retenue = choisies[0]
        libelle = f"{produit.get('title', '?')} — {retenue.get('title', '?')}"
    else:
        retenue = min(variantes, key=lambda v: float(v.get("price", "inf")))
        libelle = f"{produit.get('title', '?')} (le moins cher : {retenue.get('title', '?')})"
    return Fiche(libelle=libelle, prix=float(retenue["price"]),
                 devise=str(retenue.get("price_currency") or "?"))


def analyser(liens: dict, catalogue: list, telecharger=telecharger_json,
             delai: float = DELAI_PAR_DEFAUT) -> list[Verdict]:
    """Un verdict par souris : le lien ouvre-t-il le modèle annoncé, au prix publié ?"""
    prix_publies = {m.id: m.price_eur for m in catalogue}
    verdicts: list[Verdict] = []
    for souris in sorted(k for k in liens if not k.startswith("_")):
        fiche: Fiche | None = None
        if souris not in prix_publies:
            # Un lien qui ne correspond à aucune souris du catalogue : à signaler, jamais à deviner.
            verdicts.append(Verdict(souris, "", "", None, None, SANS_CATALOGUE))
            continue
        try:
            hote, prefixe, handle, variante = extraire(liens[souris])
        except EntreeInvalide as exc:
            verdicts.append(Verdict(souris, "", "", None, prix_publies[souris],
                                    LIEN_INEXPLOITABLE, str(exc)))
            continue
        try:
            fiche = lire_fiche(telecharger(url_fiche(hote, prefixe, handle), delai), variante)
        except EntreeInvalide as exc:
            statut = VARIANTE_ABSENTE if variante else INACCESSIBLE
            verdicts.append(Verdict(souris, handle, variante or "—", None, prix_publies[souris],
                                    statut, str(exc)))
            continue
        except (URLError, HTTPError, OSError, ValueError, KeyError) as exc:
            verdicts.append(Verdict(souris, handle, variante or "—", None, prix_publies[souris],
                                    INACCESSIBLE, exc.__class__.__name__))
            continue
        publie = prix_publies[souris]
        if fiche.devise != "EUR":
            verdict = HORS_COMPARAISON
        elif publie is None or abs(fiche.prix - publie) >= 0.005:
            verdict = PRIX_DIFFERENT
        else:
            verdict = OK
        verdicts.append(Verdict(souris, handle, variante or "—", fiche, publie, verdict))
    return verdicts


def _montant(valeur: float | None, devise: str = "EUR") -> str:
    if valeur is None:
        return "—"
    symbole = "€" if devise == "EUR" else f" {devise}"
    return f"{valeur:.2f}".replace(".", ",") + symbole


def code_de_sortie(verdicts: list[Verdict]) -> int:
    """0 : tout est cohérent · 1 : au moins un écart · 2 : rien n'a pu être vérifié.

    La distinction compte : un réseau qui bloque les boutiques (bac à sable, pare-feu, boutique en
    panne) ne doit **pas** se lire comme « le catalogue est faux ». Dans ce cas, le contrôle n'a pas eu
    lieu et le code le dit.
    """
    if not verdicts:
        return 2
    if all(v.statut == INACCESSIBLE for v in verdicts):
        print("\nAucune fiche n'a pu être ouverte : le contrôle n'a pas eu lieu (réseau, pare-feu ou "
              "boutique indisponible). Relancer depuis un poste qui joint les boutiques.")
        return 2
    return 1 if any(v.echec for v in verdicts) else 0


def rapporter(verdicts: list[Verdict]) -> None:
    largeur = max((len(v.souris) for v in verdicts), default=8)
    for v in verdicts:
        boutique = f"{_montant(v.fiche.prix, v.fiche.devise)}" if v.fiche else "—"
        print(f"{v.souris:<{largeur}}  {v.verdict:<32} boutique {boutique:>10}  "
              f"publié {_montant(v.prix_publie):>10}  variante {v.variante}")
    # Un « écart » est une divergence PROUVÉE entre la boutique et le catalogue. Une fiche injoignable
    # n'en est pas une : elle est comptée à part, dans la même ligne — « 0 écart » tout seul, quand rien
    # n'a pu être ouvert, serait un faux rassurant.
    ecarts = [v for v in verdicts if v.statut in (ECHECS - {INACCESSIBLE})]
    injoignables = [v for v in verdicts if v.statut == INACCESSIBLE]
    resume = f"\n{len(verdicts)} lien(s) contrôlé(s) · {len(ecarts)} écart(s)."
    if injoignables:
        resume = resume[:-1] + f" · {len(injoignables)} fiche(s) inaccessible(s)."
    print(resume)
    if ecarts:
        print("Mettre à jour le relevé puis l'inventaire §8 de "
              "docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md et data/mouse_db.json.")


def main(argv: list[str] | None = None, telecharger=telecharger_json) -> int:
    analyseur = argparse.ArgumentParser(
        description="Vérifie que chaque lien d'achat ouvre bien le modèle et le prix publiés (réseau requis).")
    analyseur.add_argument("--souris", nargs="+", default=None,
                           help="identifiants à contrôler (défaut : tout le catalogue)")
    analyseur.add_argument("--delai", type=float, default=DELAI_PAR_DEFAUT, help="délai réseau en secondes")
    options = analyseur.parse_args(argv)

    try:
        liens = load_commercial_links(COMMERCIAL_LINKS_PATH)
        catalogue = load_catalog(MOUSE_DB_PATH)
    except (CatalogError, OSError) as exc:
        analyseur.error(f"catalogue ou liens illisibles : {exc}")

    connues = {m.id for m in catalogue}
    inconnues = [s for s in (options.souris or []) if s not in connues]
    if inconnues:
        analyseur.error(f"souris inconnue(s) du catalogue : {', '.join(sorted(inconnues))}")
    if options.souris:
        liens = {k: v for k, v in liens.items() if k in set(options.souris)}

    if not liens:
        analyseur.error(f"aucun lien d'achat exploitable dans {COMMERCIAL_LINKS_PATH}")

    verdicts = analyser(liens, catalogue, telecharger=telecharger, delai=options.delai)
    rapporter(verdicts)
    return code_de_sortie(verdicts)


if __name__ == "__main__":
    sys.exit(main())
