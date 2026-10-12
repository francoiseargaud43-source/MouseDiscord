# Chasse aux bugs et fiabilisation du bot — 2026-10-12

Signalement du propriétaire, mot pour mot : « des fois le bot bug et en fait ça cherche dans le vide
et ça dit comme quoi c'est plus possible, donc on est obligé de rejeter le message et de recommencer
à 0, et là ça remarche ».

Ce document explique **ce qui se passait**, **ce qui a été corrigé**, **comment c'est vérifié** et
**ce qui reste à surveiller**. Aucun barème, aucune donnée de souris, aucun texte affiché au membre
n'a été modifié par cette passe : ce sont des corrections de fiabilité.

---

## 1. Le diagnostic

Le symptôme (« ça recommence à marcher quand on repart de zéro ») désigne une panne *intermittente*
qui dépend de l'état du bot, pas du calcul. Deux causes réelles ont été trouvées, plus deux
faiblesses qui pouvaient produire le même effet.

| # | Cause trouvée | Ce que le membre voyait | Pourquoi « recommencer à 0 » réparait |
|---|---|---|---|
| 1 | **Les menus des étapes n'étaient pas durables.** Chaque vue portait un identifiant tiré au hasard, valable seulement dans le processus en cours, et expirait au bout d'une heure (`VIEW_TIMEOUT`). | Un clic dans un menu après un redémarrage du bot (ou après une heure) : Discord affiche « cette interaction a échoué », le bot ne reçoit rien, aucun message n'explique. | Le nouveau parcours recréait des menus neufs, avec des identifiants connus du bot. |
| 2 | **Les parcours vivaient uniquement en mémoire.** Un redémarrage du bot (mise à jour, redémarrage du serveur, tâche planifiée) effaçait le parcours en cours. | « ⏱️ Ce parcours n'est plus actif (expiré ou remplacé par un nouveau test). » | Un nouveau parcours repartait d'une session neuve. |
| 3 | **Un parcours terminé était effacé immédiatement.** Discord réémet parfois une interaction (double appui, réseau) : la seconde arrivait après l'effacement. | « Ce parcours n'est plus actif », alors que le résultat venait d'être affiché. | Un nouveau test créait une nouvelle session. |
| 4 | **Aucun filet de sécurité sur les erreurs.** Une exception dans une réponse laissait l'interaction sans réponse : silence, puis « interaction échouée ». | Rien, puis un échec muet. | Relancer refaisait le chemin sans l'erreur passagère. |

Le moteur de scoring a été **disculpé par la mesure** : 27 170 profils passés au banc d'essai
(`tools/qa_flow_matrix.py`) → 0 exception, 0 dépassement des limites Discord, 0 profil sans résultat
en dehors d'un budget personnalisé trop bas (où l'absence de résultat est la bonne réponse).
Le calcul complet d'un résultat prend **2,1 ms en local** (mesuré) : le plafond de 3 secondes imposé
par Discord n'était pas en cause, aucun `defer` n'a donc été ajouté.

---

## 2. Les corrections

### 2.1 Composants durables (`cogs/finder_flow.py`, `bot.py`)

- **Identifiants fixes** pour tous les composants d'étapes, déclarés en constantes :
  `mouse_finder:start`, `:grip`, `:claw_variant`, `:thenar`, `:measures`, `:budget`,
  `:measures_modal`, `:budget_modal`. Ils ne doivent plus jamais changer : les messages déjà affichés
  chez les membres s'appuient dessus.
- **Aucun délai** (`timeout=None`) sur toutes les vues et tous les formulaires.
- **Enregistrement au démarrage** via `persistent_views()` appelé par `bot.py` (`add_view`) : les six
  vues et les deux formulaires sont connus de Discord dès le lancement, donc un clic est reconnu même
  si le bot vient de redémarrer. Vérifié en lisant le registre de distribution de discord.py 2.7.1.
- **Rattachement au membre** : les composants ne transportent plus d'identifiant de parcours. Chaque
  action retrouve le parcours vivant du membre qui clique (`SessionStore.current`). Aucun composant ne
  peut donc atteindre le parcours d'un autre membre — la propriété de confidentialité est conservée,
  et elle devient vraie même après un redémarrage (impossible avec un identifiant inscrit dans un
  message publié avant le redémarrage).

### 2.2 Parcours conservés (`utils/session.py`, `config.py`, `bot.py`)

- Les parcours **en cours** sont enregistrés dans `state/sessions.json` (chemin `SESSION_STATE_PATH`),
  avec l'âge du dernier geste, en écriture atomique (fichier temporaire + renommage).
- **Aucune réponse n'est perdue** : `_remember()` enregistre l'état après chaque réponse (prise,
  variante, thénar, mesures, budget). Le fichier est relu au démarrage ; un parcours trop ancien
  (`SESSION_TTL_SECONDS`, 30 min par défaut) n'est pas restauré.
