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
| T09 | `T09_griffe_paume_doigts.png` | `step1_grip` | **Étape 1/4 — prise** (`grip_step_embed`) | **Branchée** |
| T10 | `T10_tailles_de_main.png` | `step2_thenar` | **Étape 2/4 — thénar** (`thenar_step_embed`), informatif — **étape sautée en Fingertip** | **Branchée** |
| T11 | `T11_mesurer_la_main.png` | `step2_measure` | **Étape 3/4 — mesures** (`measure_step_embed`) | **Branchée** |
| — | *(aucun fichier)* | `step3_budget` | Étape 4/4 — budget : laissée vide, aucune image imposée | Disponible |
| T12 | `T12_souris_longueur_largeur.png` | `illustration_mouse_dimensions` | Résultat, embed 2 « 📐 Repères de taille » | **Branchée** |
| T13 | `T13_arriere_etroit.png` | `illustration_rear_narrow` | Résultat, embed 2 **si thénar « Petite »** et prise Palm/Claw (note indicative ; jamais en Fingertip) | **Branchée** |
| T14 | `T14_bosse_centrale.png` | `illustration_hump_mid` | Résultat, embed 1 — bosse Mid du match idéal | **Branchée** |
| T15 | `T15_bosse_avant.png` | `illustration_hump_front` | Résultat, embed 1 — bosse Front / Mid-Front | **Branchée** |
| T07 | `T07_bosse_arriere.png` | `illustration_hump_rear` | Résultat, embed 1 — bosse Rear | **Branchée** |
| T01 | `T01_boutons_hauts.png` | `illustration_buttons_high` | Résultat, embed 1 — boutons High (ou bosse inconnue) | **Branchée** |
| T02 | `T02_boutons_bas.png` | `illustration_buttons_low` | Résultat, embed 1 — boutons Low | **Branchée** |
| T03 | `T03_boutons_moyens.png` | `illustration_buttons_mid` | Résultat, embed 1 — boutons Mid | **Branchée** |
| T04 | `T04_griffe_relachee.png` | `illustration_grip_relaxed` | Documentation uniquement (variantes de prise) | Clé prête, non affichée |
| T05 | `T05_griffe_agressive.png` | `illustration_grip_aggressive` | Documentation uniquement | Clé prête, non affichée |
| T06 | `T06_griffe_pince.png` | `illustration_grip_pincer` | Documentation uniquement | Clé prête, non affichée |

**Parcours adaptatif** : en **Fingertip**, l'étape thénar n'est pas proposée (3 étapes : 1 → 2/3 → 3/3) et ni la note
« arrière étroit » ni l'illustration T13 n'apparaissent : cette prise ne s'appuie pas sur l'arrière de la souris, et le
barème y ignore déjà la bosse. La numérotation s'adapte (`_steps_total`) ; elle reste 1/4 → 4/4 pour Palm et Claw.

**Règle de choix de l'image du résultat** (`result_image_key`) : la **bosse** d'abord (plus déterminante pour le ressenti),
puis les **boutons** si la bosse est inconnue ou non lue (Fingertip). Une seule image par embed, jamais trois.

T04/T05/T06 illustrent les variantes de la prise Claw (relâchée / agressive / pince). Conformément au Master Prompt
(§9.2 F), elles restent **documentaires** : elles n'entrent pas dans le résultat pour ne pas surcharger le message.

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
| `docs/apercu_parcours.png` | Accueil (T08) → 1/4 prise (T09) → 2/4 thénar (T10) → 3/4 mesures (T11) → 4/4 budget |
| `docs/apercu_resultat.png` | Résultat en deux embeds : recommandation (score unique, confiance, alternative), puis repères de taille (T12) ou note thénar (T13) — avec les boutons |

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
2. **Liens commerciaux d'exemple** : `data/commercial_links.json` contient encore `https://url.com/…` (scyrox_v8,
   atk_a9_plus). Ce sont des espaces réservés du propriétaire : à remplacer ou à vider, sinon le bouton d'achat pointe
   vers un site tiers. Aucun lien n'a été inventé ni supprimé par cette mission.
3. **Thénar** : informatif uniquement, et **non proposé en Fingertip** (décision du propriétaire, 2026-10-11). Aucune
   règle thénar → dimensions n'est documentée ; la note « arrière étroit » (T13) n'entre pas dans le score et le dit.
4. **Largeur de prise** : toujours estimée (coque − 3 mm) pour toutes les souris, donc confiance plafonnée à
   « moyenne » (Scyrox : « faible », données `owner_spec_unverified`).
5. **T04/T05/T06** non utilisées dans les embeds (choix documenté §2). Les aperçus de §6 sont des rendus
   simulés : les emojis y apparaissent sous forme de carrés (police de la machine de génération), pas dans Discord.
6. **Aucune vérification sur un serveur Discord réel** : les rendus mobile/desktop restent à contrôler par le
   propriétaire (`docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md`).

## 9. Résultat : un écran court, un bouton « Détails » (2026-10-11)

Le résultat ne s'affiche plus en deux embeds superposés (trop dense sur mobile) :

- **écran principal** : souris + prix, **pourcentage du maximum théorique**, badge de confiance, alternative
  (avec son propre pourcentage), raison du choix en une ligne, nombre de souris non classées ;
- **bouton 🔍 Détails** (dans le message privé, puis ↩️ Résumé pour revenir) : repères de taille, score
  complet, explication de la confiance, liste des souris écartées et leurs raisons, note thénar.

Aucune information n'est perdue : tout ce qui a été retiré du résumé est dans cet onglet. Les montants et
mesures s'affichent à la française (« 118,8–123,8 mm », « 74,90 € »).
