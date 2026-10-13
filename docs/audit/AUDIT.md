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
- **Note datée 2026-10-11 (mission design visuel)** : refonte de la présentation seule (palette AzeMouse, 4 étapes avec le thénar informatif, résultat en deux embeds allégés, 15 illustrations `ImageUse` intégrées). **Aucun calcul, seuil, score, statut ni prix modifié** : Z1 reste à **30/40**, V6 30, A9 Plus 25, X1 20. Détail : `docs/REPORTE_DESIGN.md`.

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
| C10 | Catalogue — A9 Plus | Largeur 63.5 mm (cahier des charges) contre 64.0 mm (EloShapes). | M | **Tranché le 2026-10-12 (33e passe)** : la fiche officielle ATK relue annonce « 125 x 63.5 x 40 mm » pour la coque pleine taille, le propriétaire a mesuré 63,5 mm sur sa propre A9 Plus 2.0 — la coque A9 « large » publie **63,5 mm sur ses quatre entrées**, l'écart avec EloShapes reste consigné dans `conflicts` (C29). Aucun effet à 180×90 (5 pts dans les deux cas). |
| C11 | Catalogue — formes | EloShapes classe F1 V2 et X1 V2 en « Back - minimal » alors que le cahier des charges indique « Mid ». | M | **Signalé, non modifié** (valeur propriétaire conservée). À arbitrer. |
| C12 | Catalogue — Z1 | Les dimensions de la **Z1 originale** (ATK : 119.57 × 60.99 × 36.26) sont identiques à celles de la Fierce X. | H | **Non ajoutée** (donnée suspecte). La Z1 V2 (122.5 × 66.8 × 42.4) est concordante sur trois sources. |
| C13 | Catalogue — Duckbill | Longueur 118.0 mm (EloShapes) contre 117 mm (blog ATK). Aucune source trouvée à 55 mm. | H | **Corrigé** : `length_mm = null` + `conflicts` ; souris en « à vérifier ». **Tranché le 2026-10-12 (22e passe)** : la fiche officielle ATK publie **118 × 55 × 37,4 mm** — le fabricant est retenu, les deux valeurs (tierce et article de blog) restent consignées dans `conflicts`, et la souris devient classable (score partiel : hauteur des boutons non documentée). |
| C14 | Catalogue — Y9 Ultimate | Polling 8000 Hz (EloShapes, MaxGaming) contre 1000 Hz (FPSTools) ; poids 55 g contre 58 g. | M | **Corrigé** : polling non renseigné, conflits listés. Aucun score n'en dépend. |
| C15 | Prix | Aucun prix EUR vérifié pour les nouvelles variantes ; ATK affiche en USD. Les six prix d'origine viennent du cahier des charges, sans date. | H | **Signalé** : prix nouveaux à `null` ; `price_status` indique l'origine. Les modes à prix ne classent pas les souris sans prix. |
| C16 | Catalogue — Scyrox | Dimensions et compatibilités issues du cahier des charges, non revérifiées. | M | **Signalé** : `dimension_status = owner_spec_unverified` → confiance « faible ». |
| C17 | Images | Clé `step4_budget` devenue `step3_budget`. | B | **Corrigé** avec repli : `step4_budget` est lue si `step3_budget` est vide. Aucune URL n'était renseignée. |
| C18 | Documentation | README décrivait l'étape thénar, 4 étapes, « Compatibilité estimée », et le re-post de `!setup_finder`. | M | **Corrigé**. |
| C19 | Libellé « Points sur 100 » | Le cahier des charges dit « sur 100 » alors que le barème totalise 40. | M | **Conservé sur 40** (points bruts). **Point ouvert** : confirmer le libellé final (le wording de la mission, `X/40`, est appliqué). |
| C20 | Couverture de tests | Aucun test sur les statuts, les conflits, le catalogue v2, l'idempotence de `!setup_finder`. | M | **Corrigé** : +61 tests (`RAPPORT_FINAL.md` §4). |
| C21 | Documentation — règle des boutons | **Cinq documents** (README, prompt de référence, AMELIORATIONS, PROMPT_RECHERCHE, REVERSE_ENGINEERING) annonçaient `Claw {Low, Mid}` / `Fingertip {Low}` alors que le moteur applique `Claw {Low}` / `Fingertip {Low, Mid}` depuis le reverse engineering du 2026-10-11 (captures du propriétaire). | H | **Corrigé le 2026-10-12 (28e passe)** : les quatre documents normatifs portent la même phrase de référence, comparée au moteur par `tests/test_doc_references.py` ; le journal de décision reste dans `REVERSE_ENGINEERING_OBLIVITY.md` §4. Effet de l'ancien texte : 6 souris à boutons `Mid` (5 pts à tort en Claw, 10 pts perdus à tort en Fingertip). Aucun score n'était faux : seul le texte l'était. |
| C22 | Documentation — matrice de traçabilité | `tools/compare_profiles.py` classait les **cinq** modes sur une liste évaluée sous budget plafonné à 75 € : **8 lignes sur 15** annonçaient un autre gagnant que le bot, et le README recopiait ces gagnants. | H | **Corrigé le 2026-10-12 (28e passe)** : chaque mode est jugé sur la liste que le bot lui donne, les deux colonnes sont les deux places affichées (`result_slots`), matrice régénérée ; `tests/test_compare_profiles.py` (13e passe) verrouille l'invariant et échoue contre l'ancienne version. |
| C23 | Catalogue — provenance | **44 valeurs** (sur 492 renseignées) étaient sourcées dans les notes mais leur source ne déclarait pas le champ (`sources[].fields`) : la provenance n'était pas vérifiable par la machine, et rien ne l'exigeait (sauf pour `shape`). | H | **Corrigé le 2026-10-12 (32e passe)** : 9 sources datées ajoutées (pages EloShapes pour la bosse, moule de coque A9 « large » / F1, cahier des charges du propriétaire), 2 sources existantes étendues. **Aucune cote, aucun prix, aucun score ne change** (grille du banc identique au chiffre près). `tests/test_data.py::test_chaque_valeur_du_catalogue_cite_la_source_qui_l_atteste` le verrouille : 0 valeur sans source, et le test échoue si l'inventaire devient vide. |
| C24 | Catalogue — statut `verified` | Dix entrées Pulsar portaient `dimension_status = "verified"` avec **une seule** source, alors que la règle écrite partout disait « ≥ 2 sources concordantes ». | M | **Corrigé le 2026-10-12 (32e passe)** : règle précisée dans les quatre documents (`README`, master prompt, `CATALOGUE_ATK.md`, prompt de recherche) — « ≥ 2 sources concordantes à ≤ 0,5 mm, **ou la boutique officielle du fabricant** » — et testée (`test_un_statut_verified_se_justifie_par_ses_sources`). `single_source` = une seule source tierce. |
| C25 | Catalogue — valeurs vides | Onze clés `"mcu": ""` (et 11 clés nulles redondantes) là où les autres entrées omettent la clé : deux écritures pour un seul état, qui rendent les audits par script faux (une clé absente se lit `None`, jamais `""`). | B | **Corrigé le 2026-10-12 (32e passe)** : clés vides retirées, `test_le_catalogue_ne_contient_aucune_valeur_vide` interdit leur retour. |
| C26 | Documentation — 3ᵉ place | `REPORTE_DESIGN.md` ne citait que deux titres (« 💸 » / « ➕ ») après l'ajout de « 🔎 Autre piste » (2ᵉ et 3ᵉ places). | B | **Corrigé le 2026-10-12 (32e passe)** : les trois titres sont décrits, y compris la priorité du prix. |
| C27 | Message — renvoi mort | Le pied du message (verrouillé par le master prompt : « garder tel quel ») renvoyait au bloc « Comment lire ce résultat », **qui n'existe plus** dans le résultat actuel. | M | **Corrigé le 2026-10-13 (35e passe, autorisation du propriétaire)** : le pied de page renvoie au bloc qui existe — « 🧭 Pourquoi ce choix ? » — et seulement quand ce bloc est dans le message (sur un parcours incomplet, il ne reste que l'avertissement de score). La phrase ne dit plus de direction : « plus bas » était faux, le pied de page est posé sur le dernier bloc. `tests/test_flow.py::test_le_pied_de_message_ne_renvoie_plus_a_un_bloc_disparu` le verrouille. |
| C28 | Catalogue — source et valeur | Les deux Scyrox déclaraient `height_mm` dans leur source (« cahier des charges » : V6S 119 × 61 × 40, V8S 118 × 63 × 40) alors que le champ valait `null` : la fiche disait à la fois « hauteur attestée » et « hauteur inconnue ». | M | **Corrigé le 2026-10-12 (33e passe)** : hauteur **40,0 mm** publiée pour les deux (valeur déjà écrite dans la source qui la déclarait). Aucun effet sur les scores (la hauteur n'entre dans aucun barème). `tests/test_data.py::test_aucune_source_ne_declare_un_champ_resté_vide` balaie tout le catalogue. |
| C29 | Catalogue — coque A9 | La même coque (125 mm) publiait **deux largeurs** : 63,5 mm (propriétaire, fiche ATK pour l'A9 Plus / NB) et 64,0 mm (EloShapes, pour l'A9 Ultimate et l'A9 Air), sans que l'écart soit écrit pour ces deux dernières. | H | **Corrigé le 2026-10-12 (33e passe)** : fiche ATK de la série A9 relue (« Dimensions 125 x 63.5 x 40 mm ») → la coque publie **63,5 mm partout**, l'écart reste dans `conflicts` pour les trois entrées concernées. Effet mesuré : **1 043 profils sur 27 170 (3,8 %)** changent d'une place, dont **977 (93,7 %) au profit d'une autre variante de la même coque, plus légère et moins chère** (A9 Ultimate remplace A9 Plus 2.0 / A9 NB) ; l'A9 Ultimate passe de 27,6 % à **31,5 %** des sorties. Places remplies et détection d'anomalies : **inchangées** (85,50 %, 0 problème). |
| C30 | Catalogue — note contradictoire | La note de l'ATK X1 V2 Ultra Max annonçait un capteur « non renseigné » alors que le champ publiait « PAW3395 Ultra » (et la même note le citait plus loin). Le conflit, lui, citait des sources vagues. | M | **Corrigé le 2026-10-12 (33e passe)** : note réécrite (valeur retenue, pourquoi), source EloShapes déclarant le champ, conflit nommant la variante et renvoyant au tableau du fabricant. **Aucune valeur changée** : la page ATK liste deux capteurs pour six modèles sans correspondance lisible → point signalé au propriétaire (§8) plutôt que deviné. `test_la_note_de_l_x1_ne_contredit_pas_ses_champs` le verrouille. |
| C31 | Code — résidu d'édition | `cogs/finder_flow.py` gardait, à la fin du texte de l'étape thénar, un point suivi d'un guillemet de fermeture et de trois guillemets collés : une chaîne vide implicite. Le défaut était **invisible** — les littéraux voisins se concatènent à la compilation (le texte affiché restait juste) et `pyflakes` ne signale pas une chaîne vide. | B | **Corrigé le 2026-10-12 (34e passe)** : résidu retiré. `tests/test_code_hygiene.py` interdit désormais ce motif dans tout le code livré, interdit `print()` dans le bot (il ne laisserait aucune trace horodatée dans `~/admin/logs/jobs/`) et vérifie que le contrôle porte bien sur l'ensemble des fichiers. |
| C32 | Catalogue — provenance | L'ATK Y9 Ultimate listait **deux fois la même source** (libellé, URL et date rigoureusement identiques) : la même lecture était comptée pour deux attestations, et tout audit de provenance gonflait d'une unité. | M | **Corrigé le 2026-10-12 (34e passe)** : fusion en une seule source déclarant les deux champs (`claw_grip_fit`, `price_eur`). `tests/test_data.py::test_aucune_source_n_est_enregistree_deux_fois_dans_une_entree` interdit le retour du doublon ; deux lectures d'une même page à des dates ou libellés différents restent deux sources légitimes. |
| C33 | Catalogue — statut de cotes | Trois entrées annonçaient `dimension_status = "single_source"` (« une seule source, tierce ») alors que leurs propres sources réunissaient déjà les conditions de `"verified"` : la fiche du fabricant atteste les cotes de l'ATK Duckbill (trois sources de cotes), de l'ATK A9 Air et de la VXE X3. Le sens « statut fort sans preuve » était testé ; le sens inverse ne l'était pas. | M | **Corrigé le 2026-10-12 (34e passe)** : `verified` pour les trois (règle écrite du README : « deux sources concordantes, ou la boutique officielle du fabricant »). Aucun score ne change — seul le statut `conflicting` bloque une souris — et la grille complète le prouve : **0 profil sur 27 170** modifié (nouvel outil `tools/db_effect.py`). `tests/test_data.py::test_le_statut_des_cotes_ne_reste_pas_sous_estime` contrôle la règle **dans les deux sens**. |
| C34 | Message — prix non vérifié | Le marqueur « (prix non vérifié) » prévu par le master prompt (ses exemples de résultat montrent « 74.90 € (prix non vérifié) » et son croquis de code l'ajoute quand `price_status != "verified"`) **n'apparaissait plus dans aucun message** : il ne vivait que derrière un paramètre `verified_hint` qu'aucun appelant n'activait depuis le retrait de l'onglet « Détails » (2026-10-11). Le prix d'une souris non attestée s'affichait donc exactement comme un prix attesté. | M | **Corrigé le 2026-10-13 (35e passe, décision du propriétaire : « remettre le marqueur »)** : les trois places l'affichent, ainsi que la petite ligne de prix du mode « Peu importe le prix ». Effet mesuré : **4 373 places sur 27 170 profils (16,09 %)** portent le marqueur (contre 0 %) ; Scyrox V6 et ATK A9 Plus 2.0 sont les deux souris concernées. La plus longue ligne portant le marqueur mesure 79 caractères (la plus longue ligne de place du catalogue : 87). `test_a_prix_non_verifie_le_message_le_dit` et le banc d'essai le verrouillent. |
| C35 | Message — score partiel des places 2 et 3 | Une souris dont la **hauteur des boutons n'est pas documentée** est notée sur les critères disponibles (décision du 2026-10-12, `PARTIAL_SCORING_ALLOWED`) : son pourcentage est donc **sous-estimé** (le critère manquant ne peut que rapporter des points, jamais en retirer). Le message l'explique en clair… mais **seulement quand cette souris est le match idéal** (`ideal.is_partial` dans le bloc « 📐 Vos repères de taille »). En 2ᵉ ou 3ᵉ place, le pourcentage s'affiche sans aucune note : **8 187 places sur 27 170 profils (30,1 %)** — 2ᵉ place 3 832, 3ᵉ place 4 355 — réparties sur **7 304 profils** (un profil peut montrer les deux places). Le biais est toujours **défavorable** à la souris concernée (jamais de prix ni de score gonflé) : le membre peut écarter une souris potentiellement meilleure, il n'en achète jamais une survendue. | M | **Corrigé le 2026-10-13 (35e passe, décision du propriétaire : marqueur discret)** : les 2e et 3e places ajoutent « · boutons non documentés » à la fin de leur ligne (`PARTIAL_HINT`), après la forme de coque pour ne pas casser l'alignement tout à droite ; le match idéal garde la note longue (pas de doublon). **10 704 lignes** portent le marqueur (dont 8 187 pour un match idéal complet) ; la ligne la plus longue du catalogue passe de 87 à 102 caractères. Aucun score, aucun classement, aucune sélection ne change. `test_une_place_au_score_partiel_l_annonce_sur_sa_ligne` et le banc d'essai le verrouillent (dans les deux sens : pas de marqueur sur le match idéal). |
| C36 | Code — numéro d'étape hors prise | `_step_number(kind, prise)` indexait directement `STEP_NUMBERS[prise][kind]` : demander une étape qui n'existe pas pour la prise (le thénar en Fingertip, la variante de Claw hors Claw) remontait un `KeyError` **muet**, qui ne nommait ni la prise ni l'étape. Le parcours ne l'appelle jamais — `step_kind` saute le thénar en Fingertip — donc aucun membre ne l'a vu : c'est un piège pour le code futur, pas une panne. | M | **Corrigé le 2026-10-13 (38e passe)** : erreur lisible qui nomme la prise, l'étape et les étapes existantes de cette prise ; `tests/test_flow.py::test_une_etape_qui_n_existe_pas_pour_la_prise_le_dit` la verrouille (et confirme au passage les numéros normaux : thénar 2/4 en Palm, mesures 2/3 en Fingertip, variante 2/5 en Claw). Aucun texte affiché ne change. Mesure de la même passe : **0 violation** des limites Discord sur les 27 170 profils, **0 défaut réel** de typographie sur 15 133 textes, **0 exception** sur 162 combinaisons de données dégradées (détail : §26 de `ROBUSTESSE_2026-10-12.md`). |

## 3. Audit du muscle thénar

- **Constat** : collecté (Small / Medium / Large) et affiché dans le récapitulatif ; aucune équation, aucun seuil, aucune règle ne l'utilise.
- **Recherche de rôle fonctionnel** : aucune source consultée ne définit une règle de compatibilité basée sur le thénar pour les trois grips.
  Les valeurs Small/Medium/Large ne sont pas documentées dans les sources retenues.
- **Décision** : **retiré de la V1** (parcours 1/3 → 3/3, `Thenar` supprimé de `utils/models.py`, `images.json` mis à jour avec repli).
  Il pourra être réintroduit si le propriétaire documente une fonction de calcul précise.
- **Réintroduction informative — 2026-10-11 (décision du propriétaire)** : le thénar redevient l'**étape 2/4**
  (Petite / Moyenne / Grande), avec l'illustration `T10`. Règle appliquée : **stockage et affichage uniquement**
  (`FinderSession.thenar`, récapitulatif, note indicative « arrière étroit » avec `T13` si « Petite »).
  **Aucun effet** sur les équations, seuils, points, scores, classements ou exclusions ; aucune règle thénar → dimensions
  n'a été inventée. Tests : `test_thenar_is_stored_and_not_scored`, `test_thenar_petite_adds_a_purely_informative_narrow_rear_note`.
- **Exception Fingertip — 2026-10-11 (décision du propriétaire)** : l'étape thénar **n'est pas proposée** en prise Fingertip
  (parcours 1 → 2/3 → 3/3) et la note « arrière étroit » (T13) n'apparaît jamais dans ce cas : cette prise ne repose pas
  sur l'arrière de la souris, et le barème y ignore déjà la bosse (`HUMP_IDEAL` ne couvre que Palm et Claw).
  Le calcul reste inchangé : seul le nombre de questions posées varie.
  Tests : `test_fingertip_skips_the_thenar_step_and_shortens_the_path`, `test_fingertip_result_has_no_thenar_note_nor_rear_illustration`.

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
4. ~~**A9 Plus** : largeur 63.5 ou 64.0 mm ?~~ **Tranché le 2026-10-12 (33e passe)** : 63,5 mm. La fiche officielle ATK (page de la série A9) publie « 125 x 63.5 x 40 mm » pour la coque pleine taille, et le propriétaire a mesuré sa souris à 63,5 mm ; la coque est alignée partout, l'écart avec EloShapes (64,0 mm) reste consigné dans `conflicts`.
5. ~~**Duckbill** : longueur 118.0 ou 117 mm ?~~ **Tranché le 2026-10-12** : la fiche officielle ATK (pays
   France) publie **118 × 55 × 37,4 mm**. La valeur « 55 mm » de la mission existe donc bien, et c'est le
   fabricant qui tranche l'écart de longueur (l'article du blog, plus ancien, reste consigné).
6. **Z1 originale** : confirmer ses dimensions (ou confirmer qu'elle n'est pas à ajouter).
7. **Y9 Ultimate** : polling (8000 ou 1000 Hz) et poids.
8. **Rôle du thénar** : **tranché le 2026-10-11** — réintroduit comme étape 2/4 **informative** (stockée et affichée,
   sans aucun effet sur le score, §3). Une règle de calcul thénar → dimensions reste à documenter si elle doit un jour
   compter dans le classement.
9. **Libellé** « sur 100 » ou « sur 40 » ?
10. **Tolérances de sélection** : valider 5 / 2 / 2 / 2 pts.
11. **Vérifications Discord** : à faire par le propriétaire (§9).

12. **Coque `atk_x1` — VXE X3** : la X3 partage les **cotes** de l'ATK X1 V2 Ultra Max (`shell_id`,
    même 127 × 64 × 40 mm) mais ni sa bosse ni sa hauteur de boutons ne lui sont propagées : la bosse de
    l'X1 est elle-même contestée par une source tierce (« Back - minimal » chez EloShapes contre « Mid »
    du propriétaire), et rien ne prouve encore que la X3 reprend la même pièce de plastique. **Exception
    documentée et testée** (`test_no_shell_mixes_two_button_heights`) : la X3 reste « à vérifier » (deux
    manques) et n'est donc jamais recommandée. Elle se débloquera le jour où une source publiera sa bosse —
    aucune valeur n'est devinée en attendant.
