# Audit technique — Mouse Shape Finder (livrable A)

Date de l'audit : 2026-10-10 · Branche : `arena/33e33710-mousediscord` · Référence de départ : `68a5bbd`.

## 0. Résumé

- Le moteur, le catalogue et le flux Discord fonctionnaient, mais le **mode de sélection n'avait presque aucun effet**
  (il ne départageait que les ex æquo), la **largeur de prise** était une estimation codée en dur sans trace,
  le **muscle thénar** était collecté sans effet, et **`!setup_finder` publiait un nouveau message à chaque appel**.
- Corrigé : moteur à trois couches (compatibilité / éligibilité / sélection), statuts `scored` / `pending` / `excluded`,
  largeur mesurée séparée de l'estimation, schéma de catalogue v2 avec sources, thénar retiré, `!setup_finder` idempotent,
  affichage `X/40 — Y %`.
- Catalogue : 6 modèles d'origine conservés, 12 variantes ATK ajoutées **sans valeur inventée** (grip et hauteur de bouton
  « Inconnu » → à vérifier). Aucun prix EUR n'a pu être vérifié.
- Tests : 72 → **133** à la rédaction initiale ; **219** après la mission de finalisation du 2026-10-10 (voir `RAPPORT_FINAL.md` §4). Lint pyflakes propre. Aucun test Discord réel n'a été exécuté (voir §9).
- **Note datée 2026-10-10 (finalisation)** : Z1 reste à **30/40** (décision du propriétaire : bande de largeur non étendue). Confidentialité : scénarios P01–P13 et contrôle statique documentés dans `AUDIT_CONFIDENTIALITE.md` (tests automatisés uniquement, pas de validation Discord).

## 1. État du dépôt au début de la mission

| Élément | Constat |
|---|---|
| Branche / HEAD | `arena/33e33710-mousediscord` · `68a5bbd` (poussé : `origin` pointe sur le même commit). |
| Historique | `543879e` Initial commit → `3f1befa` bot + moteur + données → `68a5bbd` « Fine-tuning : seuil largeur 5 mm, affichage en pourcentage ». |
| Correction de l'état de session | Le résumé de session indiquait que le passage à 5 mm n'était pas commité : **c'est faux**, il est dans `68a5bbd` et poussé. |
| Arbre de travail | Propre. |
| Tests | 72 passent, 1 avertissement (`audioop`, dépendance discord.py, non bloquant). |

## 2. Constats et corrections

Gravité : **H** élevée (résultat ou sécurité des données faux/trompeur), **M** moyenne, **B** basse.

