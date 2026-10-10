# Protocole manuel — confidentialité du Mouse Shape Finder sur Discord

**Statut : protocole à exécuter. Il n'a PAS été exécuté.** Aucun test sur serveur Discord réel n'a été réalisé lors de la
rédaction de ce document. Les résultats se consignent dans le tableau de la fin, à remplir par la personne qui exécute le protocole.

Référence : `docs/audit/AUDIT_CONFIDENTIALITE.md` (ce que les tests automatisés couvrent, et ce qu'ils ne couvrent pas).

## 0. Prérequis

| Élément | Détail |
|---|---|
| Serveur Discord de test | Un serveur à vous (pas de serveur public). |
| Comptes | **Deux** comptes Discord différents : `Compte A` et `Compte B`. Un compte administrateur pour `!setup_finder`. |
| Bot | Lancé avec la version à tester (commit à noter : `git rev-parse --short HEAD`). Permissions : voir `README.md`, section « Discord ». |
| Intents | « Message Content Intent » activé dans le portail développeur (sinon le bot ne démarre pas). |
| Salon | Un salon dédié, identifiant copié dans `FINDER_CHANNEL_ID`. |
| Durée de session | Pour l'étape 10, réglez `SESSION_TTL_SECONDS=120` dans `.env` **pour ce test seulement**, puis remettez la valeur d'origine. |
| Instance unique | Un seul bot doit tourner (vérifiez-le avant de commencer : deux instances donnent des réponses en erreur). |

**Noter avant de commencer** : date et heure, commit testé, valeur de `SESSION_TTL_SECONDS`, noms des comptes A et B.

## 1. Publier le panneau

1. Compte administrateur : dans le salon de test, lancez `!setup_finder`.
2. Vérifiez : un message d'accueil « Start Mouse Shape Finder » est publié (visible par tous) et le salon est verrouillé en écriture pour les membres (si `LOCK_FINDER_CHANNEL=true`).
3. Relancez `!setup_finder` une seconde fois : le **même** message doit être **édité** (aucun doublon).

Attendu : un seul message d'accueil. Résultat : ☐ OK ☐ KO — ____

## 2. Deux parcours dans le même salon

1. Compte A : cliquez sur **Start**. Un menu « Votre grip » apparaît **uniquement** pour A.
2. Compte B : cliquez sur **Start**. Un menu apparaît **uniquement** pour B. Le menu de A reste inchangé pour A.
3. Vérifiez que B ne voit pas le menu de A dans le salon (les messages éphémères ne doivent pas être visibles par les autres).

Attendu : deux parcours distincts, aucun message public autre que le panneau. Résultat : ☐ OK ☐ KO — ____

## 3. Dimensions différentes par compte

1. Compte A : grip **Palm**, mesures **180 × 90** mm.
2. Compte B : grip **Claw**, mesures **170 × 80** mm.

Attendu : chaque compte voit uniquement ses propres valeurs dans son récapitulatif. Résultat : ☐ OK ☐ KO — ____

## 4. Grips et budgets différents

1. Compte A : budget **Économique**.
2. Compte B : budget **Haut de gamme** (ou **Personnalisé** avec `50` €).

Attendu : les deux parcours avancent indépendamment ; le budget de A n'apparaît pas chez B. Résultat : ☐ OK ☐ KO — ____

## 5. Soumettre les modals

1. Compte A : bouton **Saisir mes mesures**, saisissez `180` et `90`, validez.
2. Compte B : même opération avec `170` et `80`.
3. Compte B : si budget personnalisé, saisissez le montant dans le modal.

Attendu : chaque modal se valide dans le menu privé de son auteur ; aucun nouveau message public. Résultat : ☐ OK ☐ KO — ____

## 6. Erreur de saisie : confidentialité du message d'erreur

1. Compte A : ouvrez les mesures, saisissez `abc` puis `900`, validez.
2. Vérifiez : le message « Saisie invalide » apparaît **seulement pour A** et le parcours ne passe pas à l'étape suivante.
3. Compte B : vérifiez qu'il ne voit ni le message d'erreur ni la valeur `abc`.
4. Compte A : corrigez avec `180` / `90` puis continuez.

Attendu : erreur privée, parcours non avancé après erreur, saisie valide acceptée. Résultat : ☐ OK ☐ KO — ____

## 7. Terminer les deux parcours

1. Compte A : terminez le parcours jusqu'au résultat.
2. Compte B : terminez le parcours jusqu'au résultat.

Attendu : chacun reçoit son classement dans son menu privé. Résultat : ☐ OK ☐ KO — ____

## 8. Chacun ne voit que son résultat

1. Compte A : vérifiez que le résultat affiche **180 × 90** et pas 170 × 80.
2. Compte B : vérifiez que le résultat affiche **170 × 80** et pas 180 × 90.
3. Compte B : cliquez sur **Fermer** ; vérifiez que le résultat de A reste affiché pour A (et réciproquement).

Attendu : résultats strictement séparés ; « Fermer » n'affecte que son auteur. Résultat : ☐ OK ☐ KO — ____

## 9. Essayer le bouton d'un autre utilisateur

Discord n'affiche pas les messages éphémères aux autres membres : le test porte donc sur les **réutilisations** possibles.

1. Compte A : ouvrez un menu (Start), puis cliquez de nouveau **Start** : l'ancien menu doit devenir inutilisable.
2. Compte A : cliquez sur un bouton de l'**ancien** menu (grip ou mesures). Attendu : « Ce parcours n'est plus actif » ; aucun changement.
3. Compte B : tentez d'utiliser un bouton du résultat de A s'il vous est accessible (copie d'écran, autre client) : attendu « Cette action n'est pas disponible pour votre compte ».

Résultat : ☐ OK ☐ KO ☐ Non testable tel quel — ____

## 10. Après expiration et après redémarrage

**a) Expiration** (avec `SESSION_TTL_SECONDS=120`) :
1. Compte A : ouvrez un menu, attendez plus de 2 minutes sans agir, puis cliquez sur un bouton du menu.
2. Attendu : « Ce parcours n'est plus actif » ; rien n'est enregistré ; relancez **Start** et le parcours redémarre.
3. Remettez `SESSION_TTL_SECONDS` à sa valeur d'origine.

**b) Redémarrage** :
1. Ouvrez un menu avec le compte A (sans le terminer).
2. Redémarrez le bot (service Alwaysdata : voir `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` §7.3, ou arrêt/relance locale).
3. Vérifiez qu'une seule instance tourne (guide §9).
4. Compte A : ancien menu → « Ce parcours n'est plus actif » (les sessions sont en mémoire et ne survivent pas au redémarrage).
5. Compte A : cliquez sur **Start** du **message d'accueil existant** → le parcours démarre normalement.
6. Vérifiez que `!setup_finder` n'a pas dupliqué le message d'accueil.

