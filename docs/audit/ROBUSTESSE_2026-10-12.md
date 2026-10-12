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

> **Répondu le 2026-10-12** : les deux points ci-dessous ont reçu une réponse (voir le détail
> en §10) — l'élargissement de la seule ligne économie est retenu à ±5 points (6 148 profils
> sur 27 170, 22,63 %), et les sources tierces sont autorisées pour les souris dont le
> fabricant ne publie aucune compatibilité de prise.

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
   **Avancée le 2026-10-12 (§10.4)** : la MAD R est entrée au catalogue avec la prise publiée par son
   fabricant ; **dix souris** restent sans prise publiée (`atk_f1_v2`, `atk_duckbill`, `atk_fierce_x`,
   `atk_phantom_ultimate`, `atk_u2_v2_mini`, `atk_u2_v2_ultimate`, `atk_zero`, `vxe_r1`, `vxe_v3`,
   `vxe_x3`) — les sources tierces sont désormais autorisées, chaque valeur devra porter sa provenance.
2. **Hauteur des boutons manquante sur 25 souris sur 36** : c'est le critère qui pèse le plus — sur le
   banc rapide, 345 profils sur 720 ont un match idéal « partiel » (boutons non documentés).
3. **Trois souris complètes ne sortent jamais parce qu'elles perdent** : A9 Air, U2 Mini, X2H
   CrazyLight Mini (formes et prix toujours battus par une voisine moins chère).
4. ~~**Prix en attente d'arbitrage**~~ **Tranché le 2026-10-12 (§10.3)** : règle du propriétaire —
   le prix retenu est celui de la **boutique officielle**. L'**A9 Air** est donc passé de 89,90 €
   (revendeur Maxesport) à **59,95 €** (boutique ATK, `?country=FR`, relevé du 2026-10-12 ; l'ancienne
   valeur reste en observation dans la note). La **VXE MAD R** porte **40,95 €** (boutique ATK, série
   « à partir de ») avec la rupture de la variante noire écrite noir sur blanc dans sa note.
   Restent ouverts, règle désormais connue, trois prix à revérifier à la boutique officielle :
   Z1 (base 75,00 € contre 59,95 € au store), Y9 Ultimate (41,95 € en base, variante Ultimate à
   64,98 $), GHOST Extreme (68,95 € en base, même prix que l'Ultimate).

## 10. Dix-septième passe (2026-10-12) : les cinq décisions du propriétaire, appliquées et mesurées

Le 2026-10-12, le propriétaire a répondu aux cinq questions ouvertes des passes précédentes. Ce qui
suit est ce qui a été appliqué — et la commande qui le prouve. Aucun barème n'a bougé : ces décisions
ne changent que l'aiguillage des places affichées, le prix retenu et la provenance des données.

### 10.1 Les cinq réponses

| Question ouverte | Réponse du propriétaire | Application |
|---|---|---|
| Sources pour les prises non publiées | « Je t'autorise à aller chercher d'autres sources tierces » | §10.4 (la MAD R entre au catalogue sur la fiche de son fabricant) ; les dix souris restantes restent à documenter, chacune avec sa provenance |
| Hauteurs de bouton | « normalement c'est à toi de le faire via les images que tu peux récupérer » | aucun chiffre n'existe chez les fabricants : l'outil `tools/measure_button_height.py` reste la seule voie — **aucune valeur n'est encore inscrite** (25 souris sur 36) |
| Marge de la troisième place | « fais ce que tu penses le mieux » | §10.2 : fenêtre propre de ±5 points pour la seule ligne économie |
| Prix | « toujours prendre le prix côté boutique officielle » | §10.3 : A9 Air 59,95 € et MAD R 40,95 € (relevés du 2026-10-12, `?country=FR`) |
| Repli de coque | « fais ta réflexion » | §10.2 : le repli est conservé (jamais moins de résultats), mais il passe de 4 040 à 2 097 profils |

### 10.2 Trois places : deux fenêtres au lieu d'une (mesuré sur les 27 170 profils)

Règle appliquée dans `cogs/finder_flow.py` :

- **le match idéal** ne bouge pas : c'est la tête du classement du mode, comme avant ;
- **l'alternative** reste dans la zone du mode (±2 points, ±5 en Économique) et préfère la moins
  chère ; **uniquement si cette zone ne contient que des variantes de la coque déjà montrée**, elle
  cherche une autre forme jusqu'à `ALTERNATIVE_EXTENSION_POINTS` (5 points) plus bas, et **jamais plus
  chère** que le match idéal ;
- **l'économie** a sa **propre fenêtre** (`ECONOMY_SLOT_TOLERANCE_POINTS`, 5 points), doit être
  **strictement moins chère** que les deux souris affichées, et une autre coque est préférée.

Mesure (`.venv/bin/python tools/qa_flow_matrix.py` puis `tools/flow_effect.py`, 2026-10-12) :

| Mesure (grille complète) | Avant | Après |
|---|---:|---:|
| Profils comparés (au moins une place remplie) | 23 569 | 23 569 |
| Match idéal changé | — | **0** |
| Alternative changée | — | 6 939 |
| Résultats à 1 place | 7 187 | 3 236 |
| Résultats à 2 places | 16 302 | 14 185 |
| Résultats à **3 places** | 80 (0,3 %) | **6 148 (22,63 %)** |
| Deux places sur la même coque | 4 040 | **2 097** |
| Économies perdues | — | **0** |
| Pire baisse de score de l'alternative | — | **5 points** (cas de l'élargissement) |

