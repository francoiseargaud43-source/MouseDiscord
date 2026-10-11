# Protocole de validation en conditions réelles — Mouse Shape Finder sur Discord

**Statut : NON EXÉCUTÉ.** Aucune des 10 étapes ci-dessous n'a été réalisée sur un serveur Discord réel.
Les résultats se consignent dans le tableau final, à remplir par la personne qui exécute le protocole.
Tant que ce tableau n'est pas rempli, le projet n'est **pas** validé en conditions réelles.

Référence : `docs/audit/AUDIT_CONFIDENTIALITE.md` (matrice P01–P13 et limites des tests automatisés).

---

## A. Ce qui est déjà automatisé (ne pas refaire à la main)

Ces contrôles tournent sans Discord et ont été exécutés dans la sandbox de développement (voir `RAPPORT_FINAL.md` §4).
Ils ne prouvent **pas** le comportement de Discord.

| Étape du protocole | Contrôle automatisé existant |
|---|---|
| 1. Publier le panneau | `tests/test_setup_command.py` : publication, édition sans doublon, message supprimé, salon erroné |
| 2. Deux parcours, même salon | `tests/test_privacy.py::test_p07_two_simultaneous_participants_do_not_mix_data`, `tests/test_session.py` |
| 3. Dimensions différentes | `tests/test_privacy.py::test_p07_…` (vérifie « 180 × 90 » et « 170 × 80 » séparés) |
| 4. Grips et budgets différents | `tests/test_privacy.py::test_p07_…`, `tests/test_flow.py::test_custom_budget_invalid_then_valid` |
| 5. Soumettre les modals | `tests/test_flow.py::test_valid_measures_move_to_budget_step`, `test_custom_budget_invalid_then_valid` |
| 6. Erreur de saisie privée | `tests/test_privacy.py::test_p04_…`, `test_p05_…` |
| 7. Terminer les deux parcours | `tests/test_privacy.py::test_p02_p03_p06_…` |
| 8. Chacun ne voit que son résultat | `tests/test_privacy.py::test_p12_…`, `test_flow.py::test_results_close_is_owner_only_and_clears_message` |
| 9. Anciens composants / bouton d'un autre | `tests/test_privacy.py::test_p09_old_components_are_refused_and_never_modify_new_session`, `test_p09_old_results_buttons_do_not_affect_new_session`, `test_p08_…` |
| 10. Expiration et redémarrage | `tests/test_privacy.py::test_p10_…`, `test_p11_…` (simulé), `tests/test_session.py::test_session_expires_after_ttl_and_activity_refreshes_it` |
| Contrôle statique du code | `python tools/privacy_scan.py` → `0 violation(s)` |

**Ce qui n'est PAS automatisé et doit être fait par vous :** les étapes 1 à 10 telles qu'elles se déroulent dans
l'application Discord (routage des interactions, rendu des messages éphémères, comportement réel après redémarrage).

---

## B. Prérequis (à préparer avant de commencer)

