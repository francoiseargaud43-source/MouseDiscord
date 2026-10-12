# Rapport de design — AzeMouse Mouse Shape Finder (livrable design)

Date : 2026-10-11 · Branche : `arena/87fafd0d-mousediscord` · Périmètre : présentation et UX.
**Aucun calcul, seuil, score, statut, prix ou règle de confidentialité n'a été modifié** (voir §8).

> Ce document répond aux points 2, 3, 4, 5, 8 et 11 de la méthode de travail du Master Prompt :
> inventaire des images, matrice de correspondance, problèmes traités, changements visuels, intégration des ressources.

---

## 1. Inventaire réel des trois dossiers (inspection visuelle du 2026-10-11)

| Dossier | Fichiers | Rôle | Vérification |
|---|---|---|---|
| `ImageAct/` | 7 captures de l'interface d'origine | Vérité terrain à corriger | 7/7 ouvertes : étapes 1/3, 2/3, 3/3 (menu fermé/ouvert), modal mesures, **résultat monolithique** (111947) |
| `ImageEx/` | 9 références de design | Inspiration (Oblivity, triptyques de prises, cartes « Mouse Size », variantes Claw) | 9/9 ouvertes : principes extraits (fond sombre, une idée par carte, jaune précieux, liseré bordeaux) |
| `ImageUse/` | 15 assets de production `T01`–`T15` | Ressources finales | 15/15 ouvertes : **contenu conforme** à la table §3.1 du Master Prompt |