- **Confidentialité** : seuls les parcours en cours sont écrits, et à l'instant où le résultat est
  produit, les réponses quittent le fichier (`finish()`). Le parcours terminé reste quelques minutes
  **en mémoire seulement**, pour qu'un clic rejoué reçoive le même résultat.
- `SESSION_PERSIST=false` dans `.env` revient au fonctionnement « tout en mémoire ».
- Une purge périodique (toutes les 5 minutes) et un enregistrement à l'arrêt complètent le dispositif.

### 2.3 Étape courante décidée par l'état (`step_kind`, `step_for`, `_show_step`)

Un seul endroit décide de l'étape affichée, d'après les réponses **déjà** enregistrées. Conséquences :

- un clic rejoué, un ancien message ou un redémarrage rouvrent le questionnaire là où il en était,
  au lieu de le casser ;
- un bouton cliqué hors de son étape (« Saisir mes mesures » alors que la question du thénar est en
  attente) réaffiche l'étape réelle au lieu d'ouvrir un formulaire sans objet ;
- changer de prise remet à zéro les questions qui en dépendent (variante de Claw, thénar).

### 2.4 Plus jamais de silence ni de cul-de-sac

- `FinderView.on_error` / `FinderModal.on_error` : toute erreur inattendue est **tracée en entier**
  dans le journal et expliquée en privé au membre (« ⚠️ Une erreur inattendue est survenue… »).
- `_show_private` tente l'édition du message, puis l'édition de la réponse d'origine, puis un nouvel
  envoi privé : il n'y a plus de cas où le membre reste sans réponse.
- Un parcours expiré affiche un message clair **avec le bouton de reprise** juste en dessous : un clic
  suffit pour repartir, sans chercher le panneau du salon.
- Un double appui sur un bouton qui ouvre un formulaire ne produit plus d'erreur.
- Catalogue momentanément illisible (fichier en cours de copie) : message explicite au lieu d'un plantage.

### 2.5 Ménage dans le code

- Code mort supprimé (`_target_line`, jamais appelé) ; `VIEW_TIMEOUT` supprimé (plus de délai) ;
  `require_session` (par identifiant) remplacé par `_current_session` (par membre).
- Les `assert` de production remplacés par des garde-fous explicites : plus aucun parcours incomplet ne
  peut faire échouer l'affichage (un bloc facultatif absent est simplement omis).
- Commentaires et en-têtes mis à jour pour décrire le comportement réel (durabilité, confidentialité).

---

## 3. Les faits vérifiables

