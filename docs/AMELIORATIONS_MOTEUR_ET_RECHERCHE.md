# Oblivity « The Scientific Way to Pick A Mouse » — analyse, veille produits et améliorations

Document de travail du **2026-10-11**. Il répond à trois questions :

1. Que dit la vidéo d'Oblivity, et qu'est-ce que cela change pour **notre** moteur ?
2. Quelles souris ATK/VXE **encore vendues** manquaient au catalogue, et lesquelles ont été ajoutées ?
3. Quelles améliorations sont justifiées — et sous quelle forme (données, présentation, ou moteur) ?

> Sources vidéo : <https://www.youtube.com/watch?v=sUkxQ5Vre28> — *« The Scientific Way to Pick A Mouse »*, chaîne **Oblivity**,
> publiée le **2026-10-02**, 16:20 (titre alternatif affiché par YouTube : *« Your Mouse Probably Doesn't Fit Your Hand | Mouse Guide »*).
> Transcript complet lu le 2026-10-11. Leur outil : *Oblivity Mouse Finder Tool*, sur leur serveur Discord.

---

## 1. Ce que dit la vidéo (minutages) et ce que ça confirme chez nous

| Minutage | Contenu de la vidéo | Notre moteur |
|---|---|---|
| **3:19 — Standards** | Les index doivent tomber **au milieu des clics**, au-dessus des switches ; le pouce **au milieu du flanc, parallèle au capteur** ; une souris trop longue met les index à l'arrière des clics ; trop courte, on courbe les doigts à l'extrême | ❌ **Non exploité** : critère de confort, non mesurable sans essai. Notre moteur approxime par la **longueur** et la **largeur de prise** |
| **3:19 — Largeur** | La largeur pertinente n'est **pas** la largeur maximale du fabricant : elle est prise **au niveau du capteur**, là où le pouce et l'auriculaire touchent. Le store mesure au point le plus large, déformé par l'évasement arrière | ✅ **Confirmé** : notre champ `grip_width_mm` = « largeur de prise **mesurée** », et notre estimation par défaut (`width_max − 3 mm`) compense exactement ce biais. La vidéo justifie enfin ce −3 mm |
| **9:13 — Rear design** | L'**évasement arrière** (le « cul » de la souris) couvre les muscles thénars : plus il est large, moins la paume se courbe, moins on a de mobilité. Les formes « safe » (GPX, Viper V3) n'ont **pas** d'évasement arrière | ✅ **Cohérent avec le thénar informatif** (on ne score pas) et avec la T13 « Arrière étroit » ; pourrait devenir un champ (voir I2) |
| **9:13 — Bosse** | Le placement de la bosse dépend de la prise : **milieu ou arrière → Claw** (soutient l'arche de la main), **avant → Palm** (suit l'effilement naturel de la main) | ✅ **Identique** à `HUMP_IDEAL` : Palm → {Front, Mid}, Claw → {Mid, Rear}, Fingertip → ignorée |
| **9:13 — Boutons** | **Claw → boutons bas** (sinon les tendons extenseurs travaillent en permanence) ; **Palm → boutons hauts** (doigts posés à plat) | ✅ **Identique** à `BUTTON_IDEAL` : Claw → {Low, Mid}, Palm → {High}, Fingertip → Low |
| **11:21 — Poids** | 2 études (poids 50/60/90/100 g) : **4 % plus rapide et 9 % plus précis** en léger. Leur propre test (980 runs) : 42 g bat 77 g de **3,6 %** ; une souris de 21 g bat les deux (5,2 % et 1,62 %). **Pas de poids idéal**, mais le léger gagne à tous les coups | ❌ **Non pris en compte** : `weight_g` est stocké mais n'entre dans aucun score (voir I3) |
| **15:02 — Optimum** | Une souris trop légère est **moins stable** (les tremblements humains se voient plus) | 🔎 Nuance à retenir : le poids est un compromis, pas une note |

### 1.1 Bonne nouvelle : notre équation de longueur reproduit leur outil

Le vidéaste donne son cas : **main de 18,4 cm → souris de 120 à 125 mm** (prise Claw).

Notre moteur, même main (184 mm, prise Claw) : `71,4 + 184 × 0,2633 = 119,8 mm` → plage **119,8 – 124,8 mm**.

**Écart : 0,2 mm** — alors que leur plage vient d'une **bande statistique à 90 %** sur 40 participants
et la nôtre d'une droite linéaire. Les deux méthodes convergent, ce qui valide notre équation de longueur.

### 1.2 Ce que la vidéo ne tranche pas

- La **largeur idéale** : leur outil l'affiche mais on ne connaît pas la largeur de main de leur exemple
  → impossible de comparer nos 55,6–59,6 mm (main 90 mm) à leur 57–61 mm. À creuser via tes tests (§4).
- Le **poids** ne donne lieu à **aucun** seuil chiffré (« il n'y a pas de poids idéal »).
- La **prise Fingertip** n'est pas traitée spécifiquement dans leurs recommandations de forme
  (leur outil demande la prise, mais les 3 critères de forme présentés sont surtout Palm/Claw).

---

## 2. Veille produits : souris ATK/VXE encore vendues (atk.store, 2026-10-11)

La collection officielle <https://www.atk.store/fr-fr/collections/souris> liste **23 produits** (22 en stock).
Croisées avec `data/mouse_db.json`, **8 souris encore vendues manquaient** : elles ont été ajoutées
(sources ATK Store + EloShapes + revendeurs, cf. `docs/audit/CATALOGUE_ATK.md` §4).

| Ajout | Dimensions (mm) | Poids | Bosse (EloShapes → schéma) | Prix store (USD) | Intérêt |
|---|---|---|---|---|---|
| **VXE Dragonfly V3 / V3 Pro** | 116,6 × 62,2 × 38,2 | 49–54 g | Back-moderate → **Rear** | dès 14,98 $ | **Seule « Small » du catalogue** : comble le trou des mains < 175 mm |
| **VXE Dragonfly R1 / R1 Pro** | 120,6 × 64,0 × 37,8 | 51 g | Back-moderate → **Rear** | dès 14,98 $ | Profil « safe » sans évasement (flancs plats), très diffusé |
| **VXE MAD R / Major** | 120,1 × 63,1 × 38,1 | 36 g | Back-moderate → **Rear** | dès 44,98 $ | Même coque que l'ATK ZERO déjà au catalogue, mais moins cher |
| **VXE Dragonfly X3 / X3 Pro / Turbo** | 127,0 × 64,0 × 40,0 | 51–54 g | *inconnue* (pas de fiche EloShapes) | dès 29,98 $ | Grande symétrique (coque X1), sortie octobre 2026 |
| **ATK Blazing Sky U2 Mini** | 119,5 × 63,0 × 38,5 | 38 g | Back-minimal → **Rear** | 84,98 $ | Compacte ultralégère, 8K |
| **ATK Dragonfly A9 NB Ultra** | 125,0 × 63,5 × 40,0 | 56 g | Mid (coque A9) | 79,98 $ | Coque A9 pleine taille + station de charge |
| **ATK Blazing Sky F1 V2** | 118,2 × 62,4 × 38,8 | 38–39 g | Mid (coque F1) | dès 44,98 $ | Génération précédente de la F1 V3, moins chère |
| **ATK Blazing Sky U2** (base) | 123,7 × 64,6 × 39,1 | 49–55 g | **Rear** | dès 24,98 $ | Entrée de gamme de la famille U2 |

**Règles appliquées** (identiques à celles du catalogue existant) :

- **Aucune compatibilité de prise inventée** : les mentions « Claw / Palm » de l'éditeur ne sont pas converties en
  `Élevé/Moyen/Faible`. Les 8 souris sont donc `fit_status = "unverified"` → elles apparaissent en
  « À vérifier (non classées) » et **ne sont jamais recommandées** tant que tu n'as pas validé leurs compatibilités.
- **Aucun prix en euros inventé** : le store vend en dollars → `price_eur = null` + `price_note`.
  Conséquence réelle : **elles n'entrent pas** dans les modes Économique / Qualité-Prix / Budget personnalisé
  (ces modes exigent un prix connu). Voir **I4** ci-dessous.
- **`budget_tier`** est déduit de la bande de prix du store (< 50 $ = Économique, 50–100 $ = Qualité-Prix, > 100 $ = Haut de Gamme).
  C'est une **règle nouvelle**, inventoriée ici : à valider ou remplacer par tes prix réels.
- La correspondance EloShapes → schéma (déjà utilisée par le catalogue) est appliquée telle quelle :
  `Center → Mid`, `Back - minimal/moderate/aggressive → Rear`.

**Reste à faire pour ces 8 souris** (c'est toi qui as la main, et c'est rapide) : renseigner pour chacune
1) compatibilité Palm, 2) compatibilité Claw, 3) compatibilité Fingertip, 4) hauteur des boutons.
Les sources disent « hauteur de boutons » pour aucune d'entre elles → `Inconnu` aujourd'hui, ce qui suffit à les rendre non classables.