13. ~~**Ordre des pourcentages entre les places**~~ **Tranché le 2026-10-13 (35e passe)** : l'ordre est
    **garanti** — une place n'affiche jamais un meilleur pourcentage que celle du dessus. Le moteur
    plafonne chaque place par le score de la précédente (au moment du choix de la souris, jamais en
    retouchant un score). Effet mesuré : 2 046 → **84 profils** (0,31 %) où l'ordre n'est pas garanti — ce
    sont les profils où le plafond ne laisse **aucun** candidat (grande main à budget serré) ; la place
    reste alors remplie (jamais de trou) et le banc d'essai les compte. Le match idéal ne change jamais
    (0 profil sur 24 609). Détail : §24.1 de `ROBUSTESSE_2026-10-12.md`.
14. ~~**Marqueur « prix non vérifié »**~~ **Tranché le 2026-10-13 (35e passe)** : le marqueur est
    **remis** dans la ligne de prix (décision : « remettre le marqueur dans la ligne de prix »), pour les
    trois places et pour la petite ligne de prix du mode « Peu importe le prix ». **16,09 % des profils**
    (4 373 places) l'affichent désormais, contre 0 % auparavant.
15. ~~**Score partiel en 2ᵉ et 3ᵉ place**~~ **Tranché le 2026-10-13 (35e passe)** : **marqueur discret**
    sur la ligne — les 2e et 3e places d'une souris au score partiel affichent « · boutons non documentés »
    (`PARTIAL_HINT`), le match idéal gardant la note longue du bloc « 📐 Vos repères de taille ». Avant :
    **8 187 places** sur 27 170 profils (2ᵉ 3 832 · 3ᵉ 4 355, réparties sur 7 304 profils) où le pourcentage
    s'affichait comme un score complet alors qu'il était calculé sans le critère des boutons (donc
    sous-estimé) ; **10 704 lignes** portent désormais le marqueur. Détail : §24.4 de
    `ROBUSTESSE_2026-10-12.md`.