Le banc d'essai de bout en bout se termine avec **0 problème** ; il compte de son côté 2 052 profils à
deux places de même coque (sa définition ne retient que la paire « match idéal + une autre place »,
là où `flow_effect.py` compte toutes les paires).

Exemple de changement d'alternative par élargissement : `palm/185x60`, thénar petit, budget 45 € —
ATK A9 Plus 2.0 (25/40) → ATK Blazing Sky U2 (20/40), une autre forme, moins chère, dans la fenêtre de
5 points.

### 10.3 Prix : la boutique officielle, jamais un revendeur

- **ATK A9 Air** : 89,90 € (Maxesport, relevé du 2026-10-11) → **59,95 €** (boutique ATK, variante
  « Air / Shadow White », prix normal 72,95 €, relevé du 2026-10-12). L'ancienne valeur reste en
  observation dans la note de la fiche ; la source officielle est datée.
- **VXE MAD R** : aucun prix → **40,95 €** (boutique ATK, série « à partir de »). La variante noire à
  dongle 1K était **en rupture** au moment du relevé : la note le dit explicitement, le prix n'est pas
  masqué pour autant.
- Le **fabricant** annonce des switchs « ATK Custom Tuned Optical » là où le revendeur annonçait
  « Omron » : la valeur fabricant est retenue et la divergence est écrite dans la fiche.
- Trois prix restent à revérifier à la boutique officielle (règle connue, donc simples à trancher) :
  Z1, Y9 Ultimate, GHOST Extreme — listés en §9.5.

### 10.4 VXE MAD R : la prise est publiée par le fabricant, aucune tierce source n'est employée

La fiche officielle du produit porte « 120mm CLASSIC ERGONOMIC DESIGN **Perfect Fit for Claw and Palm
Grips** » : `palm_grip_fit` et `claw_grip_fit` passent à « Élevé », `fit_status` à
`manufacturer_guide`, avec la citation et la source datée. La compatibilité **Fingertip reste
« Inconnu »** : le fabricant ne la publie pas et rien n'est deviné — la souris reste donc « à
vérifier » sur les profils Fingertip. Effet : la MAD R devient classable en Palm et en Claw, alors
qu'elle ne l'était pour aucune prise.

### 10.5 Banc d'essai durci : chaque place est contrôlée contre SA fenêtre

`tools/qa_flow_matrix.py` ne contrôlait qu'une seule tolérance pour les trois places. Depuis cette
passe, il vérifie profil par profil :

1. le match idéal est bien la tête du classement du mode (et non un candidat quelconque) ;
2. l'alternative reste dans la zone du mode, **ou** n'en sort que si aucune autre coque ne s'y trouve
   et sans jamais coûter plus cher que le match idéal ;
