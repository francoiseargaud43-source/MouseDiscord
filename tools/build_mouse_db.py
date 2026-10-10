"""Génère data/mouse_db.json (schéma v2) à partir des données de recherche documentées.

Ce script est l'artefact de traçabilité du catalogue : chaque valeur géométrique est
accompagnée de ses sources et de sa date de vérification (docs/audit/CATALOGUE_ATK.md).
Pour modifier une donnée, éditez directement data/mouse_db.json ; ce script ne doit être
relancé que si l'on souhaite régénérer l'ensemble à partir de ce fichier-source.
"""
from __future__ import annotations

import json
from pathlib import Path

DATE = "2026-10-10"
ROOT = Path(__file__).resolve().parent.parent

# --- Sources (URL telles qu'observées le 2026-10-10) ------------------------
S = {
    "eso_phantom": ("EloShapes — ATK Phantom Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-phantom-ultimate"),
    "eso_ghost_u": ("EloShapes — ATK GHOST Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-ghost-ultimate"),
    "eso_ghost_cmp": ("EloShapes — comparaison GHOST Extreme / Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-ghost-extreme-vs.-atk-ghost-ultimate-vs.-delux-m800-pro-vs.-razer-viper-mini"),
    "eso_y9": ("EloShapes — ATK Y9 Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-y9-ultimate"),
    "maxg_y9": ("MaxGaming — ATK Y9 Ultimate", "https://www.maxgaming.com/en/wireless-mouses/atk-y9-ultimate-wireless-gaming-mouse-pink"),
    "fps_y9": ("FPSTools — ATK Y9 Ultimate", "https://fpstools.com/en/gear/mouse/atk-y9-ultimate"),
    "atk_fierce": ("ATK Store — ATK FIERCE X", "https://www.atk.store/products/atk-fierce-x-lightweight-wireless-gaming-mouse"),
    "eso_fierce": ("EloShapes — ATK Fierce X", "https://www.eloshapes.com/mouse/compare?p=atk-fierce-x"),
    "mm_fierce": ("MouseMetric — ATK Fierce X", "https://www.mousemetric.com/mice/atk-fierce-x"),
    "atk_u2_coll": ("ATK Store — collection U2 Series", "https://www.atk.store/collections/atk-u2-series-esports-wireless-mouse"),
    "atk_u2_manual": ("Notice ATK U2 V2 Ultimate (manuals.plus)", "https://manuals.plus/ae/1005010572844508"),
    "eso_u2u": ("EloShapes — ATK U2 V2 Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-u2-v2-ultimate"),
    "eso_f1_u2m": ("EloShapes — comparaison F1 V2 Ultimate / U2 V2 Mini", "https://www.eloshapes.com/mouse/compare?p=atk-f1-v2-ultimate-vs.-atk-u2-v2-mini"),
    "eso_zero": ("EloShapes — ATK Zero", "https://www.eloshapes.com/mouse/compare?p=atk-zero"),
    "eso_duck": ("EloShapes — ATK Duckbill", "https://www.eloshapes.com/mouse/compare?p=atk-duckbill"),
    "atk_duck_blog": ("ATK Blog — Duck Bill", "https://www.atk.store/blogs/news/atk-duck-bill-gaming-mouse"),
    "eso_a9u": ("EloShapes — ATK A9 Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-a9-ultimate"),
    "atk_a9u": ("ATK Store — ATK Dragonfly A9 Ultimate", "https://www.atk.store/products/atk-dragonfly-a9-ultimate-lightweight-wireless-mouse"),
    "eso_a9air": ("EloShapes — comparaison A9 Air / A9 Ultimate", "https://www.eloshapes.com/mouse/compare?p=atk-a9-air-vs.-atk-a9-ultimate"),
    "eso_a9_cmp": ("EloShapes — comparaison A9 / A9 Plus / A9 Pro / A9 SE / A9 Ultra", "https://www.eloshapes.com/mouse/compare?p=atk-a9-vs.-atk-a9-se-vs.-atk-a9-plus-vs.-atk-a9-pro-vs.-atk-a9-ultra"),
    "atk_a9_coll": ("ATK Store — collection A9 Series", "https://www.atk.store/collections/atk-a9-series-lightweight-wireless-mouse"),
    "eso_x1v2": ("EloShapes — ATK X1 V2 Ultra Max", "https://www.eloshapes.com/mouse/compare?p=atk-x1-v2-ultra-max"),
    "eso_x1": ("EloShapes — ATK X1", "https://www.eloshapes.com/mouse/compare?p=atk-x1"),
    "atk_x1_coll": ("ATK Store — collection X1 Series", "https://www.atk.store/collections/atk-x1-series-esports-wireless-mouse"),
    "atk_f1_blog": ("ATK Blog — Which mouse is right for you (F1)", "https://www.atk.store/blogs/news/which-mouse-is-right-for-you"),
    "atk_z1_coll": ("ATK Store — collection Z1 Series", "https://www.atk.store/collections/atk-z1-series-esports-wireless-mouse"),
    "atk_z1_blog": ("ATK Blog — Blazing Sky Z1 Series", "https://www.atk.store/blogs/news/the-first-ever-right-handed-ergonomic-asymmetrical-mouse-atk-blazing-sky-z1-series"),
    "meckeys_z1": ("Meckeys — ATK Z1 Series", "https://meckeys.com/shop/mouse/atk-z1-series/"),
    "eso_a9plus": ("EloShapes — comparaison A9 Plus / A9 Pro", "https://www.eloshapes.com/mouse/compare?p=atk-a9-plus-vs.-atk-a9-pro"),
}


