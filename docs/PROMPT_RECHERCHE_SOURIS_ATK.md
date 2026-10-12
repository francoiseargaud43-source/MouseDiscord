# Pack IA — faire enrichir le catalogue par une IA (recherche de souris ATK/Scyrox)

Ce document contient **tout ce qu'il faut donner à une IA de recherche** pour qu'elle comprenne le fonctionnement du bot
et qu'elle produise des fiches souris directement classables par le moteur, sans rien inventer.

Sommaire : [1. Ce qu'il faut donner](#1-ce-quil-faut-donner-à-lia) · [2. Créer le pack](#2-créer-le-pack-en-une-commande)
· [3. Le prompt à copier-coller](#3-le-prompt-à-copier-coller) · [4. Annoter la vidéo et les captures](#4-annoter-la-vidéo-et-les-captures)
· [5. Après la réponse de l'IA](#5-après-la-réponse-de-lia) · [6. Règles non négociables](#6-règles-non-négociables)

---

## 1. Ce qu'il faut donner à l'IA

**Ne donnez pas tout le dépôt** : c'est inutile et cela noie l'information. Donnez le **pack** décrit ci-dessous (§2), qui
contient exactement :

| Fichier | Pourquoi l'IA en a besoin |
|---|---|
| `docs/PROMPT_RECHERCHE_SOURIS_ATK.md` | **Le prompt** (ce document) : mission, règles, format de sortie |
| `data/mouse_db.json` | Le catalogue actuel (26 souris) : format réel, valeurs déjà connues, identifiants à ne pas réutiliser |
| `docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md` | Ce que la vidéo Oblivity ajoute (largeur au capteur, évasement arrière, poids) et les améliorations en attente |
| `docs/audit/CATALOGUE_ATK.md` | Les 23 produits ATK déjà étudiés et les **décisions de non-ajout** (Z1 originale, Duckbill, doublons) : évite de reproposer ce qui a été écarté |
| `docs/audit/matrice_profils.md` | Comment chaque souris obtient son score (profils Palm/Claw/Fingertip) : montre ce qui compte vraiment |
| `README.md` | Comment le bot fonctionne (parcours, score, modes, sources) — section « Moteur de scoring » incluse |
| `utils/matcher.py` | Le barème exact (40 points) et les plages cibles |
| `utils/selection.py` | Les modes de sélection (Économique, Qualité/Prix, Haut de Gamme, Budget perso) |
| `utils/models.py` | Le vocabulaire autorisé (`Élevé/Moyen/Faible/Inconnu`, `Low/Mid/High`, `Front/Mid/Rear`…) |
| `utils/catalog.py` | La validation réelle du catalogue : l'IA comprendra ce qui est **refusé** |
| `ids_existants.txt` (généré) | Liste des identifiants et libellés déjà pris |

**À ne jamais donner** : `.env` (token Discord), `state/`, vos liens d'affiliation, ni le dossier `.venv`. Le script du
§2 ne les inclut pas.

---

## 2. Créer le pack en une commande

Depuis la racine du projet :

```bash
python tools/build_ai_bundle.py
```

Résultat : **`pack_ia_mousediscord.zip`** à la racine du projet (ignoré par Git), prêt à être joint à la conversation
avec l'IA. Le script affiche la liste des fichiers inclus.

Vous pouvez aussi ne rien zipper : joignez simplement les fichiers listés au §1 à votre message (l'IA lira le contenu).

**Ce que vous joignez en plus du pack :**

1. **La/les vidéo(s) YouTube** : mettez les **liens** dans votre message (l'IA les ouvre) — voir §4 pour ce qu'il faut y
   lui demander d'extraire.
2. **Vos captures Discord** (`ImageAct/`) : le parcours actuel et un résultat, pour qu'elle voie comment les données
   sont utilisées.
3. Les **images produit** ou pages que vous avez déjà (facultatif).

---

## 3. Le prompt à copier-coller

> Copiez **tout le bloc ci-dessous** dans votre message, juste après les fichiers joints et les liens vidéo.
> Ce prompt est autonome : l'IA n'a besoin d'aucun autre contexte.

```text
RÔLE
Tu es un documentaliste technique spécialisé en souris gaming. Tu produis des fiches produit SOURCÉES,
destinées à une base de données qui note la compatibilité entre une forme de souris et la main d'un joueur.

CONTEXTE TECHNIQUE (lis les fichiers joints avant de commencer)
- Le bot « AzeMouse Mouse Shape Finder » recommande une souris selon : la prise (Palm / Claw / Fingertip),
  deux mesures de la main (longueur, largeur sans le pouce) et une gamme de prix.
- Moteur : `utils/matcher.py` note 40 points maximum :
  * longueur (10 / 5 / 0) : plage cible = 71.4 + longueur_main × 0.2633 → +5.0 mm (Palm/Claw) ;
    en Fingertip, pas de minimum, seule la borne haute compte ;
  * largeur de prise (10 / 5 / 0) : plage cible = 48.4 (Palm/Claw) ou 47.3 (Fingertip) + largeur_main × 0.08,
    puis +4.0 mm (Palm/Claw) ou +3.9 mm (Fingertip). Sans largeur de prise mesurée, le moteur utilise
    `width_max_mm − 3.0` (estimation provisoire) ;
  * compatibilité de prise (10 / 5 / exclusion) : `Élevé` / `Moyen` / `Faible` / `Inconnu` ;
  * position de la bosse (5 / 0) : idéale = Palm → {Front, Mid}, Claw → {Mid, Rear}, Fingertip → ignorée ;
  * hauteur des boutons (5 ou 10 / 0) : idéale = Palm → {High} · Claw → {Low} · Fingertip → {Low, Mid} (règle unique des quatre documents normatifs).
- Une donnée absente vaut « Inconnu » : la souris sort alors du classement (« à vérifier ») au lieu de recevoir un
  score inventé. C'est un comportement VOULU.
- Mode « Haut de Gamme » : +1 si `polling_hz` ≥ 8000 est documenté, +1 si `sensor` ∈ {PAW3950, PAW3950 Ultra,
  PAW3955, PAW3955 Master}.

MISSION
1) Compléter les fiches EXISTANTES dont les compatibilités sont « Inconnu » (les 12 variantes ATK du catalogue).
2) Rechercher les souris ATK (et Scyrox) RÉCENTES absentes du catalogue, avec leurs données vérifiables.
3) Pour chaque souris retenue, fournir une fiche JSON prête à coller dans `data/mouse_db.json`.

SOURCES — RÈGLE CENTRALE
- Chaque valeur doit venir d'une source consultable, avec son URL et la date de consultation (AAAA-MM-JJ).
- Une dimension n'est `verified` que si AU MOINS DEUX sources indépendantes concordent à ≤ 0.5 mm près.
  Sinon : `single_source` (une seule source) ou `conflicting` (désaccord : alors `length_mm`/`width_max_mm` = null
  et le conflit est documenté dans `conflicts`).
- Utilise par priorité : site officiel ATK (fiches produit et pages « shape/dimensions »), bases de formes
  (EloShapes), fiches revendeurs, tests et vidéos documentées (dont les vidéos fournies par l'utilisateur).
- **EloShapes donne des champs de forme à relever systématiquement** : `Hump placement` (Center / Back - minimal /
  moderate / aggressive…), `Front flare`, `Side curvature`, `Thumb rest`, `Ring finger rest`. Reporte-les tels quels :
  la correspondance vers le schéma (`Center → Mid`, `Back - … → Rear`) est appliquée par le projet, pas par toi.
- **Largeur de prise** : les fabricants et EloShapes publient la largeur MAXIMALE (souvent déformée par l'évasement
  arrière). Ne l'utilise JAMAIS comme largeur de prise : si une source donne une largeur mesurée **au niveau du
  capteur**, indique-la à part (`grip_width_measured_mm` + source), sinon laisse la case vide.
- **Poids, capteur, taux de sondage** : à documenter (le poids est affiché, jamais noté ; capteur ≥ 8000 Hz et PAW3950/3955
  donnent un bonus en mode « Haut de Gamme »).
- **Disponibilité et prix** : indique si le produit est encore vendu sur le store officiel (`store_listed`, `store_url`)
  et le prix **dans sa devise d'origine**, en précisant la devise. Un prix en dollars **n'est pas** un prix en euros.
- Les vidéos YouTube que je te fournis servent à documenter ce qui n'est pas écrit ailleurs : forme réelle,
  position de la bosse, hauteur des boutons, ressenti de prise. Indique pour chacune l'auteur, le titre et le lien,
  et le minutage précis quand tu en tires une information (ex. « 04:12 — la bosse est clairement à l'arrière »).

INTERDICTIONS ABSOLUES
- N'invente AUCUNE valeur, aucune compatibilité, aucune source. Une valeur non trouvée s'écrit « Inconnu »
  (ou `null` pour une dimension non vérifiée, avec une note).
- Ne convertis JAMAIS un prix USD en euros : si le prix n'est PAS documenté en euros chez un revendeur,
  `price_eur` reste `null` et tu l'expliques dans `price_note`.
- Ne crée aucun lien d'affiliation, aucun prix promo ponctuel, aucune valeur « estimée au feeling ».
- Ne déduis pas la compatibilité d'une prise uniquement de la forme : sans source qui l'affirme explicitement,
  la valeur est « Inconnu ».
- Ne propose pas une souris déjà écartée dans `docs/audit/CATALOGUE_ATK.md` sans le signaler explicitement et
  expliquer ce qui a changé.
- Ne modifie pas les souris déjà présentes dans le catalogue (leurs valeurs ont été validées par le propriétaire) :
  tu peux seulement PROPOSER des compléments, en les listant à part.

VOCABULAIRE AUTORISÉ (toute autre valeur fait échouer la validation du catalogue)
- `budget_tier` : "Économique" | "Qualité-Prix" | "Haut de Gamme"
- `hump_position` : "Front" | "Mid" | "Rear" | "Mid-Front" | "Mid-Rear" | "Any" | "Inconnu"
- `button_height` : "Low" | "Mid" | "High" | "Inconnu"
- `palm_grip_fit`, `claw_grip_fit`, `fingertip_grip_fit` : "Élevé" | "Moyen" | "Faible" | "Inconnu"
- `dimension_status` : "verified" | "single_source" | "conflicting" | "owner_spec" | "owner_spec_unverified"
- `price_status` : "verified" | "owner_spec_unverified" | "unknown"
- `fit_status` : "owner_spec" (uniquement cahier des charges du propriétaire) | "unverified" (tout le reste)

FORMAT DE SORTIE ATTENDU
(1) Un tableau récapitulatif : souris proposée · dimensions L×l×H · poids · capteur · polling · bosse · boutons ·
    compatibilités Palm/Claw/Fingertip · prix et devise · nombre de sources · statut proposé.
(2) Puis, pour CHAQUE souris, un objet JSON complet, dans ce format exact :

{
  "id": "atk_exemple_ultra",
  "brand": "ATK",
  "model": "Exemple Ultra",
  "category": "ATK",
  "family": "Exemple",
  "budget_tier": "Qualité-Prix",
  "length_mm": 121.5,
  "width_max_mm": 62.0,
  "height_mm": 38.5,
  "grip_width_mm": null,
  "shell_id": null,
  "hump_position": "Rear",
  "button_height": "Low",
  "palm_grip_fit": "Inconnu",
  "claw_grip_fit": "Moyen",
  "fingertip_grip_fit": "Élevé",
  "fit_status": "unverified",
  "fit_rationale": "Une phrase courte expliquant la forme, appuyée par une source.",
  "dimension_status": "verified",
  "price_eur": null,
  "price_status": "unknown",
  "price_note": "Prix constructeur en USD (79.99 $), non converti : aucun prix EUR documenté.",
  "weight_g": 47.0,
  "sensor": "PAW3950 Ultra",
  "polling_hz": 8000,
  "store_listed": true,
  "store_url": "https://www.atk.store/products/…",
  "elo_shapes": {"hump_placement": "Back - moderate", "front_flare": "Outward - slight", "side_curvature": "Inward"},
  "grip_width_measured_mm": null,
  "conflicts": {},
  "sources": [
    {"label": "ATK — fiche officielle", "url": "https://…", "fields": ["length_mm", "width_max_mm", "weight_g"], "date_checked": "AAAA-MM-JJ"},
    {"label": "EloShapes — forme", "url": "https://…", "fields": ["hump_position", "button_height"], "date_checked": "AAAA-MM-JJ"}
  ],
  "notes": "Ce qui reste à confirmer, et par qui."
}

RÈGLES DE REMPLISSAGE
- `width_max_mm` est OBLIGATOIRE (largeur maximale de la coque, pas la largeur de prise).
- `grip_width_mm` / `grip_width_measured_mm` restent `null` sauf mesure réelle au niveau du capteur (règle du projet :
  aucune largeur de prise estimée n'est écrite dans le catalogue).
- `length_mm` ou `width_max_mm` à `null` : uniquement si les sources se contredisent, ET le conflit est décrit ainsi :
  "conflicts": {"length_mm": {"values": [118.0, 117.0], "sources": ["https://…", "https://…"]}}
- `dimension_status = "verified"` ou `"single_source"` ⇒ `sources` non vide (au moins une source pour `single_source`,
  au moins deux concordantes pour `verified`).
- `price_status = "verified"` ⇒ `price_eur` renseigné ; sinon `price_status` = "unknown" ou "owner_spec_unverified".
- `fit_status` = "unverified" pour tout ce que tu trouves sur le web (seul le propriétaire pose "owner_spec").
- `id` : minuscules, préfixe de marque, underscore, jamais un identifiant déjà présent dans `ids_existants.txt`.
- `fit_rationale` : UNE phrase, factuelle, sans superlatif marketing.
- Si tu hésites entre deux valeurs : mets « Inconnu » et explique dans `notes`.

CE QUE TU DOIS AJOUTER À LA FIN
(3) La liste des sources utilisées avec leur date de consultation, et, pour chacune, les champs qu'elle couvre.
(4) La liste explicite de ce que tu n'as PAS pu documenter (avec la raison), pour que je sache quoi vérifier.
(5) Aucune conclusion commerciale, aucun lien d'achat, aucune recommandation d'achat : uniquement des faits sourcés.
```

---

## 4. Annoter la vidéo et les captures

Dans votre message, accompagnez les liens vidéo d'une demande précise :

```text
Pour chaque vidéo fournie, extrais et cite avec minutage : forme générale de la coque, position de la bosse
(avant / milieu / arrière), hauteur des boutons (bas / moyens / hauts), poids annoncé, capteur, taux de
sondage (polling), et toute phrase où le testeur parle de la prise (Palm, Claw, Fingertip), du confort de la
main ou de l'arrière de la souris. Si une information est contredite par une source écrite, signale le conflit.
```

Et précisez le contexte de vos captures :

```text
Les captures jointes montrent le parcours actuel du bot (prise, thénar informatif, mesures, budget, résultat,
« à vérifier »). Elles montrent comment chaque donnée est affichée : ne propose rien qui contredise ces règles
(par exemple, aucune donnée de thénar n'est utilisée dans le score, et la prise Fingertip ne pose pas la
question du thénar).
```

---

## 5. Après la réponse de l'IA

1. **Contrôle de cohérence** : chaque valeur doit avoir sa source ; refusez toute fiche sans URL.
2. **Intégration** : collez les nouveaux objets à la fin de la liste de `data/mouse_db.json` (après la dernière souris).
3. **Vérification technique** (obligatoire — la validation du catalogue refuse ce qui est inventé ou mal formé) :

   ```bash
   python tools/check_deployment.py     # catalogue lisible ? 0 erreur(s) bloquante(s) ?
   pytest -q                            # la suite de tests doit rester verte
   python tools/compare_profiles.py     # régénère docs/audit/matrice_profils.md
   ```

   Si `check_deployment.py` affiche `data/mouse_db.json invalide : …`, le message indique la souris et le champ
   fautifs (vocabulaire hors liste, source manquante, conflit incomplet…).
4. **Nouvelles souris et classement** : une souris dont les compatibilités de prise sont « Inconnu » apparaît dans
   « À vérifier (non classées) », jamais dans le classement — c'est voulu.
5. **Liens d'achat** : à ajouter **vous-même** dans `data/commercial_links.json` (clé = `id` de la souris), jamais par l'IA.
6. **Après transfert sur le serveur** : `pkill -f "bot.py"` (§7.7 du guide de déploiement) — le catalogue et les images
   sont relus à chaud, mais un fichier JSON invalide bloque les parcours jusqu'à correction.

---

## 6. Règles non négociables

| Règle | Pourquoi |
|---|---|
| Aucune valeur inventée, tout est sourcé et daté | Une valeur plausible mais fausse se propage dans tous les scores |
| Deux sources concordantes à ≤ 0.5 mm pour « verified » | C'est le seuil déjà appliqué aux 12 variantes ATK du catalogue |
| Prix en euros uniquement s'ils sont documentés en euros | Aucune conversion ne doit être faite (règle du projet) |
| `grip_width_mm` laissé `null` | Cette donnée exige une mesure réelle, pas une estimation de catalogue |
| Compatibilités de prise en « Inconnu » sans source explicite | La forme ne prouve pas le confort de prise |
| Aucun lien commercial | `data/commercial_links.json` reste sous contrôle du propriétaire |
| Les souris validées ne sont pas modifiées | Le barème et les valeurs existantes sont testés (non-régression) |
| Les champs de forme (bosse, flare, courbure) sont recopiés tels quels | La conversion vers le schéma du bot est une décision du projet, pas de la source |
| Un prix en dollars n'est jamais un prix en euros | Les modes « Économique », « Qualité-Prix » et « Budget perso » exigent un prix EUR **documenté** |