3. l'économie reste dans sa fenêtre de ±5 points et coûte strictement moins cher que les deux autres ;
4. les contrôles de contenu (nom, prix, score, bouton d'achat) portent désormais sur la place
   concernée, plus sur une zone unique.

### 10.6 Ce qui reste ouvert après cette passe

1. **Dix souris sans prise publiée** : `atk_f1_v2`, `atk_duckbill`, `atk_fierce_x`,
   `atk_phantom_ultimate`, `atk_u2_v2_mini`, `atk_u2_v2_ultimate`, `atk_zero`, `vxe_r1`, `vxe_v3`,
   `vxe_x3`. Les sources tierces sont autorisées (§10.1) : chacune devra porter sa provenance
   (`fit_status`) et une divergence avec le fabricant ne devra jamais écraser ce dernier.
2. **Hauteur des boutons : 25 souris sur 36.** Aucun fabricant ne la publie (vérifié) ; la mesure se
   fait sur les visuels récupérables (`tools/measure_button_height.py`), vue de côté uniquement.
   C'est le critère qui pèse le plus : 11 273 profils sur 27 170 ont un match idéal partiel.
3. **Position de la bosse : une seule souris** (`vxe_x3`, coque partagée avec l'ATK X1).
4. **Trois prix à revérifier à la boutique officielle** : Z1, Y9 Ultimate, GHOST Extreme (§9.5.4).
5. **Deux coques jumelles non tranchées** : `pulsar_x2a_v3_medium` et `pulsar_x2_crazylight_medium`
   (dimensions publiées identiques, aucune source fabricant ne confirme qu'il s'agit de la même
   coque).

## 11. Dix-huitième passe (2026-10-12) : les prises publiées par les fabricants entrent au catalogue

Le propriétaire a demandé de documenter les souris restées « sans prise publiée » et de vérifier les
prix à la boutique officielle. Cette passe ne touche **aucun barème** : uniquement des données
sourcées, chacune datée — et les canaris qui en dépendent.

### 11.1 Neuf souris sur dix reçoivent leur prise, du fabricant lui-même

Fiches officielles ATK (`atk.store`, pays France, relevé du 2026-10-12), champ « **Grip Style** » :
mention explicite → « Élevé », prise non mentionnée → « Inconnu » (jamais de déduction).

| Souris | Prise publiée par le fabricant | Suite |
|---|---|---|
| ATK Duckbill | Claw / Palm / Fingertip | prise documentée (souris toujours inutilisable, §11.6) |
| ATK Fierce X | **Claw uniquement** | Palm et Fingertip restent « Inconnu » |
| ATK Phantom Ultimate | Claw / Palm / Fingertip | devient la tête du profil Palm de référence (§11.6) |
| ATK U2 V2 Mini et Ultimate | **Claw** | Palm et Fingertip restent « Inconnu » |
| ATK ZERO | Claw / Palm / Fingertip | — |
| VXE Dragonfly R1 / V3 / X3 | Claw / Palm / Fingertip | — |
| ATK Y9 Ultimate | Claw **et** Palm (palm déjà publié) | claw complété |

- **ATK Blazing Sky F1 V2 : aucune prise.** Le bloc « Specifications » de sa fiche n'est pas lisible
  par le robot et `mouseshape.com/mice/atk-f1-v2` répond 404 : la souris reste « à vérifier », aucune
  valeur n'est devinée. C'est la seule des dix.
- Provenance : `fit_status = manufacturer_guide`, citation et source datée dans la fiche, partout.
  Aucune source tierce n'a été nécessaire pour ces neuf souris.

### 11.2 Cinq prix officiels corrigés (règle « boutique officielle »)

| Souris | Avant | Après | Source datée |
|---|---:|---:|---|
| `atk_z1_ultra` (Z1 V2 **Ultimate**) | 75,00 € (cahier des charges) | **59,95 €** | fiche ATK, `?country=FR`, 2026-10-12 |
| `atk_y9_ultimate` (Y9 **Ultimate**) | 41,95 € (modèle d'entrée) | **59,95 €** | fiche ATK, `?country=FR`, 2026-10-12 |
| `atk_ghost_extreme` (GHOST **Extreme**) | 68,95 € (prix de l'Ultimate) | **86,95 €** | fiche ATK, variante `47320425627866`, 2026-10-12 |
| `atk_f1_ultimate` (F1 V3 **Ultimate+**) | 70,00 € (cahier des charges) | **59,95 €** | fiche ATK, modèle « Ultimate+ », 2026-10-12 (variante en précommande) |
| `atk_x1_ultra_max` (X1 V2 **Ultra Max 2.0**) | 75,00 € (cahier des charges) | **40,95 €** | fiche ATK, variante « Ultra Max 2.0 / Black », 2026-10-12 |

Les cinq relevés sont datés, la source officielle est inscrite dans chaque fiche, et l'ancienne valeur
(quand elle existait) reste citée dans la note. La règle du propriétaire est donc **entièrement
appliquée** : plus aucun prix du catalogue ne vient d'un revendeur ou d'un cahier des charges non
vérifié.

### 11.3 Un écart de largeur relevé, rien d'écrasé

La fiche officielle de la **Duckbill** donne **118 × 55 × 37,4 mm** (« Best for Hand Size:
Small-to-Medium ») là où EloShapes donne 62,5 mm de largeur : l'écart est écrit dans la note de la
fiche, **aucune valeur du catalogue n'est remplacée** tant qu'il n'est pas tranché.

### 11.4 Effet mesuré

| Mesure | Avant les compléments (17e passe) | Après (18e passe) |
|---|---:|---:|
| Grille complète : profils sans résultat | 3 601 | **2 561** |
| Grille complète : deux places sur la même coque | 2 052 | **492** |
| Grille complète : profils à trois places | 6 148 (22,6 %) | **6 609 (24,3 %)** |
| Grille complète : problèmes détectés | 0 | **0** |
| Stats 18 522 : profils sans résultat | 1 044 | **252** |
| Stats 18 522 : souris jamais recommandées | 17 sur 36 | **11 sur 36** |

Six souris entrent au tableau et y restent : Fierce X, Phantom Ultimate, U2 V2 Mini, U2 V2 Ultimate,
VXE R1 et VXE V3. Le ZERO y était entré avec le relevé des prises, puis en est ressorti après la
correction du prix de l'**X1 V2 Ultra Max** (75,00 → **40,95 €**) : moins cher que lui, il ne gagne
plus aucun profil — conséquence directe des prix officiels, pas d'une donnée manquante.

Effet du **code** seul (mêmes données, `cd977a6` → arbre, 24 609 profils comparés) : match idéal
**inchangé** ; trois places 77 → **6 609** ; deux places sur la même coque 3 235 → **510** ;
économie **gagnée 6 550 / perdue 0** ; pire baisse de l'alternative **5 points**.

### 11.5 Hauteur des boutons : l'outil est validé, les images manquent

`tools/measure_button_height.py` a été rejoué le 2026-10-12 : sur une vue de profil du **Z1 V2**
(hauteur de boutons déjà connue, « High »), il redonne **55 %** de la hauteur totale — exactement la
valeur d'étalonnage (0,551). Le paramètre `--front` est décisif : la même image donne 37 % (donc
« Low ») si l'avant est inversé — d'où la règle « orientation vérifiée à l'œil avant de mesurer ».

En revanche, **aucune nouvelle vue exploitable** n'a pu être récupérée : toutes les images obtenues
par recherche (Phantom, U2, U2 Mini, F1 V3, R1, Ghost) sont refusées par le contrôle de perspective
du banc — autre modèle ou autre angle. **Aucune valeur n'a donc été inscrite** : les 25 souris sur 36
restent sans hauteur de boutons. La commande le prouve : chaque refus affiche
« vue refusée : rapport longueur/hauteur trop éloigné des cotes officielles ».

### 11.6 Conséquence assumée : l'ATK Phantom Ultimate passe devant les souris du propriétaire

Sur le profil Palm 180 × 90, tous modes, l'ATK Phantom Ultimate atteint **35/40** : sa prise est
désormais publiée par son fabricant, il n'est donc plus « en attente ». Les quatre souris du
propriétaire gardent exactement leurs points (V6 30, Z1 30, A9 Plus 25, X1 20) et restent juste
derrière. La règle du 2026-10-12 reste vraie — une souris **incomplète** ne dépasse jamais le
propriétaire — mais le Phantom n'est plus incomplète. Cinq tests de flux et un test de barème
figeaient l'ancien gagnant : réécrits avec la date et la raison (jamais « ajustés »), et la sentinelle
« le Phantom ne doit pas apparaître » remplacée par les écartées du jour.

### 11.7 Ce qui reste ouvert après cette passe

1. ~~Une souris sans prise publiée~~ → **réglé en 21e passe** : `atk_f1_v2` reçoit les compatibilités de sa coque jumelle (§11.8) ; plus aucune souris du catalogue n'est `unverified`.
2. **La Duckbill reste inutilisable** : sa longueur est en conflit (118 vs 117 mm) et sa largeur est
   contestée (55 mm officiel contre 62,5 mm EloShapes). Trancher avec une seule source à la fois.
3. **Hauteur des boutons : 25 souris sur 36** (aucun fabricant ne la publie).
4. **Bosse de la VXE X3** (`vxe_x3`) : coque partagée avec l'ATK X1, position non publiée.
5. **Deux coques jumelles non tranchées** : `pulsar_x2a_v3_medium` / `pulsar_x2_crazylight_medium`.

---

### 11.8 ATK F1 V2 débloquée par sa coque jumelle (21e passe, 2026-10-12)

**Le problème.**

Depuis la 16e passe, le rapport de statistiques désignait une souris que rien ne pouvait faire entrer
dans le tableau : l'**ATK Blazing Sky F1 V2**, la **seule** du catalogue sans aucune compatibilité de
prise publiée. Sa fiche officielle ne contient aucune recommandation de prise — le « Grip Style:
Claw / Palm » de sa page est la mention marketing générique que la règle du §1 de
`docs/audit/CATALOGUE_ATK.md` interdit de convertir en compatibilité — et `mouseshape.com/mice/atk-f1-v2`
(page tierce autorisée depuis le 2026-10-12) répond **404** : vérifié ce jour.

**La décision : hériter de la coque, jamais deviner.**

La F1 V2 partage la **coque** de l'ATK F1 V3 Ultimate (`shell_id` = `atk_f1` : 118,2 × 62,4 × 38,8 mm,
bosse « Mid », boutons bas) — le catalogue utilise déjà `shell_id` pour les dimensions partagées
(`utils/models.py`). Les verdicts de prise de cette coque sont connus et datés (cahier des charges du
propriétaire : Palm « Faible », Claw « Élevé », Fingertip « Élevé ») : ils sont **repris tels quels**
pour la F1 V2, avec `fit_status = owner_spec` et une source dédiée qui déclare les trois champs. Rien
n'est deviné : géométrie identique au dixième de millimètre, et le verdict palm reste défavorable
(exclusion 180×90), donc les deux générations restent cohérentes entre elles.

**Effet mesuré** (grille complète, 18 522 profils, moteur inchangé — seule la donnée change) :

| Mesure | Avant | Après |
|---|---|---|
| Sorties de l'ATK F1 V2 | **0** (11 760 profils « à vérifier ») | **4 778** (idéal 2 503, alternative 1 685, économie 590) |
| Souris jamais recommandées | 11 sur 36 | **10 sur 36** |
| Sorties de l'ATK F1 V3 Ultimate (même coque) | 4 073 | **669** |
| Profils où deux places montrent la même coque | 299 | 683 (dont 384 paires F1 V3 + F1 V2) |
| Profils sans aucun résultat | 252 | 252 (inchangé) |

La V3 Ultimate cède donc sa place à la V2 là où seule la même coque était éligible : c'est le
comportement voulu (même forme, moins chère — 40,95 € contre 59,95 €) ; la V3 garde les profils où le
mode « Peu importe le prix » départage par les composants (PAW3955 Master, Nordic 54LM20). Le repli
« deux places, même coque » passe de 299 à 683 profils sur 18 522 (3,7 %) : c'est le repli documenté de
`result_slots()`, il reste minoritaire. Le chiffre « souris jamais recommandées » du tableau §11.4
(passé de 17 à 11 sur 36 par les cinq prix du 19e) est donc maintenant de **10 sur 36**.

**Prix relevé au passage.**

La même vérification a mis à jour le prix officiel de la F1 V2 : **40,95 €** (fiche ATK pays France,
variante « Ultra Max 2.0 / Black », prix normal 63,95 €, relevé le 2026-10-12) contre 41,95 €
(« à partir de » de la collection relevé le 2026-10-11). Autres modèles de la série : Ultimate 2.0
(39 ± 2 g, modèle décrit en base) **54,95 €**, Extreme 2.0 **77,95 €**.

**Preuves.**

- `pytest -q` : **346 tests** (344 + 2 ajoutés) — dont deux nouveaux tests dans `tests/test_data.py` :
  la F1 V2 porte exactement les verdicts de sa coque jumelle et une source déclare chaque champ ;
  **aucune souris du catalogue n'est `unverified`**.
- `tools/qa_flow_matrix.py` (grille complète, 27 170 profils) : **0 problème**, aucune impasse ;
  2 561 profils sans résultat (inchangé), 1 410 replis de coque, **6 523 profils à trois places
  (24,01 %)** ; la grille rapide (720 profils) donne elle aussi 0 problème.
- `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` et `docs/audit/matrice_profils.md`
  régénérés par leurs outils (jamais édités à la main).