---

## 3. Leur outil vs le nôtre

| | Oblivity Mouse Finder Tool | AzeMouse `!setup_finder` |
|---|---|---|
| Canal | Bot Discord, dans **leur** serveur, via un salon de tickets | Bot Discord, **ton** serveur, `!setup_finder` |
| Entrées | Prise + longueur + largeur de main, puis **choix visuel** (« quelle image ressemble à ta paume ? ») | Prise → (thénar, informatif) → longueur + largeur (formulaire) → budget + mode |
| Sortie | **Un fil (thread) privé** par utilisateur, avec la **plage de taille idéale** (longueur + largeur) | **Deux embeds** mis à jour en place : recommandation (score /40, %, confiance), alternative, « pourquoi ce choix », « à vérifier » + repères de taille + illustrations + liens |
| Suite | « Informations additionnelles » de forme : **rear design, hump placement, button height**, puis comparaison de souris sur EloShapes | Modes commerciaux (Économique / Qualité-Prix / Haut de gamme / Budget perso), catalogue local, exclusions motivées |
| Base de données | Renvoie vers EloShapes (mesures manuelles pour la largeur au capteur) | Catalogue local **sourcé et tracé** (`data/mouse_db.json` + sources datées) |

**Ce qui nous distingue** : catalogue tracé (sources datées, statuts `verified`/`conflicting`), exclusions **expliquées**
(longueur/largeur/compatibilité), modes de prix, illustrations, et **aucune donnée inventée**.
**Ce qu'ils font mieux** : ils expliquent le *pourquoi* biomécanique (index sur les switches, courbure de la paume) et
ils donnent une plage **par prise** issue d'un échantillon — utile pour convaincre, pas pour scorer.

