# Audit de confidentialité — Mouse Shape Finder

Date : 2026-10-10 (mise à jour 2026-10-11 : le parcours compte désormais 4 étapes + un résultat en deux embeds ; les règles de confidentialité sont inchangées) · Branche d'origine : `arena/33e33710-mousediscord` · Périmètre : parcours Discord du Mouse Shape Finder (`cogs/finder_flow.py`, `utils/session.py`, `cogs/mouse_finder.py`).

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
| Identifiant de session | Chaque parcours reçoit un `session_id` aléatoire (`secrets.token_urlsafe`), qui sert de clé interne. **Depuis le 2026-10-12, il ne circule plus dans les messages** : les composants portent des identifiants fixes et l'action se rattache au parcours vivant du membre qui clique (`SessionStore.current`). | `utils/session.py` |
| Double contrôle | `SessionStore.current` résout le parcours **par le membre** (aucun identifiant ne peut être injecté depuis un message) ; `SessionStore.lookup` vérifie en plus l'identifiant **et** le propriétaire, la durée de vie (TTL) et que le parcours est bien le parcours actif. Défense en profondeur. | `utils/session.py`, `_current_session` |
| Un parcours actif par utilisateur | Un nouveau démarrage remplace le précédent : l'ancien parcours est supprimé, ses menus agissent alors sur le parcours vivant du membre (jamais sur celui d'un autre). | `SessionStore.start` |
| Durabilité des composants | Tous les menus et formulaires sont enregistrés au démarrage (`persistent_views()` → `Bot.add_view`), sans délai et avec des identifiants fixes : un clic reste reconnu après un redémarrage du bot (panne corrigée le 2026-10-12, voir `docs/audit/ROBUSTESSE_2026-10-12.md`). | `cogs/finder_flow.py`, `bot.py` |
| Résultat sans action | Le résultat ne porte plus aucun composant interactif (liens d'achat uniquement, ou rappel « 🔗 Liens à venir » désactivé) : aucune action d'un tiers n'est possible. | `cogs/finder_flow.py` |
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
| P02 | Toutes les étapes sont privées | `test_p02_p03_p06_full_path_is_private_and_result_goes_to_participant_only` et `test_p02_all_step_openings_are_private` — `tests/test_privacy.py` *(nouveau)* | Parcours complet grip → thénar → mesures → budget → résultat (5 étapes depuis le 2026-10-11), puis ouverture des modals ; `assert_private` sur chaque interaction | Toute réponse `ephemeral=True`, étapes affichées par édition du message éphémère | PASS | Interactions factices ; pas de vérification du rendu client |
| P03 | La soumission du modal de mesures garde le parcours privé | `test_valid_measures_move_to_budget_step` — `tests/test_flow.py` ; étape 4 de `test_p02_p03_p06_…` *(nouveau)* | Soumission valide → étape budget éditée en privé | Pas de nouveau message public, parcours avancé | PASS | — |
| P04 | Erreur de saisie : privée, parcours non avancé | `test_invalid_measures_show_error_and_keep_step` — `tests/test_flow.py` ; `test_p04_invalid_measures_are_private_and_do_not_advance` — `tests/test_privacy.py` *(nouveau)* | Saisie `abc` / `900` : message « Saisie invalide » éphémère, `edit_message` absent, rien enregistré | Erreur privée, aucune mesure stockée | PASS | — |
| P05 | Budget personnalisé et erreurs privés | `test_custom_budget_invalid_then_valid` — `tests/test_flow.py` ; `test_p05_custom_budget_invalid_and_valid_are_private` — `tests/test_privacy.py` *(nouveau)* | Saisie `trois` puis `50` : erreur privée sans avancer, puis validation privée | Erreur privée, budget enregistré seulement si valide | PASS | — |
| P06 | Résultat final visible par le seul participant | `test_p02_p03_p06_…` — `tests/test_privacy.py` *(nouveau)* ; `test_results_close_is_owner_only_and_clears_message` — `tests/test_flow.py` | Le second participant ne reçoit ni édition ni message ; le résultat n'est édité que dans l'interaction du participant | Résultat uniquement dans la réponse du participant | PASS | Pas de test du rendu visuel du message |
| P07 | Deux utilisateurs simultanés sans mélange | `test_p07_two_simultaneous_participants_do_not_mix_data` — `tests/test_privacy.py` *(nouveau)* ; `test_replacing_one_users_session_does_not_touch_another_user` — `tests/test_session.py` | Interclassement : grips, mesures et résultats distincts ; le résultat de chacun ne contient que ses mesures | Données strictement séparées | PASS | Concurrence simulée séquentiellement (une seule boucle asyncio), pas en parallèle réel |
| P08 | Un utilisateur ne peut pas agir sur le parcours d'un autre | `test_p08_intruder_cannot_act_on_any_step_of_another_session` et `test_p08_intruder_cannot_use_results_buttons_of_another_user` — `tests/test_privacy.py` *(nouveau)* ; `test_intruder_acts_only_on_his_own_parcours`, `test_intruder_cannot_open_the_measures_of_someone_else` — `tests/test_flow.py` ; `test_other_user_cannot_use_session_id` — `tests/test_session.py` | Grip, ouverture des mesures, soumission de modal, budget et boutons du résultat tentés par un intrus : refus éphémère, aucun changement d'état | Refus privé (message d'expiration + bouton de reprise), état de la victime inchangé | PASS | Vérifie aussi que le contrôle n'est pas trivial : la mutation du contrôle de propriétaire (voir §6) fait échouer ces tests |
| P09 | Une nouvelle recherche ne modifie ni un autre parcours ni l'ancien | `test_p09_new_search_does_not_touch_other_users_session` — `tests/test_privacy.py` *(nouveau)* ; `test_p09_old_components_are_refused_and_never_modify_new_session` et `test_p09_old_results_buttons_do_not_affect_new_session` — `tests/test_privacy.py` *(nouveau, non-régression)* ; `test_new_start_replaces_previous_session_of_same_user`, `test_replacing_one_users_session_does_not_touch_another_user` — `tests/test_session.py` ; `test_old_message_never_breaks_a_running_parcours` — `tests/test_flow.py` | Relance de l'utilisateur 1 : session de l'utilisateur 2 intacte ; ancienne session de l'utilisateur 1 inactive ; grip, mesures, modal de mesures, budget et modal de budget **de l'ancienne session** refusés (« plus actif », aucune édition, aucun modal) ; état de la **nouvelle** session identique avant et après ces tentatives ; la nouvelle session reste utilisable | Autre session intacte ; ancienne session inutilisable ; nouvelle session jamais modifiée | PASS | **Décision confirmée par le propriétaire** : une seule session active par utilisateur. Relancer un test invalide l'ancienne session (elle ne coexiste pas avec la nouvelle) |
| P10 | Session expirée inutilisable normalement | `test_session_expires_after_ttl_and_activity_refreshes_it` — `tests/test_session.py` ; `test_expired_session_informs_user_privately` — `tests/test_flow.py` ; `test_p10_expired_session_cannot_be_used_and_is_removed` — `tests/test_privacy.py` *(nouveau)* | Horloge factice +61 s : grip et budget refusés en privé, session retirée du store | Message « a expiré » + bouton de reprise, session supprimée | PASS | Durée réelle (`SESSION_TTL_SECONDS`) non attendue ; horloge simulée |
| P11 | Après redémarrage : panneau persistant fonctionnel, anciennes interactions traitées | `test_p11_persistent_panel_works_after_restart_in_fresh_bot_instance` — `tests/test_privacy.py` *(nouveau)* | Deux `MouseBot` successifs sur le même fichier d'état : le second retrouve le parcours **en cours** (prise, thénar) et ses huit composants enregistrés (6 vues + 2 formulaires) ; le bouton des mesures ouvre bien le formulaire | Parcours repris là où il en était, composants reconnus | PASS | Vérifié dans le registre de distribution de discord.py 2.7.1 ; reste à confirmer par un redémarrage réel sur serveur (`ROBUSTESSE_2026-10-12.md` §4) |
| P12 | Le résultat ne contient aucun composant interactif et ne touche à aucune session | `test_p12_result_has_no_interactive_component_and_touches_no_session` — `tests/test_privacy.py` ; `test_result_view_has_no_interactive_button_only_purchase_links`, `test_result_shows_the_explanation_block_below_the_recommendation`, `test_result_never_mentions_the_excluded_mice` — `tests/test_flow.py` | Seuls des liens d'achat (ou le rappel désactivé) ; aucun clic ne peut modifier un parcours, y compris celui d'un autre | Aucun composant actif côté bot | PASS | Boutons « Fermer » / « Refaire » / « Détails » retirés le 2026-10-11 |
| P14 | Un clic rejoué par Discord après le résultat reçoit le même résultat | `test_p14_replayed_click_after_the_result_gets_the_same_result` — `tests/test_privacy.py` | Le dernier menu du parcours est envoyé deux fois : les deux réponses sont identiques, aucun message d'expiration | Même résultat, aucun cul-de-sac | PASS | Corrige le signalement « ça dit comme quoi c'est plus possible » |
| P15 | Une erreur inattendue est expliquée en privé, jamais un silence | `test_p15_unexpected_error_is_explained_privately_and_never_left_silent`, `test_p15_modal_error_is_also_explained_privately` — `tests/test_privacy.py` | Panne simulée dans une réponse d'étape et dans un formulaire, via le chemin de distribution réel (`_scheduled_task`) | Message privé « erreur inattendue », erreur tracée | PASS | Le message ne contient aucune donnée du parcours |
| P16 | Le fichier d'état ne contient que les parcours en cours | `test_p16_state_file_only_holds_running_parcours` — `tests/test_privacy.py` | Parcours en cours enregistré (prise + mesures) puis terminé : l'entrée disparaît du fichier | Aucune réponse conservée après le résultat | PASS | Contenu minimal, documenté au §5 |
| P17 | Un parcours trop ancien n'est pas restauré au démarrage | `test_p17_expired_parcours_is_not_restored` — `tests/test_privacy.py` | Entrée vieillie au-delà du TTL : le magasin relu ne la reprend pas | Expiration respectée après redémarrage | PASS | — |
| P18 | Un fichier d'état illisible ne bloque jamais le bot | `test_p18_unreadable_state_file_never_breaks_the_bot` — `tests/test_privacy.py` | Fichier corrompu : démarrage normal, nouveau parcours utilisable | Bot opérationnel | PASS | L'incident est journalisé, jamais montré |
| P13 | Le contrôle statique détecte les chemins d'envoi publics de données individuelles | `tests/test_privacy_scan.py` (5 cas valides, 14 violations, dépôt réel, injection et restauration) | Voir §3 | Aucune violation sur le dépôt ; violations détectées dans les variantes | PASS | Analyse locale, forme du code seulement (voir §3) |

Aucun test n'a été ajouté pour « faire le nombre » : chaque nouveau test couvre un enchaînement qui n'était pas testé
de bout en bout (P02, P07, P08 et P12 sur les boutons de résultat, P09, P11).

## 5. Limites transverses (non couvertes par les tests)

- **Journaux** : les gestionnaires d'erreur appellent `log.exception(..., exc_info=error)`. Une exception inattendue peut écrire dans les journaux son message, qui pourrait contenir une valeur saisie. Les erreurs de saisie attendues (`InputError`) ne sont pas journalisées. Non testé ; à relire si la validation évolue.
- **Discord réel** : routage des interactions, durée de vie des jetons d'interaction (environ 15 minutes), rendu des messages éphémères, et comportement du client en cas de double clic : **aucun test automatisé**.
- **Concurrence** : les tests simulent des utilisateurs entrelacés dans une même boucle asyncio ; ils ne reproduisent pas des requêtes réellement simultanées.
- **Stockage** : les parcours **EN COURS** sont écrits dans `state/sessions.json` (chemin `SESSION_STATE_PATH`), en écriture atomique, avec l'âge du dernier geste. Contenu minimal : identifiant de parcours, identifiant Discord du membre, réponses données sous forme de valeurs numériques et d'énumérations (prise, variante, thénar, longueur/largeur de main, mode et plafond de budget). Aucun texte libre, aucun message, aucune donnée d'un tiers. Un parcours trop ancien (TTL 30 min par défaut) n'est pas repris au démarrage. `SESSION_PERSIST=false` revient au tout-mémoire.
- **Données de session après résultat** : à l'affichage du résultat, le parcours passe en `finished` — ses réponses **quittent immédiatement le fichier d'état** (`test_p16_state_file_only_holds_running_parcours`) et il reste quelques minutes en mémoire seulement (rejeu d'une interaction par Discord). Le résultat affiché reste dans le message éphémère de Discord, hors de contrôle du bot.
- **Accès croisé** : structurellement impossible — l'action ne contient jamais d'identifiant de parcours, elle part de l'identifiant Discord du membre qui clique. Un intrus sans parcours reçoit le message d'expiration (avec le bouton de reprise) et l'état de la victime reste identique (`test_p08_*`, `test_intruder_*`).

## 6. Preuves d'exécution

- Suite complète : voir `docs/audit/RAPPORT_FINAL.md` §4 (commande et résultat exacts).
- Mutation contrôlée (exécutée le 2026-10-10) : suppression du contrôle de propriétaire dans `SessionStore.lookup` → **3 tests échouaient** (`test_p08_intruder_cannot_act_on_any_step_of_another_session`, `test_other_user_cannot_use_session_id` dans `test_flow.py` et `test_session.py`). Fichier restauré, comparaison binaire identique à l'original.
- **Depuis le 2026-10-12**, ce contrôle est une défense en profondeur : la protection principale est le rattachement par membre (`SessionStore.current`), qui ne lit aucun identifiant dans le message. Le test de mutation correspondant est donc : rendre `current()` sensible à un identifiant fourni → les tests `test_intruder_*` et `test_p08_*` ne peuvent plus passer, puisque l'intrus agirait alors sur le parcours de la victime (aucun identifiant de parcours n'étant disponible dans un composant, cette mutation est aujourd'hui impossible à écrire : c'est précisément l'intérêt du changement).
- Contrôle statique : `python tools/privacy_scan.py` → `0 violation(s)` sur le dépôt ; échec/réussite démontrés par `test_injected_violation_in_real_flow_module_is_reported`.
- **Relance d'un test (P09), mutations de `SessionStore.start` / `lookup`** (exécutées le 2026-10-10, fichier restauré et comparé à HEAD) :
  - **Mutant A** — retrait de `discard_user(user_id)` dans `start()`, contrôle `lookup` conservé : **0 test ne change**. Le comportement observable est identique, car le contrôle de session active protège seul. Conséquence réelle : l'ancienne session reste en mémoire jusqu'à son expiration (observation, sans effet sur la confidentialité).
  - **Mutant B** — retrait de `discard_user` **et** du contrôle de session active : **5 tests échouent**, dont `test_p09_new_search_does_not_touch_other_users_session`, `test_p09_old_components_are_refused_and_never_modify_new_session`, `test_new_start_replaces_previous_session_of_same_user`, `test_replacing_one_users_session_does_not_touch_another_user`, `test_stale_grip_menu_cannot_write_into_new_session`.

## 7. Conclusion

Au niveau du code et des tests automatisés, les scénarios P01 à P18 sont couverts et passent. **Ce n'est pas une validation de confidentialité sur Discord.** Le statut reste « à valider sur serveur » tant que le protocole `PROTOCOLE_DISCORD_CONFIDENTIALITE.md` n'a pas été exécuté et son résultat consigné.

## 8. Statut de validation (à lire avant toute conclusion)

Trois niveaux distincts, à ne jamais confondre :

**8.1 Validé automatiquement (code et tests, sans Discord)** — exécuté dans la sandbox le 2026-10-10 :
- scénarios P01 à P13 couverts par les tests listés en §4 ;
- contrôle statique `tools/privacy_scan.py` : 0 violation ;
- mutations du contrôle de propriétaire et de la bande de largeur détectées par les tests.

**8.2 À valider sur un serveur Discord réel (non réalisé)** — protocole `docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md` :
- routage réel des interactions, rendu des messages éphémères, visibilité réelle entre deux comptes ;
- anciens composants après une relance réelle ; expiration avec le TTL réel ;
- panneau persistant après redémarrage réel (P11 est simulé aujourd'hui) ;
- absence de doublon de panneau après redémarrage ;
- contenu réel des journaux (voir §5).

**8.3 Observé sur Discord réel** : **aucun**. Aucune étape du protocole n'a été exécutée.

Conclusion : la confidentialité du parcours est **validée au niveau du code et des tests automatisés** ; elle n'est **pas validée sur Discord**.

