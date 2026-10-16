# Registre des noms de tests retirés

**But.** Les documents du dépôt citent des tests comme preuves (« vérifié par … »). Quand un test est
renommé ou disparaît avec la fonction qu'il vérifiait, la citation devient un **renvoi mort** : le lecteur
— ou la personne qui exécute le protocole de confidentialité — cherche une preuve qui n'existe pas. Ce
registre tient la correspondance, et deux contrôles automatiques s'y appuient
(`tests/test_doc_references.py`) :

1. un nom de test cité dans un document doit être **un test vivant** ou figurer dans la première colonne
   de ce tableau ;
2. tout nom cité dans les autres colonnes doit être **un test vivant** (un renvoi de ce registre ne peut
   pas pourrir), et un nom de la première colonne ne doit **plus** exister comme test.

Constat du 2026-10-14 (66e passe) : dix-sept citations mortes dormaient dans l'audit de confidentialité,
le protocole de validation, `AUDIT.md` et le master prompt. Détail : §26.53 de
`ROBUSTESSE_2026-10-12.md`.

| Nom retiré | Aujourd'hui | Pourquoi |
|---|---|---|
| `test_results_close_is_owner_only_and_clears_message` | `test_p12_result_has_no_interactive_component_and_touches_no_session` | Le bouton « Terminer » du résultat a été retiré (refonte du 2026-10-11, commit `e2c040e`) : la propriété du résultat se vérifie par l'absence de composant interactif et par `test_p02_p03_p06_full_path_is_private_and_result_goes_to_participant_only`. |
| `test_p08_intruder_cannot_use_results_buttons_of_another_user` | `test_p08_intruder_cannot_act_on_any_step_of_another_session` | Même retrait du bouton ; l'intrus ne peut plus agir sur **aucune** étape d'un autre parcours. |
| `test_p09_old_components_are_refused_and_never_modify_new_session` | `test_p14_replayed_click_after_the_result_gets_the_same_result` | Renommage du 2026-10-13 (commit `04324d0`) ; le clic rejoué après le résultat est couvert aussi par `test_old_message_never_breaks_a_running_parcours`. |
| `test_p09_old_results_buttons_do_not_affect_new_session` | `test_p12_result_has_no_interactive_component_and_touches_no_session` | Le bouton a été retiré : il n'y a plus de composant à rejouer sur l'ancien résultat. |
| `test_p11_persistent_panel_works_after_restart_in_fresh_bot_instance` | `test_p11_a_restart_keeps_the_running_parcours_and_its_components` | Renommage du 2026-10-13 (`04324d0`) ; même scénario : deux `MouseBot` successifs sur le même fichier d'état. |
| `test_result_shows_the_explanation_block_below_the_recommendation` | `test_result_sections_follow_the_reference_tool_order` | Renommage du 2026-10-11 (commit `fc375dc`) : le contrôle porte sur l'ordre des sections, pas sur un bloc isolé. |
| `test_stale_grip_menu_cannot_write_into_new_session` | `test_old_message_never_breaks_a_running_parcours` | Renommage du 2026-10-13 (`04324d0`) : un vieux message ne casse plus un parcours en cours. |
| `test_thenar_is_stored_and_not_scored` | `test_thenar_selection_stores_value_and_moves_to_measures` | Le thénar a été implémenté (2026-10-11, `a4a8ba7`) et la vérification s'est scindée en deux : stockage (ci-contre) et barème (ci-dessous). |
| `test_thenar_not_affecting_score` | `test_thenar_never_changes_the_score` | Même scission ; le second nom est celui du master prompt, le test vivant est dans `tests/test_matcher.py`, doublé par `test_thenar_never_changes_the_recommendation`. |
| `test_thenar_petite_adds_a_purely_informative_narrow_rear_note` | `test_thenar_petite_ou_moyenne_ajoute_le_paragraphe_arriere_etroit` | Renommage du 2026-10-11 (`a4a8ba7`) : la note est un paragraphe illustré, pas une ligne informative. Renommé une seconde fois le 2026-10-14 : le test couvre désormais Petite **et** Moyenne. |
| `test_thenar_petite_adds_a_narrow_rear_paragraph_with_its_illustration` | `test_thenar_petite_ou_moyenne_ajoute_le_paragraphe_arriere_etroit` | Le nom parlait de « Petite » seulement, ce qui n'est plus la règle. |
| `test_thenar_step` | `test_grip_selection_edits_message_to_thenar_step` | Nom proposé dans le master prompt avant l'implémentation ; le test livré porte le nom du parcours (`tests/test_flow.py`). |
| `test_expired_session_informs_user` | `test_expired_session_informs_user_privately` | Citation tronquée dans `AUDIT.md` : le test a toujours dit « privément ». |
| `test_l_arriere_etroit_reste_reserve_au_thenar_petite_malgre_la_reference` | `test_l_arriere_etroit_suit_la_reference_pour_petite_et_moyenne` | Écart refermé le 2026-10-14 : le bot suit la référence (arrière étroit conseillé à Petite ET Moyenne) ; l'ancien nom disait le contraire, il ne pouvait pas rester. |

Les deux rapports **datés** (`RAPPORT_FINAL.md` du 2026-10-10, `REPORTE_DESIGN.md` du 2026-10-11) citent
les noms de la suite de leur jour et gardent donc leurs citations : le premier est le rapport de migration
lui-même (« Supprimé », « Devient … »), le second décrit le design tel qu'il était alors.