---

## 4. Tests à faire sur leur bot (et ce que tu me renvoies)

Fais les parcours ci-dessous dans **leur** serveur Discord (lien dans la description de la vidéo), puis colle-moi les réponses :

1. **Ton gabarit, 3 fois** — avec tes mesures réelles de main (longueur, largeur) : une fois en **Palm**, une fois en
   **Claw**, une fois en **Fingertip** → note les **plages de longueur et de largeur** affichées pour chaque prise.
2. **Les 3 infos de forme** qu'ils donnent pour chaque prise (rear design / hump / button height) → recopie le texte exact.
3. **Demande-leur explicitement** (si l'outil le permet) : *hump avant, milieu ou arrière ? boutons bas, moyens ou hauts ?*
   → c'est ce qui manque à nos 8 nouvelles souris.
4. **Leur liste de souris** proposée pour tes plages (s'il y en a une) → on comparera avec notre classement.
5. **Captures d'écran** de chaque réponse (et le message exact), comme tu l'as fait pour ton bot.

Ce que j'en ferai : si leurs plages par prise **s'écartent** des nôtres, je te produis la comparaison chiffrée et,
si le moteur doit bouger, un prompt **uniquement** sur le point concerné (avec tests de non-régression).
Si elles **concordent**, on garde le moteur tel quel — c'est le scénario le plus probable vu le §1.1.

---

## 5. Améliorations proposées (classées par rapport bénéfice/risque)

### I1 — Remplir `grip_width_mm` (largeur de prise mesurée) — **priorité 1, données uniquement**
Aujourd'hui, sans mesure, le moteur estime `largeur_max − 3,0 mm` (marqué « provisoire » dans le résultat).
La vidéo donne la méthode : mesurer la largeur **au niveau du capteur**.
- **Ta souris** (Scyrox V6/V8, F1 V3…) : une mesure au réglet/pied à coulisse suffit → `grip_width_mm` = valeur réelle.
- **Les autres** : mesure sur une capture EloShapes, à l'échelle (leur site n'ayant pas cette donnée).
- Effet : le libellé du résultat passe de « estimée (coque − 3 mm, provisoire) » à « mesurée » → confiance 🟢 plus souvent.
- **Aucun changement de code** : le champ existe déjà.

### I2 — Nouveau champ `rear_flare` (évasement arrière) — schéma v3, **affichage seulement**
La vidéo en fait un critère de confort (mobilité du thénar). EloShapes expose déjà un axe proche (« Front flare », courbure des flancs).
Proposition : ajouter `rear_flare` ∈ {`Aucun`, `Léger`, `Modéré`, `Marqué`, `Inconnu`} + affichage dans l'embed 2
(« Évasement arrière : Léger — mobilité du thénar préservée »). **0 point, 0 exclusion** : informatif, comme le thénar.
Impact moteur : nul (champ non lu par `utils/matcher.py`).

### I3 — Afficher le poids (et le capteur) — **affichage seulement**
`weight_g`, `sensor`, `polling_hz` sont déjà stockés mais invisibles dans le résultat.
Proposition : une ligne dans l'embed 2 (« Poids 36 g · PAW3955 Master · 8000 Hz ») + rappel que **le poids ne modifie pas
le score** (la vidéo ne fixe aucun seuil). Si tu veux **scorer** le poids un jour, il faudra une décision explicite :
le barème passerait de 40 à 45 points et **tous** les scores de référence changeraient → à ne pas faire par effet de bord.

### I4 — Prix en euros **et** disponibilité — **priorité 2, données**
Deux manques que la veille a mis en évidence :
- Les 8 nouvelles souris n'ont **pas de prix EUR** → invisibles dans 3 des 4 modes. Solution : trouver des prix
  documentés en euros (revendeur FR/UE réel), **jamais** par conversion du dollar.
- Un champ `store_listed` + `store_url` permettrait d'afficher « encore vendue sur le store officiel »
  (et d'éviter de recommander un modèle retiré du catalogue).

### I5 — Présentation du résultat (embeds) — **faible risque**
1. **Embed 2 autoportant** : y répéter la prise et les mesures de main (« Prise Fingertip · main 180 × 100 mm »),
   pour qu'il reste compréhensible quand il est partagé seul (aujourd'hui l'info n'est que dans l'embed 1).
2. **Compteur de classement** : « 9 souris classées sur 26 » dans la ligne « À vérifier », pour montrer que le
   catalogue est plus large que le classement (utile maintenant que les non-classées passent de 11 à 19).
3. **Une seule mention « indicateur provisoire »** : elle apparaît aujourd'hui dans l'embed 1 (footer) et dans
   « Pourquoi ce choix ? » → garder celle de l'embed 1.
4. **Détail des raisons d'attente** : quand plus de 8 souris sont en attente, le message actuel est une phrase globale ;
   ajouter la répartition (« 12 sans compatibilité de prise, 5 sans hauteur de boutons, 2 sans bosse ») aide à savoir
   quoi compléter en priorité.

### I6 — Ce que je **ne** propose pas (et pourquoi)
- **Changer le barème** (bosse, boutons, largeur) : la vidéo **confirme** nos règles actuelles (§1) → aucun motif.
- **Notes « biomécaniques »** (index sur les switches, courbure de la paume) : non mesurables sans photo de ta main
  sur chaque souris ; les ajouter reviendrait à inventer une note.
- **Migrer vers une plage statistique** type « bande à 90 % » : nous n'avons que 40 participants chez eux, pas de données
  propres → notre droite linéaire est plus honnête (et coïncide à 0,2 mm, cf. §1.1).

---

## 6. Prompt d'amélioration (v1 — à affiner après tes tests du §4)

> Copie ce bloc tel quel dans la conversation d'implémentation (le dépôt doit être ouvert dans le même espace de travail).
> Coche / supprime les points que tu ne veux pas.

```text
CONTEXTE
Dépôt MouseDiscord (bot Discord AzeMouse). Lis d'abord docs/MASTER_PROMPT_AZEMOUSE.md (contrat non négociable),
puis docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md (analyse de la vidéo Oblivity sUkxQ5Vre28 et veille produits).
Le moteur (utils/matcher.py, utils/selection.py, utils/models.py, utils/session.py, utils/validation.py) NE DOIT PAS
changer de comportement sauf si un point ci-dessous le demande explicitement.

MISSION — applique uniquement les points cochés :

[ ] I1 — grip_width_mm : pour chaque souris du catalogue, si une largeur de prise MESURÉE est documentée, la renseigner
    (champ existant, aucune autre modification). Sinon ne rien mettre : l'estimation « largeur_max − 3 mm » reste.
    Ajoute dans docs/audit/CATALOGUE_ATK.md la méthode de mesure utilisée (au niveau du capteur, cf. vidéo 3:19) et sa source.
[ ] I2 — champ rear_flare (Aucun / Léger / Modéré / Marqué / Inconnu) : ajoute-le au dataclass Mouse (défaut "Inconnu"),
    à la validation du catalogue (valeurs autorisées + migration douce : clé absente = "Inconnu"), et AFFICHE-LE dans
    l'embed « Repères de taille » avec une phrase informative. AUCUN point, AUCUNE exclusion : utils/matcher.py ne doit pas le lire.
[ ] I3 — affichage poids/capteur/polling : une ligne « Poids … · capteur … · taux de sondage … » dans l'embed 2, avec la
    mention que le poids ne modifie pas le score. Ne pas toucher au barème.
[ ] I4 — disponibilité et prix : ajoute les champs store_listed (booléen) et store_url (URL du store officiel) au catalogue,
    affiche « Encore vendue sur le store officiel » quand store_listed est vrai. N'invente AUCUN prix : si un prix EUR
    vérifié n'existe pas, price_eur reste null.
[ ] I5 — présentation : (1) embed 2 autoportant (prise + longueur/largeur de main), (2) ligne « X souris classées sur Y »
    dans « À vérifier », (3) une seule mention « indicateur provisoire » (footer de l'embed 1), (4) répartition des raisons
    d'attente quand plus de 8 souris sont en attente.

CONTRAINTES
- Aucune régression : pytest -q doit rester vert (mettre à jour les tests qui contraignent le format, jamais les supprimer).
- pyflakes propre ; tools/privacy_scan.py → 0 ; outils et docs en français.
- Tout ce qui touche au résultat reste ephemeral sauf la bannière publique.
- docs/REPORTE_DESIGN.md et README.md mis à jour si l'affichage change ; docs/audit/* si les données changent.
- Ne crée aucun lien commercial, aucun prix inventé, aucune compatibilité de prise inventée.

LIVRABLE
Un commit par point coché, avec message explicite, et un résumé final : fichiers touchés, tests, captures d'écran si l'affichage change.
```

---

## 7. Ce qu'il me manque de toi pour finir

1. **Les réponses de leur bot** (§4) — surtout les plages par prise pour ton gabarit et leur texte sur bosse/boutons.
2. **Ta mesure de largeur de prise** sur les souris que tu possèdes (I1) — au réglet, au niveau du capteur.
3. **Tes prix en euros** (ou l'autorisation de chercher) pour les 8 nouvelles souris (I4).
4. **Le choix des points** à implémenter (I1 → I5) : je peux tout faire d'un coup, ou seulement I1/I3/I5 (les moins risqués).