| # | Zone | Constat (état avant) | Gravité | Traitement |
|---|---|---|---|---|
| C1 | Modes (`utils/matcher.py`) | Les modes ne servaient qu'à départager les ex æquo : Économique et Qualité/Prix donnaient le même résultat que le classement brut. | H | **Corrigé** : `utils/selection.py`, tolérances par mode, critère de classement propre à chaque mode (§5). |
| C2 | Largeur de prise | `width_max − 3` codé en dur dans `evaluate`, sans distinction entre donnée mesurée et estimée, sans source. | H | **Corrigé** : `grip_width_mm` (mesurée), `GRIP_WIDTH_ESTIMATE_OFFSET_MM` (constante), `width_source` affiché dans le résultat. |
| C3 | Thénar | Collecté à l'étape 3, affiché dans le récapitulatif, **aucun effet** sur le calcul. | M | **Corrigé** : retiré du parcours (§3). |
| C4 | Schéma compatibilité | Les valeurs de grip / bosse / boutons étaient des énumérations strictes : impossible de représenter « non vérifié » sans inventer une valeur. | H | **Corrigé** : valeur `Inconnu` ; une souris avec une donnée `Inconnu` passe en `pending` et n'est jamais classée. |
| C5 | Libellé d'affichage | « Compatibilité estimée : X % » se lit comme une probabilité. | H | **Corrigé** : `Score de correspondance : X/40 — Y % du maximum théorique du barème` + pied de page explicite (« ni une probabilité… »). |
| C6 | Seuils flottants | Les écarts étaient comparés sans arrondi. Une frontière exacte (écart = 3.0 mm) peut basculer par bruit flottant. | B | **Corrigé** : arrondi à 6 décimales avant comparaison + test de non-régression (`test_decimal_boundary_…`). Aucun cas réel faux n'a été observé ; la garde est préventive. |
| C7 | `!setup_finder` | Chaque exécution publie un nouveau message : doublons dans le salon. | H | **Corrigé** : identifiant mémorisé dans `state/finder_message.json` (ignoré par Git), édition du message existant, republication si supprimé ou autre salon. |
| C8 | Gestion d'erreur | `on_error` et les réponses d'erreur pouvaient lever une exception si l'interaction était expirée. | M | **Corrigé** : `_send_ephemeral` journalise au lieu de propager. |
| C9 | Erreurs de saisie | Les modals valident déjà les bornes ; le comportement est conservé. | — | Vérifié, inchangé (tests `test_validation`, `test_flow`). |
| C10 | Catalogue — A9 Plus | Largeur 63.5 mm (cahier des charges) contre 64.0 mm (EloShapes). | M | **Conservé et documenté** : écart 0.5 mm, dans la tolérance de concordance (0.5 mm). Pas d'effet sur le score à 180×90 (5 pts dans les deux cas). À confirmer. |
| C11 | Catalogue — formes | EloShapes classe F1 V2 et X1 V2 en « Back - minimal » alors que le cahier des charges indique « Mid ». | M | **Signalé, non modifié** (valeur propriétaire conservée). À arbitrer. |
| C12 | Catalogue — Z1 | Les dimensions de la **Z1 originale** (ATK : 119.57 × 60.99 × 36.26) sont identiques à celles de la Fierce X. | H | **Non ajoutée** (donnée suspecte). La Z1 V2 (122.5 × 66.8 × 42.4) est concordante sur trois sources. |
| C13 | Catalogue — Duckbill | Longueur 118.0 mm (EloShapes) contre 117 mm (blog ATK). Aucune source trouvée à 55 mm. | H | **Corrigé** : `length_mm = null` + `conflicts` ; souris en « à vérifier ». |
| C14 | Catalogue — Y9 Ultimate | Polling 8000 Hz (EloShapes, MaxGaming) contre 1000 Hz (FPSTools) ; poids 55 g contre 58 g. | M | **Corrigé** : polling non renseigné, conflits listés. Aucun score n'en dépend. |
| C15 | Prix | Aucun prix EUR vérifié pour les nouvelles variantes ; ATK affiche en USD. Les six prix d'origine viennent du cahier des charges, sans date. | H | **Signalé** : prix nouveaux à `null` ; `price_status` indique l'origine. Les modes à prix ne classent pas les souris sans prix. |
| C16 | Catalogue — Scyrox | Dimensions et compatibilités issues du cahier des charges, non revérifiées. | M | **Signalé** : `dimension_status = owner_spec_unverified` → confiance « faible ». |
| C17 | Images | Clé `step4_budget` devenue `step3_budget`. | B | **Corrigé** avec repli : `step4_budget` est lue si `step3_budget` est vide. Aucune URL n'était renseignée. |
| C18 | Documentation | README décrivait l'étape thénar, 4 étapes, « Compatibilité estimée », et le re-post de `!setup_finder`. | M | **Corrigé**. |
| C19 | Libellé « Points sur 100 » | Le cahier des charges dit « sur 100 » alors que le barème totalise 40. | M | **Conservé sur 40** (points bruts). **Point ouvert** : confirmer le libellé final (le wording de la mission, `X/40`, est appliqué). |
| C20 | Couverture de tests | Aucun test sur les statuts, les conflits, le catalogue v2, l'idempotence de `!setup_finder`. | M | **Corrigé** : +61 tests (`RAPPORT_FINAL.md` §4). |

## 3. Audit du muscle thénar

- **Constat** : collecté (Small / Medium / Large) et affiché dans le récapitulatif ; aucune équation, aucun seuil, aucune règle ne l'utilise.
- **Recherche de rôle fonctionnel** : aucune source consultée ne définit une règle de compatibilité basée sur le thénar pour les trois grips.
  Les valeurs Small/Medium/Large ne sont pas documentées dans les sources retenues.
- **Décision** : **retiré de la V1** (parcours 1/3 → 3/3, `Thenar` supprimé de `utils/models.py`, `images.json` mis à jour avec repli).
  Il pourra être réintroduit si le propriétaire documente une fonction de calcul précise.

## 4. Incohérences avec les résultats attendus

| Attendu | Obtenu | Explication |
|---|---|---|
| Z1 = 35/40 en Top 1 (180×90 Palm) | **30/40** (Top 1 en Haut de gamme, ex æquo avec V6) | Écart de largeur 4.2 mm : dans la zone 2–5 mm, qui donne 0 point. Le seuil d'exclusion à 5 mm (demande de fine-tuning) n'ajoute **pas** de point. Passer à 35 exigerait une **bande +5 pour 2 ≤ écart ≤ 5 mm**, qui n'est pas dans le cahier des charges : **décision propriétaire requise** (§8). |
| Z1 « kept » pour le profil C | **Exclue** (écart 5.4 mm > 5 mm) | Cohérent avec la règle. À noter : la Z1 n'est plus proposée en Claw (ni en Fingertip, où son grip est « Faible »). |
| Mode économique : résultat distinct | A9 Plus (25/40, 45 €) | Auparavant V6 (30/40) : la tolérance de 5 pts laisse passer une baisse de 5 pts pour le prix. |

