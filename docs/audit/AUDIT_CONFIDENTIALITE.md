# Audit de confidentialité — Mouse Shape Finder

Date : 2026-10-10 · Branche : `arena/33e33710-mousediscord` · Périmètre : parcours Discord du Mouse Shape Finder (`cogs/finder_flow.py`, `utils/session.py`, `cogs/mouse_finder.py`).

> **Portée de ce document.** Il décrit ce qui est **vérifié automatiquement** (tests unitaires et tests de scénario avec
> interactions factices, plus un contrôle statique du code). Il **ne prouve pas** le comportement réel de Discord.
> Aucune validation sur un serveur Discord réel n'a été effectuée : elle reste à faire selon
> `docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md`. Ce document ne déclare donc pas la confidentialité « entièrement validée ».

## 1. Ce qui est protégé, et pourquoi

Les données individuelles d'un parcours sont : le grip choisi, les mesures de la main (longueur, largeur), le budget
(mode et montant), le résultat (classement personnel). Elles ne doivent apparaître que dans les messages éphémères
de l'utilisateur concerné.

Seul le **message d'accueil** est public (panneau publié par `!setup_finder`). Il ne contient aucune donnée personnelle.

## 2. Mécanismes en place

| Mécanisme | Fonctionnement | Fichier |
|---|---|---|
| Réponses éphémères | Chaque réponse d'interaction est `send_message(..., ephemeral=True)`, `defer(ephemeral=True)`, `followup.send(..., ephemeral=True)` ou `edit_message` sur le message éphémère du parcours. | `cogs/finder_flow.py` |
| Identifiant de session | Chaque parcours reçoit un `session_id` aléatoire (`secrets.token_urlsafe`). Chaque vue et chaque modal le porte. | `utils/session.py` |
| Double contrôle | `SessionStore.lookup` vérifie l'identifiant **et** le propriétaire, la durée de vie (TTL) et que le parcours est encore le parcours actif de l'utilisateur. | `utils/session.py`, `require_session` |
| Un parcours actif par utilisateur | Un nouveau démarrage remplace le précédent : l'ancien menu devient inutilisable. | `SessionStore.start` |
| Résultat réservé | `ResultsView` vérifie le propriétaire (`_check_owner`) avant « Fermer » et « Refaire le test ». | `cogs/finder_flow.py` |
| Contrôle statique | Analyse AST qui signale tout envoi non éphémère, toute édition hors fonctions autorisées, tout alias ou appel dynamique des méthodes d'interaction, et tout envoi public hors commande d'administration. | `tools/privacy_scan.py` |

## 3. Contrôle statique (P13) : fonctionnement et limites

`tools/privacy_scan.py` parcourt l'arbre syntaxique des fichiers du bot (`SCANNED_FILES`) et applique six règles :