16. **Prix de l'A9 Plus** (nouveau, 37e passe, 2026-10-13) : le lien sponsorisé de la souris fige la
    variante « A9 Plus / White », relevée **27,95 €** à la boutique ATK FR (prix normal 36,95 €) —
    alors que le catalogue porte **45,00 €** (cahier des charges, non daté) et qu'un revendeur affiche
    44,90 €. Rien ne prouve, en l'état, que « A9 Plus » (la variante vendue 27,95 €) et « A9 Plus 2.0 »
    (les 45,00 € du cahier des charges) soient le même produit : peut-être une édition antérieure, un
    autre capteur. **Le prix du catalogue n'a donc pas été changé** ; une source d'observation datée du
    2026-10-13 a été ajoutée pour garder la trace, et la question est posée. **L'effet est mesuré** (grille
    complète, 27 170 profils, mesure du 2026-10-13) : si l'A9 Plus passait à 27,95 €, **3 556 profils
    (13,09 %)** changeraient d'au moins une place — place idéale 1 491, alternative 2 711, économie 1 790
    (une liste peut changer sur deux places) —, **0 place gagnée, 0 perdue**, 3 016 listes reconstruites
    sans deux fois la même coque et 540 avec le repli documenté. Autrement dit, cette décision **redistribue
    le classement sans jamais raccourcir une liste** ; elle est donc moins risquée que le retrait des
    ruptures (point 18). Détail et commande : §25.6 de `ROBUSTESSE_2026-10-12.md`. Source :
    §7 de `VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`.