| # | Élément | Comment vérifier |
|---|---|---|
| B1 | **Serveur Discord de test** créé par vous (pas un serveur public) | Discord > Ajouter un serveur |
| B2 | **Deux comptes Discord distincts** : compte **A** et compte **B** (deux comptes réellement différents, pas deux onglets du même compte) | Le compte B doit être membre du serveur de test. Un troisième compte, optionnel, peut servir à l'étape 9 |
| B3 | **Un compte administrateur** du serveur (peut être A ou un troisième) pour lancer `!setup_finder` | Permission « Gérer le serveur » |
| B4 | **Application Discord et token** créés sur https://discord.com/developers/applications, bot invité avec les permissions du `README.md` | Onglet **Bot** ; **Message Content Intent** activé |
| B5 | **Un salon dédié** (ex. `#mouse-finder`) ; son identifiant copié (mode développeur de Discord) dans `FINDER_CHANNEL_ID` | Clic droit sur le salon > Copier l'identifiant |
| B6 | **Configuration** : fichier `.env` avec `DISCORD_TOKEN`, `FINDER_CHANNEL_ID`, `LOCK_FINDER_CHANNEL=true` | Ne jamais publier le fichier ni le token |
| B7 | **Version testée notée** : `git rev-parse --short HEAD` | Doit correspondre au commit de la validation |
| B8 | **Contrôle de déploiement** (sur la machine ou l'hébergement où tourne le bot) : `python tools/check_deployment.py` → aucune ERREUR | Les ATTENTION sont notées, non bloquantes |
| B9 | **Une seule instance du bot** en cours | Voir `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` §9 |
| B10 | **Durée de session de test** : pour l'étape 10, `SESSION_TTL_SECONDS=120` dans `.env`, puis remettre la valeur d'origine (défaut `1800`) | Relancer le bot après modification |

Notez avant de commencer : date, heure, commit, comptes utilisés (noms d'affichage), valeur de `SESSION_TTL_SECONDS`, lieu d'exécution du bot (PC ou Alwaysdata).

**Textes exacts attendus dans l'application** (copiés du code, à comparer caractère par caractère) :
- Refus : `🔒 Cette action n'est pas disponible pour votre compte.`
- Parcours périmé : `⏱️ Ce parcours n'est plus actif (expiré ou remplacé par un nouveau test). Cliquez à nouveau sur **Start Mouse Shape Finder**.`
- Erreur de saisie : un message commençant par `❌ **Saisie invalide**`.
- Panneau : bouton **Start Mouse Shape Finder**.

---

## C. Déroulement (10 étapes)

Pour chaque étape : faites l'action, comparez à « Attendu », cochez OK ou KO, et notez ce que **chaque compte** voit
(captures d'écran autorisées, à condition de masquer le token et les identifiants de salon si vous les publiez).

### Étape 1 — Publier le panneau
1. Compte administrateur, dans le salon `#mouse-finder` : tapez `!setup_finder`.
2. Attendu : un message d'accueil visible par **tous** les membres, avec le bouton **Start Mouse Shape Finder**. Les membres ne peuvent pas écrire dans le salon (si `LOCK_FINDER_CHANNEL=true`).
3. Tapez `!setup_finder` une **deuxième** fois.
4. Attendu : le **même** message est édité ; il n'y a pas de deuxième panneau.
- ☐ OK ☐ KO — Observé : ______________________

### Étape 2 — Deux parcours dans le même salon
1. Compte A : cliquez **Start Mouse Shape Finder**. Attendu : un menu « Votre grip » visible **seulement pour A**.
2. Compte B : cliquez **Start Mouse Shape Finder**. Attendu : un menu visible **seulement pour B**. Le menu de A ne change pas.
3. Attendu : aucun message public autre que le panneau (pas de « A a commencé… »).
- ☐ OK ☐ KO — Observé : ______________________

### Étape 3 — Dimensions différentes
1. Compte A : grip **Palm** ; bouton **Saisir mes mesures** ; longueur `180`, largeur `90`.
2. Compte B : grip **Claw** ; mesures `170` et `80`.
3. Attendu : chaque récapitulatif affiche **ses** valeurs. A ne voit jamais « 170 × 80 » ; B ne voit jamais « 180 × 90 ».
- ☐ OK ☐ KO — Observé : ______________________

### Étape 4 — Grips et budgets différents
1. Compte A : budget **Économique**.
2. Compte B : budget **Personnalisé** puis montant `50` (modal) — ou **Haut de gamme** si vous préférez.
3. Attendu : chaque parcours avance indépendamment ; le budget de A n'apparaît pas chez B.
- ☐ OK ☐ KO — Observé : ______________________

### Étape 5 — Soumettre les modals
1. Compte A : la saisie des mesures a été validée à l'étape 3 : vérifiez que l'étape suivante (budget) s'affiche dans le même message privé.
2. Compte B : si budget personnalisé, vérifiez que la validation du modal `50` fait avancer le menu privé.
3. Attendu : aucune réponse publique ; chaque validation met à jour **le message privé** de son auteur.
- ☐ OK ☐ KO — Observé : ______________________

### Étape 6 — Confidentialité des erreurs de saisie
1. Compte A : rouvrez les mesures, saisissez longueur `abc`, largeur `900`, validez.
2. Attendu : un message `❌ **Saisie invalide**` **visible seulement pour A** ; le parcours ne passe pas à l'étape suivante.
3. Compte B : vérifiez qu'il ne voit ni le message d'erreur, ni la valeur `abc`.
4. Compte A : saisissez `180` / `90`, validez. Attendu : le parcours avance.
5. Compte B : si budget personnalisé, saisissez `trois` puis `50`. Attendu : erreur privée puis acceptation.
- ☐ OK ☐ KO — Observé : ______________________

### Étape 7 — Terminer les deux parcours
1. Compte A puis compte B : terminez le parcours jusqu'au résultat.
2. Attendu : chacun reçoit son **résultat** dans son message privé (match idéal, alternative, économie ; boutons d'achat réels ou « 🔗 Liens à venir »), **sans aucun bouton interactif** (ni Fermer, ni Refaire, ni Détails).
- ☐ OK ☐ KO — Observé : ______________________

### Étape 8 — Chacun ne voit que son résultat
1. Compte A : vérifiez que le résultat contient **180 × 90** et jamais **170 × 80**.
2. Compte B : vérifiez le contraire.
3. Compte B : vérifiez qu'aucun bouton interactif n'apparaît côté bot (seuls des liens 🛒 / « 🔗 Liens à venir »).
4. Compte A : même vérification ; clic en dehors d'un lien → Discord ne doit jamais afficher « n'a pas répondu à temps ».
- ☐ OK ☐ KO — Observé : ______________________

### Étape 9 — Anciens composants et bouton d'un autre utilisateur
Cette étape vérifie les **anciens composants** : après une relance, un menu ouvert avant la relance ne doit plus fonctionner, et ne doit jamais modifier le nouveau parcours.
1. Compte A : cliquez **Start** → menu **M1** (ne rien faire dedans).
2. Compte A : cliquez **Start** une seconde fois → menu **M2**. Attendu : M2 s'affiche normalement.
3. Compte A : dans **M1** (ancien), choisissez un grip ou cliquez **Saisir mes mesures**.
   Attendu : `⏱️ Ce parcours n'est plus actif…` ; **M2 n'a pas changé** (vérifiez que ses choix précédents sont intacts).
4. Compte A : dans **M2**, continuez normalement. Attendu : le parcours fonctionne.
5. Compte B : si vous avez un troisième compte (ou un second navigateur connecté au compte B), ouvrez le résultat de A sur ce compte. Attendu : refus `🔒 Cette action n'est pas disponible pour votre compte.` ; ne pas confondre avec l'étape 8, où Discord n'affiche pas un message éphémère d'un autre compte.
- ☐ OK ☐ KO ☐ Non testable tel quel (aucun moyen d'afficher le composant d'un autre compte) — Observé : ______________________

### Étape 10 — Expiration et redémarrage
**10a. Expiration** (avec `SESSION_TTL_SECONDS=120`, bot relancé) :
1. Compte A : **Start**, puis attendez plus de 2 minutes sans agir.
2. Cliquez un bouton du menu. Attendu : `⏱️ Ce parcours n'est plus actif…`, rien n'est enregistré.
3. Cliquez **Start** à nouveau : le parcours recommence normalement.
4. Remettez `SESSION_TTL_SECONDS` à sa valeur d'origine et relancez le bot.

**10b. Redémarrage** :
1. Compte A : ouvrez un menu **M3** et ne le terminez pas.
2. Arrêtez le bot (PC : `Ctrl+C` ; Alwaysdata : voir `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` §7.3–7.4), puis relancez-le (PC : `python bot.py` ; Alwaysdata : `Redémarrer`).
3. Vérifiez qu'**une seule** instance tourne (guide §9).
4. Compte A : cliquez un bouton de **M3**. Attendu : `⏱️ Ce parcours n'est plus actif…` (les sessions sont en mémoire et disparaissent au redémarrage).
5. Compte B : cliquez **Start** sur le **message d'accueil existant** (sans relancer `!setup_finder`). Attendu : le parcours démarre.
6. Attendu : aucun second message d'accueil n'a été publié.
- ☐ OK ☐ KO — Observé : ______________________

---

## D. Tableau de consignation (à remplir après exécution)

| Étape | Attendu | Observé (qui a vu quoi) | Statut |
|---|---|---|---|
| 1. Panneau | un message, relance = édition | | ☐ Non exécuté |
| 2. Deux parcours | menus séparés, rien en public | | ☐ Non exécuté |
| 3. Dimensions | récapitulatifs distincts | | ☐ Non exécuté |
| 4. Grips et budgets | parcours indépendants | | ☐ Non exécuté |
| 5. Modals | validation privée | | ☐ Non exécuté |
| 6. Erreurs de saisie | erreur privée, pas d'avancement | | ☐ Non exécuté |
| 7. Fin des deux parcours | chacun son résultat | | ☐ Non exécuté |
| 8. Résultats séparés | pas de mélange ; aucun bouton interactif | | ☐ Non exécuté |
| 9. Anciens composants | refus propre, nouvelle session intacte | | ☐ Non exécuté |
| 10. Expiration et redémarrage | « plus actif », panneau opérationnel, pas de doublon | | ☐ Non exécuté |

**Informations à consigner** : date, commit (B7), hébergement (PC ou Alwaysdata), comptes utilisés, TTL utilisé, KO éventuels avec le texte exact affiché.

**Ce que ce protocole ne prouve pas** : la sécurité des comptes, la conservation de données par Discord, le comportement des clients Discord autres que celui utilisé, ni la charge d'un serveur réel.