**Aucune image n'a été associée arbitrairement** : chaque `T*.png` a été ouvert et son sujet comparé au libellé prévu
(titre de la « pill » bordeaux dans l'image) avant branchement.

---

## 2. Matrice de correspondance définitive

| # | Fichier livré (`ImageUse/` → `assets/illustrations/`) | Clé `assets/images.json` | Où l'image apparaît | Statut |
|---|---|---|---|---|
| T08 | `T08_azemouse_banniere.png` | `banner` | Message persistant d'accueil (`banner_embed`) | **Branchée** |
| T09 | `T09_griffe_paume_doigts.png` | `step1_grip` | **Étape 1 — prise** (`grip_step_embed`) | **Branchée** |
| T04 | `T04_griffe_relachee.png` | `illustration_grip_relaxed` | **Étape 2/5 « variante de Claw »** (Claw uniquement) **et** bloc de variante du résultat | **Branchée** |
| T05 | `T05_griffe_agressive.png` | `illustration_grip_aggressive` | Résultat, prise **Claw** — variante « Claw agressive » | **Branchée** |
| T06 | `T06_griffe_pince.png` | `illustration_grip_pincer` | Résultat, prise **Claw** — variante « Claw pincée » | **Branchée** |
| T10 | `T10_tailles_de_main.png` | `step2_thenar` | **Thénar** (`thenar_step_embed`) : 2/4 en Palm, 3/5 en Claw, informatif — **sautée en Fingertip** | **Branchée** |
| T11 | `T11_mesurer_la_main.png` | `step2_measure` | **Mesures** (`measure_step_embed`) : 3/4 en Palm, 4/5 en Claw, 2/3 en Fingertip | **Branchée** |
| — | *(aucun fichier)* | `step3_budget` | Budget : laissée vide, aucune image imposée | Disponible |
| T12 | `T12_souris_longueur_largeur.png` | `illustration_mouse_dimensions` | Résultat, bloc 2 « 📐 Vos repères de taille » | **Branchée** |
| T13 | `T13_arriere_etroit.png` | `illustration_rear_narrow` | Résultat, bloc 3 **si thénar « Petite »** et prise Palm/Claw (jamais en Fingertip) | **Branchée** |
| T14 | `T14_bosse_centrale.png` | `illustration_hump_mid` | Résultat : bosse Mid de la souris retenue (bloc 1) **et** conseil « bosse au milieu ou à l'avant » en Palm | **Branchée** |
| T15 | `T15_bosse_avant.png` | `illustration_hump_front` | Résultat, bloc 1 — bosse Front / Mid-Front de la souris retenue | **Branchée** |
| T07 | `T07_bosse_arriere.png` | `illustration_hump_rear` | Résultat : bosse Rear de la souris retenue **et** conseil « bosse au milieu ou à l'arrière » en Claw | **Branchée** |
| T01 | `T01_boutons_hauts.png` | `illustration_buttons_high` | Résultat : boutons High de la souris retenue (bloc 1) **et** conseil « boutons hauts » en Palm | **Branchée** |
| T02 | `T02_boutons_bas.png` | `illustration_buttons_low` | Résultat : boutons Low de la souris retenue **et** conseil « boutons bas » en Claw | **Branchée** |
| T03 | `T03_boutons_moyens.png` | `illustration_buttons_mid` | Résultat : boutons Mid de la souris retenue **et** conseil « boutons médians à bas » en Fingertip | **Branchée** |

**Parcours adaptatif** (`_steps_total`, `STEP_NUMBERS`) : **Palm** 1 → 4 (prise, thénar, mesures, budget),
**Claw** 1 → 5 (la **variante de Claw** s'insère en 2/5), **Fingertip** 1 → 3 (thénar sauté : ni thénar ni note
« arrière étroit » ni illustration T13, cette prise ne s'appuyant pas sur l'arrière de la souris).

**Règle de choix de l'image de la recommandation** (`result_image_key`) : la **bosse** d'abord (plus déterminante pour
le ressenti), puis les **boutons** si la bosse est inconnue ou non lue (Fingertip). Une seule image par bloc.

Signalement et correction de conception (2026-10-11, 3ᵉ passe) : les illustrations T04/T05/T06 étaient réservées à la
documentation. Elles sont **désormais affichées** — au choix de la variante de Claw (étape 2/5) puis dans le bloc de
variante du résultat. L'outil de référence (Oblivity) consacre une section illustrée à chacune, et le propriétaire veut
la même complétude.
Chaque conseil de forme a son image : la recommandation illustre la souris retenue, les blocs d'explication illustrent
la consigne pour la prise choisie.

---

## 3. Hébergement des images (procédure propriétaire)

Le bot n'héberge rien : Discord exige des URL `https://` publiques. Deux méthodes, déjà supportées par
`utils/assets.py` :

1. **Hébergement sur Alwaysdata (recommandé, une seule variable à changer)**
   1. Publier le contenu de `assets/illustrations/` sur le web : soit en le copiant dans `~/www/illustrations/`,
      soit par un lien symbolique `ln -s ~/MouseDiscord/assets/illustrations ~/www/illustrations`
      (pratique : les mises à jour du dépôt se reflètent automatiquement).
   2. Dans `.env`, renseigner la base publique :
      `IMAGES_BASE_URL=https://[compte].alwaysdata.net/illustrations/`
   3. `assets/images.json` reste tel quel (noms de fichiers). Le bot relit le fichier à chaque interaction :
      **aucun redémarrage** n'est nécessaire.
2. **Hébergement externe** : remplacer les noms de fichiers par des URL `https://…` complètes (une seule source stable).

Contrôle : `python tools/check_deployment.py` affiche `images configurées : 15/15` et signale les cas à corriger
(base absente, schéma non https, fichier manquant). Une valeur vide ou invalide n'affiche simplement pas d'image.

---

## 4. Charte appliquée (rappel opérationnel)

| Élément | Valeur | Application dans le code |
|---|---|---|
| Bordeaux (identité) | `#8A2342` | `COLOR` : couleur latérale de **tous** les embeds |
| Orange | `discord.Color.orange()` | Uniquement `expired_embed()` (session expirée) |
| Nuit / Encre | `#0B1220` / `#070B14` | Fonds des illustrations `T*` (images, pas d'embed) |
| Étincelle | `#F0C43C` | Highlight présent **uniquement** dans les images (jamais en aplat, jamais en couleur d'embed) |
| Crème | `#F6F1EA` | Dans les illustrations uniquement (jamais un fond d'embed) |

Typographie : les polices Syne / Fraunces / JetBrains Mono restent dans les images (Discord n'autorise pas de police
personnalisée dans le texte natif). Dans les embeds, la hiérarchie est rendue par le Markdown et les champs :
`**gras**`, puces `•`, 1 à 4 champs par embed, textes courts.

**Sobriété** : 2 à 3 emojis par embed maximum, aucune ligne de séparation `---`, aucun titre en « ## » simulé,
aucun champ de plus de 700 caractères.

---

## 5. Problèmes de l'interface d'origine et corrections apportées

| # | Problème constaté (captures `ImageAct`) | Correction | Vérification |
|---|---|---|---|
| P1 | Détails internes exposés (`Longueur 127.0 mm vs cible … : 10 pts`) | Toutes les lignes `… : X pts` retirées de l'UI ; remplacées par une phrase humaine (`_match_summary`). Le barème reste dans `MouseScore.details` et la matrice. | `test_result_never_exposes_internal_scoring_details` |
| P2 | Liste « À vérifier » interminable avec scores partiels | 5 noms maximum, **sans score partiel**, puis renvoi vers `docs/audit/matrice_profils.md` ; au-delà de 8, une phrase de synthèse | `test_pending_text_*`, `test_results_show_pending_candidates_separately` |
| P3 | Hiérarchie inexistante entre match idéal, alternative et souris à vérifier | Match Idéal en premier champ (prix + score + confiance + phrase), alternative conditionnelle, « à vérifier » en dernier et discret | `test_standard_budget_shows_results_with_percentage_wording` |
| P4 | Score répété deux fois et `100 %` affiché sans contexte | Score affiché **une seule fois** (`X/40 — Y % du maximum théorique`), pied de page honnête conservé | idem + `test_embed_colors_follow_the_azemouse_charter` |
| P5 | Confiance noyée | Ligne `🟢/🟡/🔴 Confiance … — raison` sous le score (info jamais portée par la couleur seule) | idem |
| P6 | Deux boutons grisés « Lien bientôt disponible » | Plus aucun bouton grisé par souris : liens réels uniquement, sinon **un** bouton `🔗 Liens à venir` | `test_missing_commercial_link_shows_disabled_placeholder_button`, `test_real_link_creates_purchase_button_without_placeholder` |
| P7 | Couleur latérale blurple générique | Bordeaux `#8A2342` partout (sauf « session expirée », orange) | `test_embed_colors_follow_the_azemouse_charter` |
| P8 | Aucune illustration dans le parcours | `banner`, `step1_grip`, `step2_thenar`, `step2_measure` + illustrations de résultat branchées | `test_step_illustrations_are_branched_*` |
| P9 | Textes trop longs sur mobile | Champs ≤ 700 caractères (test), descriptions courtes, récapitulatif sur une ligne | `test_embeds_respect_discord_limits_and_stay_short` |
| P10 | Alternative systématique même sans différence | Alternative affichée seulement si prix ≥ 30 % inférieur, performances documentées différentes ou géométrie différente | `_alternative_is_relevant`, `test_standard_budget_shows_results_with_percentage_wording` |

---

## 6. Captures après refonte (générées sans serveur)

> **Mise à jour du 2026-10-11** : le résultat a été compacté (décompte par raison dans « À vérifier »,
> match idéal en trois lignes, embed 2 autoportant) — voir `docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md` §7.
> Les deux captures ci-dessous ont été régénérées à cette date.

Deux aperçus sont versionnés dans le dépôt (rendu simulé du client, thème sombre, fond `#313338`,
carte `#2B2D31`, liseré bordeaux `#8A2342`) :

| Fichier | Contenu |
|---|---|
| `docs/apercu_parcours.png` | Accueil (T08) → 1/5 prise (T09) → 2/5 variante de Claw (T04) → 3/5 thénar (T10) → 4/5 mesures (T11) → 5/5 budget |
| `docs/apercu_resultat.png` | Résultat complet : recommandation (match idéal, alternative, économie) puis repères de taille (T12), arrière étroit (T13, si thénar « Petite »), bosse et forme, variante de Claw et boutons — chaque bloc illustré |
| `docs/apercu_prix_libre.png` | Mode « Peu importe le prix » : le menu à cinq options (nouvelle option surlignée) puis la ligne de résultat — nom · pourcentage, prix en tout petit et composants documentés |

Régénération (développement uniquement, nécessite Pillow) :

```bash
python tools/render_preview.py     # docs/apercu_parcours.png, docs/apercu_resultat.png
```

Ce rendu est une **aide à la validation** : il ne remplace pas un contrôle sur un vrai serveur Discord
(mobile et desktop), qui reste à faire par le propriétaire.

## 7. Avant / après (description des écrans)

| Écran | Avant (captures `ImageAct`) | Après |
|---|---|---|
| Accueil | Embed blurple, texte sec, `banner` vide | Bannière AzeMouse (T08), 3 lignes, bordeaux, bouton unique |
| Étape 1/3 | Texte Palm/Claw/Fingertip sans illustration | 1/4 : illustration des 3 prises (T09) + libellés courts |
| Étape 2/3 | Aucun schéma, pas d'aide à la mesure | 3/4 : illustration main + règle (T11), 2 puces, récapitulatif de prise |
| Étape 3/3 | Menu aux libellés longs, pas d'image | 4/4 : libellés courts, récapitulatif, image facultative |
| **Nouvelle étape 2/4** | — | Thénar (T10) : informatif, disclaimer explicite |
| Résultat | 1 embed monolithique : 5 niveaux de détail, 10+ lignes « à vérifier », `… : 10 pts` visibles | 2 embeds : recommandation (score unique + confiance + phrase humaine) puis repères de taille illustrés (T12 ou T13) |
| Boutons | 2 boutons grisés + acheter + fermer + refaire (3 rangées) | Liens réels (max 2) ou un seul `Liens à venir` ; `✖️ Fermer` et `🔄 Refaire le test` ensemble |

---

## 8. Ce qui n'a pas été touché (contrat de préservation)

`utils/matcher.py` (équations, seuils stricts, barème 40 pts, `GRIP_WIDTH_ESTIMATE_OFFSET_MM`, `HUMP_IDEAL`,
`BUTTON_IDEAL`), `utils/selection.py` (tolérances 5/2/2/2, `performance_index`, ordres de tri), `utils/catalog.py`,
`data/mouse_db.json`, `data/commercial_links.json`, `utils/validation.py` (bornes et parsing),
`utils/session.py` (TTL, isolation, `_active_by_user`), les règles de confidentialité et la vue persistante.
Seuls ajouts fonctionnels : champ `thenar` de session (stockage/affichage), variable `IMAGES_BASE_URL`,
clés d'images supplémentaires.

---

## 9. Tests exécutés

```
$ pytest -q
239 passed, 1 warning in 0.97s          # warning : audioop (dépendance discord.py), non bloquant
$ python -m pyflakes bot.py config.py cogs utils tests tools
(aucune sortie : propre)
$ python tools/privacy_scan.py
0 violation(s) de confidentialité détectée(s).
```

Non-régression du barème vérifiée : main `180 × 90 mm`, Palm → V6 **30**, Z1 **30**, A9 Plus **25**, X1 **20**,
V8 et F1 exclues ; le thénar renseigné ne change **aucun** score (`test_thenar_is_stored_and_not_scored`).

---

## 10. Limites et points ouverts

1. **Illustrations non hébergées à ce jour** : `assets/illustrations/` est livré, `assets/images.json` référence les
   fichiers, mais tant que `IMAGES_BASE_URL` n'est pas renseigné, aucun embed n'affiche d'image (comportement prévu,
   sans erreur). Le contrôle `tools/check_deployment.py` le rappelle en `ATTENTION`.
2. **Liens commerciaux** : `data/commercial_links.json` contient les liens officiels vérifiés un par un
   (2026-10-11) ; les anciens espaces réservés `https://url.com/…` ont disparu. Aucun lien n'est inventé par le bot :
   un identifiant sans lien affiche « Liens à venir ».
3. **Thénar** : informatif uniquement, et **non proposé en Fingertip** (décision du propriétaire, 2026-10-11). Aucune
   règle thénar → dimensions n'est documentée ; la note « arrière étroit » (T13) n'entre pas dans le score et le dit.
4. **Variante de Claw** : collectée (étape 2/5, Claw uniquement) mais **jamais utilisée dans un calcul** : elle
   ne change que le texte du conseil de bosse. Un parcours ouvert sans cette réponse affiche les trois variantes.
5. **Largeur de prise** : toujours estimée (coque − 3 mm) pour toutes les souris ; les mesures locales
   (`docs/MESURES_LARGEUR_2026-10-11.md`) ne sont pas encore inscrites dans `data/mouse_db.json`. La confiance
   des données reste donc plafonnée à « moyenne » (Scyrox : « faible ») — mais elle n'est **plus affichée**
   depuis le 2026-10-11.
6. **T04/T05/T06** affichées depuis le 2026-10-11, uniquement en prise Claw (voir §2 et §9). Les aperçus de §6 sont des rendus
   simulés : les emojis y apparaissent sous forme de carrés (police de la machine de génération), pas dans Discord.
7. **Aucune vérification sur un serveur Discord réel** : les rendus mobile/desktop restent à contrôler par le
   propriétaire (`docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md`).

## 9. Résultat : la recommandation d'abord, l'explication plus bas (2026-10-11)

Le message privé ne montre plus ni score, ni badge de confiance, ni repères de taille en premier niveau :

- **🎯 Votre recommandation** (en haut) : une ligne descriptive du parcours (prise, thénar, mesures, gamme),
  puis **🥇 le match idéal**, **🥈 l'alternative** et, quand elle existe, **💸 l'économie** — chacune sur une
  seule ligne « **Nom** · poids · prix · pourcentage du maximum théorique · forme de coque ». Rien d'autre : ni score /40, ni confiance,
  ni détail de géométrie, et aucune liste de souris écartées. Image : la bosse de la souris retenue (ou ses boutons).
  **Exception (mode « Peu importe le prix », 2026-10-11)** : la ligne garde « Nom · pourcentage » et le prix descend en
  tout petit, suivi des composants documentés (capteur, fréquence, poids) — le prix ne concurrence plus la forme ;
- **📐 Vos repères de taille** : les deux plages cibles, d'où elles se mesurent, le score `/40 — %`, la souris
  retenue « en clair » avec ses dimensions et le « pourquoi ce choix ». Illustration T12 ;
- **🖐️ Un arrière étroit pour votre thénar** : **seulement** si le thénar déclaré est « Petite » (jamais en
  Fingertip). Illustration T13 ;
- **⛰️ La bosse et la forme** : où placer la bosse — **selon la variante de Claw déclarée** (relâchée → arrière
  marquée ; agressive → médiane ; pincée → arrière à flancs plats) — quelle forme de coque convient à la prise
  (Palm : symétrique comme ergonomique ; Claw : symétrique avant tout) et la forme de la souris retenue
  (`shape`). Illustration T14 ou T07. Absent en Fingertip (la bosse n'y travaille pas) ;
- **🦾 Votre variante de Claw** : la variante déclarée à l'étape 2/5, illustrée (T04, T05 ou T06) ; en repli, les
  trois variantes sont présentées si le parcours a été ouvert avant l'ajout de l'étape ;
- **🖱️ La hauteur des boutons** : le niveau conseillé pour la prise (Palm → hauts ; Claw → bas ; Fingertip →
  médians à bas) et le pourquoi. Illustration T01, T02 ou T03.

La **confiance des données** n'est plus affichée (décision du propriétaire, 2026-10-11) : elle mesure la
solidité des chiffres disponibles sur la souris, pas la qualité du choix. Elle reste calculée dans
`MouseScore.confidence` et pourra revenir plus tard. Chaque bloc porte l'illustration de son propos, et seul le
dernier porte le rappel « score géométrique provisoire… » : les blocs s'enchaînent sans répéter le même texte.

Le mode **« Peu importe le prix »** (demande du propriétaire, 2026-10-11) répond à « cherchons la forme, pas le
budget » : la zone de tolérance reste de 2 pts, le classement suit le **score** (la forme), puis le classement des
**composants documentés** — capteur (génération), puis MCU, puis switchs, puis fréquence (``components_index``,
``utils/selection.py``) —, puis le prix le plus bas ; aucun prix connu n'est exigé, donc les souris sans prix
redeviennent classables. Le poids documenté est affiché dès la ligne du match idéal et de l'alternative, pour
comparer deux formes équivalentes d'un coup d'œil, avec la forme de coque (« Symétrique » / « Ergonomique »)
tout à droite — le poids et la forme sont les deux critères qui différencient deux souris à score égal. La
ligne de prix en petit texte (`-#`) rappelle que le montant n'entre pas dans le classement. Aucun barème n'est
touché : c'est une stratégie de sélection de plus (`utils/selection.py`), comme demandé dans le master prompt.

Les trois rôles sont choisis dans le classement du mode, sans jamais recalculer un score : le match idéal est la
tête du classement ; l'alternative est la souris qui correspond le mieux au profil, en préférant une souris un
peu moins chère (son pourcentage sert sinon à faire accepter un léger surcoût) ; l'économie n'apparaît que si une
souris reste dans la zone de compatibilité du mode (tolérance `TOLERANCE_BY_MODE`) tout en étant vraiment moins
chère que les deux autres. Les montants et mesures s'affichent à la française (« 118,8–123,8 mm », « 74,90 € »).

## 11. Boutons « Fermer » / « Refaire » / « Détails » : retirés (2026-10-11)

Sur le bot déployé, « 🔄 Refaire le test » et « ✖️ Fermer » ne répondaient plus (« AzeMouse n'a pas répondu à
temps ») : après un redémarrage du bot ou l'expiration de la vue, Discord envoyait bien l'interaction, mais plus
personne ne la traitait. Une première correction les a rendus persistants (identifiants fixes + vue enregistrée au
démarrage) ; le propriétaire a ensuite demandé de les retirer purement et simplement (« juste retire les »).

Conséquence : le résultat ne porte plus **aucun** bouton interactif. Il ne reste que les boutons d'achat — des
liens (`discord.ui.Button(url=…)`) gérés par Discord, qui fonctionnent toujours, même si le bot est arrêté, sans
aucune interaction à traiter — ou, à défaut de lien, un unique rappel désactivé « 🔗 Liens à venir ». Le message
se ferme avec la croix du client Discord et un nouveau test se lance depuis le panneau public : plus rien du
résultat ne peut rester muet.

## 12. Forme de coque et variante de Claw (2026-10-11, 4ᵉ passe)

Deux manques restaient par rapport à l'outil de référence (Oblivity) :

1. **« Mouse Design » (symétrique / ergonomique)** — la donnée n'existait pas. Elle a été levée pour les
   **26 souris** (puis étendue aux 10 Pulsar ajoutées le 2026-10-12, soit 36) et inscrite dans
   `data/mouse_db.json` (champ `shape`, `Symmetrical` ou `Ergonomic`), chacune
   avec la source qui l'atteste (fiche ATK/VXE, EloShapes, Maxesport, test indépendant…). `utils/catalog.py`
   refuse désormais une forme renseignée sans source listant `shape` : aucune forme n'est devinée.
   Elle s'affiche dans le bloc « ⛰️ La bosse et la forme » (conseil par prise + forme de la souris retenue).
   Résultat du relevé : **24 souris symétriques**, **2 ergonomiques** (ATK Z1 V2 Ultra, ATK Y9 Ultimate).
2. **Les trois variantes de Claw** étaient listées sans savoir laquelle s'appliquait. Le parcours Claw pose
   maintenant une **étape 2/5 « Votre variante de Claw »** (relâchée / agressive / pincée, illustrée par T04).
   La réponse n'entre dans **aucun** calcul : elle choisit le texte du conseil de bosse (relâchée → arrière
   marquée ; agressive → médiane ; pincée → arrière à flancs plats) et le bloc de variante du résultat.
   Sans réponse (parcours ouvert avant cette version), les trois variantes sont présentées.

`_steps_total` et `STEP_NUMBERS` portent la numérotation : Palm 1 → 4, Claw 1 → 5, Fingertip 1 → 3.

## 13. Dix souris Pulsar ajoutées au catalogue (2026-10-12, 9ᵉ passe)

Le propriétaire a demandé de récupérer **toutes les souris disponibles** sur `https://eu.pulsar.gg/collections/mice`
(prix, tailles, composants, forme), et de ne pas se contenter de reproposer toujours les mêmes.

1. **Relevé du catalogue Pulsar EU** (≈ 41 modèles/tailles hors éditions de couleur, 59,99 € à 199,99 € TTC) :
   `docs/audit/PULSAR_CATALOGUE_2026-10-12.md`.
2. **Dix fiches entièrement sourcées** sur la fiche officielle du modèle (dimensions, poids, capteur XS-1, fréquence
   publiée 1 000 Hz, switchs optiques, forme, recommandations de prise du fabricant) : `pulsar_x2_v3_mini`,
   `pulsar_x2h_v3_mini`, `pulsar_x2a_v3_medium`, `pulsar_x2_crazylight_medium`, `pulsar_x2_crazylight_mini`,
   `pulsar_x2h_crazylight_mini`, `pulsar_xlite_crazylight_medium`, `pulsar_xlite_v4_mini`,
   `pulsar_xlite_v4_medium`, `pulsar_xlite_v4_large`. Le **MCU reste vide** (Pulsar ne le publie pas) et la fréquence retenue est la valeur
   **publiée** (1 000 Hz) : les 8 000 Hz exigent le dongle 8K vendu séparément.
3. **Provenance des compatibilités de prise** : nouveau statut `manufacturer_guide` (`utils/models.py`) pour les
   valeurs reprises d'une recommandation **écrite** du fabricant (« Recommended for Claw / Fingertip Grip »). Une
   prise non recommandée reste « Inconnu » : aucun point inventé, et `tests/test_catalog_lookup.py` refuse désormais
   toute valeur non « Inconnu » sans provenance ni justification.
4. **Effet mesuré** : le profil Claw 150 × 75 mm passe de 3 à 7 souris classables et le match idéal devient une
   Pulsar (X2 v3 Mini **40/40**, puis X2 CrazyLight Mini 40/40) ; Claw 180 × 100 mm : 4 → 10 classables
   (X2A v3 puis X2 CrazyLight Medium, 40/40 chacune) ; Fingertip 200 × 100 mm : la Pulsar X2 v3 Mini rejoint
   le Scyrox V6 en tête (40/40 ex æquo).
   Le profil Palm 180 × 90 mm est **inchangé** (Scyrox V6, ATK Z1 V2 Ultra, A9 Plus, X1 Ultra Max).
5. **Cause profonde du « toujours les mêmes »** : sur les 36 souris, seules les souris dont les **cinq** données
   (longueur vérifiée, largeur, compatibilité de prise, bosse, hauteur des boutons) sont connues peuvent être
   classées ; les autres restent « à vérifier » et ne sont jamais affichées. Il manque donc, pour la plupart des
   modèles, **la hauteur des boutons** et les **compatibilités de prise** : ce sont les deux relevés à compléter
   en priorité (liste à compléter : `docs/audit/PULSAR_CATALOGUE_2026-10-12.md` §5).