17. ~~**Cohérence entre le prix annoncé et le prix réellement ouvert par le lien**~~ **Tranché le
    2026-10-13 (37e passe)** : le prix d'une souris est **le prix de la page que son lien ouvre**, relevé
    chez le marchand le jour de la conclusion (`products/<handle>.js?country=FR` chez atk.store,
    `search/suggest.json` chez eu.pulsar.gg). Les **36 liens** ont été relus : **six prix étaient faux** —
    l'A9 Ultimate annonçait 41,95 € (prix d'une *autre* édition de la même page) pour une variante vendue
    59,95 €, et cinq souris avaient vieilli d'un euro depuis le relevé précédent (X1 V2 Ultra Max 40,95 →
    41,95 €, F1 V2 40,95 → 41,95 €, MAD R 40,95 → 41,95 €, A9 NB 72,95 → 73,95 €, Duckbill 81,95 →
    82,95 €). **Trois liens recâblés** vers le coloris en stock, au même prix (GHOST Ultimate → Silver,
    U2 V2 Ultimate → Lake Green, Y9 Ultimate → Pink). **Effet mesuré** : 6 058 profils sur 27 170
    (22,30 %) changent d'une place, **0 place gagnée, 91 perdues**. **Trois tests** verrouillent la règle,
    dont celui qui manquait (`test_chaque_prix_de_souris_est_date_par_une_source` : aucun prix sans source
    de prix datée). Détail : §7 de `VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`, effet complet dans
    `ROBUSTESSE_2026-10-12.md` §25.