| Contrôle | Avant | Après |
|---|---|---|
| Tests | 281 | **288** (dont P14–P18 nouveaux : clic rejoué, erreur inattendue, fichier d'état) |
| `pyflakes` (fichiers suivis) | vide | vide |
| `tools/privacy_scan.py` | 0 violation | 0 violation |
| `tools/qa_flow_matrix.py` | 0 problème sur 27 170 profils | 0 problème (le moteur n'a pas bougé) |
| Composants reconnus après redémarrage | **non** (identifiants aléatoires, aucun enregistrement) | **oui** : 6 vues + 2 formulaires enregistrés au démarrage, vérifié test par test |

Nouveaux tests de robustesse (tous dans `tests/test_privacy.py`) :

- `test_p11_a_restart_keeps_the_running_parcours_and_its_components` : deux `MouseBot` successifs sur
  le même fichier d'état ; le second retrouve la prise et le thénar déjà répondus, et le bouton des
  mesures ouvre bien le formulaire.
- `test_p11_step_components_are_registered_even_without_any_parcours` : les huit composants sont
  enregistrés dès le démarrage, sans dépendre d'un parcours vivant.
- `test_p14_replayed_click_after_the_result_gets_the_same_result` : le second envoi reçoit exactement
  le même résultat.
- `test_p15_*` : une erreur inattendue (callback et formulaire) produit un message privé, jamais un silence.
- `test_p16_state_file_only_holds_running_parcours` : le fichier ne contient que les parcours en cours ;
  après le résultat, les réponses n'y sont plus.
- `test_p17_expired_parcours_is_not_restored` / `test_p18_unreadable_state_file_never_breaks_the_bot` :
  un parcours trop ancien n'est pas repris, un fichier illisible ne bloque pas le démarrage.
- `test_old_message_never_breaks_a_running_parcours` (`tests/test_flow.py`) : un ancien message ne
  renvoie plus « ce parcours n'est plus actif », il fait avancer le parcours vivant.

---

## 4. Ce qui reste à vérifier sur le serveur (non simulable ici)

1. **Redémarrage réel** : lancer un parcours, redémarrer le bot (`pkill -f bot.py`), puis cliquer dans
   l'étape affichée → la question doit continuer, sans message d'erreur.
2. **Double appui** sur le dernier menu du parcours → le même résultat doit s'afficher deux fois, sans
   message « expiré ».
3. **Après 30 minutes d'inactivité** → message d'expiration clair, suivi du bouton de reprise.
4. **Dossier `state/` inscriptible** : `python tools/check_deployment.py` le contrôle déjà (le fichier
   `state/sessions.json` est créé tout seul).

## 5. Risques résiduels assumés

- Le **format du fichier d'état** peut changer lors d'une future mise à jour : une version non reconnue
  est ignorée en silence (journalisée), ce qui équivaut à « mémoire seulement » — jamais un plantage.
- Les composants publiés **avant** cette mise à jour portent d'anciens identifiants aléatoires : les
  parcours ouverts au moment de la mise à jour devront être relancés une fois (dernière fois que ce cas
  se produit). Les messages publiés ensuite sont stables.
- `state/sessions.json` contient, quelques minutes au plus, les réponses d'un parcours **en cours**
  (prise, mesures, budget) sous forme de valeurs numériques et d'énumérations : aucune donnée libre,
  aucun message. Voir `docs/audit/AUDIT_CONFIDENTIALITE.md`.


---

## 6. Deuxième vague de chasse aux bugs (2026-10-12, après « je suis persuadé qu'il y en a »)

Neuf défauts réels trouvés dans le code, corrigés et verrouillés par un test. **Le moteur de scoring
n'a pas été touché** (27 170 profils repassés au banc d'essai : 0 problème, 0 exception, limites
Discord respectées).

| # | Défaut | Ce que le membre voyait | Correctif |
|---|---|---|---|
| 1 | **Les boutons d'achat ne suivaient pas les souris affichées** : ils prenaient les deux premiers du classement interne, pas le match idéal, l'alternative et l'économie réellement écrits dans le message. | En Qualité/Prix (main 180 × 90), le message montrait « Scyrox V6 » en alternative, mais le second bouton menait à « ATK GHOST Extreme » — une souris absente du message — et l'alternative n'avait **aucun** bouton. Idem en Économique, Haut de gamme et Peu importe le prix. | `ResultsView` reçoit désormais **exactement** les souris montrées (`result_slots`), dans l'ordre, un bouton par souris. |
| 2 | **`capitalize()` écrasait les majuscules du résumé** : « prise Palm Grip bien soutenue » devenait « prise palm grip bien soutenue ». | Libellés dégradés dans le bloc « en clair ». | Seule la première lettre est mise en majuscule. |
| 3 | **Message d'expiration en texte brut** : la charte prévoit un embed orange pour l'expiration. | Message sans identité visuelle, alors que tout le reste est bordeaux. | `expired_embed()` (orange) est désormais joint au message, avec le bouton de reprise dans le même message. |
| 4 | **Saisies refusées injustement** : l'espace fine insécable (U+202F) et l'espace fine que posent les claviers français (« 1 800 € ») n'étaient pas reconnues ; « 180 MM » non plus. Et un chiffre non latin provoquait une exception technique au lieu d'un message. | « n'est pas un nombre valide » sur une saisie correcte. | Tous les espaces sont ignorés, le suffixe d'unité est reconnu quelle que soit sa casse, les chiffres non latins reçoivent le message clair. |
| 5 | **Double appui sur le bouton d'accueil** : la seconde réponse levait `InteractionResponded`, captée comme « erreur inattendue ». | Message d'alerte alors que le parcours venait de s'ouvrir. | Le double appui est absorbé en silence : une seule étape à l'écran, aucun message d'erreur. |
| 6 | **Fichiers de données abîmés = plantage** : une liste d'entrées non-objet, un champ texte remplacé par un nombre, une source incomplète, un `conflicts` mal formé, un `commercial_links.json` ou un `images.json` qui n'est pas un objet. | « Une erreur inattendue est survenue » au moment du résultat, sans explication. | `CatalogError` avec message précis (ou fichier ignoré proprement) dans `utils/catalog.py` et `utils/assets.py` ; 9 nouveaux tests dans `tests/test_catalog_hardening.py`. |
| 7 | **Configuration dangereuse acceptée** : `SESSION_TTL_SECONDS=0` (ou négatif) faisait expirer chaque parcours aussitôt — le symptôme exact du signalement — et un `FINDER_CHANNEL_ID` négatif passait inaperçu. | « Ce parcours a expiré » à chaque clic. | Refus au démarrage avec le nom de la variable et la valeur fautive ; `bot.py` affiche une ligne claire au lieu d'une trace technique. |
| 8 | **État du message d'accueil écrit sans précaution** (`state/finder_message.json`) : une coupure en pleine écriture publiait un second message au redémarrage. | Deux panneaux d'accueil dans le salon. | Écriture atomique (fichier temporaire puis renommage), comme pour `state/sessions.json`. |
| 9 | **`assert` de production** dans le calcul (`compute_selection`) : supprimé par `python -O`, il ne protégeait rien. | Aucun (défensif). | Vérification explicite qui lève une erreur claire, captée et journalisée. |

### Ce qui a été vérifié sans rien changer

- **Deux places ne montrent jamais la même souris** (et jamais la même coque quand la zone offre un
  autre choix) : vérifié sur les 27 170 profils par le banc d'essai.
- **Limites Discord** : au pire 8 embeds (limite 10) et 2 582 caractères tout compris (limite 6 000)
  pour un message de résultat.
- **Aucun envoi public** : contrôle statique `tools/privacy_scan.py` → 0 violation ; les messages
  d'erreur destinés au membre restent éphémères.

### Point ouvert (décision du propriétaire)

**La troisième place (« 💸 L'économie ») n'apparaît que dans 0,18 % des profils** (49 sur 27 170 au
banc d'essai complet, 0,19 % sur la grille 1 029 ; §8.2 corrige au passage un défaut de la règle, ce
qui la porte à 0,39 %). Vérification faite : ce n'est pas un bug de calcul, mais un effet de seuil — la zone de
compatibilité du mode est étroite (±2 points sur 40) et l'alternative prend déjà la meilleure des
souris moins chères ; il reste donc rarement une souris encore moins chère **et** toujours dans la
zone. Deux options, à trancher par le propriétaire (cela changerait une règle de présentation) :

1. laisser ainsi : la place apparaît quand elle existe vraiment ;
2. élargir la zone de la seule ligne « économie » (par exemple jusqu'à 5 points sous le meilleur
   score), avec une mention du type « un peu moins compatible, mais moins chère ».

---

## 7. Troisième vague (13e passe) : le thénar modifiait le score en silence

Les deux premières vagues (§5 et §6) portaient sur le parcours et les fichiers de données. Cette
troisième passe part du résultat lui-même : le score, le classement et la coque des souris.

### 7.1 Les deux défauts corrigés

| # | Défaut | Preuve (avant correction) | Correction |
|---|---|---|---|
| 10 | **Le thénar changeait le score et donc la recommandation**, alors que le README (« aucun effet sur le score »), le `MASTER_PROMPT` §7.6 (« zéro effet sur les équations, seuils, points, score, classement »), `docs/audit/AUDIT.md` §3 et §8 et le rapport final promettent tous l'inverse. `THENAR_WIDTH_ADJUSTMENT` valait **−2 / 0 / +2** (hypothèse bornée du reverse engineering d'Oblivity, présentée comme réversible) alors que la décision retenue était le repli « conforme Oblivity » à **0 point**. | Banc de mesure : **2 805 profils** comparés avec « Thénar Petite » et « Thénar Grande » → **537 profils (19,1 %)** donnaient une réponse différente. Sur le Paris main 190 × 80 en Qualité/Prix, le gagnant changeait de souris selon la taille de thénar déclarée. | Les trois valeurs repassent à **0** : le score, le classement et les exclusions sont désormais **identiques quel que soit le thénar**, comme promis. Le mécanisme, le bornage 0–10 et la note d'embed restent en place (test dédié), donc une activation reste possible en changeant une ligne (`docs/REVERSE_ENGINEERING_OBLIVITY.md` §3). Les trois textes qui annonçaient un effet (« Effet borné à ±2 points », « pénalisée à la marge dans le score ») sont corrigés. **Après correction : 0 profil sur 2 805 change de réponse.** |
| 11 | **Deux entrées de la même coque pouvaient être proposées ensemble** dans le même résultat (le match idéal, puis « l'alternative » = la même souris). `shell_id` était vide pour l'A9 NB Ultra, les deux U2 Mini et la X3, alors que les notes du catalogue affirment déjà « coque A9 pleine taille », « même coque » (page de série A9 d'ATK), « coque de la famille X1 » et que les dimensions publiées sont identiques au dixième de millimètre. | **92 profils** montraient deux fois la même souris : 68 avec « A9 Plus 2.0 » (45 €) et « A9 NB Ultra » (72,95 €), 24 avec « X2A v3 » et « X2 CrazyLight Medium ». | `shell_id` enregistrés (`atk_a9_large` pour l'A9 NB, `atk_u2_mini` pour les deux U2 Mini, `atk_x1` pour la X3) d'après les notes déjà sourcées. **Après correction : 0 profil** pour la paire A9 et les U2 Mini ; il reste la paire Pulsar (voir points ouverts). |
| 12 | **`tools/build_mouse_db.py` écrasait le catalogue** : ce script régénère le relevé d'origine (**18 souris**, 2026-10-10) et écrivait sans prévenir dans `data/mouse_db.json`, qui contient **36 souris** enrichies à la main (prix, mesures, sources, prises). Une exécution par distraction détruisait 18 souris et tous les enrichissements postérieurs — dont les 10 Pulsar. | Mesure : le script génère 18 identifiants, le catalogue en contient 36 → 18 perdues. | Refus d'écrire quand des entrées seraient perdues, **message qui les nomme**, écriture atomique et option `--force` pour régénérer volontairement ; 3 tests (`tests/test_build_mouse_db_guard.py`). |

### 7.2 Ce qui a été vérifié sans rien changer

- **Les cinq modes tiennent leur promesse** : 1 395 profils contrôlés mode par mode (économie = la
  moins chère de la zone de tolérance ; qualité/prix = le meilleur rapport points/€ ; haut de gamme =
  le meilleur indice de performance documenté ; peu importe le prix et budget personnalisé = le
  meilleur score) → **0 violation**.
- **Les composants Discord de chaque étape** (identifiants fixes, ≤ 5 boutons par rangée, liens
  d'achat en `https://`, ≤ 25 options par menu) et le résultat sur les **15 combinaisons prise ×
  mode** → 0 erreur.
- **Le banc des 27 170 profils** reste à 0 problème, `tools/privacy_scan.py` à 0 violation, et le
  catalogue se charge sans erreur (36 souris, 36 liens).
- **Aucun résultat vide sans explication** : sur les profils extrêmes (main 140 × 60 ou 250 × 130,
  budget minuscule), le message affiche « Aucun match classable… » et propose une autre gamme —
  jamais une impasse.

### 7.3 Limite constatée (outil de mesure) — aucune valeur inventée

`tools/measure_button_height.py` refuse toute vue qui n'a pas les proportions officielles du modèle.
Limite honnête découverte cette passe : ce contrôle valide des **proportions**, pas l'**identité** de
la souris. Une vue de profil du X1 V2 (page produit X1 V2) est acceptée aux cotes du U2 Mini
(rapport mesuré 3,09 contre 3,10 attendu) : les deux coques sont trop proches pour être distinguées
par ce seul critère. Règle appliquée : une image n'est mesurée que si elle vient de la **fiche du
modèle mesuré**, et la vérification visuelle reste obligatoire. Conséquence : aucune nouvelle hauteur
de boutons n'a été ajoutée cette passe — les vues de profil disponibles (Xlite v4 Large et Mini) sont
**refusées** (0,4 % d'écart accepté, ici 72 à 87 %), et les recherches d'images « U2 Mini » renvoient
des vues d'autres souris. Aucune valeur n'a donc été inventée.

### 7.4 Points ouverts (décision du propriétaire)

1. **La troisième place (« 💸 L'économie »)** n'apparaît que dans 0,1 % des profils (voir §5).
2. **Deux paires de coques à trancher** : `atk_u2` / `atk_u2_v2_ultimate` (dimensions publiées
   identiques : 123,7 × 64,6 × 39,1 mm) et `pulsar_x2a_v3_medium` / `pulsar_x2_crazylight_medium`
   (120,4 × 63 × 38 mm). Aujourd'hui, aucune des deux ne peut apparaître deux fois dans un résultat
   (l'une des deux entrées est toujours « à vérifier »), mais il faut une source fabricant pour
   enregistrer la coque — les deux paires sont donc listées dans un test canari et dans les points
   ouverts du rapport statistique.
3. **Souris jamais recommandées** : le tableau complet (57 057 profils, 5 modes, toutes les tailles
   de main) est dans `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md`, avec le motif exact
   souris par souris.


---

## 8. Quatrième vague (13e passe, suite) : le banc d'essai regarde le CONTENU du message

Les vagues précédentes vérifiaient que le résultat **ne plante pas** et qu'il respecte les règles de
sélection. Cette vague-ci vérifie ce que le membre **lit réellement**.

### 8.1 Ce que le banc d'essai contrôle désormais

`tools/qa_flow_matrix.py` lit le texte des embeds et les boutons produits, et vérifie pour chaque
profil (27 170 profils × 5 modes × toutes les tailles de main, toutes les prises, tous les thénars) :

- chaque souris affichée porte son **nom**, son **prix** (au format français, virgule décimale), son
  **score** (« 25/40 ») et son **pourcentage** ;
- le pourcentage affiché est bien `score / 40` du maximum théorique, jamais du maximum « du moment » ;
- les **repères de taille** affichés (longueur, largeur de prise) sont ceux de la souris montrée ;
- la **justification du choix** (« pourquoi ce choix ? ») est présente et non vide ;
- **aucune souris « en attente »** (donnée manquante) ni écartée (prise « Faible ») n'est affichée ;
- aucune souris n'est proposée **au-dessus du budget** en budget personnalisé ;
- les places affichées restent **dans la zone de tolérance du mode** ;
- les **boutons d'achat** correspondent exactement aux souris affichées : un bouton par souris
  affichée qui a un lien, jamais de bouton pour une souris absente du message ;
- deux places ne montrent jamais la même souris, ni la même coque quand une autre coque est
  disponible dans la zone.

Résultat : **27 170 profils contrôlés, 0 problème**, et la répartition des places devient mesurable :

| Places remplies | Profils | Part |
|---:|---:|---:|
| 0 (message « Aucun match classable ») | 4 082 | 15,0 % |
| 1 | 5 889 | 21,7 % |
| 2 | 17 150 | 63,1 % |
| 3 | 49 | 0,18 % |

### 8.2 Défaut 13 — la troisième place était supprimée par sa propre préférence de coque

`result_slots()` annonce « l'économie : la moins chère de la zone, **d'une autre coque si possible** ».
Le code filtrait **d'abord** sur la coque, **ensuite** sur le prix : dès que la moins chère d'une autre
coque dépassait le plafond de prix, la place disparaissait — alors qu'une souris moins chère restait
disponible. Mesure sur la grille 1 029 profils : **2 profils** avec la place, **4** avec la règle
annoncée. Correction : la préférence de coque s'applique **parmi les souris déjà sous le plafond**,
jamais au prix de la place elle-même. Test dédié (échoue sans le correctif, passe avec).

### 8.3 Défaut 14 — une mesure fausse annoncée dans le test de l'économie

Le test affirmait « 1 profil sur 960 avant, **101 sur 960 après** » le correctif de la 2e vague — soit
10,5 % des profils. La mesure ne se reproduit avec **aucune** des deux règles : 4 sur 1 029 pour
l'ancienne, 2 sur 1 029 pour la nouvelle. Le chiffre est remplacé par les valeurs mesurées et
reproductibles, avec la méthode (grille, modes, budget).

### 8.4 Défaut 15 — la phrase de bilan affirmait un sens que le score ne porte pas

Le résumé disait « largeur de prise **un peu large** » et « longueur **en léger retrait** » pour toute
souris à 0 point sur le critère — y compris quand la souris est **plus étroite** ou **plus longue** que
la cible (cas réel : grande main et souris fine). Le score ne porte pas le sens de l'écart : les deux
phrases deviennent neutres (« un peu hors de la cible »), et un test interdit le retour des anciennes.

### 8.5 Canaris de barème : plus aucun rang « 0 » silencieux

`components_index()` (départage du mode « Peu importe le prix ») rend **0** pour toute valeur qu'il ne
connaît pas : une faute de frappe dans le catalogue faisait donc disparaître un départage **sans
erreur, sans test rouge et sans trace**. Quatre tests figent désormais la liste :

- capteurs et MCU du catalogue : chacun a un rang **ou** une justification écrite (`PAW3315`,
  `Xhero AI / PAW3395 SE`, MCU Broadcom / BK Custom / NearLink, MCU non publié des Pulsar) ;
- capteur haut de gamme absent de `PERFORMANCE_SENSORS` : `Pulsar XS-1`, justifié (incohérence
  mesurée, **0 recommandation modifiée** sur 1 309 profils) ;
- toutes les chaînes de switchs du catalogue sont reconnues (14 libellés distincts).

Preuve que les canaris mordent : chaque table vidée d'une valeur fait échouer le test correspondant
(vérifié pour les trois).

### 8.6 Cause racine des messages vides et des souris jamais recommandées (mesurée)

- Les **4 082 profils sans résultat** sont **tous** en budget personnalisé, et toujours pour la même
  raison : le budget demandé est inférieur à la souris classable la moins chère. Sur la grille 1 029,
  **56 profils vides sur 56** contiennent au moins une souris « à vérifier » faute de compatibilité de
  prise publiée.
- **11 souris sur 36** n'ont **aucune** compatibilité de prise publiée par le fabricant : elles ne
  peuvent donc jamais être classées — `atk_duckbill`, `atk_f1_v2`, `atk_fierce_x`,
  `atk_phantom_ultimate`, `atk_u2_v2_mini`, `atk_u2_v2_ultimate`, `atk_zero`, `vxe_mad_r`, `vxe_r1`,
  `vxe_v3`, `vxe_x3`.
- Conséquence concrète : **trois des quatre souris les moins chères** (VXE R1 13,95 €, VXE V3
  13,95 €, VXE X3 27,95 €) sont inutilisables. En Fingertip sous 30 €, il ne reste **aucune** souris
  possible : le membre reçoit « Aucun match classable ».
- C'est la même cause qui explique la majorité des **21 souris jamais recommandées** du rapport
  statistique. Aucune donnée n'a été inventée pour combler ces trous.

### 8.7 Le vrai motif pour lequel « ce sont toujours les mêmes souris » (mesuré)

Le banc d'essai compte désormais, sans le compter comme une faute, les profils où **deux places du
résultat montrent la même coque** : **4 555 profils sur 27 170 (16,8 %)**. C'est le repli documenté de
`result_slots()` — quand la zone de tolérance du mode ne contient que des variantes de la coque
retenue, la deuxième place reprend la même coque au lieu de disparaître. Les familles concernées sur
la grille de contrôle :

| Paire affichée ensemble | Profils (grille 1 029) |
|---|---:|
| `pulsar_x2_v3_mini` + `pulsar_x2_crazylight_mini` | 77 |
| `atk_a9_ultimate` + `atk_a9_plus` | 33 |
| `pulsar_x2a_v3_medium` + `pulsar_x2_crazylight_medium` | 15 |
| `atk_a9_nb` + `atk_a9_plus` | 14 + 11 |
| `atk_ghost_ultimate` + `atk_ghost_extreme` | 2 |

Autrement dit : dans près d'un résultat sur six, le membre voit **deux fois la même forme** à deux
prix différents (par exemple A9 Plus 2.0 à 45 € puis A9 NB Ultra à 72,95 €). Ce n'est pas un défaut de
calcul, c'est la conséquence de deux règles qui se rencontrent :

1. la zone de tolérance du mode est étroite (±2 points sur 40, ±5 en Économique) ;
2. la famille A9 (trois entrées, une seule coque) et la famille X2 (deux entrées Mini, deux Medium)
   occupent les meilleurs scores sur une grande partie des mains.

Trois sorties possibles, **chacune mesurable** (à trancher par le propriétaire) :

1. **Laisser ainsi** (repli actuel) : 16,8 % des résultats montrent deux fois la même forme.
2. **Chercher une autre coque un peu plus loin** pour la 2ᵉ place seulement (par exemple jusqu'à
   5 points sous le meilleur score, au lieu des 2 du mode) : la 2ᵉ place devient une forme
   réellement différente, légèrement moins compatible, et la phrase de tolérance du mode est ajustée
   en conséquence.
3. **Ne pas afficher la 2ᵉ place** quand elle reprend la même coque (1 seule place proposée) : c'est
   la seule option qui ne change aucun classement, mais elle enlève un choix.

### 8.8 Décision demandée au propriétaire (trois choix)

1. **Troisième place** — la place n'apparaît que si une souris d'une autre coque est à la fois dans la
   zone du mode **et** strictement moins chère que les deux affichées. Taux mesurés si l'on élargit la
   zone **de la seule ligne économie** : ±2 pts (aujourd'hui) **0,4 %**, ±5 pts **6,3 %**,
   ±10 pts **23,6 %** des profils. Rien ne change pour le match idéal ni pour l'alternative.
2. **Souris sans prise publiée** — autoriser une source tierce (EloShapes, test écrit) pour les 11
   souris ci-dessus, ou les laisser hors service. Sans source, elles resteront invisibles ; avec une
   source tierce, il faut ajouter une provenance explicite dans le catalogue (`fit_status`).

## 9. Cinquième vague (16e passe) : les souris « jamais recommandées » sortent du tableau

### 9.1 Le doute sur les coques répétées est refermé, la preuve est dans la commande

Le §8.7 laissait une piste ouverte : quatre profils semblaient montrer deux fois la même coque alors
qu'une AUTRE coque se trouvait, d'après un contrôle indépendant, dans la zone de tolérance du mode.
Contrôle refait **avec le moteur réel** sur la grille complète (27 170 profils : longueurs 140–230 mm,
largeurs 60–120 mm, trois prises, trois thénars, cinq modes et cinq budgets personnalisés) :

- **4 472 profils (16,5 %)** affichent deux places sur la même coque ;
- **0 profil** où une autre coque est dans la zone de tolérance du mode ;
- les cinq paires concernées : `pulsar_x2_crazylight_mini` + `pulsar_x2_v3_mini` **2 214** ·
  `atk_a9_plus` + `atk_a9_ultimate` **1 500** · `pulsar_x2_crazylight_medium` + `pulsar_x2a_v3_medium`
  **380** · `atk_a9_nb` + `atk_a9_plus` **332** · `atk_ghost_extreme` + `atk_ghost_ultimate` **46**.

Conclusion : le repli « même coque » n'est jamais un défaut de calcul — il ne se produit que lorsque la
zone ne contient rien d'autre. **Piste fermée**, pas « en attente d'explication ».

### 9.2 Deux familles de données manquantes complétées (sourcées, datées)

- **Pulsar Xlite v4 Mini, v4 Medium, v4 Large et Xlite CrazyLight Medium** : la position de la bosse est
  publiée par EloShapes (« Hump placement : **Center** »), relevée fiche par fiche le 2026-10-12 →
  **Mid** (règle de correspondance du projet, `tools/build_mouse_db.py`). Les dimensions de la boutique
  Pulsar sont confirmées à l'identique (Xlite v4 Mini 115,6 × 63,4 × 40,7 · 52 g ; Medium 122 × 66 × 43
  · 54 g ; Large 126 × 69,5 × 44,5 · 58 g ; CrazyLight Medium 122 × 66 × 43 · 44 g). Ces quatre souris
  sortent de l'état « à vérifier » en Palm et en Claw.
- **ATK A9 Mini** : prix EUR officiel **59,95 €** (boutique ATK, pays France, variante « Mini » de la
  fiche A9 Ultimate, prix normal 72,95 €) et bosse « Center » → **Mid** ; dimensions passées en
  **vérifié** (EloShapes donne exactement 118,4 × 61,2 × 38,6 · 39 g, et son lien « où acheter » pointe
  la variante ATK 47852235718874 identifiée dès le 2026-10-11 dans
  `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` §6.8).
  Précision honnête : EloShapes annonce un capteur **PAW3950 Ultra** là où la fiche InputGear FR annonce
  un **PAW3955** — divergence signalée dans la fiche, valeur d'origine conservée, rien de tranché.
- **ATK U2 V2 Mini** : prix corrigé de 77,95 € à **59,95 €** (variante « U2 V2 Mini / White », boutique
  ATK, pays France). La correction était demandée par
  `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` §6.6 : l'ancienne valeur venait de l'U2 Mini,
  qui n'est pas la V2.

### 9.3 Effet mesuré (même grille de 18 522 profils, `tools/recommendation_stats.py`)

| Mesure | Avant (15e passe) | Après (16e passe) |
|---|---:|---:|
| Profils sans aucun résultat | 1 422 (7,7 %) | **1 212 (6,5 %)** |
| dont une souris « à vérifier » faute de donnée publiée | 1 170 | 960 |
| Profils à deux places sur la même coque | 3 109 (16,8 %) | **2 830 (15,3 %)** |
| Souris jamais recommandées | 19 sur 36 | **17 sur 36** |

Deux souris entrent au tableau : l'**ATK A9 Mini** (prix) et la **Pulsar Xlite v4 Mini** (bosse).
Trois autres deviennent classables sans jamais gagner : Xlite v4 Medium, Xlite v4 Large et Xlite
CrazyLight Medium — mêmes formes que la v4 Mini, plus grandes et plus chères : elles perdent le match,
ce n'est pas une donnée manquante.

### 9.4 Ce que cela change dans le message de référence (canaris mis à jour, jamais « ajustés »)

Sur le profil Palm 180 × 90 en Qualité/Prix, cinq souris sont à 30/40 et le mode « rapport points/€ »
retient la moins chère : l'**ATK A9 Mini (59,95 €)**, devant l'ATK GHOST Ultimate (68,95 €). L'image du
résultat, le bloc « en clair » et l'alternative suivent (illustration T14, bosse centrale). Trois tests
figeaient l'ancien gagnant : ils ont été réécrits avec la date et la raison, et un canari a été ajouté
pour figer les nouvelles données. **344 tests verts**, banc d'essai **0 problème** (720 profils),
`pyflakes` propre, `privacy_scan` 0 violation.

À l'œil du propriétaire : la compatibilité Palm de l'A9 Mini vient de la phrase du fabricant sur la
**série** A9 (« comfortably accommodating claw, palm, and fingertip grips », fiche ATK), appliquée à la
version Mini — exactement comme pour l'A9 Plus, l'A9 NB et l'A9 Air. C'est ce transfert qui la place en
tête de ces profils ; s'il doit être revu, c'est une décision du propriétaire, pas un calcul à changer
seul.

### 9.5 Ce qui reste, après cette passe

1. **11 souris sans compatibilité de prise publiée** : `atk_f1_v2`, `atk_duckbill`, `atk_fierce_x`,
   `atk_phantom_ultimate`, `atk_u2_v2_mini`, `atk_u2_v2_ultimate`, `atk_zero`, `vxe_r1`, `vxe_v3`,
   `vxe_x3`, `vxe_mad_r`. Jamais classables, donc jamais proposées, quel que soit le profil — aucune
   valeur ne peut être devinée. Décision attendue : source tierce autorisée (§8.8, choix 2).
   Deux pistes vérifiées le 2026-10-12 : la fiche officielle de la **VXE MAD R** porte la phrase
   « Perfect Fit for **Claw and Palm** Grips » (même nature de source que celle utilisée pour l'U2), et
   la fiche **U2 V2** ne publie rien de plus que « two sizes to fit different hand types ».
2. **Hauteur des boutons manquante sur 25 souris sur 36** : c'est le critère qui pèse le plus — sur le
   banc rapide, 345 profils sur 720 ont un match idéal « partiel » (boutons non documentés).
3. **Trois souris complètes ne sortent jamais parce qu'elles perdent** : A9 Air, U2 Mini, X2H
   CrazyLight Mini (formes et prix toujours battus par une voisine moins chère).
4. **Prix en attente d'arbitrage** : l'**A9 Air** vaut 89,90 € chez Maxesport (relevé du 2026-10-11)
   mais la boutique ATK affiche la variante « Air / Shadow White » à **59,95 €** (relevé du 2026-10-12,
   `?country=FR`). Deux marchés : la base garde la valeur d'origine jusqu'à la décision du propriétaire.
   La **VXE MAD R** est affichée « à partir de 40,95 € » mais en rupture de stock : aucun prix retenu.