def src(key: str, fields: list[str]) -> dict:
    label, url = S[key]
    return {"label": label, "url": url, "fields": fields, "date_checked": DATE}


HUMP_NOTE = ("Correspondance bosse EloShapes -> schéma : « Center » = Mid ; « Back - minimal/moderate » = Rear "
             "(règle de correspondance, à confirmer par le propriétaire).")

mice = [
    # ----------------------------------------------------------------- Références cahier des charges (non-ATK)
    {
        "id": "scyrox_v8", "brand": "Scyrox", "model": "V8 / V8S", "category": "Autre", "family": "Scyrox V8",
        "budget_tier": "Haut de Gamme", "length_mm": 118.0, "width_max_mm": 63.0, "height_mm": None,
        "hump_position": "Rear", "button_height": "Low",
        "palm_grip_fit": "Faible", "claw_grip_fit": "Élevé", "fingertip_grip_fit": "Élevé",
        "fit_status": "owner_spec", "dimension_status": "owner_spec_unverified",
        "price_eur": 74.90, "price_status": "owner_spec_unverified",
        "price_note": "Prix issu du cahier des charges, date de vérification inconnue.",
        "fit_rationale": "La bosse arrière verrouille parfaitement le Claw grip. Très légère pour le Fingertip.",
        "notes": "Non-ATK. Dimensions et compatibilités fournies par le cahier des charges, non revérifiées.",
        "sources": [],
    },
    {
        "id": "scyrox_v6", "brand": "Scyrox", "model": "V6", "category": "Autre", "family": "Scyrox V6",
        "budget_tier": "Qualité-Prix", "length_mm": 119.0, "width_max_mm": 61.0, "height_mm": None,
        "hump_position": "Mid", "button_height": "Mid",
        "palm_grip_fit": "Moyen", "claw_grip_fit": "Élevé", "fingertip_grip_fit": "Élevé",
        "fit_status": "owner_spec", "dimension_status": "owner_spec_unverified",
        "price_eur": 74.90, "price_status": "owner_spec_unverified",
        "price_note": "Prix issu du cahier des charges, date de vérification inconnue.",
        "fit_rationale": "Bosse centrale très polyvalente, parfaite pour le Relaxed Claw.",
        "notes": "Non-ATK. Dimensions et compatibilités fournies par le cahier des charges, non revérifiées.",
        "sources": [],
    },
    # ----------------------------------------------------------------- ATK : références d'origine
    {
        "id": "atk_f1_ultimate", "brand": "ATK", "model": "F1 V3 Ultimate", "category": "ATK", "family": "F1",
        "shell_id": "atk_f1", "budget_tier": "Qualité-Prix", "length_mm": 118.2, "width_max_mm": 62.4,
        "height_mm": 38.8, "hump_position": "Mid", "button_height": "Low",
        "palm_grip_fit": "Faible", "claw_grip_fit": "Élevé", "fingertip_grip_fit": "Élevé",
        "fit_status": "owner_spec", "dimension_status": "verified",
        "price_eur": 70.00, "price_status": "owner_spec_unverified",
        "price_note": "Prix issu du cahier des charges, date de vérification inconnue.",
        "fit_rationale": "Arrière étroit empêchant les crampes de l'éminence thénar en Fingertip.",
        "notes": ("Dimensions 118.2 × 62.4 × 38.8 : ATK (famille F1) et EloShapes (F1 V2 Ultimate). "
                  "Génération V3 non mesurée séparément. EloShapes classe la bosse en « Back - minimal » "
                  "alors que le cahier des charges indique « Mid » : conflit de forme signalé, valeur propriétaire conservée."),
        "sources": [src("atk_f1_blog", ["length_mm", "width_max_mm", "height_mm"]),
                    src("eso_f1_u2m", ["length_mm", "width_max_mm", "height_mm", "weight_g"])],
    },
    {
        "id": "atk_x1_ultra_max", "brand": "ATK", "model": "X1 V2 Ultra Max", "category": "ATK", "family": "X1",
        "shell_id": "atk_x1", "budget_tier": "Qualité-Prix", "length_mm": 127.0, "width_max_mm": 64.0,
        "height_mm": 40.0, "hump_position": "Mid", "button_height": "Mid",
        "palm_grip_fit": "Élevé", "claw_grip_fit": "Élevé", "fingertip_grip_fit": "Faible",
        "fit_status": "owner_spec", "dimension_status": "verified",
        "price_eur": 75.00, "price_status": "owner_spec_unverified",
        "price_note": "Prix issu du cahier des charges, date de vérification inconnue.",
        "fit_rationale": "Idéale pour soutenir les grandes mains sans forcer l'arche.",
        "weight_g": 55.0, "polling_hz": 8000,
        "notes": ("127 × 64 × 40 mm confirmés par EloShapes et la collection ATK X1. "
                  "Capteur indiqué différemment selon les sources (PAW3395 Ultra chez EloShapes, "
                  "PAW3950 Ultra ou PAW3955 Master chez ATK) : non renseigné. "
                  "EloShapes : bosse « Back - minimal » vs « Mid » du cahier des charges (conflit signalé)."),
        "conflicts": {"sensor": {"values": ["PAW3395 Ultra", "PAW3950 Ultra / PAW3955 Master"],
                                 "sources": ["EloShapes", "ATK Store"]}},
        "sources": [src("eso_x1v2", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz"]),
                    src("atk_x1_coll", ["length_mm", "width_max_mm", "height_mm"])],
    },
    {
        "id": "atk_z1_ultra", "brand": "ATK", "model": "Z1 V2 Ultra", "category": "ATK", "family": "Z1",
        "shell_id": "atk_z1_v2", "budget_tier": "Haut de Gamme", "length_mm": 122.5, "width_max_mm": 66.8,
        "height_mm": 42.4, "hump_position": "Mid-Front", "button_height": "High",
        "palm_grip_fit": "Élevé", "claw_grip_fit": "Moyen", "fingertip_grip_fit": "Faible",
        "fit_status": "owner_spec", "dimension_status": "verified",
        "price_eur": 75.00, "price_status": "owner_spec_unverified",
        "price_note": "Prix issu du cahier des charges, date de vérification inconnue.",
        "fit_rationale": "Coque ergonomique asymétrique. Boutons hauts. Le choix absolu pour le Palm Grip.",
        "weight_g": 54.0, "polling_hz": 8000,
        "notes": ("122.5 × 66.8 × 42.4 mm : ATK (collection Z1), article ATK 2024 et Meckeys. "
                  "Ne pas confondre avec la Z1 originale (119.57 × 60.99 × 36.26 mm selon ATK, "
                  "dimensions identiques à la Fierce X : non ajoutée, à vérifier). "
                  "Bosse « Mid-Front » du cahier des charges, à confirmer."),
        "sources": [src("atk_z1_coll", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz"]),
                    src("atk_z1_blog", ["length_mm", "width_max_mm", "height_mm"]),
                    src("meckeys_z1", ["length_mm", "width_max_mm", "height_mm"])],
    },
    {
        "id": "atk_a9_plus", "brand": "ATK", "model": "A9 Plus 2.0", "category": "ATK", "family": "A9",
        "shell_id": "atk_a9_large", "budget_tier": "Économique", "length_mm": 125.0, "width_max_mm": 63.5,
        "height_mm": 40.0, "hump_position": "Mid", "button_height": "Mid",
        "palm_grip_fit": "Élevé", "claw_grip_fit": "Élevé", "fingertip_grip_fit": "Moyen",
        "fit_status": "owner_spec", "dimension_status": "verified",
        "price_eur": 45.00, "price_status": "owner_spec_unverified",
        "price_note": "Prix issu du cahier des charges, date de vérification inconnue.",
        "fit_rationale": "Rapport qualité/prix imbattable pour les budgets serrés. Forme 'patate' universelle.",
        "weight_g": 57.0, "polling_hz": 1000,
        "notes": ("Largeur 63.5 mm (cahier des charges) contre 64.0 mm chez EloShapes : écart de 0.5 mm, "
                  "dans la tolérance de concordance (0.5 mm) ; valeur propriétaire conservée. "
                  "Polling 1000 Hz documenté (EloShapes) : pas de bonus haut de gamme."),
        "sources": [src("eso_a9plus", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz"]),
                    src("eso_a9_cmp", ["length_mm", "width_max_mm", "height_mm"])],
    },
    # ----------------------------------------------------------------- ATK : nouvelles références (géométrie vérifiée, grip NON vérifié)
    {
        "id": "atk_phantom_ultimate", "brand": "ATK", "model": "Phantom Ultimate", "category": "ATK", "family": "Phantom",
        "budget_tier": "Haut de Gamme", "length_mm": 119.7, "width_max_mm": 62.5, "height_mm": 37.3,
        "hump_position": "Mid", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "single_source",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié. ATK affiche 99.98 USD (collection, consultée 2026-10-10) : non converti.",
        "fit_rationale": "",
        "weight_g": 44.0, "sensor": "PAW3955 Master", "polling_hz": 8000,
        "notes": "Dimensions d'une seule source (EloShapes). Forme carbone symétrique moyenne. Grip et boutons non vérifiés.",
        "sources": [src("eso_phantom", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz", "hump_position"])],
    },
    {
        "id": "atk_ghost_ultimate", "brand": "ATK", "model": "GHOST Ultimate", "category": "ATK", "family": "Ghost",
        "shell_id": "atk_ghost", "budget_tier": "Qualité-Prix", "length_mm": 121.0, "width_max_mm": 61.3,
        "height_mm": 38.0, "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "single_source",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 48.0, "sensor": "PAW3950 Ultra", "polling_hz": 8000,
        "notes": f"Dimensions d'une seule source (EloShapes). {HUMP_NOTE}",
        "sources": [src("eso_ghost_u", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz"])],
    },
    {
        "id": "atk_ghost_extreme", "brand": "ATK", "model": "GHOST Extreme", "category": "ATK", "family": "Ghost",
        "shell_id": "atk_ghost", "budget_tier": "Qualité-Prix", "length_mm": 121.0, "width_max_mm": 61.3,
        "height_mm": 38.0, "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "single_source",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 48.0, "sensor": None, "polling_hz": None,
        "notes": ("Même coque que le GHOST Ultimate selon la comparaison EloShapes (dimensions identiques). "
                  "Capteur et autonomie non vérifiés. " + HUMP_NOTE),
        "sources": [src("eso_ghost_cmp", ["length_mm", "width_max_mm", "height_mm", "weight_g"])],
    },
    {
        "id": "atk_y9_ultimate", "brand": "ATK", "model": "Y9 Ultimate", "category": "ATK", "family": "Y9",
        "budget_tier": "Haut de Gamme", "length_mm": 125.6, "width_max_mm": 67.5, "height_mm": 43.3,
        "hump_position": "Mid", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "verified",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 55.0, "sensor": "PAW3950 Ultra", "polling_hz": None,
        "notes": ("125.6 × 67.5 × 43.3 mm concordants (EloShapes, MaxGaming, FPSTools). "
                  "Poids 55 g (EloShapes, MaxGaming) contre 58 g (FPSTools) : conflit de poids, sans impact géométrique. "
                  "Polling 8000 Hz (EloShapes, MaxGaming) contre 1000 Hz (FPSTools) : non retenu. "
                  "Forme ergonomique : compatibilité de grip NON vérifiée."),
        "conflicts": {"polling_hz": {"values": [8000, 1000], "sources": ["EloShapes / MaxGaming", "FPSTools"]},
                      "weight_g": {"values": [55, 58], "sources": ["EloShapes / MaxGaming", "FPSTools"]}},
        "sources": [src("eso_y9", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor"]),
                    src("maxg_y9", ["length_mm", "width_max_mm", "height_mm"]),
                    src("fps_y9", ["length_mm", "width_max_mm", "height_mm"])],
    },
    {
        "id": "atk_fierce_x", "brand": "ATK", "model": "Fierce X", "category": "ATK", "family": "Fierce",
        "budget_tier": "Haut de Gamme", "length_mm": 119.57, "width_max_mm": 60.99, "height_mm": 36.26,
        "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "verified",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 42.0, "sensor": "PAW3950 Ultra", "polling_hz": 8000,
        "notes": ("119.57 × 60.99 × 36.26 mm (ATK) concordants à 0.1 mm près avec EloShapes (119.6 × 60.9 × 36.2) "
                  "et MouseMetric. ATK présente la Fierce X comme une souris « claw grip » : indication marketing, "
                  "NON assimilée à une compatibilité « Élevé ». Dimensions identiques à celles attribuées à la Z1 originale : à surveiller."),
        "sources": [src("atk_fierce", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz"]),
                    src("eso_fierce", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz", "hump_position"]),
                    src("mm_fierce", ["length_mm", "width_max_mm", "height_mm"])],
    },
    {
        "id": "atk_u2_v2_ultimate", "brand": "ATK", "model": "U2 V2 Ultimate", "category": "ATK", "family": "U2",
        "budget_tier": "Haut de Gamme", "length_mm": 123.7, "width_max_mm": 64.6, "height_mm": 39.1,
        "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "verified",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 45.0, "sensor": "PAW3950 Ultra", "polling_hz": 8000,
        "notes": "123.7 × 64.6 × 39.1 mm concordants (EloShapes, notice ATK). " + HUMP_NOTE,
        "sources": [src("eso_u2u", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz"]),
                    src("atk_u2_manual", ["length_mm", "width_max_mm", "height_mm"]),
                    src("atk_u2_coll", ["length_mm", "width_max_mm", "height_mm"])],
    },
    {
        "id": "atk_u2_v2_mini", "brand": "ATK", "model": "U2 V2 Mini", "category": "ATK", "family": "U2",
        "budget_tier": "Qualité-Prix", "length_mm": 119.5, "width_max_mm": 63.0, "height_mm": 38.5,
        "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "verified",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 39.0, "sensor": None, "polling_hz": 8000,
        "notes": ("119.5 × 63 × 38.5 mm concordants (EloShapes, notice ATK, collection U2). "
                  "Notice ATK : taille « Small/Medium hands ». Capteur non vérifié. " + HUMP_NOTE),
        "sources": [src("eso_f1_u2m", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz"]),
                    src("atk_u2_manual", ["length_mm", "width_max_mm", "height_mm"])],
    },
    {
        "id": "atk_zero", "brand": "ATK", "model": "ZERO", "category": "ATK", "family": "ZERO",
        "budget_tier": "Qualité-Prix", "length_mm": 120.1, "width_max_mm": 63.2, "height_mm": 38.1,
        "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "single_source",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 39.0, "sensor": None, "polling_hz": 8000,
        "notes": ("Dimensions d'une seule source (EloShapes). Forme symétrique moyenne. " + HUMP_NOTE),
        "sources": [src("eso_zero", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz"])],
    },
    {
        "id": "atk_duckbill", "brand": "ATK", "model": "Duckbill", "category": "ATK", "family": "Duckbill",
        "budget_tier": "Haut de Gamme", "length_mm": None, "width_max_mm": 62.5, "height_mm": 37.4,
        "hump_position": "Rear", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "conflicting",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 46.0, "sensor": "PAW3950 Ultra", "polling_hz": 8000,
        "conflicts": {
            "length_mm": {"values": [118.0, 117.0], "sources": ["EloShapes (118.0)", "ATK Blog (117 mm)"],
                          "note": "Écart de 1.0 mm sur la longueur : valeur non retenue tant que non confirmée."},
            "weight_g": {"values": [46.0, 49.0], "sources": ["EloShapes (46 g)", "ATK Blog (≈49 g)"]},
        },
        "notes": ("Longueur en conflit (118.0 vs 117 mm) : donnée essentielle non retenue, souris en attente. "
                  "Aucune source trouvée annonçant 55 mm de largeur. Largeur 62.5 mm seulement chez EloShapes. "
                  + HUMP_NOTE),
        "sources": [src("eso_duck", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz"]),
                    src("atk_duck_blog", ["length_mm", "height_mm", "weight_g"])],
    },
    {
        "id": "atk_a9_ultimate", "brand": "ATK", "model": "A9 Ultimate", "category": "ATK", "family": "A9",
        "shell_id": "atk_a9_large", "budget_tier": "Qualité-Prix", "length_mm": 125.0, "width_max_mm": 64.0,
        "height_mm": 40.0, "hump_position": "Mid", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "verified",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 53.0, "sensor": "PAW3950 Ultra", "polling_hz": 8000,
        "notes": ("Largeur 64.0 mm (EloShapes) contre 63.5 mm (ATK) : écart 0.5 mm, dans la tolérance de concordance. "
                  "ATK présente l'A9 Ultimate comme « Medium-to-large hands » ; grip non vérifié."),
        "sources": [src("eso_a9u", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz"]),
                    src("atk_a9u", ["length_mm", "width_max_mm", "height_mm", "weight_g", "sensor", "polling_hz"])],
    },
    {
        "id": "atk_a9_air", "brand": "ATK", "model": "A9 Air", "category": "ATK", "family": "A9",
        "shell_id": "atk_a9_large", "budget_tier": "Qualité-Prix", "length_mm": 125.0, "width_max_mm": 64.0,
        "height_mm": 40.0, "hump_position": "Mid", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "single_source",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 47.0, "sensor": None, "polling_hz": 8000,
        "notes": ("Même taille que l'A9 Ultimate selon EloShapes (comparaison directe). Poids différent (47 g) : "
                  "seule la géométrie est partagée. Capteur non vérifié."),
        "sources": [src("eso_a9air", ["length_mm", "width_max_mm", "height_mm", "weight_g", "polling_hz"])],
    },
    {
        "id": "atk_a9_mini", "brand": "ATK", "model": "A9 Mini", "category": "ATK", "family": "A9",
        "budget_tier": "Économique", "length_mm": 118.4, "width_max_mm": 61.2, "height_mm": 38.6,
        "hump_position": "Inconnu", "button_height": "Inconnu",
        "palm_grip_fit": "Inconnu", "claw_grip_fit": "Inconnu", "fingertip_grip_fit": "Inconnu",
        "fit_status": "unverified", "dimension_status": "single_source",
        "price_eur": None, "price_status": "unknown",
        "price_note": "Aucun prix EUR vérifié.", "fit_rationale": "",
        "weight_g": 39.0, "sensor": None, "polling_hz": None,
        "notes": "Dimensions d'une seule source (ATK, fiche produit). Bosse, boutons et grip non vérifiés.",
        "sources": [src("atk_a9u", ["length_mm", "width_max_mm", "height_mm", "weight_g"])],
    },
]

# Le placeholder ci-dessus n'est pas utilisé : on normalise les champs « Inconnu » explicitement.
for m in mice:
    if m.get("button_height") in (None, ""):
        m["button_height"] = "Inconnu"
    m.setdefault("notes", "")
    m.setdefault("sources", [])

out = ROOT / "data" / "mouse_db.json"
out.write_text(json.dumps(mice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(mice)} entrées écrites dans {out}")