18. **Souris en rupture de stock recommandées** (nouveau, 37e passe, 2026-10-13) : la relecture des
    36 liens a aussi relevé la disponibilité. **Quatre souris du catalogue sont en rupture** à cette date
    — VXE MAD R (produit entier), ATK Fierce X (produit entier), Pulsar Xlite v4 Large et Pulsar Xlite v4
    Medium (les deux coloris de chacune) — plus quelques **coloris** isolés dont le bouton d'achat a déjà
    été recâblé vers un coloris en stock (GHOST Ultimate, U2 V2 Ultimate, Y9 Ultimate, U2 Mini). Mesure sur
    la grille statistique (18 522 profils) : ces quatre souris occupent **1 614 places sur 51 504**
    (3,1 %) — la MAD R à elle seule en occupe 1 317 (7,1 % des profils), la Xlite v4 Large 180, la
    Fierce X 105, la Xlite v4 Medium 12. **L'effet d'un retrait est mesuré** (grille complète, 27 170
    profils, option `--retrait` du comparateur) : les sortir du classement changerait **1 682 profils
    (6,19 %)** — place idéale 102, alternative 557, économie 1 517 —, avec **0 place gagnée et 78 places
    perdues** : la MAD R occupe 1 517 places avant, la Fierce X 152, la Xlite v4 Medium 13, la Xlite v4
    Large aucune sur cette grille. Les places libérées vont à l'A9 Plus 2.0 (315 fois), la VXE R1 (256),
    l'U2 V2 Mini (236), la F1 V2 Ultimate (204). **Rien n'a été changé** : retirer une souris du classement,
    la faire passer après les autres ou écrire « en rupture » sur sa ligne sont trois décisions différentes,
    toutes visibles par les membres, et aucune n'a été tranchée. La question est posée telle quelle, avec
    les chiffres. Le **coût de la troisième option** est mesuré lui aussi : la plus longue des lignes
    concernées mesure **95 caractères** aujourd'hui et **116** avec « · en rupture de stock » (107 avec
    « · en rupture »), à comparer aux 102 caractères de la plus longue ligne affichée et à la limite Discord
    d'un champ (1 024) ; **1 682 places** sont concernées (économie 1 121, alternative 459, idéale 102). Détail : §25.4 et §25.6 de `ROBUSTESSE_2026-10-12.md`.

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