Résultat : ☐ OK ☐ KO — ____

---

## Tableau de consignation

| Étape | Résultat attendu | Observé (qui a vu quoi) | Statut |
|---|---|---|---|
| 1. Publier le panneau | Un seul message, relance = édition | | ☐ Non exécuté |
| 2. Deux parcours, même salon | Menus séparés, pas de message public | | ☐ Non exécuté |
| 3. Dimensions différentes | Chaque récapitulatif = ses valeurs | | ☐ Non exécuté |
| 4. Grips et budgets différents | Parcours indépendants | | ☐ Non exécuté |
| 5. Soumettre les modals | Validation privée | | ☐ Non exécuté |
| 6. Erreur de saisie | Erreur privée, pas d'avancement | | ☐ Non exécuté |
| 7. Terminer les deux | Chacun reçoit son résultat | | ☐ Non exécuté |
| 8. Résultats séparés | Pas de mélange ; Fermer local | | ☐ Non exécuté |
| 9. Bouton d'un autre / ancien menu | Refus propre | | ☐ Non exécuté |
| 10. Expiration et redémarrage | « plus actif », panneau opérationnel, pas de doublon | | ☐ Non exécuté |

**Conclusion à écrire après exécution** : date, commit, comptes utilisés, étapes OK / KO, captures d'écran éventuelles (ne pas publier de token ni de données personnelles).
Tant que ce tableau n'est pas rempli, la confidentialité sur Discord n'est **pas** validée.