## 5. Problèmes de classement

- **Haut de gamme sans données de performance** : pour les six modèles d'origine, aucun capteur ni polling n'est documenté
  (sauf Z1 V2 et X1 V2). Le mode retombe alors sur l'**ordre du catalogue** en cas d'égalité (ex. Profil C : V8 avant V6).
  Ce n'est pas un choix de performance. **Donnée propriétaire requise.**
- **Qualité/Prix** : l'indicateur `points / €` est provisoire ; il dépend des prix non vérifiés des six modèles d'origine.
- **Départage par `budget_tier`** : supprimé du tri (il ne servait que d'étiquette ; il est conservé et affiché pour information).
  Les attentes de tests correspondantes ont été remplacées (documentées au rapport final).
- **Tolérances (5 / 2 / 2 / 2 pts)** : provisoires, centralisées dans `utils/selection.py`, à valider par le propriétaire.

## 6. Risques

- La largeur de prise est **estimée** pour toutes les souris (aucune mesure disponible) : `coque − 3 mm` est un correctif provisoire.
- Les correspondances de forme (bosse « Back - minimal » → `Rear`, « Center » → `Mid`) sont des **règles de correspondance**, à confirmer.
- Les prix du cahier des charges n'ont pas de date : les modes à prix peuvent être obsolètes.
- Le catalogue n'est **pas exhaustif** (voir livrable B).
- Les sources « EloShapes » sont un site tiers ; ATK Store est le site du fabricant.

## 7. Corrections effectuées

Fichiers modifiés ou créés (voir `RAPPORT_FINAL.md` pour la liste complète) : `utils/matcher.py`, `utils/selection.py` (nouveau),
`utils/models.py`, `utils/catalog.py`, `utils/session.py`, `utils/assets.py`, `cogs/finder_flow.py`, `cogs/mouse_finder.py`,
`config.py`, `data/mouse_db.json`, `assets/images.json`, `.gitignore`, `README.md`, `tools/`, `docs/audit/`, `tests/`.

## 8. Points ouverts (propriétaire)

1. **Bande de largeur** : étendre la règle +5 pts à `2 ≤ écart ≤ 5 mm` (Z1 → 35/40) ? **Décision (mission de finalisation, 2026-10-10) : non.** Z1 reste à 30/40 : écart 4.2 mm, 0 point de largeur (bonus strict < 2 mm). Toute évolution du barème devra être générale, justifiée et testée sur plusieurs modèles.
2. **Compatibilités des nouvelles variantes** (grip Palm / Claw / Fingertip, hauteur des boutons) : à renseigner pour les classer.
3. **Prix EUR** et date de vérification pour les six modèles d'origine et les nouvelles variantes.
4. **A9 Plus** : largeur 63.5 ou 64.0 mm ? Confirmer la source.
5. **Duckbill** : longueur 118.0 ou 117 mm ? La valeur « 55 mm » évoquée dans la mission n'a été trouvée dans aucune source.
6. **Z1 originale** : confirmer ses dimensions (ou confirmer qu'elle n'est pas à ajouter).
7. **Y9 Ultimate** : polling (8000 ou 1000 Hz) et poids.
8. **Rôle du thénar** : documenté ou définitivement retiré ?
9. **Libellé** « sur 100 » ou « sur 40 » ?
10. **Tolérances de sélection** : valider 5 / 2 / 2 / 2 pts.
11. **Vérifications Discord** : à faire par le propriétaire (§9).

## 9. Vérifications Discord

**Aucun test Discord réel n'a été exécuté** : l'environnement n'a pas de connexion à un serveur Discord.
Les comportements suivants sont couverts uniquement par des interactions simulées (`tests/test_flow.py`, `tests/test_setup_command.py`) :

| Vérification | Couverture automatisée | Vérification manuelle requise |
|---|---|---|
| Isolation des sessions (deux utilisateurs) | Sessions indexées par `user_id` (`test_session.py`) | Oui — deux comptes en parallèle |
| Interactions expirées | Session expirée → message (`test_expired_session_informs_user`) | Oui — bouton d'un ancien menu |
| Vue persistante après redémarrage | `add_view(StartView())` dans `setup_hook` (code) | Oui — redémarrer le bot puis cliquer |
| Pas d'accumulation de messages | `!setup_finder` édite le message existant (`test_setup_command.py`) | Oui — exécuter 3 fois `!setup_finder` |
| Permissions limitées au salon | `set_permissions` sur le salon, rien au niveau serveur (code + test) | Oui — vérifier qu'un autre salon n'est pas modifié |
| Verrouillage documenté | README §Initialiser le salon | Oui — un membre ne peut pas écrire |