| Règle | Interdit | Exception |
|---|---|---|
| R1 | `send_message` ou `defer` sans `ephemeral=True` littéral (un `**kwargs` n'est **pas** une preuve) | — |
| R2 | `followup.send` sans `ephemeral=True` littéral | — |
| R3 | `send` / `reply` / `respond` sur un autre objet (salon, message, contexte) | `PUBLIC_ALLOWLIST` : `setup_finder`, `setup_finder_error`, `_edit_existing` dans `cogs/mouse_finder.py` (administration et panneau public, sans donnée individuelle) |
| R4 | `edit_message` / `edit_original_response` | `EDIT_ALLOWED_FUNCTIONS` : `_show_private`, `_close`, `_restart` dans `cogs/finder_flow.py` |
| R5 | Référence non appelée à une méthode sensible (alias : `f = interaction.response.send_message`) | — |
| R6 | `getattr` / `setattr` / `partial` visant une méthode sensible ou un objet d'interaction | — |

**Preuves de robustesse** (`tests/test_privacy_scan.py`) :
- le dépôt réel ne produit aucune violation ;
- le test vérifie que le contrôle lit bien les 7 appels sensibles actuels de `finder_flow.py` (un contrôle qui ne lirait rien passerait sinon) ;
- 5 variantes valides ne sont pas signalées ;
- 14 variantes de violation sont détectées (kwargs, `ephemeral=False`, `ephemeral` variable, `defer` public, `channel.send`, `reply`, alias, `getattr`…) ;
- **échec puis réussite** : une violation injectée dans une copie du vrai `finder_flow.py` est signalée (R3), puis disparaît après restauration du fichier d'origine.

**Limites connues** (à lire avant de conclure) :
- analyse **locale à chaque fichier** : pas de suivi inter-modules ni d'import sous un autre nom ;
- un appel construit dynamiquement hors des cas R5/R6 (ex. chaîne reconstruite) peut échapper au contrôle ;
- il vérifie la **forme du code**, pas le comportement de Discord (un message éphémère peut quand même être refusé ou expirer côté client) ;
- la liste `SCANNED_FILES` doit être mise à jour si un nouveau module envoie des messages.

## 4. Matrice des scénarios P01–P13

Les colonnes « Dernier résultat réel » indiquent l'exécution automatisée (`pytest`, sandbox, 2026-10-10). **Aucune** de ces lignes n'est un test sur serveur Discord.
Les tests marqués *(nouveau)* ont été ajoutés pour combler un manque ; les autres existaient avant cette mission.

| ID | Scénario | Test(s) — nom exact, fichier | Ce qui est vérifié | Résultat attendu | Dernier résultat réel | Limites |
|---|---|---|---|---|---|---|
| P01 | Le questionnaire démarre en privé | `test_start_button_sends_ephemeral_step1_with_grip_select` — `tests/test_flow.py` ; `test_p02_p03_p06_full_path_is_private_and_result_goes_to_participant_only` — `tests/test_privacy.py` *(nouveau, 1re étape)* | Le clic sur « Start » répond en `ephemeral=True` avec le menu grip | Réponse éphémère, aucun message public | PASS | Le clic réel n'est pas exécuté ; le message public d'accueil reste un message normal publié par le bot |
| P02 | Toutes les étapes sont privées | `test_p02_p03_p06_full_path_is_private_and_result_goes_to_participant_only` et `test_p02_all_step_openings_are_private` — `tests/test_privacy.py` *(nouveau)* | Parcours complet grip → mesures → budget → résultat, puis ouverture des modals ; `assert_private` sur chaque interaction | Toute réponse `ephemeral=True`, étapes affichées par édition du message éphémère | PASS | Interactions factices ; pas de vérification du rendu client |
| P03 | La soumission du modal de mesures garde le parcours privé | `test_valid_measures_move_to_budget_step` — `tests/test_flow.py` ; étape 3 de `test_p02_p03_p06_…` *(nouveau)* | Soumission valide → étape budget éditée en privé | Pas de nouveau message public, parcours avancé | PASS | — |
| P04 | Erreur de saisie : privée, parcours non avancé | `test_invalid_measures_show_error_and_keep_step` — `tests/test_flow.py` ; `test_p04_invalid_measures_are_private_and_do_not_advance` — `tests/test_privacy.py` *(nouveau)* | Saisie `abc` / `900` : message « Saisie invalide » éphémère, `edit_message` absent, rien enregistré | Erreur privée, aucune mesure stockée | PASS | — |
| P05 | Budget personnalisé et erreurs privés | `test_custom_budget_invalid_then_valid` — `tests/test_flow.py` ; `test_p05_custom_budget_invalid_and_valid_are_private` — `tests/test_privacy.py` *(nouveau)* | Saisie `trois` puis `50` : erreur privée sans avancer, puis validation privée | Erreur privée, budget enregistré seulement si valide | PASS | — |
| P06 | Résultat final visible par le seul participant | `test_p02_p03_p06_…` — `tests/test_privacy.py` *(nouveau)* ; `test_results_close_is_owner_only_and_clears_message` — `tests/test_flow.py` | Le second participant ne reçoit ni édition ni message ; le résultat n'est édité que dans l'interaction du participant | Résultat uniquement dans la réponse du participant | PASS | Pas de test du rendu visuel du message |
| P07 | Deux utilisateurs simultanés sans mélange | `test_p07_two_simultaneous_participants_do_not_mix_data` — `tests/test_privacy.py` *(nouveau)* ; `test_replacing_one_users_session_does_not_touch_another_user` — `tests/test_session.py` | Interclassement : grips, mesures et résultats distincts ; le résultat de chacun ne contient que ses mesures | Données strictement séparées | PASS | Concurrence simulée séquentiellement (une seule boucle asyncio), pas en parallèle réel |
| P08 | Un utilisateur ne peut pas agir sur le parcours d'un autre | `test_p08_intruder_cannot_act_on_any_step_of_another_session` et `test_p08_intruder_cannot_use_results_buttons_of_another_user` — `tests/test_privacy.py` *(nouveau)* ; `test_other_user_cannot_use_session_id`, `test_other_user_cannot_open_measures_or_submit_modal`, `test_results_restart_is_owner_only` — `tests/test_flow.py` ; `test_other_user_cannot_use_session_id` — `tests/test_session.py` | Grip, ouverture des mesures, soumission de modal, budget et boutons du résultat tentés par un intrus : refus éphémère, aucun changement d'état | Refus « Cette action n'est pas disponible pour votre compte. », état inchangé | PASS | Vérifie aussi que le contrôle n'est pas trivial : la mutation du contrôle de propriétaire (voir §6) fait échouer ces tests |
| P09 | Une nouvelle recherche ne modifie ni un autre parcours ni l'ancien | `test_p09_new_search_does_not_touch_other_users_session` — `tests/test_privacy.py` *(nouveau)* ; `test_new_start_replaces_previous_session_of_same_user`, `test_replacing_one_users_session_does_not_touch_another_user` — `tests/test_session.py` ; `test_stale_grip_menu_cannot_write_into_new_session` — `tests/test_flow.py` | Relance de l'utilisateur 1 : session de l'utilisateur 2 intacte ; ancienne session de l'utilisateur 1 inactive | Autre session intacte ; ancienne session inutilisable | PASS | **Conception** : une session précédente du *même* utilisateur n'est pas conservée valide (un seul parcours actif par utilisateur). Ce n'est pas une « session encore valide » qui coexiste |
| P10 | Session expirée inutilisable normalement | `test_session_expires_after_ttl_and_activity_refreshes_it` — `tests/test_session.py` ; `test_expired_session_informs_user_privately` — `tests/test_flow.py` ; `test_p10_expired_session_cannot_be_used_and_is_removed` — `tests/test_privacy.py` *(nouveau)* | Horloge factice +61 s : grip et budget refusés en privé, session retirée du store | Message « n'est plus actif », session supprimée | PASS | Durée réelle (`SESSION_TTL_SECONDS`) non attendue ; horloge simulée |
| P11 | Après redémarrage : panneau persistant fonctionnel, anciennes interactions traitées | `test_p11_persistent_panel_works_after_restart_in_fresh_bot_instance` — `tests/test_privacy.py` *(nouveau)* | Deux instances `MouseBot` successives : la seconde enregistre `StartView` (custom_id fixe), a un store vide ; le bouton répond ; un ancien menu renvoie « plus actif » | Panneau opérationnel, ancien menu refusé proprement | PASS | **Simulé** : le routage réel des interactions après redémarrage Discord n'est pas testé. À vérifier sur serveur (protocole, étape 10) |
| P12 | « Fermer » ne touche que le résultat de son propriétaire | `test_p12_close_affects_only_owner_result_and_no_session` et `test_results_buttons_still_work_after_session_was_discarded` — `tests/test_privacy.py` *(nouveau)* ; `test_results_close_is_owner_only_and_clears_message` — `tests/test_flow.py` | Fermeture par un intrus : rien ; fermeture par le propriétaire : message vidé ; autre session intacte ; « Fermer » et « Refaire le test » fonctionnent après suppression de la session | Fermeture limitée au propriétaire, sans effet sur les autres | PASS | — |
| P13 | Le contrôle statique détecte les chemins d'envoi publics de données individuelles | `tests/test_privacy_scan.py` (5 cas valides, 14 violations, dépôt réel, injection et restauration) | Voir §3 | Aucune violation sur le dépôt ; violations détectées dans les variantes | PASS | Analyse locale, forme du code seulement (voir §3) |

Aucun test n'a été ajouté pour « faire le nombre » : chaque nouveau test couvre un enchaînement qui n'était pas testé
de bout en bout (P02, P07, P08 et P12 sur les boutons de résultat, P09, P11).

## 5. Limites transverses (non couvertes par les tests)

- **Journaux** : les gestionnaires d'erreur appellent `log.exception(..., exc_info=error)`. Une exception inattendue peut écrire dans les journaux son message, qui pourrait contenir une valeur saisie. Les erreurs de saisie attendues (`InputError`) ne sont pas journalisées. Non testé ; à relire si la validation évolue.
- **Discord réel** : routage des interactions, durée de vie des jetons d'interaction (environ 15 minutes), rendu des messages éphémères, et comportement du client en cas de double clic : **aucun test automatisé**.
- **Concurrence** : les tests simulent des utilisateurs entrelacés dans une même boucle asyncio ; ils ne reproduisent pas des requêtes réellement simultanées.
- **Stockage** : les sessions sont en mémoire. Un redémarrage les supprime (voulu : aucune donnée personnelle n'est écrite sur disque). Le message d'accueil persiste dans `state/finder_message.json` (identifiant de message uniquement).
- **Données de session après résultat** : la session est supprimée à l'affichage du résultat (`test_results_discard_session_after_display`). Le résultat affiché reste dans le message éphémère de Discord, hors de contrôle du bot.

## 6. Preuves d'exécution

- Suite complète : voir `docs/audit/RAPPORT_FINAL.md` §4 (commande et résultat exacts).
- Mutation contrôlée (exécutée le 2026-10-10) : suppression du contrôle de propriétaire dans `SessionStore.lookup` → **3 tests échouent** (`test_p08_intruder_cannot_act_on_any_step_of_another_session`, `test_other_user_cannot_use_session_id` dans `test_flow.py` et `test_session.py`). Fichier restauré, comparaison binaire identique à l'original.
- Contrôle statique : `python tools/privacy_scan.py` → `0 violation(s)` sur le dépôt ; échec/réussite démontrés par `test_injected_violation_in_real_flow_module_is_reported`.

## 7. Conclusion

Au niveau du code et des tests automatisés, les scénarios P01 à P13 sont couverts et passent. **Ce n'est pas une validation de confidentialité sur Discord.** Le statut reste « à valider sur serveur » tant que le protocole `PROTOCOLE_DISCORD_CONFIDENTIALITE.md` n'a pas été exécuté et son résultat consigné.
