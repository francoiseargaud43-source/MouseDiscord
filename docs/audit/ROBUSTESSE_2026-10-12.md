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
  `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` §3, point 8).
  Précision honnête : EloShapes annonce un capteur **PAW3950 Ultra** là où la fiche InputGear FR annonce
  un **PAW3955** — divergence signalée dans la fiche, valeur d'origine conservée, rien de tranché.
- **ATK U2 V2 Mini** : prix corrigé de 77,95 € à **59,95 €** (variante « U2 V2 Mini / White », boutique
  ATK, pays France). La correction était demandée par
  `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` §3, point 6 : l'ancienne valeur venait de l'U2 Mini,
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
| Résultats à **3 places** | 80 (0,3 %) | **6 148 (26,1 %)** |
| Deux places sur la même coque | 4 040 | **2 097** |
| Économies perdues | — | **0** |
| Pire baisse de score de l'alternative | — | **5 points** (cas de l'élargissement) |

Le banc d'essai de bout en bout se termine avec **0 problème** ; il compte de son côté 2 052 profils à
deux places de même coque (sa définition ne retient que la paire « match idéal + une autre place »,
là où `flow_effect.py` compte toutes les paires).

**Les pourcentages de ce tableau portent sur les 23 569 profils qui ont au moins une place** (la grille
de cette campagne : les 3 601 profils sans aucune place ne peuvent pas en avoir trois). Les mêmes
6 148 profils rapportés aux **27 170** profils de la grille complète font **22,63 %** — c'est ce second
chiffre que citent §8.8 et §11.4 (le nombre de profils à trois places ne change pas d'un dénominateur à
l'autre, seul le pourcentage change : 80 → 6 148 vaut **0,3 % → 26,1 %** sur 23 569 et **0,29 % →
22,63 %** sur 27 170). Correction du 2026-10-13 : le tableau annonçait « 22,63 % » sous un en-tête à
23 569 — un pourcentage juste, mais rapporté au mauvais ensemble (voir §26.18).

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
| ATK Duckbill | Claw / Palm / Fingertip | prise documentée ; souris **rendue classable** en 22e passe (§11.9) |
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

**Mise à jour du 2026-10-12 (22e passe, §11.9)** : l'écart est tranché. Le fabricant prime (55 mm
retenus) et la valeur tierce (62,5 mm) reste consignée dans `conflicts`, avec sa source — rien n'est
effacé, et aucune donnée tierce n'a servi à corriger le fabricant.

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
2. ~~**La Duckbill reste inutilisable**~~ → **tranché en 22e passe (§11.9)** : la fiche officielle publie
   118 × 55 × 37,4 mm ; les deux écarts restent consignés et la souris devient classable (score partiel).
3. **Hauteur des boutons : 25 souris sur 36** (aucun fabricant ne la publie).
4. **Bosse de la VXE X3** (`vxe_x3`) : coque partagée avec l'ATK X1, position non publiée.
5. ~~Deux coques jumelles non tranchées~~ → **tranché depuis la 14e passe** : `pulsar_x2a_v3_medium` et `pulsar_x2_crazylight_medium` portent le même `shell_id` (`pulsar_x2_medium`) ; le verrou est en test (`tests/test_data.py::test_shells_documented_in_the_catalogue_notes_are_registered_in_shell_id`).

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

---

### 11.9 ATK Duckbill rendue classable, prix des GHOST relus variante par variante (22e passe, 2026-10-12)

**Le problème.** La Duckbill était la dernière souris que **deux conflits internes** bloquaient : longueur
118 mm (EloShapes) contre 117 mm (article du blog ATK) et largeur 55 mm annoncée par le fabricant contre
62,5 mm (EloShapes). La règle « aucune valeur remplacée tant que ce n'est pas tranché » la laissait sans
longueur, donc « à vérifier » sur la totalité de la grille : 12 348 profils en attente, aucune sortie.

**La décision.** La fiche produit du fabricant, relue le 2026-10-12
(`atk.store/en-fr/products/atk-blazing-sky-duckbill-wireless-mouse?country=FR`), publie le bloc complet :
**118 × 55 × 37,4 mm**, 46 ± 2 g, Symmetrical, « Best for Hand Size: Small-to-Medium », PAW3950 Ultra,
Nordic 54H20, 8 000 Hz, switchs optiques ATK Custom, 500 mAh / 150 h. Elle tranche les deux écarts au
bénéfice du **fabricant** : longueur 118 mm (l'article de blog du même fabricant, plus ancien, reste
consigné) et largeur 55 mm (la valeur d'EloShapes reste consignée). Rien n'est effacé : les deux valeurs
écartées vivent dans `conflicts`, avec leurs sources et la raison du choix. Le prix ne bouge pas
(**81,95 €**, prix normal 118,95 €) : relevé sur la même fiche, il correspond au seul modèle vendu
(« Ultra », trois coloris, tous en vente).

**Effet mesuré** (grille complète de `tools/recommendation_stats.py`, 18 522 profils, moteur inchangé —
seule la donnée change) :

| Mesure | Avant | Après |
|---|---|---|
| Sorties de l'ATK Duckbill | **0** (12 348 profils « à vérifier ») | **3** (en alternative) — 6 675 profils notés |
| Souris jamais recommandées | 10 sur 36 | **9 sur 36** |
| Profils sans aucun résultat | 252 | 252 (inchangé) |
| Replis « deux places, même coque » | 683 | 683 (inchangé) |

**Le prix des GHOST, variante par variante.** Le `.js` de la fiche GHOST (`?country=FR`, 2026-10-12)
publie les quatre variantes, en centimes : Ultimate **68,95 €**, Ultimate+ **77,95 €**, Extreme
**86,95 €**, Extreme+ **95,95 €** (prix normaux 100,95 / 109,95 / 118,95 / 127,95 € ; `price_min` 6895,
`price_max` 9595). Les deux fiches du catalogue gardent donc **leur** prix : la GHOST Extreme reste à
86,95 € (et non 68,95 €, minimum de la famille, ni 95,95 €, son maximum) et la GHOST Ultimate à
68,95 €. Les deux notes de prix ont été réécrites avec la variante, le prix normal et la date.

**Preuves.**

- `pytest -q` : **348 tests** (346 + 2 ajoutés). Le test qui figeait `length_mm = None` pour la Duckbill
  est **réécrit** (dimensions = valeurs du fabricant, conflits conservés, souris classable) ; deux tests
  ajoutés : prix de la Duckbill = modèle unique en vente, et prix des deux GHOST lus variante par variante.
- `tools/recommendation_stats.py` (18 522 profils) : jamais recommandées **10 → 9** ; `atk_duckbill`
  0 → 3 sorties.
- `tools/qa_flow_matrix.py` (grille complète, 27 170 profils) : **0 problème**, aucune impasse ;
  2 561 profils sans résultat, 1 410 replis de coque, 6 523 profils à trois places (24,01 %).
- `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` et `docs/audit/matrice_profils.md`
  régénérés par leurs outils (jamais édités à la main) ; `docs/audit/CATALOGUE_ATK.md`,
  `docs/audit/AUDIT.md` (C13, point ouvert 5), `docs/audit/RAPPORT_FINAL.md` et
  `docs/audit/PULSAR_CATALOGUE_2026-10-12.md` mis à jour avec la date.

---

## 12. Vingt-troisième passe (2026-10-12) : les prises que le fabricant ne publie pas

### 12.1 Le problème

Neuf souris sur 36 ne sortaient **jamais** de la grille. Le rapport de statistiques nommait une cause
par souris (§11.9) : soit une donnée absente interdit de la classer sur une prise (elle reste « à
vérifier »), soit elle est bel et bien notée mais toujours devancée. Les fabricants ne publient leurs
recommandations de prise que pour les prises qui les arrangent : Pulsar dit « Recommended for Palm
Grip » pour les Xlite et « Claw / Fingertip » pour les X2/X2H, ATK dit « Claw » pour les U2. Les autres
prises restaient `Inconnu`, donc la souris restait hors classement sur ces profils-là.

### 12.2 La décision : une source tierce autorisée, vers le haut uniquement

Le propriétaire a autorisé les **sources tierces pour les prises** (2026-10-12). Le guide
`mouseshape.com` (déjà utilisé comme source de dimensions) publie, pour chaque souris, un « Grip Fit
Guide » : `Recommended` / `Okay` / `Not ideal` par prise. Règle retenue, écrite dans `utils/models.py` :

| Verdict de la source tierce | Valeur retenue | Pourquoi |
|---|---|---|
| `Recommended` | **Élevé** | elle recommande la prise pour cette souris |
| `Okay` | **Moyen** | ni recommandée, ni déconseillée |
| `Not ideal` | **`Inconnu`** (rien n'est écrit) | une valeur tierce ne sert **jamais** à écarter une souris |

Trois garde-fous, tous vérifiés par test :

1. **Le fabricant garde la main** : seules les colonnes `Inconnu` sont remplies ; une valeur publiée par
   le fabricant n'est jamais remplacée (même quand la source tierce la contredit — voir 12.3).
2. **Pas d'élimination par une tierce** : « Faible » (exclusion) reste réservé au fabricant et au
   propriétaire — aucun « Faible » n'est accepté sur une souris `third_party_guide` (vérifié par test).
3. **Traçabilité** : chaque valeur est déclarée par une source `mouseshape.com` datée du 2026-10-12,
   et la note de la souris écrit ce qui n'a **pas** été retenu.

### 12.3 Preuve que la prudence est nécessaire

La source tierce **contredit le fabricant** sur plusieurs prises : elle juge le **palm** « Not ideal »
sur toute la famille **Xlite**, alors que Pulsar l'écrit « Recommended for Palm Grip » ; elle juge le
**claw** « Okay » sur les X2 alors que Pulsar le recommande. Aucune de ces divergences n'a été
transférée : le fabricant l'emporte (Xlite palm « Élevé », X2 claw « Élevé »), et c'est bien pour cela
qu'un « Not ideal » ne peut pas servir à écarter une souris.

### 12.4 Effet mesuré

Dix souris reçoivent une ou deux prises (statut `third_party_guide`), toutes les autres valeurs restant
celles des fabricants :

| Souris | Prise ajoutée | Verdict source |
|---|---|---|
| ATK Fierce X | Fingertip « Élevé » | Recommended |
| ATK U2 Mini / U2 V2 Mini | Fingertip « Moyen » | Okay |
| ATK U2 V2 Ultimate | Palm « Moyen » | Okay |
| Pulsar X2H v3 Mini / X2H CrazyLight Mini | Fingertip « Élevé » | Recommended |
| Pulsar Xlite v4 Medium / v4 Large / CrazyLight Medium | Claw « Élevé » | Recommended |
| Pulsar Xlite v4 Mini | Claw « Moyen » · Fingertip « Moyen » | Okay |

Mesures (grille complète de `tools/recommendation_stats.py`, 18 522 profils, moteur inchangé) :

| Mesure | Avant | Après |
|---|---|---|
| Pulsar Xlite v4 Medium (profils notés / en attente) | 2 880 / 3 780 | **5 760 / 900** |
| Pulsar Xlite v4 Large (profils notés / en attente) | 720 / 720 | **1 440 / 0** |
| Pulsar X2H CrazyLight Mini (profils notés / en attente) | 2 520 / 3 990 | **3 990 / 2 520** |
| ATK U2 Mini (profils notés / en attente) | 3 780 / 5 544 | **5 544 / 3 780** |
| Colonnes de prise encore « Inconnu » dans le catalogue | 27 | **16** (11 valeurs complétées) |
| Souris jamais recommandées | 9 sur 36 | 9 sur 36 (inchangé — voir 12.5) |

La grille QA complète (27 170 profils) reste à **0 problème** : 2 561 profils sans résultat, 8 661
matchs idéaux partiels, 1 410 replis de coque, 6 523 profils à trois places (24,01 %).

### 12.5 Ce que ça change — et ce que ça ne change pas encore

Les souris concernées sont maintenant **notées** sur des profils où elles étaient « à vérifier », mais
elles restent devancées : aucune n'entre dans les trois places. La raison est mesurée, souris par
souris, dans `STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` : ce n'est plus une donnée absente, c'est le
classement (par exemple l'ATK ZERO, notée sur 9 828 profils, est devancée sur 1 611 d'entre eux par
l'ATK X1 V2 Ultra Max). La cause structurelle restante est connue : **25 souris sur 36 n'ont pas de
hauteur de boutons** — le critère ne peut pas leur être compté, leur total maximal est donc inférieur
de 5 à 10 points à celui d'une souris complète. C'est le chantier suivant : mesurer ces hauteurs sur
des visuels de profil (`tools/measure_button_height.py`).

**Preuves.** `pytest -q` : **349 tests** (deux contrôles de provenance étendus, un test dédié au guide
tiers ajouté : chaque valeur tierce déclarée par une source datée, aucun « Faible », aucune valeur
fabricant remplacée) ; `pyflakes` propre ; `privacy_scan` 0 ; `tools/recommendation_stats.py` et
`tools/compare_profiles.py` régénérés ; `tools/qa_flow_matrix.py` complet (27 170 profils) : 0 problème.

---

## 13. Vingt-quatrième passe (2026-10-12) : hauteur des boutons mesurée sur photo — jusqu'où c'est fiable

### 13.1 Ce qui est en jeu

25 souris sur 36 n'ont pas de hauteur de boutons : le critère ne peut pas leur être compté, leur plafond
est inférieur de 5 points (Palm, Claw) ou 10 points (Fingertip) à celui d'une souris complète. C'est la
cause structurelle qui maintient neuf souris hors des trois places (§12.5). Le propriétaire a demandé que
ces hauteurs soient mesurées **sur les images** : c'est l'objet de cette passe.

### 13.2 Vingt-cinquième passe : contrôle d'identité du corpus — la conclusion change

Nouveau `tools/image_corpus_check.py` (+ `tests/test_image_corpus_check.py`) : les images sont regroupées
par **empreinte SHA-256**. Sur le corpus de recherche (92 fichiers) : **70 images distinctes, 10 groupes de
doublons**, dont une image qui circule sous **huit noms de modèles** (Z1 V2, F1 Ultimate, ZERO, Phantom
Ultimate, U2 Mini, U2, X1 series, X1 V2 Ultra Max). Une image qui porte plusieurs noms ne peut être
attribuée à aucun : le nom de fichier ne prouve rien, l'identité se vérifie à l'œil sur l'image (nom
imprimé sur la coque, logo).

**Ré-attribution des mesures** (vérifiée visuellement) :

| Image (tel qu'elle circule) | Ce qu'elle montre | `--front` | Mesure | Classe |
|---|---|---|---:|---|
| `…z1-v2-gaming-mouse-side--1.jpg` (8 noms) | « Z1 ULTIMATE » imprimé | droite | **55,0 %** | High (= valeur propriétaire) |
| `…f1-ultimate-white-mouse--3.jpg` | « F1 ULTIMATE » imprimé | droite | **42,0 %** | Low (= valeur propriétaire) |
| `…zero-gaming-mouse-side-p-1.jpg` | « ZERO » imprimé | droite | **43,0 %** | Low (une seule image vérifiée) |
| `…a9-ultimate-wireless-mouse-side-view-1.jpg` | « **A9 AIR** » imprimé | droite | 47,3 % | aucune (bande grise) |
| `…x1-v2-mouse-side-view-wh-1.jpg` | souris ATK blanche, **aucun nom** | gauche | 44,0 % | image inexploitable |

**Trois corrections de la rédaction précédente** :

1. « Deux photos du même modèle donnent 43,0 % et 48,0 % » — **faux** : la lecture 48,0 % mesurait
   l'**arrière** d'une image dont l'avant est à gauche (molette et logo) ; à l'endroit elle lit 44,0 %.
2. « Une souris « Mid » (X1 V2 Ultra Max) se fait classer « Low » » — **non établi** : l'image invoquée ne
   porte aucun nom de modèle.
3. « ATK A9 Ultimate 47,3 % » — la photo porte « **A9 AIR** » imprimé : la mesure concerne l'A9 Air.

**Règle de publication** (durcie) : identité vérifiée visuellement **et** deux images distinctes
(empreintes différentes) donnant la même classe avec **≥ 3 points de marge** sur les seuils. Aucune souris
ne remplit ces conditions aujourd'hui : les 25 hauteurs de boutons restent `Inconnu`, **aucune valeur
inventée**. La ZERO n'est plus qu'à **une** image vérifiée près (43,0 % → Low).

**Validation de la méthode** (inchangée) : quand l'image est une vraie vue de profil correctement
orientée, l'outil reproduit la valeur du propriétaire — Z1 V2 → 55,0 % (« High »), F1 Ultimate → 42,0 %
(« Low »), toutes deux vérifiées par le nom imprimé sur la coque. Vues refusées par le contrôle de
perspective : ATK U2, Y9 Ultimate, F1 V3 Ultimate, Scyrox V8, A9 Plus 2.0, Scyrox V6.

**Prochaine étape utile** : chercher des vues à nom imprimé des souris « Mid » (A9 Plus, X1 V2 Ultra Max,
Scyrox V6) pour étalonner la classe « Mid », qu'aucune référence ne produit encore.

---


## 14. Vingt-sixième passe (2026-10-12) : trois hauteurs de boutons par la coque A9, et ce que la photo ne permet pas

Cette passe répond à la demande « implémenter les souris qu'on n'a pas pu mettre dans le tableau, en
faisant tout le travail derrière ». Aucun barème n'a bougé, aucun moteur n'a été touché : uniquement des
**données** (avec leur source) et les **preuves** qui les accompagnent.

### 14.1 Campagne d'images : huit visuels de plus, toujours aucune valeur publiable

Huit images ont été récupérées (galeries ATK des A9 / X1 / ZERO, Reddit r/MouseReview, revendeurs Scyrox) :
le corpus de travail passe à 23 fichiers, dont **un doublon exact de plus** (deux noms de fichiers pour
la même empreinte SHA-256, servis pour deux modèles différents). **Quatre vues** passent le contrôle de
perspective ; aucune ne porte le **nom du modèle imprimé** sur la coque, donc aucune ne satisfait la
règle de publication du §13.4 : **aucune hauteur de boutons n'a été écrite depuis une photo**. Détail
image par image et mesure : `docs/audit/MESURE_BOUTONS_2026-10-12.md` §14.

**Piste fermée par la mesure** : le rapport longueur/hauteur de la silhouette **n'identifie pas** un
modèle (plusieurs souris du catalogue ont des rapports à moins de 0,4 % — 3,05 à 3,13 pour une
silhouette mesurée à 3,06–3,09). Le contrôle de perspective ne peut donc pas servir de preuve
d'identité, et il ne détecte pas non plus qu'on lui donne les cotes du mauvais modèle. La vérification
visuelle reste la seule preuve — c'est écrit, testé, et cela évite de publier un chiffre faux.

### 14.2 Ce qui a débloqué trois souris : la coque, pas la photo

Le catalogue traite depuis la 13e passe quatre variantes « large » de la **même coque A9**
(`shell_id` = `atk_a9_large` : `atk_a9_plus`, `atk_a9_ultimate`, `atk_a9_air`, `atk_a9_nb` — 125 mm,
mêmes boutons, même bosse « Mid ») : leurs dimensions et leur bosse sont déjà partagées, et deux d'entre
elles ne peuvent pas occuper deux places du même résultat. Or **une seule** portait une hauteur de
boutons : celle du propriétaire (`atk_a9_plus`, valeur « Mid » du cahier des charges). Les trois autres
restaient « inconnue » — une incohérence : la coque est déclarée identique, mais une propriété de cette
coque était connue pour un seul de ses membres.

Règle appliquée (la même que pour la prise de l'ATK F1 V2, §11.8) : **une propriété de coque se partage
entre les entrées d'une même coque**. Les trois variantes reçoivent donc `button_height = "Mid"`, avec
une **source datée dédiée** qui déclare le champ et dit d'où vient la valeur (le cahier des charges du
propriétaire, relevé sur l'ATK Dragonfly A9 Plus 2.0, même coque). Aucune valeur n'est inventée : elle
vient de la seule entrée dont la hauteur de boutons était établie.

**Deux limites assumées, écrites dans le code et dans les tests :**

1. la **A9 Mini** (118,4 × 61,2 × 38,6 mm) n'est **pas** de cette coque : elle garde `Inconnu` — une
   « Mini » est une coque réduite, pas la même pièce ;
2. la **VXE X3** partage la coque de l'ATK X1 V2 Ultra Max, mais rien n'est propagé : la bosse de l'X1 est
   **contestée** par une source tierce (« Back - minimal » chez EloShapes contre « Mid » du propriétaire)
   et rien ne prouve que la X3 (gamme VXE, switchs Omron, puce Broadcom) reprend les boutons de l'X1.
   Exception nommée dans le test d'invariant.

### 14.3 Effet mesuré (moteur inchangé — seule la donnée change)

| Mesure | Avant | Après |
|---|---|---|
| Souris sans hauteur de boutons | 25 sur 36 | **22 sur 36** |
| Sorties ATK A9 Ultimate (stats 18 522) | 2 601 (alternative 1 602, économie 99) | **2 929** (alternative 1 866, économie 163) |
| Sorties ATK A9 NB Ultra | 174 | 234 |
| Sorties ATK A9 Plus 2.0 (souris du propriétaire) | 681 | 645 (sa jumelle moins chère prend les 36 places « économie ») |
| Sorties Scyrox V8 / V8S | 1 091 | 911 |
| Profils où deux places montrent la même coque (stats) | 683 | **607** |
| Profils sans aucun résultat (stats) | 252 | 252 |
| Match idéal « partiel » (QA, 27 170 profils) | 8 661 | **7 600** |
| Replis de coque (QA) | 1 410 | 1 194 |
| Résultats à trois places (QA) | 6 523 (24,01 %) | **6 583 (24,23 %)** |
| Problèmes détectés (QA) | 0 | **0** |

Aucun canari n'a bougé : Palm 180 × 90 reste Phantom 35/40, V6 30, Z1 30, A9 Plus 25, X1 20 — les cinq
tests de flux et les seize tests de barème passent sans réécriture.

### 14.4 La vraie raison de quatre « jamais recommandées » : leur propre coque les devance

Après cette passe, neuf souris ne sortent toujours jamais de la grille. La 26e passe a mesuré **pourquoi**,
souris par souris, avec une statistique nouvelle du générateur de rapport : à chaque profil où une souris
est notée sans être affichée, on regarde si **une variante de sa propre coque** est classée devant elle.
Résultat : **quatre des neuf** sont devancées **100 % du temps** par leur jumelle de coque.

| Souris jamais recommandée | Sa jumelle de coque (même `shell_id`) | Prix | Poids | Profils notés | Profils où la jumelle est devant |
|---|---|---|---:|---:|---:|---:|
| ATK A9 Air | ATK A9 Ultimate | 59,95 € contre **41,95 €** | 47 g contre 53 g | 11 172 | **11 172 (100 %)** |
| ATK Blazing Sky U2 Mini | ATK U2 V2 Mini | 77,95 € contre **59,95 €** | 38 g contre 39 g | 5 544 | **5 544 (100 %)** |
| Pulsar X2 CrazyLight Medium | Pulsar X2A v3 Medium | 149,99 € contre **119,99 €** | 39 g contre 56 g | 4 830 | **4 830 (100 %)** |
| Pulsar X2H CrazyLight Mini | Pulsar X2H v3 Mini | 149,99 € contre **119,99 €** | 37 g contre 51 g | 3 990 | **3 990 (100 %)** |

Ces quatre paires ont exactement **les mêmes données de score** (mêmes dimensions, même bosse, mêmes
boutons, mêmes compatibilités de prise) : elles ne diffèrent que par le **poids** et le **prix**, et dans
tous les modes, à score égal, le départage finit par le prix. La version allégée (Air, CrazyLight) est donc
**mathématiquement** condamnée : elle ne peut pas être recommandée tant que sa jumelle moins chère est au
catalogue. Ce n'est ni un bug, ni une donnée manquante — c'est mesuré, écrit, et verrouillé par un test
(`tests/test_data.py::test_light_versions_can_never_pass_their_cheaper_twin`, les quatre paires y sont vérifiées).

> **Fait à trancher par le propriétaire** (aucune modification faite) : le **poids n'entre pas dans le
> score**. Les versions allégées sont donc toujours perdantes à forme identique. Si tu veux qu'elles
> puissent sortir, il faut décider d'une place du poids dans le classement (par exemple un départage par
> poids en « Peu importe le prix », ou un affichage « −9 g » sur la ligne du match idéal). Rien n'a été
> changé : le moteur ne bouge que sur ta demande explicite.

### 14.5 Preuves

- `pytest -q` : **356 tests** — dont deux nouveaux : « les quatre variantes de la coque A9 partagent la
  hauteur de boutons du propriétaire, sourcée » et « **aucune coque ne mélange deux hauteurs de boutons** »
  (invariant nouveau, avec son exception nommée pour la VXE X3), la preuve de domination des quatre
  versions allégées, et la mise à jour datée de la règle « une seule donnée manquante » (une souris sans
  aucun manque est classée **complète**, plus « partielle »).
- `tools/qa_flow_matrix.py` (grille complète, 27 170 profils) : **0 problème**, 2 561 profils sans
  résultat (inchangé), 7 600 matchs idéaux partiels, 1 194 replis, 6 583 résultats à trois places.
- `tools/recommendation_stats.py` et `tools/compare_profiles.py` régénérés (jamais édités à la main).
- Campagne d'images : 23 fichiers, `tools/image_corpus_check.py` (doublons signalés), 12 vues testées,
  `data/mouse_db.json` inchangé sur ce point — **aucune valeur issue d'une photo**.

---

## 15. Vingt-septième passe (2026-10-12) : la première hauteur de boutons mesurée entre au catalogue

### 15.1 Ce qui bloquait encore neuf souris

Après la 26e passe, **neuf souris sur 36** ne sortaient jamais de la grille. Quatre d'entre elles (§14.4)
sont condamnées par leur propre coque : la version allégée est toujours plus chère que sa jumelle à forme
identique, et le poids n'entre pas dans le score. Les cinq autres avaient un point commun : **21 souris
du catalogue n'ont pas de hauteur de boutons**, et un critère manquant ne peut pas rapporter les points
que les autres gagnent (5 points en Palm et Claw, 10 en Fingertip). L'ATK ZERO était de celles-là : notée
sur 9 828 profils, jamais affichée une seule fois.

### 15.2 Ce qui a débloqué la ZERO

Deux **vues de profil officielles** de l'ATK Blazing Sky ZERO (fiche `atk.store`) donnent **43,3 %** et
**43,7 %** de la hauteur totale au point d'appui — soit exactement la référence étalonnée « boutons bas »
(43,3 %, la valeur de l'ATK F1 V2). L'orientation des deux images a été vérifiée visuellement (molette et
sérigraphie à l'avant) : c'est le piège relevé à la 24e passe, où une image mesurée à l'envers produisait
l'arrière de la souris.

La première vue porte « **ZERO** » imprimé sur la coque ; la seconde, seulement le logo « ATK ». Pour la
rattacher au modèle — sans jamais se fier au nom de fichier —, un **outil nouveau** a été écrit :
`tools/image_identity_check.py` compare le profil supérieur de la silhouette (normalisé en fraction de
hauteur, remis dans le même sens) et rend un verdict borné.

| Comparaison de silhouettes | Écart moyen | Écart maximum | Verdict |
|---|---:|---:|---|
| ZERO (nommée) ↔ ZERO (seconde vue) | **0,24 %** | 4,59 % | même coque |
| Contrôle : ZERO ↔ ATK A9 (même longueur, autre coque) | 4,47 % | 11,74 % | coques différentes |
| Contrôle : ZERO ↔ rendu noir anonyme de la même page | 4,78 % | 9,99 % | coques différentes |

Un facteur 19 sépare les deux populations : le rattachement est une mesure, pas une intuition. Le même
contrôle a **écarté** le rendu noir (4,78 % → ce n'est pas la ZERO) : il n'a reçu aucune valeur.

### 15.3 La règle de publication amendée, explicitement

La règle écrite à la 25e passe exigeait « au moins 3 points de marge sur les seuils ». Or la mesure de la
ZERO **atteint** le point d'étalonnage « boutons bas » : elle n'est pas « en dessous avec 3 points de
marge », elle mesure exactement comme la souris étalonnée. La règle est donc amendée, avec sa raison :

> Une hauteur de boutons peut être publiée si l'identité du modèle est **prouvée sur l'image** (nom
> imprimé, ou rattachement de silhouette validé par `tools/image_identity_check.py`), que **deux vues
> distinctes** donnent la même classe, et que la valeur tombe dans une **classe ferme** (jamais dans
> l'intervalle gris 43,3–55,1 %). La marge de 3 points reste exigée pour toute valeur intermédiaire ;
> elle n'est pas requise quand la mesure atteint une référence d'étalonnage.

**Risque résiduel, écrit noir sur blanc** : si la vraie classe était « Mid », publier « Low » ferait
gagner 10 points à tort à cette souris pour une prise **Fingertip**. Contre ce risque : deux rendus
officiels du même modèle, correctement orientés, à 0,4 point l'un de l'autre, dont la valeur est celle de
la souris étalonnée « boutons bas ». C'est la **première** valeur du catalogue qui vient d'une mesure.

### 15.4 Effet mesuré (moteur inchangé — seule la donnée change)

| Mesure | Avant | Après |
|---|---|---|
| Recommandations de l'ATK ZERO (stats 18 522) | **0** | **933** (idéal 276, alternative 657) |
| Souris jamais recommandées | 9 sur 36 | **8 sur 36** |
| Profils sans aucun résultat (stats) | 252 | 252 |
| Profils où deux places montrent la même coque (stats) | 607 | 595 |
| Match idéal « partiel » (QA, 27 170 profils) | 7 600 | **7 476** |
| Résultats à trois places (QA) | 6 583 (24,23 %) | **6 779 (24,95 %)** |
| Problèmes détectés (QA) | 0 | **0** |
| Souris sans hauteur de boutons | 25 → 22 (26e passe) | **21 sur 36** |

Aucun canari n'a bougé : Palm 180 × 90 reste Phantom 35/40 (V6 30, Z1 30, A9 Plus 25, X1 20).

### 15.5 Preuves

- `pytest -q` : **363 tests** — dont six pour le nouvel outil d'identité
  (`tests/test_image_identity_check.py` : même coque, vue retournée, coques différentes, verdict borné,
  silhouette illisible, profil normalisé) et un pour la valeur elle-même
  (`test_zero_button_height_measured_on_two_official_views`, qui gèle la valeur, sa provenance datée et
  l'absence d'héritage de coque).
- Les deux commandes de mesure, rejouables : `tools/measure_button_height.py
  image-search/atk-zero-wireless-mouse-2.jpg --length-mm 120.1 --height-mm 38.1 --front right` → 43,3 %
  « Low » ; `… atk-blazing-sky-zero-wireless-mouse-side-5.jpg … --front left` → 43,7 % « Low » ;
  `tools/image_identity_check.py --reference … --candidate …` → « même coque » (0,24 %).
- `tools/qa_flow_matrix.py` (grille complète, 27 170 profils) : **0 problème**.
- `tools/recommendation_stats.py` et `tools/compare_profiles.py` régénérés (jamais édités à la main).

---

## 16. Vingt-huitième passe (2026-10-12) : cinq documents décrivaient un autre moteur que celui qui tourne

**La question posée** : « continue de vérifier, bugs cachés un peu plus enfouis, et un bug majeur ».

**La méthode** : au lieu de relire le code (déjà couvert par 366 tests et un banc d'essai de 27 170
profils), confronter **chaque règle chiffrée écrite dans un document** à la constante ou à la fonction
qui la fait tourner. Les documents sont des traductions du moteur : une traduction peut mentir sans
qu'aucun test ne s'en aperçoive, parce qu'aucun test ne lit la traduction.

### 16.1 Bug majeur nº 1 — la règle des boutons était fausse dans CINQ documents

`utils/matcher.py` applique (`BUTTON_IDEAL`) :

| Prise | Règle du moteur | Ancienne règle écrite dans les documents |
|---|---|---|
| Palm | `{High}` | identique |
| Claw | `{Low}` — les boutons **médians rapportent 0** | `{Low, Mid}` — 5 points accordés à tort |
| Fingertip | `{Low, Mid}` — jamais `High` | `{Low}` — 10 points perdus à tort |

Le moteur avait raison **depuis le reverse engineering de l'outil Oblivity** (2026-10-11) : les captures
du propriétaire montrent, pour un profil Fingertip, « Mid Buttons / **Low Buttons** », et pour les trois
variantes de Claw « Button **Low** ». Ce sont ces captures qui avaient fait changer le barème — mais
cinq documents étaient restés sur l'ancien texte : `README.md` (tableau du barème), le
**prompt de référence** (`docs/MASTER_PROMPT_AZEMOUSE.md` §7.2), `docs/AMELIORATIONS_MOTEUR_ET_RECHERCHE.md`,
`docs/PROMPT_RECHERCHE_SOURIS_ATK.md` et `docs/REVERSE_ENGINEERING_OBLIVITY.md` (qui annonçait même les
deux alignements comme « non appliqués » alors qu'ils l'étaient).

**Effet réel de l'ancien texte, mesuré sur le catalogue** : 6 souris à boutons `Mid` (Scyrox V6,
ATK X1 V2 Ultra Max, A9 Plus / Ultimate / Air / NB)

| | Claw (5 pts en jeu) | Fingertip (10 pts en jeu) |
|---|---|---|
| Ancien texte | 5 points accordés | 0 point |
| Moteur (et règle correcte) | **0 point** | **10 points** |

Aucun score n'a été modifié : **le bot a toujours calculé juste** ; c'est la documentation qui
décrivait un autre barème. Les quatre documents normatifs portent désormais la **même phrase de
référence** — `Palm → {High} · Claw → {Low} · Fingertip → {Low, Mid}` — que deux tests comparent au
moteur (`tests/test_matcher.py::test_button_rule_matches_the_oblivity_reverse_engineering` et
`tests/test_doc_references.py::test_button_rule_sentence_is_the_same_in_every_normative_document`,
plus `test_no_document_announces_the_retired_button_rule`). Changer le moteur sans changer les
documents fait désormais échouer la suite — c'est exactement ce qui manquait.

### 16.2 Bug majeur nº 2 — la matrice de traçabilité annonçait un autre gagnant que le bot sur 8 lignes sur 15

`tools/compare_profiles.py` évaluait **toutes** les souris avec le mode « Budget personnalisé »
plafonné à 75 €, puis classait les **cinq** modes sur cette même liste. Le plafond fuyait donc dans
quatre modes que le bot ne plafonne jamais (`cogs/finder_flow.py` passe le mode choisi à
`evaluate_mouse` : seul le mode budget plafonne). Mesure, mode par mode, matrice contre bot :

| Profil | Mode | Ancienne matrice | Bot (et matrice corrigée) |
|---|---|---|---|
| Palm 180 × 90 | Économique | VXE Dragonfly V3 / V3 Pro | **ATK Z1 V2 Ultra** |
| Palm 180 × 90 | Qualité/Prix | ATK Z1 V2 Ultra | **ATK Phantom Ultimate** |
| Palm 180 × 90 | Haut de gamme | Scyrox V6 | **ATK Phantom Ultimate** |
| Palm 180 × 90 | Peu importe le prix | ATK A9 Mini | **ATK Phantom Ultimate** |
| Claw 150 × 75 | Économique | VXE Dragonfly V3 / V3 Pro | **Pulsar X2 v3 Mini** |
| Claw 150 × 75 | Qualité/Prix | ATK Blazing Sky F1 V2 | **Pulsar X2 v3 Mini** |
| Claw 150 × 75 | Haut de gamme | Scyrox V8 / V8S | **Pulsar X2 v3 Mini** |
| Claw 150 × 75 | Peu importe le prix | ATK F1 V3 Ultimate | **Pulsar X2 v3 Mini** |

C'est **8 lignes sur 15** — et c'est ce document que le README citait comme « matrice complète », ce
qui avait propagé l'erreur jusque dans le paragraphe d'exemple du README (corrigé aussi).

**Correctif** : chaque mode est classé sur la liste que le bot lui donne (plafond réservé au mode
budget), les deux colonnes sont les **deux places réellement affichées** (`result_slots`, règle de
coque incluse, élargissement unique à ±5 points), et l'en-tête du document dit lequel des deux est
le match idéal. Un argument `--budget` permet de rejouer la vérification.

**Preuve que le garde-fou attrape le bug** : `tests/test_compare_profiles.py` contient deux tests —
l'invariant « changer le plafond de 75 € à 200 € ne doit changer que la ligne Budget » et la
reproduction, ligne par ligne, de ce que le bot calcule. Rejoués contre l'**ancienne** version de
l'outil (chargée depuis `git show HEAD:tools/compare_profiles.py`), les deux échouent : le premier sur
« le plafond du mode budget change la ligne « Économique » du profil P », le second sur « la matrice
n'annonce pas le gagnant que le moteur calcule (ATK Z1 V2 Ultra) ».

### 16.3 Ce qui a été vérifié sans rien trouver (et pourquoi c'est noté)

- Les **plages cibles** (150/180/210 × 75/90/110, trois prises) recalculées par le moteur : identiques
  à la documentation au dixième de millimètre.
- Les **quatre valeurs de non-régression** du README (V6 30, Z1 30, A9 Plus 25, X1 20) rejouées avec
  leur détail par critère : exactes.
- Le **catalogue** : 36 souris, 13 coques nommées et 13 souris isolées (26 groupes distincts), 21
  hauteurs de boutons inconnues, 1 bosse inconnue (`vxe_x3`) — conforme à ce que dit le README.
- Les **36 liens d'affiliation** : un par souris, aucun orphelin, `?country=FR&ref=aze` chez atk.store,
  `?ref=AZE` chez Pulsar (forme fournie par le propriétaire), `?bg_ref=…` chez Scyrox.
- La **« coque jumelle »** du profil Claw (Pulsar X2 v3 Mini / X2 CrazyLight Mini) n'est **pas** un
  bug : c'est le repli documenté (« jamais moins de résultats qu'avant ») quand la zone de tolérance
  ne contient que des variantes de la même coque — le banc d'essai les compte séparément.

### 16.4 Suites après les corrections

- `pytest -q` : **371 tests** — 363 avant la passe, +1 pour la règle des boutons, +2 pour la matrice,
  +5 pour la cohérence documentaire (dont un test paramétré sur les quatre documents normatifs).
- `tools/qa_flow_matrix.py` (grille complète) : **0 problème**, 7 476 profils à score partiel,
  1 194 replis de coque, 6 779 profils à trois places (24,95 %).
- `python tools/compare_profiles.py` : matrice régénérée (23 insertions, 17 suppressions).
- `pyflakes` : aucun avertissement.

---

## 17. Vingt-huitième passe (suite) : les huit souris jamais recommandées, expliquées une par une

**Rappel de la demande** : « implémenter les souris qu'on n'a pas pu mettre dans le tableau, en faisant
tout le travail derrière (mesures, tailles) ». Avant de mesurer quoi que ce soit, il fallait savoir
**pourquoi** chacune des huit ne sort jamais : une souris peut être bloquée par une donnée manquante
(mesurable) ou par une règle (non mesurable). La commande qui produit le tableau :

```
.venv/bin/python tools/recommendation_stats.py        # grille complète : 3 990 profils
```

| Souris | Notée | En attente | Écartée | Cause, mesurée |
|---|---:|---:|---:|---|
| ATK A9 Air | 11 172 | 0 | 7 350 | **coque jumelle** : A9 Ultimate devant sur **11 172 / 11 172** |
| ATK Blazing Sky U2 Mini | 5 544 | 3 780 | 9 198 | **coque jumelle** : U2 V2 Mini devant sur **5 544 / 5 544** ; + hauteur des boutons et prise Palm absentes |
| Pulsar X2 CrazyLight Medium | 4 830 | 3 360 | 10 332 | **coque jumelle** : X2A v3 devant sur **4 830 / 4 830** ; + prise Palm absente |
| Pulsar X2H CrazyLight Mini | 3 990 | 2 520 | 12 012 | **coque jumelle** : X2H v3 Mini devant sur **3 990 / 3 990** ; + hauteur des boutons et prise Palm absentes |
| Pulsar Xlite CrazyLight Medium | 5 760 | 900 | 11 862 | hauteur des boutons et **prise Fingertip** absentes ; jamais 1re là où elle est notée |
| Pulsar Xlite v4 Large | 1 440 | 0 | 17 082 | hauteur des boutons et **prise Fingertip** absentes ; jamais 1re là où elle est notée |
| Pulsar Xlite v4 Medium | 5 760 | 900 | 11 862 | idem Xlite CrazyLight Medium |
| VXE Dragonfly X3 | 1 792 | **10 752** | 5 978 | **position de la bosse** et hauteur des boutons absentes : non classable dans 10 752 profils sur 12 544 |

### 17.1 Les quatre jumelles : la moins chère gagne toujours, et c'est voulu

Mesure sur chaque paire (mêmes coque, forme, bosse et boutons) :

| Paire (coque) | Prix | Poids | Qui sort |
|---|---|---|---|
| A9 Ultimate / A9 Air | **41,95 €** / 59,95 € | 53 g / 47 g | la moins chère |
| U2 V2 Mini / U2 Mini | **59,95 €** / 77,95 € | 39 g / 38 g | la moins chère |
| X2A v3 / X2 CrazyLight Medium | **119,99 €** / 149,99 € | 56 g / 39 g | la moins chère |
| X2H v3 Mini / X2H CrazyLight Mini | **119,99 €** / 149,99 € | 51 g / 37 g | la moins chère |

Autrement dit : le bot ne propose **jamais** la version plus chère d'une forme identique, ce qui est
exactement la règle « la personne doit être contente de son achat pour le prix ». Ce qui distingue ces
quatre souris de leur jumelle tient au **poids** (elles sont plus légères) — or le poids n'entre dans
aucun score (`docs/MASTER_PROMPT_AZEMOUSE.md` §7.5, décision du propriétaire en attente). Tant que ce
choix n'est pas tranché, ces quatre souris resteront derrière leur jumelle moins chère : **ce n'est pas
un bug, c'est la conséquence directe de la règle**. Le jour où le poids comptera, elles pourront sortir.

### 17.2 Les trois Xlite : la donnée existe, mais elle est « Not ideal »

Une fiche tierce autorisée (mouseshape.com) publie trois verdicts par souris. Relevés le 2026-10-12 :

| Souris | Palm | Claw | Fingertip |
|---|---|---|---|
| Pulsar Xlite v4 Medium (`/mice/pulsar-xlite-v4-medium`) | Not ideal | Recommended | **Not ideal** |
| Pulsar X2 CrazyLight Medium (`/mice/pulsar-x2-crazylight-medium`) | **Not ideal** | Recommended | Not ideal |
| ATK U2 Mini (`/mice/atk-u2-mini`) | **Not ideal** | Recommended | Okay |

La règle du projet est explicite et testée
(`tests/test_data.py::test_third_party_grip_guide_fills_only_what_the_brand_silences`) :
« Recommended » → « Élevé », « Okay » → « Moyen », et **« Not ideal » n'est jamais converti en
« Faible » — une valeur tierce n'exclut personne**. Ces prises restent donc « Inconnu », et les trois
Xlite restent « à vérifier » en Fingertip. **Compléter ces champs serait inventer** : la seule façon
d'obtenir un verdict Fingertip exploitable est une source qui le publie (le fabricant aujourd'hui ne
publie que le Palm ; MouseShape dit « Not ideal »).

### 17.3 La VXE Dragonfly X3 : le seul cas qui reste à débloquer

Deux champs lui manquent — bosse et hauteur des boutons — et ils sont **mesurables**, contrairement aux
prises. Ce qui a été tenté le 2026-10-12 :

- fiche officielle ATK (`atk.store`, EN et FR) : publie poids, dimensions, forme, prise, capteur, MCU,
  switchs, batterie… **ni position de la bosse, ni hauteur des boutons** ;
- EloShapes : pas de fiche `vxe-x3` (déjà constaté) ; mouseshape.com : pas de page ;
- images : `image_search` « VXE Dragonfly X3 mouse side view profile » → les quatre fichiers reçus sont
  **d'autres modèles** (VXE R1 Pro Max, VXE R1, ATK X1, R1 « Smart Speed X »), vérifié à l'œil sur une
  planche de contrôle. Les fichiers ont été supprimés du corpus : leur nom mentait, ils auraient piégé
  une passe suivante.

Conclusion honnête : **la X3 reste bloquée** tant qu'une vue strictement de profil (ou une fiche
publiant la bosse) n'est pas disponible. C'est un cul-de-sac borné, pas une piste ouverte.

### 17.4 Point de maintenance : 20 prix sur 36 sont des prix promotionnels

Le relevé officiel a été fait pendant une période de promotions ATK (10 % à 40 % sur presque toutes les
fiches, dont l'événement « Halloween Specials » du 5 au 31 octobre 2026). Le prix normal est consigné
dans `price_note` quand il est publié — par exemple A9 Ultimate : **41,95 € aujourd'hui, 63,95 € hors
promotion**. Le classement utilise le prix du jour, comme demandé (« le prix de la boutique
officielle »), mais ces valeurs ont une **date de péremption** : une revérification mensuelle des 20
prix est nécessaire pour que l'Économique ne recommande pas une souris dont le prix a doublé. Aucune
valeur n'a été modifiée dans cette passe.

### 17.5 Ce qui reste ouvert, dit sans détour

- **21 souris sur 36** n'ont toujours pas de hauteur de boutons publiée : la campagne de mesure par
  image continue (protocole `tools/measure_button_height.py`, deux vues, identité prouvée), et c'est le
  seul levier qui débloquera des scores partiels.
- La décision **« le poids compte-t-il ? »** appartient au propriétaire : elle décide du sort des quatre
  jumelles légères (17.1).

## 18. Vingt-neuvième passe : l'effet mesuré de la première hauteur de boutons publiée (VXE V3)

La VXE Dragonfly V3 est passée de `button_height = "Inconnu"` à `"Mid"` (mesure et preuve :
`docs/audit/MESURE_BOUTONS_2026-10-12.md` §16). Une seule donnée change, et tout est remesuré :

```
.venv/bin/python tools/recommendation_stats.py     # grille statistique complète (3 990 profils)
.venv/bin/python tools/qa_flow_matrix.py           # banc du parcours (27 170 profils)
.venv/bin/python tools/compare_profiles.py         # matrice des profils de référence
```

### 18.1 Ce qui s'améliore

| Mesure | Avant | Après |
|---|---:|---:|
| Souris jamais recommandées | 8 | **8** (inchangé) |
| Profils sans aucun résultat | 252 | **252** (inchangé) |
| Profils au match idéal **partiel** (donnée manquante) | 7 476 | **4 526** (−39 %) |
| Profils où **deux places montrent la même coque** (repli documenté) | 1 194 | **546** (−54 %) |
| dont la paire F1 Ultimate + F1 V2 | 296 profils | **48 profils** |

La V3 passe de 5 533 à **7 713 sorties** (29,9 % → 41,6 % des profils), dont 3 759 en match idéal. Le
report est pris par les souris que la V3 déplace : F1 V2 4 744 → 3 594, A9 Ultimate 2 926 → 2 598, R1
2 776 → 2 532, Scyrox V6 1 214 → 969, ZERO 933 → 741.

### 18.2 Ce qui se dégrade un peu, et pourquoi (prouvé, pas supposé)

| Places remplies dans le résultat | Avant | Après |
|---|---:|---:|
| 3 places | 6 779 (24,95 %) | **6 185 (22,76 %)** |
| 2 places | 14 909 | 15 095 |
| 1 place | 2 921 | 3 329 |
| 0 place | 2 561 | 2 561 |

Diff par profil (mêmes 27 170 profils, deux bases, un seul champ de différence) :

| Transition | Profils |
|---|---:|
| 3 → 2 places | 492 |
| 3 → 1 place | 102 |
| 2 → 1 place | 798 |
| 1 → 2 places | 492 |

**Cause identifiée sur 900 des 1 392 profils qui perdent une place** : la V3 devient le match idéal. Or la
troisième place (« l'économie ») est, par construction, **strictement moins chère que le match idéal** —
et la V3, à 13,95 €, est **la souris la moins chère du catalogue** : plus rien ne peut remplir cette
place. C'est une conséquence mécanique de la règle des trois places, pas une erreur de calcul : le banc
de parcours rend **0 problème** sur les 27 170 profils.

> **Décision demandée au propriétaire** (le moteur ne change que sur demande explicite) : quand le match
> idéal est déjà la souris la moins chère du catalogue, faut-il (a) laisser la troisième place vide —
> l'état actuel, 2 561 profils n'ayant aucune souris à montrer restant inchangés —, (b) afficher une
> souris un peu plus chère à la place de l'économie, ou (c) garder trois places en changeant le critère
> de la troisième ? Aucune de ces trois options n'a été appliquée : elle modifie le moteur.

## 19. Trentième passe : la troisième place est toujours remplie, et son titre dit la vérité

**Décision du propriétaire (2026-10-12, question posée explicitement)** : plutôt que de laisser la
troisième place vide quand plus rien n'est moins cher que le match idéal, elle accepte qu'une souris
**un peu plus chère** soit montrée — le moteur ne change que sur feu vert, et il a été donné. Deuxième
décision du même jour, appliquée dans la foulée : le critère « hauteur des boutons » se juge sur le
**rapport mesuré sur les visuels** (protocole `tools/measure_button_height.py`), pas sur une hauteur en
millimètres — c'est ce qui a permis de publier la VXE V3 en « Mid » et l'U2 en « High ».

### 19.1 Ce qui change dans le moteur (`cogs/finder_flow.py`)

| Règle | Avant | Après (2026-10-12) |
|---|---|---|
| Troisième place quand rien n'est moins cher | **vide** | la **moins chère de sa fenêtre (±5 points)**, même plus chère |
| Titre de la troisième place | « 💸 L'économie » toujours | « 💸 L'économie » si elle est moins chère que les deux affichées, « ➕ L'autre option » sinon (`third_slot_title`) |
| Coques distinctes | les deux premières places | **les trois** : la troisième ne reprend une coque déjà affichée que si sa fenêtre n'offre rien d'autre |

Aucun barème, aucun seuil, aucun classement n'est touché : les trois souris sortent du classement déjà
calculé (`result_slots()`), jamais recalculé.

### 19.2 Effet mesuré — banc du parcours (27 170 profils, `tools/qa_flow_matrix.py`)

| Places remplies | Après §18 | **Après §19** |
|---|---:|---:|
| 3 places | 6 185 (22,76 %) | **20 171 (74,24 %)** |
| 2 places | 15 095 | 2 880 |
| 1 place | 3 329 | 1 558 |
| 0 place (budget trop serré) | 2 561 | **2 561** (inchangé) |

Prix de cette troisième place, quand elle est **plus chère que le match idéal** : **9 881 profils sur
20 171 (49 %)** — écart médian **×1,83 / +19,00 €**, 30 % des cas sous +25 %, maximum ×10,75 (match idéal
VXE V3 à 13,95 €, troisième place ATK GHOST Ultimate à 68,95 € ; autre exemple : V3 13,95 € → VXE MAD R
40,95 €). Dans tous ces cas, le titre affiché est « ➕ L'autre option » : le message ne promet jamais une
économie qui n'en est pas une.

### 19.3 « Jamais deux fois la même coque », sur les trois places

Mesure directe sur la grille statistique (18 522 profils) : **2 175 profils (15,84 % des trois places)**
montraient, en troisième ligne, une variante d'une coque déjà affichée. Après la préférence de coque
appliquée à cette place :

| Cas | Profils |
|---|---:|
| Une autre coque existait dans la fenêtre → elle est montrée | 1 338 (surcoût médian **+4,00 €**, 61 % sous +10 €) |
| Aucune autre coque dans la fenêtre → la variante reste | 837 |
| Cas « économie » : une variante **strictement moins chère** que les deux autres | 18 (règle du prix d'abord, assumée) |
| **Total restant à deux places de même coque** | **1 095 profils (5,9 %)** — avant : 2 415 (13,0 %) |

### 19.4 Grille statistique complète (18 522 profils)

- Troisième place remplie sur **13 733 profils (74,14 %)** : « 💸 L'économie » **4 233** fois,
  « ➕ L'autre option » **10 505** fois (rapport régénéré : `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md`).
- Souris jamais recommandées : **8 sur 36** (inchangé — mais la liste change de contenu) :
  A9 Air, U2 Mini, X2 CrazyLight Medium, X2H CrazyLight Mini, Xlite CrazyLight Medium, Xlite v4 Large,
  Xlite v4 Medium, X3. Motifs mesurés (rapport §« Souris jamais recommandées ») : une variante de leur
  **propre coque est moins chère et classée devant** (A9 Air, U2 Mini, X2 CL Medium, X2H CL Mini) ou il
  manque une donnée (**hauteur des boutons** : U2 Mini, X2H CL Mini, Xlite CL Medium, Xlite v4 Large,
  Xlite v4 Medium ; **position de la bosse** en plus : X3). C'est exactement ce que la campagne de mesure
  d'images doit débloquer.
- Trois souris **sortent du zéro** grâce à la nouvelle règle : **Y9 Ultimate 24 → 294**,
  **Duckbill 3 → 63**, **U2 V2 Mini 6 → 108** ; Fierce X 81 → 96.
- **U2 / U2 Plus / U2 V2 Ultimate** (hauteur de boutons publiée « High ») : 3 177 → **6 141 sorties**,
  dont 2 097 en match idéal ; les profils à match idéal **partiel** baissent encore.

### 19.5 Deux bugs du banc d'essai trouvés et corrigés (le banc jugeait mal)

1. **Rôles décalés** : `check_result_message()` recevait la liste des souris montrées et relisait
   « idéal / alternative / économie » **par position**. Dès que l'alternative était vide, l'économie
   était jugée comme une alternative → **40 avertissements fantômes** (« alternative élargie mais plus
   chère »). Les trois places sont désormais passées **par rôle**.
2. **Invariants périmés** : le banc exigeait encore « l'économie est strictement moins chère que les deux
   autres » et « l'alternative élargie n'est jamais plus chère » — 15 064 alertes produites après la
   décision du propriétaire, toutes du même type. Les contrôles suivent maintenant la règle réelle
   (libellé attendu, place la moins chère de sa fenêtre hors coques déjà affichées).

**Après correction : 0 problème sur les 27 170 profils.** Verrous ajoutés : `tests/test_qa_flow_matrix.py`
(5 tests : rôles, libellés des deux cas, contre-épreuve du titre menteur, constantes du rapport) et
`tests/test_flow.py` (3 tests : préférence de coque sur la troisième place, repli quand il n'y a rien
d'autre, « économie » au prix d'abord).

### 19.6 Ce qui reste ouvert

- **8 souris jamais recommandées** : cinq attendent une hauteur de boutons mesurée (priorité de la
  campagne d'images), trois perdent uniquement contre une variante moins chère de leur propre coque.
- **Poids** : la décision « le poids compte-t-il dans le score ? » reste au propriétaire (elle décide du
  sort des quatre jumelles légères).
- **Crédibilité du critère « hauteur des boutons »** : le critère est le **rapport mesuré** (décision du
  propriétaire), mais l'écart entre la classe « Mid » mesurée (47,3 % sur deux rendus) et la classe
  « Low » (43,3 %) reste de **4 points** : une souris qui tombe au milieu est refusée, jamais devinée.

## 20. Trente et unième passe : « 3 lignes partout où le budget le permet » (décision du 2026-10-12)

Question posée au propriétaire, réponse retenue : **remplir quand même, avec un titre explicite**. Le
message affiche trois lignes dès que le budget le permet, et chaque ligne qui n'est pas ce qu'elle
prétend être le dit elle-même (« 🔎 Autre piste »).

### 20.1 La règle, dans l'ordre

| Palier | Condition | Ligne affichée | Titre |
|---|---|---|---|
| 1 | toujours | tête du classement du mode | « 🥇 Le match idéal » |
| 2a | une autre coque est dans la zone du mode | meilleur profil, moins chère d'abord | « 🥈 L'alternative » |
| 2b | zone vide, mais une autre coque à ≤ 5 points et pas plus chère | cette souris | « 🥈 L'alternative » |
| 2c | **sinon** | meilleure souris restante (autre coque) | **« 🔎 Autre piste »** |
| 3a | une souris de la fenêtre (±5) coûte moins cher que les deux affichées | la moins chère | « 💸 L'économie » |
| 3b | sinon, une souris de la fenêtre reste | la moins chère des coques distinctes | « ➕ L'autre option » |
| 3c | **sinon** | meilleure souris restante | **« 🔎 Autre piste »** — ou « 💸 L'économie » si elle est *strictement moins chère* que les deux autres (fait vérifiable, 574 profils de la grille) |

Le **prix d'abord** pour la troisième ligne : une souris strictement moins chère que tout ce qui est
affiché est une économie, même si elle vient du dernier palier. Aucun barème, aucun seuil, aucun
classement n'est modifié : les trois souris sortent du classement déjà calculé (`result_slots()`).

### 20.2 Effet mesuré — banc du parcours (27 170 profils)

| Places remplies | §19 | **Après §20** |
|---|---:|---:|
| 3 places | 20 171 (74,24 %) | **23 231 (85,50 %)** |
| 2 places | 2 880 | 1 196 |
| 1 place | 1 558 | 182 |
| 0 place | 2 561 | 2 561 |

**Vérification que les trous restants viennent du budget, pas des règles** (mesure directe, souris par
souris, sur les deux grilles) :

| Grille | Trous restants | Cause mesurée |
|---|---:|---|
| Banc du parcours (27 170) | 1 196 + 182 | **budget épuisé dans 100 % des cas** (aucune souris abordable restante) |
| Statistiques (18 522) | 1 086 + 1 050 + 252 | **budget épuisé dans 100 % des cas** |

Autrement dit : partout où le budget permet de montrer trois souris, le message en montre trois.

### 20.3 Effet mesuré — grille statistique (18 522 profils)

- Trois places : 13 733 (74,14 %) → **16 134 (87,11 %)**.
- Titres de la troisième place : « ➕ L'autre option » **10 200**, « 💸 L'économie » **4 608**,
  « 🔎 Autre piste » **1 326**.
- Titres de la deuxième place : « 🥈 L'alternative » **15 023**, « 🔎 Autre piste » **2 161**.
- Écart de score des « Autre piste » : **10 points médians**, 25 au maximum (sur 40) — le pourcentage
  affiché à côté du nom suffit à voir que la piste est loin.
- Profils où deux places montrent la même coque (repli documenté, jamais sanctionné) : 1 095 → **1 341**
  (5,9 % → 7,2 %), conséquence d'une deuxième ligne désormais remplie là où elle était vide.

### 20.4 Ce qui n'est pas fait, et pourquoi

- **Aucune souris hors budget n'est montrée** : le plafond du Budget personnalisé reste la règle. Les
  252 profils sans aucun résultat (et les 1 196 + 182 à une ou deux lignes) ont un budget plus serré que
  la souris la moins chère qui convient — c'est une information, pas un bug.
- **Les pistes ne sont jamais présentées comme des alternatives** : le titre du dernier palier est
  distinct (« 🔎 Autre piste »), et le banc d'essai **échoue** si une piste est annoncée autrement
  (`tools/qa_flow_matrix.py`, deux contrôles de titre indépendants du moteur).
- **Le texte du résultat ne change pas** par ailleurs : ni score /40, ni confiance, ni liste d'écartées.

---

## 21. Trente-deuxième passe : audit des données et de la traçabilité (traque des bugs)

**Commande du propriétaire (2026-10-12)** : après le palier « trois lignes partout où le budget le permet »,
passer à l'**audit** et à la **chasse aux bugs** — sans nouvelle campagne d'images. Cette passe n'a donc
touché ni le moteur (`utils/matcher.py`, `utils/selection.py`, `utils/catalog.py`), ni les fenêtres des
trois places : elle a contrôlé la **donnée** et sa **provenance**, et corrigé ce qui ne tenait pas.

### 21.1 Méthode : trois contrôles automatisés, exhaustifs

| Contrôle | Ce qu'il vérifie | Résultat initial |
|---|---|---|
| Inventaire (souris × champ) | toute valeur renseignée est-elle déclarée par une source (`sources[].fields`) ? | **44 valeurs non attestées** sur 492 renseignées |
| Cohérence de coque | deux entrées d'une même coque (`shell_id`) : mêmes dimensions, même bosse, même hauteur de boutons ? | 1 écart de 0,5 mm (cohérent), 1 exception nommée (X3) |
| Statuts | `verified` se justifie-t-il par ses sources ? prix `verified` a-t-il un prix ? sources datées et en `https` ? identifiants uniques ? valeurs vides ? | 10 statuts `verified` non couverts par la règle écrite · 11 clés `mcu: ""` |

Les scripts d'audit sont jetables (aucun outil ajouté au dépôt : la règle du projet est de livrer des
*invariants* sous forme de tests, pas des scripts de circonstance). Les invariants correspondants sont
désormais dans `tests/test_data.py`.

### 21.2 Ce qui était cassé, et la correction apportée

**1. 44 valeurs sourcées dans les notes… mais non déclarées par leur source.** La valeur existait, la
source aussi (dans `notes`), mais `sources[].fields` ne la mentionnait pas : la chaîne de provenance
n'était donc **pas vérifiable par la machine** — exactement ce que la règle « jamais d'invention » veut
empêcher. Le catalogue est complet désormais, **valeur par valeur**, sans qu'aucune valeur géométrique ne
change :

| Origine de la valeur | Souris concernées | Ce qui a été déclaré |
|---|---|---|
| Page **EloShapes** du modèle (bosse « Center » → Mid, « Back - minimal/moderate » → Rear) | GHOST Ultimate, GHOST Extreme, Y9 Ultimate, U2 V2 Ultimate, U2 V2 Mini, ZERO, Duckbill, A9 Plus | `hump_position` ajouté à la source EloShapes qui portait déjà les cotes. Les pages **Y9 Ultimate** et **famille A9** ont été relues le 2026-10-12 : « Hump placement : Center » y est écrit pour ces modèles (date de source mise à jour). |
| **Moule** partagé (une coque = une pièce) | A9 Ultimate, A9 Air, A9 NB (nouvelle source datée) · F1 V2 (source de coque existante étendue) | `hump_position` : la coque A9 « large » a une bosse « Mid » (moule de l'A9 Plus 2.0 du propriétaire), la coque F1 aussi |
| **Cahier des charges du propriétaire** (valeur fournie, non revérifiée sur le web) | A9 Plus, Z1 V2 Ultra, X1 V2 Ultra Max, F1 V3 Ultimate, Scyrox V8/V8S, Scyrox V6/V6S | prises, bosse, hauteur des boutons, dimensions et prix (V6) — **9 sources ajoutées**, datées du 2026-10-12, URL = master prompt |

**2. Deux écarts de forme racontés seulement dans les notes.** L'ATK F1 V3 Ultimate et l'ATK X1 V2 Ultra Max
ont une bosse « Mid » (cahier des charges) alors qu'EloShapes écrit « Back - minimal ». La valeur du
propriétaire est conservée (règle « le propriétaire prime ») — mais l'écart manquait dans `conflicts`, le
champ que la machine lit. Il y est désormais, avec les deux valeurs et leurs sources.

**3. La règle « `verified` = ≥ 2 sources concordantes » n'autorisait pas dix entrées du catalogue.** Les dix
Pulsar sont relevées sur **une seule** source : la fiche officielle du fabricant (`eu.pulsar.gg`). Le
catalogue était plus permissif que la règle écrite. La règle a été précisée partout (README, master prompt,
`CATALOGUE_ATK.md`, prompt de recherche) : **≥ 2 sources concordantes à ≤ 0,5 mm, OU une seule source quand
c'est le fabricant lui-même** (sa boutique officielle). `single_source` désigne désormais explicitement une
seule source **tierce**.

**4. Deux écritures pour un même état : `"mcu": ""` d'un côté, clé absente de l'autre.** Le chargeur traite
les deux identiquement, mais un audit par script lit `None` quand la clé manque, jamais `""` — c'est ce qui
a produit un faux positif de 11 champs pendant cet audit. Les 22 clés vides (11 `mcu`, 8 `grip_width_mm`,
2 `height_mm`, 1 `shell_id`… dont les valeurs nulles redondantes) ont été retirées : « absent » veut dire
« inconnu », et c'est la seule écriture qui reste.

**5. La largeur de l'ATK A9 Plus (63,5 mm) venait du cahier des charges, pas d'EloShapes (64,0 mm).** La
source du propriétaire déclare maintenant aussi les **cotes** de sa souris, écart de 0,5 mm inclus (dans la
tolérance de concordance). Aucune valeur n'a bougé.

**6. Deux défauts d'outil (repérés en relisant les outils qui produisent les preuves).** L'outil de
mesure affichait « classe « None » » sur une vue refusée ou non tranchée — il écrit maintenant « classe
aucune (voir le verdict ci-dessous) ». Et le banc d'essai recopiait la tolérance de repli (`2`) au lieu de
la demander au moteur (`mode_tolerance`) : si la tolérance d'un mode change, le banc change avec lui, sinon
il vérifierait l'ancienne règle. Aucun des deux défauts ne touchait une valeur du catalogue ou un score.

**7. Deux corrections de forme (affichage et documentation).** Le bloc « arrière étroit » écrivait
« Votre thénar est **Petite** » (article masculin, adjectif féminin) : il dit désormais « Votre éminence
thénar est **petite** », le terme du master prompt. Et `REPORTE_DESIGN.md` ne citait que deux titres pour la
troisième place : les trois y sont (« 💸 », « ➕ », « 🔎 »), comme dans le README.

### 21.3 Constats vérifiés mais NON modifiés (et pourquoi)

| Constat | Pourquoi rien n'a été changé |
|---|---|
| Le pied de message renvoie au bloc « Comment lire ce résultat », **qui n'existe plus** dans le résultat actuel (les explications vivent dans « 🧭 Pourquoi ce choix ? » et les blocs illustrés). Renvoi mort, visible par le membre. | Le master prompt dit **« `set_footer(text=SCORE_DISCLAIMER)` — garder tel quel »** : le texte est verrouillé volontairement. **Signalé au propriétaire** ; un mot de sa part et le renvoi est corrigé. |
| L'emoji 🔎 sert à deux choses : le titre « 🔎 Autre piste » et le champ « 🔎 *souris* en clair » du bloc des repères. | Collision bénigne, **verrouillée par un test** (`tests/test_flow.py`) : la changer est une décision de libellé, pas un bug. Signalée. |
| Les entrées de la coque A9 « large » divergeaient de **0,5 mm** en largeur (63,5 mm propriétaire et fabricant / 64,0 mm EloShapes). | **Tranché à la 33e passe** (§21.6) : la fiche officielle ATK relue le 2026-10-12 annonce « 125 x 63.5 x 40 mm », le fabricant prime et le propriétaire a mesuré 63,5 mm sur la sienne — la coque est alignée à 63,5 mm, l'écart reste écrit dans `conflicts`. Deux invariants le verrouillent désormais (cohérence exacte des cotes d'une même coque, conflit obligatoire si un écart subsiste). |
| La **VXE X3** partage la coque de l'ATK X1 V2 Ultra Max sans hériter de sa bosse ni de ses boutons. | Exception **nommée et testée** depuis le 2026-10-12 : la bosse de l'X1 est contestée par une source tierce, et rien ne prouve que la X3 (gamme VXE, switchs Omron, puce Broadcom) reprenne les siens. |
| `grip_width_mm` reste `null` pour les 36 souris : la confiance « élevée » n'est donc atteignable par personne (la largeur de prise est estimée « coque − 3 mm »). | La mesure de la largeur de prise exige une photo retournée, calibrée : c'est une **campagne** à part entière, pas un correctif d'audit. Déjà documenté (`docs/audit/MESURE_BOUTONS_2026-10-12.md`). |
| Un salon verrouillé (`LOCK_FINDER_CHANNEL=true`) : les réponses **éphémères** d'interaction ne dépendent pas du droit « Envoyer des messages », mais un repli par `followup` en dépendrait. | Déjà écrit noir sur blanc dans le guide de déploiement §8.3 (« à confirmer lors de votre test manuel »). Rien à corriger dans le code : le repli est journalisé, jamais silencieux. |
| **Trois fichiers suivis dans un dossier ignoré** (`image-search/eloshapes-atk-f1-v3-mouse-top-view-shape-1|2|3`) et un résidu `image.png` à la racine (premier commit, listé « à ne pas envoyer sur le serveur »). | **Résolu le 2026-10-13** : inventaire complet du dépôt, puis retrait des quatre fichiers — §26.7. |

### 21.4 Preuves d'exécution (2026-10-12, 32e passe)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **391 passed** (386 avant : 5 tests d'audit ajoutés à cette étape, aucun test modifié) |
| `pyflakes` (cogs, utils, tools, tests, bot.py) | 0 avertissement |
| `tools/privacy_scan.py` | **0 violation** |
| `tools/qa_flow_matrix.py` (27 170 profils) | **0 problème** · 3 places **23 231 (85,50 %)** · 2 places 1 196 · 1 place 182 · 0 place 2 561 · repli « même coque » 990 · match idéal partiel 3 118 — **chiffres identiques à la 31e passe : aucune valeur du moteur n'a bougé** |
| `tools/recommendation_stats.py` (pleine grille, 18 522 profils) | rapport régénéré **identique au fichier livré** (aucun diff Git) |
| `tools/compare_profiles.py` | matrice régénérée **identique** (aucun diff Git) |
| `tools/flow_effect.py --rapide` | « aucun changement » (0 profil modifié, 0 point perdu) |
| `tools/check_deployment.py` | 1 erreur, **attendue** : `.env` absent de cet atelier (le serveur l'a) |
| Registre d'audit | `docs/audit/AUDIT.md` : cinq constats consignés (C23 provenance non vérifiable, C24 statut `verified`, C25 valeurs vides, C26 documentation de la 3ᵉ place, C27 renvoi mort du pied de message) |
| Diff des valeurs du catalogue | 36 souris × 30 champs comparés **avant/après** : seuls `conflicts` (2 souris) changent à cette étape — **aucune cote, aucun prix, aucun score** (les deux corrections de la 33e passe, qui changent bel et bien des cotes, sont décrites et mesurées au §21.6) |

### 21.5 Les huit invariants ajoutés (les bugs corrigés ne peuvent plus revenir)

1. `test_chaque_valeur_du_catalogue_cite_la_source_qui_l_atteste` — 492 valeurs inventoriées, 0 tolérée
   sans source déclarante (et le test refuse de passer si l'inventaire devient vide : un contrôle vide ne
   prouve rien).
2. `test_les_ecarts_de_forme_sont_consignes_dans_conflicts` — tout écart de bosse connu est lisible par la
   machine, et la note de la fiche doit dire la même chose que le conflit.
3. `test_le_catalogue_ne_contient_aucune_valeur_vide` — jamais d'`""` : « absent » et « inconnu » s'écrivent
   de la même façon pour tout le monde, y compris pour un audit par script.
4. `test_un_statut_verified_se_justifie_par_ses_sources` — un `verified` doit montrer soit deux sources de
   cotes, soit la boutique du fabricant.
5. `test_deux_entrees_de_la_meme_coque_ne_divergent_pas_hors_tolerance` — une même coque ne peut pas
   annoncer deux largeurs à plus de 0,5 mm d'écart.
6. `test_aucune_source_ne_declare_un_champ_resté_vide` — une source qui déclare un champ (c'est une preuve)
   ne peut pas pointer une valeur absente : c'était le cas de la hauteur des deux Scyrox (§21.6).
7. `test_deux_entrees_de_la_meme_coque_publient_les_memes_cotes` — une coque publie exactement les mêmes
   cotes ; un écart n'est admis que s'il est **consigné** dans `conflicts`.
8. `test_la_note_de_l_x1_ne_contredit_pas_ses_champs` — une fiche ne peut pas annoncer « non renseigné » un
   champ qui porte une valeur (§21.6).

---

## 22. Trente-troisième passe : trois corrections de données prouvées (et l'effet mesuré, avant/après)

**Suite de l'audit du 2026-10-12** (même commande du propriétaire : audit et chasse aux bugs). Cette passe
corrige trois défauts de **données** — et non de code — trouvés en relisant le catalogue avec les contrôles
automatisés du §21. Deux d'entre eux changent des **cotes** : leur effet est mesuré sur les deux bancs
(27 170 profils du parcours, 18 522 profils statistiques) et écrit ici, avant/après.

### 22.1 Une source attestait une valeur… qui n'existait pas (Scyrox V6/V8)

Les deux Scyrox déclaraient `height_mm` dans leur source « cahier des charges du propriétaire » (V6S :
119 × 61 × 40 mm ; V8S : 118 × 63 × 40 mm) alors que la valeur était restée `null`. Un lecteur — humain ou
script — voyait donc à la fois « hauteur attestée » et « hauteur inconnue ». **Correction** : la hauteur
publiée devient **40,0 mm** pour les deux, valeur déjà écrite dans la source qui la déclarait. Effet sur les
scores : **aucun** (la hauteur n'entre dans aucun barème ; elle sert à l'affichage et aux documents).
Invariant ajouté : `test_aucune_source_ne_declare_un_champ_resté_vide` (0 tolérance, sur tout le catalogue).

### 22.2 Une même coque décrite avec deux largeurs (ATK A9 « large »)

La coque A9 pleine taille (125 mm) était publiée avec **deux largeurs** : 63,5 mm pour l'A9 Plus 2.0 (cahier
des charges du propriétaire) et l'A9 NB (ATK Store, Ryugear), 64,0 mm pour l'A9 Ultimate et l'A9 Air
(EloShapes). Une même pièce de plastique, deux cotes — l'écart de 0,5 mm ne choquait pas la tolérance de
concordance, mais il n'était écrit nulle part pour l'A9 Ultimate et l'A9 Air.

**Ce qui a été vérifié le 2026-10-12** (relecture de la fiche fabricant, pas d'un revendeur) :
`atk.store` — page de la série A9 — annonce **« Dimensions 125 x 63.5 x 40 mm »** pour la coque pleine
taille, et « 118.4 x 61.2 x 38.6 mm » pour la Mini, avec l'A9 Air **parmi les variantes de cette page**
(deuxième section « Variety of Sizes » : « A9 Ultimate: 125*63.5*40(mm) »).

**Décision** (règle du 2026-10-12 : *le fabricant prime sur une tierce* ; le propriétaire a par ailleurs
mesuré sa propre souris — une A9 Plus 2.0, même coque — à **63,5 mm**) : la coque publie **63,5 mm
partout**. L'écart n'est pas effacé : il reste dans `conflicts` pour les trois entrées que la source tierce
relève à 64,0 mm, avec la note qui explique la règle appliquée.

**Effet mesuré** (moteur inchangé : seules deux valeurs de données, 64,0 → 63,5, pour l'A9 Ultimate et
l'A9 Air) :

| Mesure | Avant | Après |
|---|---|---|
| Profils du parcours dont une place change (27 170) | — | **1 043 (3,8 %)** |
| dont place occupée par une **autre variante de la même coque** | — | **977 (93,7 % des changements)** : la forme montrée ne change pas |
| dont une **autre forme** prend la place (ZERO, R1, A9 Mini, F1 V3, Z1 V2) | — | 66 (0,24 % des profils) |
| Score de l'A9 Ultimate modifié (grille des profils notés) | — | **96 profils** : +5 pts quand l'écart de largeur passe de 2,2 à 1,7 mm sous le seuil strict des 2 mm (`WIDTH_NEAR_DELTA_MM`) |
| Sorties de l'A9 Ultimate (grille statistique) | 5 120 (27,6 %) | **5 829 (31,5 %)** |
| Sorties de l'A9 Plus 2.0 | 1 401 (7,6 %) | **852 (4,6 %)** |
| Sorties de l'A9 NB Ultra | 138 (0,7 %) | **0** (devancée par sa jumelle de coque, moins chère) |
| Places remplies dans le message (banc du parcours) | 85,50 % · 0 problème | **85,50 % · 0 problème** (inchangé) |
| Profils à deux places sur la même coque | 1 341 | **1 339** (inchangé à 2 près) |

Autrement dit : dans 93,7 % des profils touchés, **c'est la même forme qui reste affichée** (l'A9 Plus 2.0 ou
l'A9 NB cèdent la place à l'A9 Ultimate, même coque de 125 mm, plus légère — 55 g — et moins chère —
41,95 € contre 45,00 € et 72,95 €). C'est exactement la règle suprême du propriétaire : l'expérience
d'abord, et la personne doit être contente de son achat pour le prix.

**Retour arrière** : une seule valeur, deux entrées (`atk_a9_ultimate`, `atk_a9_air`, `width_max_mm`),
et la grille revient à l'état précédent — c'est mesuré, pas supposé (`tools/flow_effect.py` compare le code,
et un script de comparaison de données a servi ici, sans être ajouté au dépôt).

### 22.3 Une fiche qui se contredisait (ATK X1 V2 Ultra Max)

La note du capteur annonçait « **non renseigné** » alors que le champ publiait « PAW3395 Ultra » — et deux
phrases plus loin la même note le citait. Deux versions de la même fiche dans le même champ. Le conflit
correspondant, lui, citait des sources vagues (« EloShapes », « ATK Store ») sans dire ce qu'elles
annonçaient.

**Correction** : la note dit désormais la valeur retenue et pourquoi ; la source EloShapes (dont le relevé
du 2026-10-10 donnait « PAW3395 Ultra ») **déclare** le champ `sensor` — la valeur est donc attestée par
trois sources du modèle exact (EloShapes, Maxesport, TechnoGeek BD) ; le conflit nomme la variante et
renvoie au tableau du fabricant. **Aucune valeur n'a changé ici** : la page ATK de la série X1 V2 liste
« PAW3950 Ultra » et « PAW3955 Master » pour ses six modèles, sans que la correspondance ligne à ligne de
la variante « Ultra Max » soit lisible sur la page — changer le capteur sur cette ambiguïté aurait modifié
les classements « Haut de gamme » et « Peu importe le prix » sans preuve. Le point est **signalé au
propriétaire** (AUDIT.md §8) au lieu d'être deviné. Invariant ajouté :
`test_la_note_de_l_x1_ne_contredit_pas_ses_champs`.

### 22.4 Ce que la passe a aussi vérifié, sans rien changer

- **Les 36 notes et les 36 prix** ont été relus ligne à ligne contre les champs : aucune autre contradiction
  du type « non renseigné » sur un champ rempli, aucune valeur sans source.
- **Les hachures du moteur** (non-régression du master prompt, main 180 × 90 Palm) : Scyrox V6 **30/40**,
  ATK Z1 V2 Ultra **30/40**, ATK A9 Plus 2.0 **25/40**, ATK X1 V2 Ultra Max **20/40** — inchangées.
- **`utils/validation.py`** (saisies du membre) : 22 saisies hostiles testées à la main (nombres négatifs,
  `nan`, `inf`, chiffres non latins, espace fine insécable, `1 800 €`, `180mm`, `180.555`…) → toutes
  acceptées ou refusées avec un message clair, aucune exception non gérée.
- **Les bornes Discord** (10 blocs, 25 champs, 1 024 caractères par champ) sont déjà contrôlées par le banc
  d'essai sur les 27 170 profils ; le plus long texte produit aujourd'hui mesure **435 caractères**
  (bloc « Vos repères ») et la plus longue ligne de place **87 caractères** — aucune limite approchée.

### 22.5 Preuves d'exécution (33e passe)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **395 passed** (391 avant la passe : 4 tests ajoutés, dont trois invariants nouveaux) |
| `pyflakes` (cogs, utils, tools, tests, bot.py) | 0 avertissement |
| `tools/qa_flow_matrix.py` (27 170 profils) | **0 problème** · 3 places 23 231 (85,50 %) · 2 places 1 196 · 1 place 182 · 0 place 2 561 · repli « même coque » 990 · match idéal partiel 3 118 |
| `tools/recommendation_stats.py` (18 522 profils) | rapport régénéré : A9 Ultimate 27,6 % → **31,5 %**, A9 Plus 7,6 % → **4,6 %**, A9 NB 0,7 % → **0 %** |
| `tools/compare_profiles.py` | matrice régénérée (deux lignes A9 mises à jour) |
| `tools/flow_effect.py --rapide` | « aucun changement » : le **code** n'a pas bougé, seules des données |
| `tools/check_deployment.py` | 1 erreur, **attendue** : `.env` absent de cet atelier (le serveur l'a) |
| `tools/privacy_scan.py` | 0 violation |

---

## 23. Trente-quatrième passe : quatre défauts trouvés en relisant le code livré

**Suite de l'audit du 2026-10-12** (même commande du propriétaire : audit et chasse aux bugs). Les passes
précédentes relisaient surtout les **données** et les **messages**. Celle-ci relit **le code livré**
(`cogs/finder_flow.py` ligne à ligne, `utils/`, `bot.py`, les outils) avec la question : « qu'est-ce qui
pourrait être faux ici sans que rien ne plante ? ». Quatre défauts en sont sortis — plus deux mesures de
présentation publiées telles quelles, et un outil nouveau pour prouver les effets d'une modification de
données.

### 23.1 Un résidu d'édition que ni Python ni `pyflakes` ne signalaient (code)

À la fin du texte de l'étape « Votre éminence thénar », `cogs/finder_flow.py` gardait la séquence
`calcul).` suivie d'un guillemet de fermeture et de **trois guillemets collés** : le vestige d'une édition
antérieure du texte. Conséquence technique : une **chaîne vide implicite** en fin de description.

Pourquoi personne ne le voyait :

- les littéraux voisins se **concatènent à la compilation** : le texte affiché au membre restait juste ;
- `pyflakes` ne dit rien d'une chaîne vide (ce n'est pas une variable inutilisée) ;
- aucune assertion ne portait sur ce texte précis, et les tests d'affichage comparent des fragments.

**Correction** : résidu retiré. **Preuve de non-effet** : `tools/flow_effect.py --rapide` compare le module
d'avant (HEAD) et d'après → « aucun changement » : rien de visible n'a bougé, seule la source est propre.

**Invariant ajouté** — `tests/test_code_hygiene.py`, trois contrôles sur **tout le code livré** :

| Contrôle | Ce qu'il interdit |
|---|---|
| Résidu de guillemets | une ligne-texte qui commence par un guillemet simple et finit par un triple (la signature exacte du défaut) |
| `print()` dans le bot | une sortie qui ne serait **pas** horodatée dans `~/admin/logs/jobs/` — donc indiagnosticable sur le serveur |
| Contrôle non vide | que ces vérifications portent bien sur l'ensemble des fichiers (sinon elles ne prouveraient rien) |

Détail savoureux : ce test a dû être écrit **en mots** — écrire le motif en toutes lettres terminait la
chaîne de documentation du test lui-même. C'est bien la preuve que ce motif est un piège réel.

### 23.2 Une source comptée deux fois (données)

L'ATK Y9 Ultimate listait **deux fois la même source** : libellé, URL et date rigoureusement identiques, la
première déclarant `claw_grip_fit`, la seconde `price_eur`. La même lecture comptait donc pour **deux
attestations** — exactement ce que la règle « deux sources concordantes » cherche à éviter.

**Correction** : les deux entrées fusionnent en une seule source, qui déclare les deux champs. Aucune valeur
n'est modifiée. Vérification faite au passage : **aucun** des statuts `verified` d'alors (27 entrées) ne
reposait sur un doublon (contrôle sur les sources dédupliquées) — le défaut était donc d'honnêteté de la
traçabilité, pas de statut.

**Invariant ajouté** : `test_aucune_source_n_est_enregistree_deux_fois_dans_une_entree` (0 tolérance sur les
**218** sources du catalogue, dont 218 distinctes après la fusion). Deux **lectures** d'une même page (dates ou libellés différents) restent
légitimes : c'est le doublon strict qui est interdit.

### 23.3 Trois statuts de cotes sous-estimés (données)

La règle écrite dans le README est claire depuis la 32e passe : `verified` = **deux sources de cotes
concordantes (≤ 0,5 mm)**, **ou la boutique officielle du fabricant** ; `single_source` = une seule source
**tierce**. Le sens « statut fort sans preuve » était testé. Le sens **inverse** ne l'était pas — et trois
entrées s'y étaient installées :

| Entrée | Statut avant | Sources de cotes que l'entrée citait elle-même | Statut après |
|---|---|---|---|
| ATK Duckbill | `single_source` | 3 (EloShapes, blog ATK, fiche officielle) dont **2 du fabricant** | `verified` |
| ATK A9 Air | `single_source` | 2 (EloShapes + fiche officielle du fabricant) | `verified` |
| VXE X3 | `single_source` | 1, **celle du fabricant** (fiche ATK de la série X3) | `verified` |

**Correction** : statut `verified` pour les trois. **Aucun score ne change** — seul le statut `conflicting`
bloque une souris dans le moteur ; `single_source` n'a jamais servi qu'à la confiance affichée dans les
outils, et la confiance de ces trois souris reste inchangée (`fit_status` ≠ `owner_spec` pour les trois,
donc « faible » dans les deux cas).

**Preuve d'effet** : mesurée sur la grille complète (27 170 profils) avec l'outil nouveau (§23.6) →
**0 profil modifié**.

**Invariant ajouté** : `test_le_statut_des_cotes_ne_reste_pas_sous_estime` — la règle est désormais
contrôlée **dans les deux sens**, sur les sources **dédupliquées** (un doublon ne vaut pas deux
attestations), et l'assertion du test du Duckbill (qui figeait l'ancien statut) est mise à jour avec la
justification.

### 23.4 La coque de la VXE X3 : cotes partagées, bosse non devinée (décision, rien changé)

Point ouvert d'audit qui traînait depuis la 32e passe : la VXE X3 porte `shell_id = atk_x1` (la coque de
l'ATK X1 V2 Ultra Max, même 127 × 64 × 40 mm) alors que sa **bosse** est « Inconnu » — une contradiction en
apparence. La relecture la tranche dans ce sens :

- `shell_id` veut dire, dans ce projet, « **même coque = dimensions partagées** » (README) : les cotes de la
  X3 sont donc bien celles de la famille X1, toutes deux publiées par la fiche ATK de la série X3
  (« Dimensions 127 x 64 x 40 mm », page relue le 2026-10-12 avec `?country=FR`) ;
- la **bosse** et la **hauteur des boutons**, elles, ne se propagent pas : la bosse de l'X1 est elle-même
  contestée par une source tierce (« Back - minimal » chez EloShapes contre « Mid » du propriétaire), et
  **rien ne prouve** que la X3 — gamme VXE, switchs Omron, puce Broadcom — reprenne la même pièce de
  plastique. La page du fabricant, relue le 2026-10-12, publie 51 g ± 3 g, 1 000 Hz, PAW 3395SE, les poids,
  « Ambidextrous Design » et les trois prises recommandées : **aucune information de bosse** ;
- la conséquence est assumée : la X3 reste « à vérifier » (deux manques) et **n'est jamais recommandée**.
  Elle se débloquera le jour où une source publiera sa bosse — aucune valeur n'est devinée en attendant.

L'exception est **écrite dans le test** (`test_no_shell_mixes_two_button_heights`) et dans la note du
catalogue : elle ne peut donc pas être prise pour un oubli.

### 23.5 Deux mesures de présentation, publiées telles quelles (rien changé)

Le balayage complet (27 170 profils, `compute_selection` + `result_slots`) a mesuré deux comportements
qu'aucun banc ne regardait — **le pourcentage d'une place peut dépasser celui de la place du dessus** :

| Comportement | Cas (grille complète) | Pourquoi c'est possible |
|---|---|---|
| En mode **Économique**, la 2e place affiche un **meilleur** pourcentage que le « match idéal » | **1 622 (6,0 %)** | le match idéal de ce mode est la souris **la moins chère** de la zone de tolérance (c'est la règle du mode) : il est donc légitime qu'une souris mieux notée, mais plus chère, le dépasse en deuxième ligne |
| La **3e place** dépasse la 2e | 24 (économique) · 62 (qualité/prix) · 70 (sans mode, haut de gamme, peu importe le prix) · 128 (budget personnalisé) — 0,09 % à 0,47 % | la fenêtre de la 3e place (±5 points) est **plus large** que la zone du mode (±2), et la 2e place a pu être choisie pour son **prix** |
| La 2e et la 3e place affichent le **même** pourcentage | 4 916 en budget personnalisé, 512 à 1 138 ailleurs | deux souris **différentes** au même score de forme : les lignes restent distinctes (nom, poids, prix), c'est le prix qui distingue les deux rôles |

Aucun libellé n'est faux (les titres disent « L'économie », « L'autre option », « Autre piste » selon le
prix réel) et le pourcentage affiché est exact. **Rien n'a été modifié** : changer l'ordre des places serait
une modification du moteur, et le master prompt réserve ces décisions au propriétaire. Le point est inscrit
dans `AUDIT.md` §8 (point 13) pour arbitrage.

### 23.6 Un outil nouveau : mesurer l'effet d'une modification de DONNÉES

La 33e passe avait besoin d'un comparateur de catalogues ; il avait été écrit dans `/tmp` et a disparu (le
dossier temporaire est volatil). Le voici au dépôt, propre et testé :

```bash
.venv/bin/python tools/db_effect.py --avant /tmp/mouse_db_avant.json                  # grille complète
.venv/bin/python tools/db_effect.py --avant ancien.json --grille rapide               # 720 profils
.venv/bin/python tools/db_effect.py --avant ancien.json --grille mini                 # 180 profils
```

Il passe **la même grille de profils** dans les deux catalogues (le barème, les fenêtres des trois places et
la présentation ne bougent pas : seul le fichier de données change) et rend : profils comparés, profils dont
le résultat change, répartition par place, place gagnée ou perdue, et si la nouvelle liste montre deux fois
la même coque. Il n'écrit rien dans le dépôt (les catalogues sont copiés dans un dossier temporaire) et
refuse de comparer deux catalogues qui ne contiennent pas les mêmes souris — au lieu de rendre un chiffre
qui ne voudrait rien dire.

**Ce qu'il a prouvé pour cette passe** : la grille complète (27 170 profils) avant/après la correction des
trois statuts et la fusion de la source dupliquée → **0 profil modifié**. C'est le résultat attendu (ces
champs n'entrent dans aucun barème) et il est désormais **mesuré**, pas supposé.

`tests/test_db_effect.py` verrouille l'outil dans les deux sens : deux catalogues identiques → aucun écart ;
un prix réellement modifié → des écarts (et la souris modifiée apparaît dans les changements) ; deux
catalogues différents → refus explicite.

### 23.7 Une contradiction entre le message et le master prompt (signalée, non modifiée)

Dernier constat de la relecture : le master prompt — document **contractuel** — montre dans ses deux
exemples de résultat un prix suivi de « (prix non vérifié) », et son croquis de code l'ajoute dès que
`price_status` n'est pas `verified`. Le message réel ne l'affiche **jamais** : le marqueur existe
toujours dans le code (`_price_text(score, verified_hint=True)`) mais **aucun appelant ne l'active**
depuis le retrait de l'onglet « Détails » (2026-10-11), et sa docstring renvoyait encore à cet onglet
disparu.

Mesure de l'enjeu, grille complète (27 170 profils) : **4 631 profils (17,04 %)** montrent au moins une
souris à prix non vérifié — Scyrox V6 3 526 fois (74,90 € du cahier des charges ; la boutique du
fabricant vend en dollars, jamais convertis) et ATK A9 Plus 2.0 1 105 fois (45,00 € du cahier des
charges, relevé revendeur à 44,90 € conservé). Dans ces profils, le prix s'affiche **comme un prix
vérifié**.

**Ce qui a été fait** : la docstring dit maintenant la vérité (plus de renvoi à un onglet disparu), la
règle reste écrite, et l'arbitrage est porté au propriétaire (`AUDIT.md` C34 et §8 point 14) — remettre
le marqueur, ou retirer la règle du master prompt. Rien n'est modifié dans la ligne de prix sans sa
réponse : c'est du texte visible, et ses décisions sur la concision du résultat sont explicites.

### 23.8 Preuves d'exécution (34e passe)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **403 passed** (395 avant la passe : 8 tests ajoutés — 3 hygiène du code, 2 données, 3 comparateur de données) |
| `pyflakes` (bot, config, cogs, utils, tests, tools) | 0 avertissement |
| `tools/db_effect.py --grille complete` (27 170 profils) | **0 profil modifié** par les corrections de cette passe |
| `tools/qa_flow_matrix.py --rapide` (720 profils) | **0 problème** · 3 places 711 (98,75 %) · 2 places 9 · repli « même coque » 10 · match idéal partiel 120 |
| `tools/flow_effect.py --rapide` | « aucun changement » : le résidu retiré ne changeait rien de visible |
| `tools/privacy_scan.py` | 0 violation |
| `tools/check_deployment.py` | 1 erreur, **attendue** : `.env` absent de cet atelier (le serveur l'a) |

---

## 24. Trente-cinquième passe : trois décisions du propriétaire (ordre des pourcentages, marqueur de prix, pied de message)

Après la publication de l'audit (§23), trois points ouverts ont été soumis au propriétaire, qui a tranché
le **2026-10-13**. Cette passe les met en œuvre, mesure chaque effet et verrouille chaque règle par un
test. Deux d'entre eux touchent un **texte visible** et un **rôle de place** : le moteur est modifié là où
la décision l'autorise, et nulle part ailleurs.

### 24.1 Ordre des pourcentages garanti (décision : « garantir l'ordre »)

**Le défaut mesuré** (§23.5) : le pourcentage affiché pouvait **remonter** d'une place à l'autre.
En mode **Économique**, le match idéal est la souris la **moins chère** de la zone de tolérance (c'est la
règle du mode) : une souris mieux notée mais plus chère le dépassait donc en deuxième ligne — **1 622
profils (6,0 %)**. La troisième place dépassait la deuxième sur 24 à 128 profils selon le mode. Le membre
lisait alors un « match idéal » moins bien noté que la ligne du dessous : cela ressemble à une erreur de
calcul, et cela abîme la confiance dans tout le résultat.

**La règle appliquée** : une place ne peut pas afficher un meilleur score que la place du dessus. Elle est
appliquée **à la sélection** de la souris (`sous_plafond` dans `result_slots`, `cogs/finder_flow.py`), pas à
l'affichage : **aucun score n'est retouché**, c'est le choix de la souris qui change. Le match idéal, lui,
n'est jamais touché.

**Effet mesuré** (`tools/flow_effect.py`, grille complète, code d'avant = `41d741d`) :

| Mesure (24 609 profils avec au moins une place) | Avant | Après |
|---|---:|---:|
| Profils où un pourcentage remonte d'une place à l'autre | **2 046** | **84** (0,34 %) |
| Match idéal changé | — | **0** |
| Deuxième place changée | — | 1 615 |
| Troisième place changée | — | 1 976 |
| Places remplies (0 / 1 / 2 / 3) | 0 · 182 · 1 196 · 23 231 | **0 · 182 · 1 196 · 23 231** (identique) |
| Profils où deux places montrent la même coque | 2 010 | **1 864** (moins de doublons de coque) |
| Pire baisse de score pour la deuxième place | — | 10 points (profil où elle dépassait le match idéal) |
| Économie gagnée / perdue | — | 0 / 0 |

**Le plafond porte sur les points du barème (sur 40), et cela garantit aussi le pourcentage affiché** :
le pourcentage est proportionnel à ces points (`compatibility_percent` = points × 100 / 40, arrondi), il ne
peut donc pas remonter quand les points ne remontent pas. Le contrôle du banc d'essai, en points, couvre
exactement le nombre affiché — vérifié sur la grille complète : **84 violations en points = 84 en
pourcentages**, aucune divergence (un second plafond serait une ligne de code de plus pour la même règle).

**Le repli restant (84 profils sur les 24 609 qui ont au moins une place, soit 0,34 %)** est documenté et
vérifié, pas toléré en silence : quand le plafond
ne laisse **aucun** candidat — grande main à budget serré, où la fenêtre ne contient plus une seule souris
sous le score de la place du dessus —, la place reste **remplie** (règle du 2026-10-12 : jamais de trou dans
le résultat) et le pourcentage peut alors remonter. Exemple mesuré : main 225 × 85, mode Économique, match
idéal ATK U2 V2 Ultimate (10/40) — la seule souris abordable restante est mieux notée (20/40). Le banc
d'essai **compte** ces profils (« ordre non garanti : 84 ») et le test `test_le_pourcentage_ne_remonte_…`
les interdit par ailleurs sur les 27 170 profils de sa grille (mêmes 84 profils, donc 0,31 % là où le
dénominateur est la grille entière : le chiffre de référence du banc d'essai, §25.1)
vérifie pour chacun qu'aucune souris du classement ne passait sous le plafond.

### 24.2 Le marqueur « (prix non vérifié) » revient dans la ligne de prix (décision : « remettre »)

**Le défaut** (§23.7, C34) : le master prompt montre « 74.90 € (prix non vérifié) », mais aucun appelant
n'activait plus le marqueur depuis le retrait de l'onglet « Détails » (2026-10-11). Un prix non attesté
s'affichait donc **exactement** comme un prix vérifié.

**La règle appliquée** : la ligne de place affiche « (prix non vérifié) » dès que `price_status` n'est pas
`verified` — dans les trois places, **et** dans la petite ligne de prix du mode « Peu importe le prix » (le
seul endroit où le prix apparaît dans ce mode). Deux souris du catalogue sont concernées : **Scyrox V6**
(74,90 € du cahier des charges ; la boutique du fabricant vend en dollars, jamais convertis) et
**ATK A9 Plus 2.0** (45,00 € du cahier des charges, relevé revendeur à 44,90 € conservé).

**Effet mesuré** (grille complète) : **4 373 places** portent le marqueur, soit **16,09 % des profils**
(contre 0 % auparavant). Lisibilité mobile : la ligne la plus longue portant le marqueur mesure
**79 caractères** — sous la plus longue ligne de place du catalogue (87 caractères, ATK U2), et le banc
d'essai contrôle les limites Discord sur les 27 170 profils (**0 problème**).

### 24.3 Le pied de message ne renvoie plus à un bloc disparu (décision : « corriger la phrase »)

Le pied de page disait « Le calcul est expliqué dans le bloc « Comment lire ce résultat », plus bas » : ce
bloc **n'existe plus** depuis le 2026-10-11 (C27). Le texte est gelé par le master prompt, d'où le signalement
plutôt qu'une correction unilatérale — le propriétaire a autorisé la correction le 2026-10-13.

**La règle appliquée** : le pied de page renvoie au bloc qui existe, **« 🧭 Pourquoi ce choix ? »**, et
seulement quand ce bloc est dans le message. Sur un parcours incomplet (aucune mesure, donc aucun bloc
d'explication), le pied de page reste le simple avertissement de score. La phrase ne dit plus aucune
direction (« plus bas » était faux : le pied de page est posé sur le dernier bloc, l'explication est
au-dessus).

### 24.4 Le score partiel des 2e et 3e places est annoncé (décision : « marqueur discret »)

Une souris dont la **hauteur des boutons n'est pas documentée** est notée sur les critères disponibles
(`PARTIAL_SCORING_ALLOWED`, décision du 2026-10-12) : son pourcentage est donc calculé **sans** ce
critère, donc **sous-estimé** — le critère manquant ne peut que rapporter des points, jamais en retirer.
Le message l'explique en clair, mais **seulement quand cette souris est le match idéal** : la note vit
dans le bloc « 📐 Vos repères de taille », écrit pour `ideal.is_partial`.

En 2e ou 3e place, le pourcentage s'affichait donc comme un score complet : **8 187 places** sur 27 170
profils (30,1 %), réparties sur **7 304 profils** — mesuré le 2026-10-13 (35e passe), signalé au
propriétaire (C35) et **tranché le jour même** : un **marqueur discret** à la fin de la ligne, plutôt
qu'une phrase sous les trois lignes.

**La règle appliquée** (`PARTIAL_HINT` dans `cogs/finder_flow.py`) : les 2e et 3e places ajoutent
« · boutons non documentés » **à la fin** de leur ligne — après la forme de coque, pour ne pas casser
l'alignement « Symétrique / Ergonomique » tout à droite. Le match idéal garde la note longue (pas de
doublon). Aucun score, aucun classement, aucune sélection ne change : c'est un texte.

**Effet mesuré** : **10 704 lignes** de place portent le marqueur sur la grille complète (8 187 pour un
match idéal complet, 2 517 en plus là où le match idéal est lui-même partiel). La ligne la plus longue
du catalogue passe de 87 à **102 caractères** (« **Pulsar Xlite CrazyLight Medium** · 44 g · 149,90 € ·
**38 %** · Ergonomique · boutons non documentés ») : le marqueur allonge la ligne, c'est le prix assumé
de l'option choisie, et le banc d'essai continue de contrôler les limites Discord (0 problème).

### 24.5 Ce que la passe a aussi vérifié

- **Les cinq profils de référence** du README et du guide de déploiement sont inchangés, mais leur ordre est
  désormais cohérent : Palm 180 × 90 Qualité/Prix → Phantom 88 % · Z1 V2 75 % · A9 Mini 75 % ;
  Palm 180 × 90 Économique → Z1 V2 75 % · A9 Mini 75 % · GHOST Ultimate 75 % (la Z1 affichait 63 % contre
  75 % pour sa deuxième ligne avant la passe) ; Palm 200 × 110 Haut de gamme → A9 Ultimate 88 % ·
  X1 V2 Ultra Max 88 % · A9 Plus 2.0 88 % · (prix non vérifié) ; Claw 180 × 100 pincée → ZERO 100 % ·
  X2A v3 100 % · MAD R 88 % ; budget 25 € / main 150 × 65 → V3 50 % · U2 38 % · R1 25 %.
- **Aucun trou nouveau** : les places remplies sont identiques au profil près (le repli « jamais de trou »
  reste en place, et il est lui aussi plafonné par l'ordre quand un candidat existe).
- **Deux places sur la même coque** : 2 010 → 1 864 profils (grille du parcours) et 1 339 → 1 274
  (grille statistique, 18 522 profils) — la règle d'ordre réduit mécaniquement les répétitions de coque.
- **Rapports régénérés** : `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md`,
  `docs/audit/matrice_profils.md` et les trois aperçus PNG (`docs/apercu_*.png`, dont le résultat).

### 24.6 Preuves d'exécution (35e passe)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **409 passed** (403 avant la passe : 6 tests ajoutés — ordre garanti, match idéal intact, marqueur de prix, pied de message, marqueur de score partiel dans les deux sens) |
| `pyflakes` (bot, config, cogs, utils, tests, tools) | 0 avertissement |
| `tools/qa_flow_matrix.py` (27 170 profils) | **0 problème** (contrôle du marqueur de score partiel ajouté) · 3 places 23 231 (85,50 %) · 2 places 1 196 · 1 place 182 · 0 place 2 561 · repli « même coque » 645 · match idéal partiel 3 118 · **ordre non garanti 84 (0,31 %)** |
| `tools/flow_effect.py --avant 41d741d` (24 609 profils) | match idéal **0 profil changé** · alternative 1 615 · troisième place 1 976 · **ordre violé 2 046 → 84** · places remplies identiques |
| `tools/privacy_scan.py` | 0 violation |
| `tools/check_deployment.py` | 1 erreur, **attendue** : `.env` absent de cet atelier (le serveur l'a) |

## 25. Trente-septième passe (2026-10-13) : le prix affiché est celui de la page ouverte par le lien

Passe d'audit, **sans nouveauté** : relire les 36 liens d'achat, prouver chaque écart contre la page du
marchand, corriger les prix, et verrouiller la règle par des tests. Aucune ligne du moteur n'a été
touchée — aucun seuil, aucun barème, aucune fenêtre, aucun libellé.

### 25.1 Le défaut : le prix annoncé peut ne pas être celui de la page ouverte

Un lien de `data/commercial_links.json` peut figer une **variante** par son paramètre `variant=<id>`. Le
contrôle du 2026-10-11 avait vérifié le **libellé** de cette variante (`variants/<id>.json`) — jamais son
**prix**, qui venait d'un relevé « **dès** X € » : le modèle le moins cher de la page, pas forcément
celui que le lien ouvre. Le piège s'était déjà refermé deux fois (Y9, Z1 V2, corrigées le 2026-10-12).

Le 2026-10-13, **les 36 liens** ont été repassés un par un sur la page du marchand
(`products/<handle>.js?country=FR` chez atk.store → prix et variantes en euros ; `search/suggest.json` et
`products/<handle>.js` chez eu.pulsar.gg). Le résultat est plus large que prévu : **six prix étaient
faux**, et **l'erreur n'était pas dans le code mais dans la donnée** — la boutique avait relevé plusieurs
tarifs d'un euro entre le 12 et le 13, sans que rien ne le signale.

| Souris | Annoncé | Prix réel du 2026-10-13 | Cause |
| --- | --- | --- | --- |
| **ATK A9 Ultimate** | 41,95 € | **59,95 €** | le lien ouvre l'édition « Ultimate » ; 41,95 € était le prix d'une **autre édition** de la même page |
| **ATK X1 V2 Ultra Max** | 40,95 € | **41,95 €** | même variante, prix relevé d'un euro depuis le 12 |
| **ATK F1 V2** | 40,95 € | **41,95 €** | variante « Ultra Max 2.0 / Black » (prix normal 63,95 €) |
| **VXE MAD R** | 40,95 € | **41,95 €** | série « à partir de » (produit toujours en rupture) |
| **ATK Dragonfly A9 NB** | 72,95 € | **73,95 €** | prix du produit (prix normal 123,95 €) |
| **ATK Blazing Sky Duckbill** | 81,95 € | **82,95 €** | modèle « Ultra » unique (prix normal 118,95 €) |

Trois liens ont aussi été **recâblés vers un coloris en stock**, au même prix — GHOST Ultimate → Silver
(68,95 €), U2 V2 Ultimate → Lake Green (59,95 €), Y9 Ultimate → Pink (59,95 €) : les variantes
précédentes étaient épuisées, donc le clic ouvrait une page sans achat possible. Les neuf autres liens
qui figent une variante sont cohérents, et les deux liens Pulsar qui tombent sur une rupture (Xlite v4
Medium et Large, aucun coloris disponible) ne peuvent pas être recâblés : c'est **noté**, pas corrigé.

Enfin, l'écart de prix de l'**A9 Plus** (variante liée à 27,95 €, catalogue à 45,00 €) **n'est pas
tranché** : rien ne prouve que ce soit le même produit. Le prix est conservé, une source d'observation
datée est ajoutée, et la question est posée (point ouvert 16 de `AUDIT.md`).

### 25.2 Effet mesuré (avant / après, grille complète)

`tools/db_effect.py --avant` (catalogue d'avant la passe) sur **27 170 profils** :

| Mesure | Avant → après |
|---|---|
| Profils dont le résultat change | **6 058 (22,30 %)** — place idéale 573 · alternative 2 517 · économique 3 781 |
| Places gagnées / perdues | **0 gagnée · 91 perdues** |
| Listes sans deux fois la même coque | **5 411** (contre 647 avec le repli documenté) |

Les 91 places perdues sont des profils à **45 € ou moins** qui voyaient l'A9 Ultimate à 41,95 € : à
59,95 €, elle sort de leur budget. C'est la conséquence assumée du prix corrigé — **le classement ne peut
pas dépendre d'un prix faux**. Les profils de référence bougent d'un seul chiffre : le parcours **Claw
180 × 100 pincée** affiche la MAD R à 41,95 € (au lieu de 40,95 €) ; les quatre autres exemples
documentés (Palm 180 × 90 Qualité/Prix et Économique, Palm 200 × 110 Haut de gamme, Palm 150 × 65 à 25 €)
sont identiques.

### 25.3 Ce que la passe a aussi vérifié

- **Chasse aux références mortes** (analyse syntaxique de tout le code) : seuls `NAVY` et `SPARK`
  ressortent — des constantes de la palette des illustrations, utilisées par le rendu d'aperçu. **Faux
  positifs, rien à nettoyer.**
- **Chasse aux renvois morts dans la documentation** : **deux** renvois de ce document citaient « §6.6 »
  et « §6.8 » d'un fichier qui n'a pas ces sections (les faits visés étaient les **points 6 et 8 du §3**
  de `VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`) — corrigés. Un **test** vérifie désormais ces renvois
  dans tout le dépôt (`tests/test_doc_references.py::test_les_renvois_de_section_pointent_sur_une_section_existante`) :
  il balaie les **74 fichiers** de documentation et de code et contrôle chaque citation « fichier §N » sur
  trois formes — **82 citations distinctes** au comptage du 2026-10-13 (72 le jour de la passe). Un renvoi
  qui pointe dans le vide fait échouer la suite.
- **Hygiène des données** (contrôle rejoué) : aucune source en double, aucune date invalide ou future,
  toutes les URL en HTTPS, cotes identiques pour une même `shell_id` — **0 problème**.
- **Audit structurel des liens** : **36 liens pour 36 souris**, tous en HTTPS, **aucun orphelin** (ni
  souris sans lien, ni lien sans souris), 24 ATK / 10 Pulsar / 2 Scyrox.
- **Domination de l'A9 Air** : l'A9 Air et l'A9 Ultimate sont au **même prix** (59,95 €) ; le test de
  domination n'exige donc plus « strictement moins chère ». Mesure : le contrôle automatisé rejoue
  **54 combinaisons** (6 modes × 3 prises × 3 mains) où l'A9 Air est classée, et elle n'est **jamais**
  devant sa jumelle ; sur la **grille statistique complète**, elle est notée dans **11 172 profils** et
  n'obtient **aucune place** (elle est aussi « jamais recommandée » dans le rapport, avec sa cause).
- **Pulsar** : les dix prix (119,99 € / 149,99 € / 149,90 €) sont **identiques** au relevé du 12.
- **Scyrox** : aucun prix en euros sur la boutique officielle ; les 74,90 € du cahier des charges sont
  conservés (V6 marquée « prix non vérifié »), la note dit maintenant pourquoi.
- **Ce qui n'a pas changé** : aucun seuil, aucun barème, aucune fenêtre, aucun libellé de place, aucune
  cote, aucun poids, aucune prise. Seules des données de prix (et leurs sources) et trois tests ont bougé.

### 25.4 Mesuré mais non modifié : quatre souris en rupture de stock

La relecture des liens a aussi rapporté la **disponibilité**. À la date du 2026-10-13, **quatre souris du
catalogue ne peuvent pas être achetées** : la **VXE MAD R** (produit entier), l'**ATK Fierce X** (produit
entier), la **Pulsar Xlite v4 Large** et la **Pulsar Xlite v4 Medium** (les deux coloris de chacune). S'y
ajoutent des **coloris** isolés, déjà traités autrement : GHOST Ultimate, U2 V2 Ultimate, Y9 Ultimate et
U2 Mini ont vu leur bouton d'achat recâblé vers un coloris en stock (§25.1).

Ce que ces ruptures pèsent, sur la grille statistique (**18 522 profils**, 51 504 places remplies) :

| Souris en rupture | Places occupées | Part des profils |
|---|---:|---:|
| VXE MAD R / MAD R Major | 1 317 | 7,1 % |
| Pulsar Xlite v4 Large | 180 | 1,0 % |
| ATK Fierce X | 105 | 0,6 % |
| Pulsar Xlite v4 Medium | 12 | 0,1 % |
| **Total** | **1 614 places sur 51 504 (3,1 %)** | — |

**Ce que coûterait un retrait — mesuré le 2026-10-13** (même outil, **grille complète et non la grille
statistique** : 27 170 profils) : sortir les quatre souris du classement changerait **1 682 profils sur
27 170 (6,19 %)** — place idéale 102, alternative 557, économie 1 517 —, **aucune place gagnée, 78 places
perdues**, et les listes reconstruites ne montrent **jamais deux fois la même coque** (1 635 sur 1 682 ;
47 retombent sur le repli documenté, coque distincte impossible). Qui reprend la place : ATK A9 Plus 2.0
(315 fois), VXE R1 (256), ATK U2 V2 Mini (236), ATK F1 V2 Ultimate (204), ATK A9 Mini (98). Le détail par
souris : **MAD R 1 517** places occupées avant, **Fierce X 152**, **Xlite v4 Medium 13**, **Xlite v4 Large
0** (sur cette grille, la Large n'occupait aucune place — d'où son absence du tableau de la grille
statistique ci-dessus, qui la compte 180 fois). Les deux grilles mesurent donc la même réalité avec deux
échantillons de profils différents : 1 614 places sur la grille statistique (18 522 profils), 1 682 profils
touchés sur la grille complète.

Pour rendre cette mesure possible, `tools/db_effect.py` a reçu une option **`--retrait`** : l'outil
**refusait** jusqu'ici de comparer deux catalogues qui ne listent pas les mêmes souris (garde-fou : la
comparaison ne voudrait rien dire), il accepte désormais **une simulation de retrait** (catalogue après =
sous-ensemble strict) et affiche le poids des souris sorties et qui reprend leur place. Un catalogue
**enrichi** reste refusé dans tous les cas — deux tests le verrouillent (`tests/test_db_effect.py`).

**Rien n'a été changé**, et c'est volontaire : un membre qui lit « VXE MAD R — 41,95 € » sur une des trois
lignes du résultat ne peut pas l'acheter aujourd'hui. Trois réponses sont possibles et elles n'ont pas le
même effet — **retirer** la souris du classement (elle sort aussi le jour où elle revient), la **classer
après** ses concurrentes disponibles, ou **écrire « en rupture »** sur sa ligne (le message reste honnête
sans toucher au classement, mais la ligne s'allonge). Aucune n'a été tranchée par le propriétaire : la
question est posée avec ces chiffres (point ouvert 18 de `AUDIT.md`), et rien n'est appliqué sans réponse —
c'est la règle du projet (le moteur ne bouge que sur demande explicite, et une donnée ne s'invente pas).

### 25.5 Preuves d'exécution (37e passe)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **486 passed** à la clôture de la passe (412 au moment des trois tests de prix, puis +74 cas venus du garde paramétré sur les renvois de section, §25.3) |
| `pyflakes` (bot, config, cogs, utils, tests, tools) | 0 avertissement |
| `tools/qa_flow_matrix.py` (27 170 profils) | **0 problème** · 3 places 23 140 (85,17 %) · 2 places 1 287 · 1 place 182 · 0 place 2 561 · repli « même coque » 631 · match idéal partiel 3 118 · ordre non garanti 70 (0,26 %) |
| `tools/db_effect.py --avant` (grille complète) | 6 058 profils changent (22,30 %) · **0 place gagnée, 91 perdue** |
| `tools/privacy_scan.py` | 0 violation |
| `tools/check_deployment.py` | 1 erreur, **attendue** : `.env` absent de cet atelier (le serveur l'a) |
| `data/mouse_db.json` | 36 souris, **254 sources** (226 avant la passe) dont **37 relevés datés du 2026-10-13**, sur 34 souris |

Les trois tests ajoutés à `tests/test_data.py` :

1. `test_le_prix_de_l_a9_ultimate_est_celui_de_sa_variante` — le prix d'une fiche est celui de la
   variante que son lien ouvre (59,95 €), pas celui d'une édition voisine de la même page (41,95 €) ;
2. `test_chaque_lien_a_variante_est_trace_par_une_source` — tout lien qui fige une variante doit porter,
   en base, une source datée de ce relevé ;
3. `test_chaque_prix_de_souris_est_date_par_une_source` — **aucun prix sans source de prix datée**, et
   la note de prix doit dire **quand** elle a été relevée. C'est le contrôle qui manquait : les six
   écarts du 13 sont exactement ce qu'il interdit désormais.

### 25.6 Après la 37e passe : les deux décisions laissées au propriétaire sont chiffrées (2026-10-13)

La 37e passe a laissé deux questions ouvertes au propriétaire (`AUDIT.md` §8, points 16 et 18). Les deux
sont maintenant accompagnées d'un **effet mesuré**, pour que la décision se prenne sur des chiffres et non
sur une impression — **aucune des deux n'est appliquée** : le moteur, les données et les messages sont
inchangés.

**1. Prix de l'ATK A9 Plus (point 16)** — si la souris prenait le prix de la variante que son lien ouvre
(**27,95 €** au lieu des 45,00 € du cahier des charges) :

| Mesure (grille complète, 27 170 profils) | Résultat |
|---|---|
| Profils dont au moins une place change | **3 556 (13,09 %)** |
| Places modifiées | idéale **1 491** · alternative **2 711** · économie **1 790** |
| Places gagnées / perdues | **0 / 0** — aucune liste ne s'allonge ni ne raccourcit |
| Listes reconstruites | 3 016 **sans deux fois la même coque** · 540 avec le repli documenté |

Les trois nombres de places dépassent 3 556 parce qu'une même liste peut changer sur deux places — ce sont
des **places**, pas des profils. Qui reprend la place : l'A9 Plus elle-même dans **1 487** listes (elle
remonte), l'A9 Ultimate 114, l'A9 Air 27, l'A9 Mini 11.

**2. Sort des quatre souris en rupture (point 18)** — si elles sortaient du classement : **1 682 profils
(6,19 %)** changent, **0 place gagnée, 78 perdues**, la MAD R occupait 1 517 places avant, la Fierce X 152,
la Xlite v4 Medium 13, la Xlite v4 Large 0 ; le détail et les souris qui reprennent la place sont au
§25.4. La différence entre les deux décisions est réelle : l'A9 Plus **redistribue** sans rien retirer à
personne, le retrait des ruptures **raccourcit la liste de 78 profils**.

**Coût de la troisième option** (écrire « en rupture » sur la ligne, mesuré aussi) : la plus longue des
lignes qui porteraient le marqueur mesure **95 caractères** aujourd'hui et **116** avec « · en rupture de
stock » (107 avec « · en rupture ») — à comparer aux **102 caractères** de la plus longue ligne affichée
aujourd'hui (`AUDIT.md` C35) et à la limite Discord d'un champ d'embed (**1 024 caractères**) : il n'y a
donc aucune contrainte technique, seulement une ligne un peu plus longue à l'écran. **1 682 places** sont
concernées dans la grille complète (économie 1 121, alternative 459, idéale 102), soit exactement le nombre
de places que ces quatre souris occupent.

**3. Comment rejouer les deux mesures** — aucun catalogue de simulation n'est versionné (`/tmp` est
volatil, il disparaît entre deux sessions) : les recettes qui les reconstituent sont donc écrites ici.

```bash
# 1) prix de l'A9 Plus ramené à celui de sa variante (27,95 €)
.venv/bin/python - <<'RECETTE'
import json, pathlib
entrees = json.loads(pathlib.Path("data/mouse_db.json").read_text(encoding="utf-8"))
for entree in entrees:
    if entree["id"] == "atk_a9_plus":
        entree["price_eur"] = 27.95
pathlib.Path("/tmp/sim_a9plus_2795.json").write_text(
    json.dumps(entrees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
RECETTE
.venv/bin/python tools/db_effect.py --avant data/mouse_db.json --apres /tmp/sim_a9plus_2795.json --grille complete

# 2) les quatre souris en rupture sorties du classement
.venv/bin/python - <<'RECETTE'
import json, pathlib
entrees = json.loads(pathlib.Path("data/mouse_db.json").read_text(encoding="utf-8"))
retirees = {"vxe_mad_r", "atk_fierce_x", "pulsar_xlite_v4_medium", "pulsar_xlite_v4_large"}
gardees = [entree for entree in entrees if entree["id"] not in retirees]
assert len(entrees) - len(gardees) == len(retirees)
pathlib.Path("/tmp/sim_sans_ruptures.json").write_text(
    json.dumps(gardees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
RECETTE
.venv/bin/python tools/db_effect.py --avant data/mouse_db.json --apres /tmp/sim_sans_ruptures.json \
    --grille complete --retrait
```

**4. Ce que cette mesure a ajouté au dépôt** : l'option `--retrait` de `tools/db_effect.py` (une
simulation de retrait se mesure désormais sans banc jetable) et **deux tests** qui la verrouillent
(`tests/test_db_effect.py` : un retrait mesuré, un catalogue enrichi toujours refusé). Suite complète
après ces ajouts : **488 passed**.

**5. Deux numéros de section remis dans l'ordre** (même date) : dans ce journal, « Preuves d'exécution »
suivait une section portant un numéro plus petit que le sien (§23.7 après §23.8, §25.4 après §25.5) — les
deux paires ont été renumérotées pour que l'ordre du fichier corresponde à l'ordre des numéros, et les
deux renvois concernés ont suivi (`AUDIT.md` point 18 → §25.4, plus le renvoi interne du C34). Le
`CATALOGUE_ATK.md` portait de son côté **deux sections « 4 »** : la seconde est devenue §5 (« Ajouts du
2026-10-11 »), la suivante §6, et les deux renvois qui visaient ces ajouts
(`AMELIORATIONS_MOTEUR_ET_RECHERCHE.md`, `tests/test_data.py`) ont été mis à jour ; le renvoi de
`RAPPORT_FINAL.md` (« Sources consultées », écrit avant le 11) reste juste.
Dans le guide de déploiement, une note en tête du §12 rappelle que les « attendu : N passed » de
chaque section sont **datés** et que seul le dernier compte (`488`) est à jour — un `pytest -q`
qui affiche plus de tests dans une section ancienne n'est pas une anomalie.

## 26. Trente-huitième passe (2026-10-13) : mesurer plutôt que supposer (limites Discord, typographie, appels hostiles)

Chasse aux **micro-défauts** demandée par le propriétaire (« chasse tous les micro-bugs »). Trois familles de
contrôles ont été passées sur le **code réellement exécuté**, pas sur des extraits : les limites de Discord
sur les messages produits, la typographie des textes affichés, et le comportement du code d'affichage quand
on lui donne des données dégradées.

### 26.1 Les limites Discord, mesurées sur toute la grille (27 170 profils)

Le contrôle existant (`tests/test_flow.py::test_embeds_respect_discord_limits_and_stay_short`) vérifie **un**
profil, le plus chargé. Il est complété ici par une mesure exhaustive : pour chacun des **27 170 profils** de
la grille complète, les embeds du résultat sont construits avec le moteur réel puis chaque limite de Discord
est vérifiée.

| Élément mesuré | Maximum observé | Limite Discord |
|---|---:|---:|
| Description d'un embed | 435 | 4 096 |
| Titre d'un embed | 38 | 256 |
| Pied de page | 152 | 2 048 |
| Nom d'un champ | 53 | 256 |
| Valeur d'un champ | 320 | 1 024 |
| Total d'un embed | 1 039 | 6 000 |
| Champs dans un embed | 3 | 25 |
| Embeds dans le message | 6 | 10 |

**0 violation.** Les marges sont larges (la valeur de champ la plus longue est à 31 % de la limite, le total
d'un embed à 17 %) : aucun profil ne peut produire un message refusé par Discord.

### 26.2 La typographie des messages affichés

**15 133 textes** collectés sur la grille rapide (toutes les étapes, tous les modes, tous les résultats) puis
passés au crible :

| Contrôle | Résultat |
|---|---|
| Double espace hors du séparateur voulu `  •  ` (récapitulatif, match idéal) | **0** |
| Espace devant une virgule ou un point | **0** |
| Espace devant `?` `!` (usage français) | respecté partout |
| Guillemet droit `"` | **0** |
| Mot répété (« de de ») | **0** |
| Espace oublié après une virgule | **0** |
| Valeur technique qui fuit (`None`, `nan`, `{`, `}`, `pts`, « Inconnu » affiché) | **0** |
| Champ vide | **0** |

Un seul écart de style est relevé, et il est **cohérent** : les apostrophes sont **droites** (`'`) partout —
dans le code livré comme dans la documentation (0 apostrophe typographique dans `cogs/` et `utils/`). Ce
n'est donc pas une incohérence, et rien n'a été changé pour un détail que personne ne voit.

### 26.3 Appels hostiles : ce que fait le code d'affichage avec des données dégradées

**162 combinaisons hostiles** construites à partir du catalogue réel (neuf souris dégradées : prix nul, poids
nul, capteur/MCU/switchs nuls, forme inconnue, bosse inconnue, longueur nulle en conflit, hauteur nulle,
`shell_id` nul, tous les champs optionnels nuls — croisées avec les trois prises et les six modes) :

- **0 exception** : aucune combinaison ne fait planter l'affichage ;
- **0 fuite** : ni `None`, ni `nan`, ni accolade, ni terme interne (`pts`) n'apparaît dans une ligne affichée ;
- **un piège réel trouvé** : `_step_number("thenar", Grip.FINGERTIP)` remontait un `KeyError: 'thenar'`
  **muet** (ni la prise, ni l'étape fautive n'étaient nommées). Le parcours normal ne l'appelle jamais —
  `step_kind` saute le thénar en Fingertip — mais tout code futur qui l'appellerait recevait une erreur
  incompréhensible. **Corrigé** : une erreur lisible qui nomme la prise et l'étape, et la liste des étapes
  qui existent pour cette prise. **Rien de visible ne change** (le chemin est inatteignable depuis le
  parcours), et un test le verrouille
  (`tests/test_flow.py::test_une_etape_qui_n_existe_pas_pour_la_prise_le_dit`).

### 26.4 Un commentaire qui promettait autre chose que le code

Le bouton d'accueil du panneau portait ce commentaire : « Double appui (fréquent sur mobile) : la première
réponse est déjà partie et le parcours est ouvert. Aucune erreur affichée, **aucune seconde session
créée** ». C'est faux, et c'est mesurable : un double appui mobile envoie **deux interactions distinctes**,
la méthode est donc appelée **deux fois**, et chaque appel **crée un parcours** — le second remplace le
premier (`SessionStore.start` supprime le parcours précédent du même membre). Rien de grave pour le membre
(il n'a jamais deux parcours vivants, et les deux messages affichés restent utilisables : chaque composant
retrouve le parcours du membre qui clique), mais le commentaire disait le contraire de la garantie réelle.

**Corrigé le 2026-10-13** : le commentaire dit maintenant la vérité (« il n'y en a jamais deux vivants »),
et **deux tests** la verrouillent —
`test_double_tap_on_start_shows_no_error_and_opens_the_parcours` (une interaction réémise ne provoque
aucune erreur visible) et le nouveau `test_deux_appuis_sur_le_panneau_ne_laissent_qu_un_parcours_vivant`
(deux appuis = un seul parcours vivant, le plus récent).

### 26.5 Le fichier d'état du serveur, attaqué de toutes les façons

Le livrable conserve les parcours en cours dans `state/sessions.json` (sur le serveur, ce fichier peut être
**tronqué** par un transfert FileZilla interrompu, **édité à la main**, écrit par une **version
antérieure**, ou son nom occupé par un **dossier**). Quatorze contenus hostiles ont été passés au
`SessionStore` : fichier vide, JSON invalide, liste à la racine, version inconnue, `sessions` qui n'est pas
une liste, entrée qui n'est pas un objet, session sans `user_id`, âge illisible (« hier »), âge démesuré
(`1e12`), prise inconnue, budget en texte, session dupliquée, âge négatif, dossier à la place du fichier.

**Résultat** : aucune exception dans tous les cas — soit le fichier est ignoré et un parcours neuf
fonctionne immédiatement, soit ce qui est lisible est récupéré. Le démarrage du bot ne peut donc pas être
bloqué par ce fichier.

**Un micro-défaut trouvé et corrigé** : un âge **négatif** (horloge reculée, ou fichier bricolé) était
accepté tel quel, et la session repartait avec `last_seen = maintenant − âge`, c'est-à-dire **dans le
futur** : elle gagnait la vie en plus, et avec un âge très négatif elle ne pouvait **plus jamais expirer**
(elle restait en mémoire et dans le fichier jusqu'au redémarrage suivant). Corrigé : un âge négatif est
ramené à zéro (« vue à l'instant »), ce qui est aussi ce que le magasin écrit lui-même
(`max(0.0, age_seconds)` dans `to_state`). Verrouillé par
`tests/test_session.py::test_un_age_negatif_ne_rend_pas_la_session_immortelle` (la session récupérée expire
après le délai normal) et par les quatre cas récupérés de
`test_ce_qui_est_lisible_est_recupere_sans_gagner_de_vie`.

### 26.6 Le catalogue, attaqué avec des valeurs hostiles

Deuxième fichier du serveur qui peut être abîmé : `data/mouse_db.json` (transfert interrompu, édition à la
main, export mal formé). **279 combinaisons** ont été testées — 31 champs de la fiche × 9 valeurs hostiles
(texte, `true`, `NaN`, infini, négatif, milliard, liste, objet, chaîne vide) — chacune appliquée à
**toutes** les souris d'un catalogue de travail, puis affichée sur 5 profils (Palm 180×90 Q/P, Palm
200×110 HDG, Palm 160×70 éco, Claw 180×100 Q/P, Fingertip 170×80 éco).

**Ce que le chargement acceptait à tort, et ce que le membre voyait alors :**

| Valeur hostile | Chargement (avant) | Ce que voyait le membre |
|---|---|---|
| `weight_g` en **texte** (« 55 g ») | accepté | **erreur inattendue** (`ValueError: Unknown format code 'g'`) |
| `weight_g` en **liste** ou en **objet** | accepté | **erreur inattendue** (`TypeError`) |
| `weight_g` = `NaN`, infini ou négatif | accepté | « nan g » · « inf g » · « -5 g » |
| `length_mm`, `width_max_mm`, `height_mm`, `grip_width_mm` = `NaN` ou infini | accepté | « nan mm » dans les repères de taille |
| `price_eur` = `NaN` ou infini | accepté | « nan € » · « inf € » |
| `polling_hz` = `true` | accepté | « 1 Hz » |
| n'importe quel nombre = `true` | accepté | `True` est un `int` en Python : la règle passait |

`nan <= 0` et `inf <= 0` sont **faux** : la règle « nombre positif » les laissait donc traverser. C'était
le **dernier endroit du livrable où une donnée hostile pouvait faire échouer l'affichage** — les 162
combinaisons du §26.3 portaient sur des données déjà chargées.

**Corrigé le 2026-10-13** : `_positive_or_none` refuse les booléens, tout ce qui n'est pas un nombre et
**tout nombre non fini** ; `weight_g` passe par cette validation comme les autres nombres (c'était le seul
champ numérique sans contrôle, et c'est précisément celui qui plantait) ; `polling_hz` refuse les
booléens. Aucune donnée réelle ne change : le catalogue livré se recharge à l'identique (36 souris, poids
inchangés), vérifié par `test_les_nombres_du_vrai_catalogue_sont_finis_et_positifs`, et
`tests/test_data.py` refuse désormais les 14 valeurs hostiles une par une.

**Le même banc a trouvé un troisième verrou manquant, sur les liens d'achat.** Un lien de
`data/commercial_links.json` contenant un espace, une tabulation, un saut de ligne ou un caractère de
contrôle était accepté (seul le schéma `http(s)://` était vérifié) puis transmis tel quel au bouton du
résultat. Une telle adresse n'est pas une URL : Discord refuse le composant au moment de l'envoi, et
c'est alors le **résultat entier** qui échoue — le membre recevrait « erreur inattendue » au lieu de ses
trois souris. Ce n'est pas éprouvable depuis cet atelier (aucun accès à l'API Discord), mais la parade ne
coûte rien : le lien fautif est écarté (avertissement dans les journaux, bouton « Liens à venir »),
**les autres souris gardent le leur** — on perd un bouton, jamais le résultat. Une espace encodée
(`%20`) reste valide, et les 36 liens livrés sont tous conservés (vérifié). La même règle a été étendue aux
**URL d'images** de `assets/images.json` : une adresse contenant une espace ou un caractère de contrôle
n'affiche rien, ce qui est déjà le contrat de ce module (« aucune image plutôt qu'une exception »).

**Ce qui reste accepté, et pourquoi** : `brand` / `model` en texte libre (c'est ce qui s'affiche, par
conception), et un prix ou un poids **géant mais fini** (`1e9`) — donnée absurde, pas erreur de code : le
poids réel est déjà encadré par un test de données (20–120 g). Seul effet d'affichage possible :
« 1e+09 g ». Aucune souris livrée n'est dans ce cas.

### 26.7 Mise au propre du dépôt : inventaire complet, résidus retirés (2026-10-13)

Le 2026-10-12 (§21.3), deux résidus étaient **signalés** sans être supprimés : la règle du projet interdit
toute suppression avant un inventaire complet. L'inventaire a été fait le 2026-10-13 sur les fichiers
suivis du dépôt ; voici ce qui est sorti, ce qui reste, et pourquoi.

**Retiré — 4 fichiers suivis (1,4 Mo) et 2 aperçus non suivis :**

| Fichier | Nature | Pourquoi il part |
|---|---|---|
| `image.png` (racine, 423 Ko, 1568 × 500) | **brouillon** de bannière (« AzeMouse ✦ by aze129 », composition illustrée) | jamais livré ni affiché : la bannière publiée est `T08_azemouse_banniere.png`, une composition photo plus récente ; aucun code, aucun test, aucun document ne l'utilisait. Récupérable tel quel : `git show 9b8e4be:image.png > image.png` (423 002 octets, vérifié) |
| `image-search/eloshapes-atk-f1-v3-mouse-top-view-shape-1.png`, `-2.jpg`, `-3.png` (1 Mo) | rendus EloShapes de l'ATK F1 V3 | **suivis dans un dossier ignoré** (`image-search/`), donc incohérence de dépôt ; les largeurs mesurées sur ces vues sont écrites et sourcées dans `MESURES_LARGEUR_2026-10-11.md`, et `image-search/` reste le dossier où déposer une image à mesurer |
| `image-search/_apercu_haut2.png`, `_apercu_pip.png` | aperçus produits par un banc de mesure | jamais suivis par Git : documents de travail d'une passe |

**Conservé — et pourquoi** (le reste de l'inventaire : **146 fichiers suivis** après l'opération) :

- `ImageUse/` — **copie à l'octet près** des 15 illustrations livrées (`assets/illustrations/`, empreintes
  MD5 identiques 15/15). Doublon en apparence, mais c'est la **source nommée** par le master prompt
  (§39 et §126) et par `REPORTE_DESIGN.md` : la retirer rendrait ces renvois faux.
- `ImageAct/` (7 captures de l'interface d'origine), `ImageEx/` (9 références de design), `Reverse/`
  (10 sorties datées de l'outil Oblivity, citées par `utils/matcher.py` et `utils/models.py`) : matériaux
  nommés par la documentation et par le code.
- **Aucun code mort** : un balayage AST de `utils/*.py`, `cogs/*.py`, `bot.py` et `config.py` ne trouve
  ni fonction, ni classe, ni constante jamais référencée — 0 candidat.
- Les **15 outils** de `tools/` sont tous cités par le README, un document ou un test ; les **26 fichiers
  de tests** sont tous exécutés (`pytest.ini` : `testpaths = tests`) ; les **27 documents** du dossier
  `docs/` sont tous atteignables depuis le README.
- Deux documents n'étaient atteignables depuis nulle part (`LISTE_LIENS_SPONSORISES_2026-10-11.md` et
  `audit/ELOSHAPES_2026-10-12.md`) : ils sont désormais listés dans le README, section « Structure du
  dépôt » — un document qu'on ne peut pas trouver ne sert à personne.
- Caches locaux (`.pytest_cache/`, `__pycache__/`) supprimés : ils ne sont jamais suivis par Git.

**Ce qui n'est jamais envoyé sur le serveur** : `docs/`, `tests/`, `ImageAct/`, `ImageEx/`, `ImageUse/`,
`Reverse/`, `pytest.ini`, `requirements-dev.txt` — soit **≈ 10 Mo** mesurés le 2026-10-13 (guide de
déploiement §2.3, chiffre corrigé à cette date).

### 26.8 Trois outils de mesure disaient leur erreur en une trace brute

Les outils de `tools/` servent au propriétaire (dépouillement, mesures, comparaisons). Trois d'entre eux
remontaient une **trace Python** au lieu d'une phrase quand on leur donnait un mauvais chemin — le genre
de message qui laisse croire à une panne de l'outil plutôt qu'à un chemin à corriger :

| Outil | Ce qui arrivait | Ce qui arrive maintenant |
|---|---|---|
| `tools/db_effect.py` (catalogue absent, ou fichier qui n'est pas du JSON) | `FileNotFoundError` · `JSONDecodeError` bruts | `catalogue introuvable (AVANT) : …` · `catalogue illisible ou incohérent : …` |
| `tools/image_identity_check.py` (image absente ou illisible) | `FileNotFoundError` · `UnidentifiedImageError` bruts | `image introuvable (référence) : …` · `image illisible : …` |
| `tools/flow_effect.py` (référence Git inconnue) | `CalledProcessError` brut | `référence introuvable dans ce dépôt : '…' (attendu : un commit, une branche ou HEAD)` |

Les trois sortent désormais en **code 2** (erreur d'usage), comme `image_corpus_check.py` qui disait
déjà « dossier introuvable » (vérifié : il reste propre même quand `image-search/` n'existe pas, cas
possible depuis le nettoyage du §26.7). Aucune mesure, aucun chiffre publié n'est touché par ce
changement : seul le message d'erreur change. Verrouillé par `tests/test_db_effect.py`,
`tests/test_image_identity_check.py` et `tests/test_flow_effect.py` (nouveau).

### 26.9 Le parcours numérotait son étape de variante avec deux tables

En parcourant **tous les états possibles du questionnaire** (9 états : aucune prise, Palm, Claw, Claw avec
variante, Claw complet, Palm avec thénar, Palm complet, Fingertip, Fingertip complet), une divergence est
apparue :

- `step_kind()` — qui décide de l'étape à afficher — renvoie `claw_variant` ;
- `STEP_NUMBERS` — qui porte les numéros d'étape — utilisait la clé `variant`.

Conséquence : `_step_number("claw_variant", Grip.CLAW)` levait un `ValueError` (« Étape « claw_variant »
inexistante en Claw Grip »), et l'étape de variante échappait à toute numérotation automatique — son
titre écrivait **`2` en dur** (`_step_title(2, Grip.CLAW, …)`), deuxième source de vérité pour la même
information : le jour où la table change, le titre aurait menti sans que rien ne le signale. Aucun membre
ne voyait d'erreur (le titre était juste, et le parcours n'appelle jamais `_step_number` pour cette
étape), mais c'était le même piège que le §26.4 : une incohérence invisible qui attend.

**Corrigé le 2026-10-13** : une seule orthographe partout (`claw_variant`, comme le `custom_id`, la clé de
session et la classe de vue), et le titre lit désormais la table. Preuve dans les deux sens :

- les **trois aperçus régénérés après la correction sont identiques à l'octet près** (MD5) : rien n'a
  changé pour le membre ;
- le nouveau `tests/test_flow.py::test_chaque_etape_affichee_porte_le_numero_de_la_table` parcourt les
  huit états du parcours, exige que le numéro de la table existe **et** se retrouve dans le titre
  affiché ; remis volontairement sur l'ancienne clé (`variant`), il **échoue** — vérifié.

### 26.10 Preuves d'exécution (38e passe)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **535 passed** (488 avant la passe : 47 tests ajoutés — code, validation, fichiers hostiles, outils) |
| Les 9 états du questionnaire, numérotés par la table | 0 écart de numéro ; aperçus régénérés identiques à l'octet près |
| Outils à mauvais chemin (3 cas) | messages lisibles, code 2 — plus aucune trace Python |
| Inventaire du dépôt (balayage AST + citations) | 0 code mort, 0 outil orphelin, 2 documents orphelins désormais listés ; 4 fichiers retirés (1,4 Mo) |
| `tools/render_preview.py` — les trois aperçus régénérés après la passe | **identiques à l'octet près** aux PNG livrés (MD5) : la passe n'a rien changé de **visible** |
| Catalogue attaqué (279 combinaisons) | 0 affichage cassé après correction (3 cas d'erreur et 8 cas de charabia avant) |
| `pyflakes` (bot, config, cogs, utils, tests, tools) | 0 avertissement |
| Mesure des limites Discord (27 170 profils) | **0 violation** (tableau §26.1) |
| Scan typographique (15 133 textes) | 0 défaut réel (tableau §26.2) |
| Appels hostiles (162 combinaisons) | 0 exception, 0 fuite technique |
| `tools/privacy_scan.py` | 0 violation |
| `tools/qa_flow_matrix.py` (27 170 profils) | **0 problème** · 3 places 23 140 (85,17 %) |
| `tools/check_deployment.py` | 1 erreur, **attendue** : `.env` absent de cet atelier |

**Ce qui n'a pas changé** : aucun score, aucun seuil, aucune fenêtre, aucun libellé, aucune donnée, aucun
prix, aucun lien. Une seule ligne de code a bougé (`_step_number`), dans un chemin que le parcours
n'emprunte jamais.

### 26.11 Le total des étapes était une seconde table, écrite en clair (C42)

Corrigé juste après C41, en relisant le même affichage : l'étape suivante était le **dénominateur**.

| Ce qui était écrit | Ce que ça produisait |
|---|---|
| `_steps_total()` recalculait le nombre d'étapes en clair — 3 en Fingertip, 5 en Claw, 4 sinon | un total séparé de la table des numéros : les deux pouvaient diverger |
| `grip_step_embed()` écrivait `Étape 1` dans une chaîne | l'étape « prise » avait, elle aussi, son numéro hors table |

Pourquoi c'est un défaut, alors que les valeurs étaient justes : le nombre affiché (« Étape n/**N** ») a
maintenant **une seule source**, la table `STEP_NUMBERS`. Avant, un total faux serait resté **plausible**
— personne ne voit qu'il manque une étape — et donc invisible ; ajouter une étape à la table n'aurait
rien changé à l'affichage. C'est la même famille que C41, avec un défaut en moins : là, l'erreur était
silencieuse de bout en bout.

Ce qui a changé dans `cogs/finder_flow.py` :

- la table porte l'étape « prise » (`"grip": 1` pour les trois prises) : elle décrit désormais **tout**
  le questionnaire ;
- `GRIP_STEP_NUMBER` (lue dans la table) remplace le `1` écrit dans le titre de l'étape 1 ;
- `_steps_total()` renvoie le **plus grand numéro de la table** et lève une erreur lisible si la prise
  est inconnue (au lieu de répondre « /4 » sans rien savoir) ;
- le commentaire de `grip_step_embed` dit le bon nombre d'étapes par prise (3 / 4 / 5).

Preuve par mutation : on ajoute une étape à `STEP_NUMBERS[Grip.PALM]`, le total **et** le titre réellement
affiché suivent (`Étape 2/5` dans le titre du thénar). Remis sur l'ancien total écrit en clair, le test
**échoue** — vérifié. Et comme la valeur affichée ne change pas, les trois aperçus régénérés sont
**identiques à l'octet près**.

### 26.12 Une légende d'aperçu pouvait contredire l'embed qu'elle coiffe (C43)

Le document de validation livré (PNG) porte, au-dessus de chaque carte, une légende en petites capitales.
Celle de `docs/apercu_prix_libre.png` annonçait :

- **légende** : « ÉTAPE **5/5** — BUDGET : CINQ OPTIONS, DONT « PEU IMPORTE LE PRIX » » ;
- **embed juste en dessous** : « Étape **4/4** — Budget et gamme » + « Palm Grip · Thénar Petite · 180 × 90 mm ».

Deux causes : la légende était écrite à la main (le numéro du parcours **Claw** avait été recopié sur une
carte du parcours **Palm**), et le nombre d'options (« cinq ») était recopié du menu. Le bot, lui, était
juste : c'est le document qui mentait.

Correction : les légendes de `tools/render_preview.py` sont dérivées de la **même table** que les titres
(`_legende_etape`, qui appelle `_step_number` et `_steps_total`), chaque carte du parcours passe la prise
de son propre embed, et le nombre d'options annoncé vient de `BUDGET_OPTIONS`. Aperçu régénéré :

| Aperçu | Effet de la correction |
|---|---|
| `apercu_prix_libre.png` | la légende devient « ÉTAPE **4/4** — BUDGET : **5** OPTIONS, DONT « PEU IMPORTE LE PRIX » » ; **zone modifiée mesurée : y 22–33** sur 1 324 px (la ligne de légende, rien d'autre) |
| `apercu_parcours.png` | **identique à l'octet près** (MD5 inchangé) — les légendes Claw étaient déjà justes |
| `apercu_resultat.png` | **identique à l'octet près** (MD5 inchangé) |

Preuve dans les deux sens : `test_les_legendes_d_apercu_suivent_le_titre_des_embeds` compare les légendes
**réellement dessinées** (les fonctions qui les assemblent, pas une copie) aux titres des embeds, et
verrouille le cas exact du défaut (parcours Palm : « Étape 4/4 — budget : 5 options »). Légende remise à
la main comme avant, le test **échoue** — vérifié.

### 26.13 Importer l'outil d'aperçu changeait le bot (C44)

Trouvé en écrivant le test ci-dessus, et c'est le plus surprenant des trois : `tools/render_preview.py`
branchait ses faux domaines d'images (`https://apercu.local/…`) sur le module du bot **au moment de
l'import**, par une simple affectation en haut du fichier. Conséquence : le simple fait d'importer l'outil
— dans un test, un script, un IDE — changeait la résolution des images **dans le même processus**. Le
symptôme est apparu tout de suite : `test_without_image_base_url_no_image_is_attached_and_nothing_breaks`
échouait **selon l'ordre d'exécution** des tests, ce qui rend une suite inutilisable pour juger une
correction.

Aucun effet en production (le bot n'importe jamais cet outil — vérifié), mais la règle est la même que
partout ailleurs dans ce dépôt : un fichier ne doit rien changer tant qu'on ne lui demande rien.
Correction : le détournement est maintenant une fonction explicite (`images_locales()`), appelée par
`main()` au début de la génération. `test_importer_l_outil_d_apercu_ne_change_rien_au_bot` le verrouille :
remis en effet de bord de l'import, il **échoue** — vérifié.

### 26.14 Preuves d'exécution (38e passe, suite)

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **538 passed** (535 avant cette suite : 3 tests ajoutés) |
| Trois mutations volontaires (ancien code remis) | total en clair → **échoue** · légende à la main → **échoue** · effet de bord d'import → **échoue** |
| Les huit états du questionnaire | numéro affiché = numéro de la table (C41) et légende d'aperçu = titre de l'embed (C43) |
| `tools/render_preview.py` — aperçus régénérés | `parcours` et `resultat` **identiques à l'octet près** · `prix_libre` : seule la ligne de légende change (y 22–33) |
| `pyflakes` (bot, config, cogs, utils, tests, tools) | 0 avertissement |
| `tools/privacy_scan.py` | 0 violation |

**Ce qui n'a pas changé** : aucun score, aucun seuil, aucune fenêtre, aucun libellé affiché au membre, aucune
donnée, aucun prix, aucun lien. Un total d'étapes dérivé de la table donne exactement les mêmes textes
(les aperçus le prouvent) ; la seule image qui bouge est la légende d'un document de validation.

### 26.15 Un fichier d'état illisible bloquait `!setup_finder` (C45)

Dernière zone non ratissée de la passe : la commande d'installation, et le fichier qui la rend
idempotente (`state/finder_message.json`, écrit par `save_state`, relu par `load_state`).

Ce que faisait `load_state` — et ce que ça donnait :

| État du fichier | Avant | Attendu |
|---|---|---|
| absent | `None` (publier un message neuf) | identique |
| JSON tronqué ou mal formé | `None` | identique |
| JSON valide mais pas un objet (`null`, liste, texte, nombre) | `None` | identique |
| **dossier à la place du fichier** | `IsADirectoryError` remontait | `None` |
| **octets non UTF-8** (fichier abîmé, copie partielle) | `UnicodeDecodeError` remontait | `None` |

Dans les deux derniers cas, l'exception traversait la commande : `!setup_finder` répondait
**« ⚠️ Erreur inattendue lors de la publication du message »** — et l'administrateur ne pouvait plus
publier le message du tout, alors que la bonne réponse était « aucun état » (publier un message neuf).
La leçon du fichier de sessions (C38) n'avait pas été appliquée ici : **un fichier d'état ne doit jamais
bloquer une commande**, quelle que soit sa forme.

Deuxième défaut, trouvé en lisant la même commande : le message est publié **avant** que son identifiant
soit mémorisé. Si `save_state` échoue (disque plein, dossier non inscriptible), la commande répondait
« ⚠️ Erreur inattendue » — faux : le message **est** publié. Pire, cette réponse pousse à relancer la
commande, donc à publier un **doublon** de la bannière.

Correction (`cogs/mouse_finder.py`) :

- `load_state` attrape `(OSError, ValueError)` : dossier, droits refusés, octets non UTF-8, JSON tronqué
  — tout vaut « aucun état ». Rien d'autre ne change : la forme du fichier est toujours vérifiée
  (`channel_id` et `message_id` entiers), un état d'un autre salon est toujours ignoré ;
- si l'enregistrement de l'identifiant échoue, la réponse **dit la vérité** : « ✅ Message de départ
  publié » **plus** une note « ⚠️ Message publié, mais son identifiant n'a pas pu être enregistré (…)
  : la prochaine exécution publiera un second message. »

Preuves (les trois tests échouent sur l'ancien code — vérifié par mutation) :

| Contrôle | Résultat |
|---|---|
| `tests/test_setup_command.py::test_un_etat_illisible_est_traite_comme_absent` | dossier, octets non UTF-8, `null`, liste, texte, nombre → `None` |
| `tests/test_setup_command.py::test_setup_publie_meme_avec_un_etat_illisible` | le message est publié et le fichier d'état réécrit proprement |
| `tests/test_setup_command.py::test_identifiant_non_enregistrable_ne_fait_pas_croire_a_un_echec` | réponse « publié » + note, jamais « Erreur inattendue » |
| `pytest -q` | **541 passed** (538 avant cette correction : 3 tests ajoutés) |
| `pyflakes` · `tools/privacy_scan.py` | 0 avertissement · 0 violation |

**Ce qui n'a pas changé** : aucun texte affiché au membre, aucun score, aucune donnée, aucun prix,
aucun lien. La commande `!setup_finder` publie et met à jour exactement comme avant — elle ne se bloque
plus, et ne laisse plus croire à un échec lorsqu'elle a publié le message.

### 26.16 Un fichier d'état tronqué empêchait le bot de démarrer (C46)

Dernier tour de la même chasse, sur le fichier le plus sensible du bot : `state/sessions.json`.
Son en-tête de tests promettait déjà qu'« un fichier hostile ne doit JAMAIS empêcher le bot de
démarrer : soit il est ignoré, soit ce qui est lisible est récupéré — jamais une exception ». Mesure
faite : cette promesse avait un trou, et le trou était le plus grave des trois.

| Contenu du fichier | Avant | Attendu |
|---|---|---|
| absent | ignoré | identique |
| JSON invalide, format inconnu, entrées absurdes | ignoré | identique |
| dossier à la place du fichier | ignoré (`IsADirectoryError` est un `OSError`) | identique |
| **tronqué en plein caractère** (octets non UTF-8) | **`UnicodeDecodeError` remontait** | ignoré |
| **identifiant en demi-caractère** (`"\ud800"`, fichier bricolé) | chargé, puis **chaque enregistrement échouait** | entrée refusée |

Conséquences, dans l'ordre de gravité :

1. `SessionStore(...)` est construit **au démarrage du bot** (`MouseBot.__init__`). Un
   `UnicodeDecodeError` y faisait donc échouer le lancement : trace dans les journaux, bot arrêté,
   tâche planifiée qui relance… et le membre ne voit plus rien fonctionner. C'est exactement la panne
   « il faut recommencer à zéro » que ce fichier devait rendre impossible. Un fichier tronqué en plein
   caractère n'est pas exotique : transfert FileZilla interrompu, disque plein, copie partielle.
2. Un identifiant contenant un demi-caractère était chargé tel quel, puis réécrit **tel quel** dans le
   fichier (`ensure_ascii=False`) : l'encodage échouait, `_save` ne protégeait que les erreurs disque,
   et l'exception remontait à **chaque réponse** — le parcours devenait impossible à continuer, à
   chaque clic, tant que le fichier restait en place (et il était restauré au redémarrage suivant).
   La docstring de `save()` promettait pourtant « ne lève jamais ».

Correction (`utils/session.py`) :

- `_load` attrape `(OSError, ValueError)` : `ValueError` couvre le JSON invalide **et** les octets non
  UTF-8 (`UnicodeDecodeError`). Le fichier est ignoré, avec un avertissement qui le nomme ;
- `from_state` refuse un identifiant qui ne peut pas être réencodé en UTF-8 (``identifiant.encode``, un
  `UnicodeEncodeError` étant un `ValueError`) : une session bricolée n'entre plus dans la mémoire ;
- `_save` attrape `(OSError, ValueError)` : un contenu impossible à écrire fait perdre
  l'enregistrement (avertissement tracé), **jamais** l'interaction du membre — la promesse
  « ne lève jamais » est maintenant vraie dans le code.

Preuves (les trois tests échouent sur l'ancien code — vérifié par mutation) :

| Contrôle | Résultat |
|---|---|
| `tests/test_session.py::test_un_fichier_tronque_en_plein_caractere_ne_bloque_pas_le_demarrage` | le magasin s'ouvre vide, un parcours neuf marche et le fichier repart proprement |
| `tests/test_session.py::test_un_identifiant_impossible_a_reecrire_est_refuse` | session bricolée écartée, parcours neuf utilisable |
| `tests/test_session.py::test_un_etat_impossible_a_ecrire_ne_casse_pas_le_parcours` | `save()` ne lève pas, le magasin reste utilisable |
| `pytest -q` | **544 passed** (541 avant cette correction : 3 tests ajoutés) |
| `pyflakes` · `tools/privacy_scan.py` | 0 avertissement · 0 violation |

**Ce qui n'a pas changé** : aucun texte affiché, aucun score, aucun seuil, aucune donnée, aucun prix,
aucun lien, et aucun comportement normal du fichier d'état (les sessions lisibles sont toujours
récupérées, un âge négatif ramené à zéro, un parcours terminé jamais écrit sur le disque).

### 26.17 Une faute de frappe dans le `.env` désactivait une fonction en silence (C47)

Dernier point de la passe, sur la configuration : `config.py` refusait déjà clairement un **entier**
invalide (`SESSION_TTL_SECONDS=trente` → message + arrêt), mais traitait les **booléens** autrement.
La règle était : « tout ce qui n'est pas reconnu comme vrai vaut faux ».

| Valeur écrite dans le `.env` | Avant | Attendu |
|---|---|---|
| `true`, `1`, `yes`, `on`, `oui` | vrai | identique |
| `false`, `0`, `no`, `off`, `non` | faux | identique |
| **`ture`** (faute de frappe sur `true`) | **faux, en silence** | refusé, avec la liste des orthographes |
| **`faux!`**, `peut-être`, `indifférent` | **faux, en silence** | refusé, avec la liste des orthographes |

Conséquence concrète : `SESSION_PERSIST=ture` désactivait la **conservation des parcours en cours** —
les questionnaires commencés disparaissaient à chaque redémarrage — alors que l'administrateur venait
d'écrire dans son `.env` qu'il voulait l'inverse. Rien n'était journalisé, rien ne le signalait : le
même défaut que partout ailleurs dans cette passe (une divergence silencieuse entre ce qui est écrit
et ce qui s'exécute), cette fois dans la configuration du serveur.

Correction (`config.py`) : deux listes explicites — `_ENV_VRAI` (`1`, `true`, `yes`, `on`, `oui`,
`vrai`) et `_ENV_FAUX` (`0`, `false`, `no`, `off`, `non`, `faux`) — et **toute autre valeur lève une
`ConfigError`** qui nomme la variable, la valeur écrite, les orthographes acceptées et le fichier à
corriger. `bot.py` traduit déjà cette erreur en message lisible sans trace technique (il l'attrape
depuis le 2026-10-12), et un `.env` vide garde la valeur par défaut.

Documentation alignée : `README.md` (variables d'environnement), `.env.example` (là où la valeur est
écrite) et ce paragraphe.

Preuves (les deux tests échouent sur l'ancien comportement — vérifié par mutation) :

| Contrôle | Résultat |
|---|---|
| `tests/test_config.py` — orthographes acceptées | 6 vraies (`1`, `true`, `TRUE`, ` on `, `oui`, `vrai`) et 6 fausses (`0`, `false`, `False`, `off`, `non`, `faux`) |
| `tests/test_config.py::test_une_valeur_booléenne_inconnue_est_refusee` | `SESSION_PERSIST=ture` → `ConfigError` qui nomme la variable |
| `tests/test_config.py::test_une_valeur_booléenne_inconnue_bloque_le_demarrage_avec_un_message_lisible` | démarrage arrêté, message « doit valoir vrai ou faux », « Corrigez-la dans le fichier » |
| `pytest -q` | **558 passed** (544 avant cette correction : 14 cas de test ajoutés) |
| `pyflakes` · `tools/privacy_scan.py` | 0 avertissement · 0 violation |

**Ce qui n'a pas changé** : aucun comportement du bot, aucun texte affiché au membre, aucun score,
aucune donnée, aucun prix, aucun lien. Un `.env` correct (les 6 variables du guide, écrites
`true`/`false`) démarre exactement comme avant ; seul un `.env` avec une valeur inconnue change de
comportement — il s'arrête en le disant, au lieu de deviner.

### 26.18 Un pourcentage juste, mais rapporté au mauvais ensemble (C48)

Dernier défaut de la passe, et le seul qui ne touche **ni le bot ni un message** : il est dans le
**dossier de preuve**. Deux passages de l'audit annonçaient un pourcentage exact — pour un **autre**
dénominateur que celui écrit juste à côté.

| Passage | Ce qui était écrit | Le même rapport |
|---|---|---|
| §10 de ce document (tableau du 2026-10-12) | « Résultats à 3 places … **6 148 (22,63 %)** », sous un en-tête à **23 569** profils | 6 148 ÷ 23 569 = **26,1 %** ; 22,63 % = 6 148 ÷ **27 170** |
| §24 de ce document et §12.18 du guide de déploiement | « **84 profils** (0,31 %) », la même phrase citant **24 609** profils | 84 ÷ 24 609 = **0,34 %** ; 0,31 % = 84 ÷ **27 170** |

Les deux pourcentages étaient donc **mesurés** — sur l'autre grille (27 170, la grille complète) — et
reposés à côté d'un décompte exprimé sur la grille « profils qui ont au moins une place » (23 569, puis
24 609). Le comptage, lui, ne change pas d'une grille à l'autre : un profil **sans aucune place** ne peut
ni en avoir trois, ni violer l'ordre des pourcentages. C'est exactement ce qui rend l'erreur invisible à
la relecture : chaque nombre pris seul est vrai, et il faut refaire la division pour voir que les deux
nombres d'une même phrase ne parlent pas du même ensemble.

Aucun effet sur le bot : aucun score, aucun seuil, aucun texte affiché au membre, aucun prix, aucun lien.
L'effet est sur le **lecteur du dossier** — le propriétaire, qui décide sur ces chiffres, et qui trouve un
autre résultat s'il recompte le rapport affiché.

**Correction** : les dénominateurs sont écrits partout, et les deux grilles sont données quand les deux
chiffres coexistent (les comptages cités — 6 148 profils à trois places, 84 profils hors ordre — sont
inchangés) :

- §10 : la ligne passe à **26,1 %**, et une note sous le tableau nomme les deux ensembles
  (26,1 % des 23 569, 22,63 % des 27 170) ;
- §24, §12.18 : « 84 profils, **0,34 %** des 24 609 (0,31 % des 27 170) » ;
- le constat n° 13 de `docs/audit/AUDIT.md` §2 et `docs/MASTER_PROMPT_AZEMOUSE.md` : même précision, le chiffre de référence
  du banc d'essai (0,31 % sur 27 170) restant cité comme tel.

**Balayage complet** (fait avant de corriger, pour ne pas s'arrêter au premier cas) : 22 formes « N sur M »
dans les documents, 5 lignes portant à la fois un ensemble et un pourcentage, 1 seule incohérence (le
§12.12 du guide) ; les cellules de tableau à dénominateur implicite ont été recalculées une par une
(§7, §10, §11.4, §24, §25, `CATALOGUE_ATK`, statistiques) — aucune autre erreur. Deux pourcentages au
dixième (« 0,3 % » pour 0,34 %, « 3,7 % » pour 3,69 %) sont des arrondis, pas des erreurs.

**Nouveau contrôle** : `tests/test_doc_coherence.py` (4 cas) vérifie que tout pourcentage d'une ligne qui
cite un « N sur M » correspond au rapport, à 0,05 point près (l'arrondi au dixième passe), en lisant
l'ensemble sur la ligne du pourcentage ou sur celle qui précède. Deux limites sont écrites dans le test
plutôt que cachées : il ne juge pas un dénominateur implicite (cellule de tableau, « N profils sur les
24 609 »), et l'élargissement du motif a été **essayé puis écarté** parce qu'il laissait passer le défaut
même qu'il devait attraper (un couple juste sur la ligne voisine excusait le mauvais).

| Contrôle | Résultat |
|---|---|
| `tests/test_doc_coherence.py` | **4 passed** ; remettre l'ancienne phrase du §12.12 → **1 failed** (vérifié par mutation) |
| 6 148 ÷ 23 569 · 6 148 ÷ 27 170 | **26,09 %** · **22,63 %** |
| 84 ÷ 24 609 · 84 ÷ 27 170 | **0,34 %** · **0,31 %** |
| `pytest -q` | **563 passed** (558 avant cette correction : 4 cas ajoutés dans `tests/test_doc_coherence.py`, plus 1 cas de contrôle des renvois) |
| `pyflakes` · `tools/privacy_scan.py` | 0 avertissement · 0 violation |

**Ce qui n'a pas changé** : aucun fichier du bot, aucun message, aucun score. Le guide de déploiement ne
demande donc **aucun envoi** pour cette correction — elle concerne les documents, pas le serveur.

### 26.19 Le README avait perdu la fin d'une phrase et douze fichiers (C49)

Le README est l'**index** du dépôt : sa section « Tests » décrit la suite fichier par fichier, et son bloc
de reproduction liste les outils. Deux défauts y avaient été introduits, tous deux invisibles à l'œil
quand on cherche du code :

1. **Une description coupée en deux.** À l'ajout du fichier `tests/test_flow_effect.py` (42e passe), sa
   puce a été insérée **au milieu** de celle de `tests/test_db_effect.py` : la première finissait sur un
   tiret (« … prouve dans les deux sens — ») et sa suite (« deux catalogues identiques ne produisent
   aucun écart, … ») se retrouvait sous la puce du nouveau fichier. Le lecteur voyait donc une
   description suspendue et une autre qui décrivait le mauvais outil.
2. **Douze fichiers jamais cités** : 8 des 26 fichiers de tests et 4 des 14 outils (`render_preview.py`,
   `measure_button_height.py`, `measure_grip_width.py`, `build_mouse_db.py`). Les tests de ces outils
   existaient, la commande pour les lancer n'apparaissait nulle part — un outil qu'on ne nomme pas est un
   outil qu'on n'utilise pas, et il redevenait invisible dès la première relecture.

**Correction** : la phrase est recollée dans le bon ordre, les douze fichiers sont cités (les huit tests
avec une phrase qui dit ce qu'ils verrouillent, les quatre outils dans le bloc de reproduction), et la
garde `tests/test_doc_references.py::test_le_readme_cite_tous_les_fichiers_de_tests_et_tous_les_outils`
empêche le retour du défaut : **tout** fichier de `tests/` et de `tools/` doit être cité, et une citation
qui nomme un fichier absent est refusée.

| Contrôle | Avant | Après |
|---|---:|---:|
| Fichiers de tests cités dans le README | 18 / 26 | **26 / 26** |
| Outils cités dans le README | 10 / 14 | **14 / 14** |
| Description de `tests/test_db_effect.py` | coupée en deux | **d'un seul tenant** |
| `pytest -q` | 563 passed | **564 passed** (1 cas ajouté) |

Preuve par mutation : remplacer une citation du README par un nom de fichier inexistant →
`test_le_readme_cite_tous_les_fichiers_de_tests_et_tous_les_outils` **échoue** (vérifié) ; restauré → vert.

**Ce qui n'a pas changé** : aucun fichier du bot, aucun message affiché, aucun score, aucune donnée. Comme
pour C48, cette correction est **documentaire** : le guide de déploiement ne demande aucun envoi.

### 26.20 Quatre outils de plus ne disaient pas leur erreur comme les autres (C50)

Le §26.8 avait corrigé trois outils (phrase + code 2 au lieu d'une trace). En **balayant les quatorze
points d'entrée** — chacun confronté à une entrée invalide, code de sortie et forme du message relevés —
quatre de plus se comportaient autrement, pour la même faute de frappe dans un chemin :

| Outil | Ce qui arrivait | Ce qui arrive maintenant |
|---|---|---|
| `measure_button_height.py` (image absente) | trace `FileNotFoundError`, code **1** | `image introuvable : …`, code **2** |
| `measure_button_height.py` (image illisible) | trace `PIL.UnidentifiedImageError`, code **1** | `image illisible : …`, code **2** |
| `measure_button_height.py` (fond uni : aucune souris) | trace `ValueError` | `mesure impossible : aucune souris détectée…`, code **2** |
| `measure_grip_width.py` (image absente) | phrase mais sur la **sortie standard**, code **1** | phrase sur la sortie d'erreur, code **2** |
| `measure_grip_width.py` (image illisible) | trace `PIL.UnidentifiedImageError` (la garde ne couvrait que le fichier absent) | `image illisible : …`, code **2** |
| `build_ai_bundle.py` (option mal orthographiée) | **écrivait une archive** nommée d'après l'option et affichait « Écrit : --help » | option refusée, code **2** ; `--help` affiche l'aide |
| `check_deployment.py`, `privacy_scan.py` (tout argument) | argument **ignoré en silence**, le contrôle se lançait quand même | argument refusé, code **2** ; `--help` affiche l'aide |

Les cinq premiers sont des chemins à corriger : un message qui ressemble à une panne de l'outil fait
perdre du temps, et deux comportements différents pour la même erreur obligent à se souvenir de quel
outil on parle. Le sixième est plus gênant : `build_ai_bundle.py --help` **créait un fichier de 73 Ko**
(une faute de frappe devient un fichier, pas un message), et `check_deployment.py --help` lançait le
diagnostic complet — un lecteur pouvait croire qu'il portait sur autre chose que le dépôt.

**Deux outils de plus ont reçu `main(argv=None)`** (`db_effect.py`, `flow_effect.py`, `qa_flow_matrix.py`
avaient déjà l'habitude de lire `sys.argv` eux-mêmes) : sans cela, aucun test ne peut les appeler
proprement, et c'est précisément pourquoi ces défauts avaient survécu à trois passes de relecture.

**Le contrôle remplace la relecture** : `tests/test_tools_usage_errors.py` confronte **les quatorze**
outils à une entrée invalide et vérifie le contrat — une phrase, sur la sortie d'erreur, code 2, jamais de
trace Python — plus l'aide (`--help` ne doit **rien** écrire dans le dossier courant, vérifié dans un
dossier temporaire vide) et l'invariant `main(argv=None)`. Le dossier `tools/` est relu à l'exécution :
un outil ajouté sans `argv` fait échouer le contrôle, donc un nouvel outil ne peut plus passer à travers.

Preuves (les cinq gardes retirées une à une font échouer le contrôle — vérifié par mutation) :

| Contrôle | Résultat |
|---|---|
| `tests/test_tools_usage_errors.py` | **34 passed** (14 outils × option inconnue, 6 entrées invalides, aide, complétude) |
| Mutations (5/5) | `measure_button_height` 1 échec · `measure_grip_width` 2 · `build_ai_bundle` 2 · `check_deployment` 2 · `privacy_scan` 2 ; restauré → 34 passed |
| `tests/test_measure_grip_width.py` | son test de ligne de commande attendait `return 1` : mis à jour vers le contrat commun |
| `pytest -q` | **599 passed** |
| `pyflakes` · `tools/privacy_scan.py` · `tools/check_deployment.py` | 0 avertissement · 0 violation · **1 erreur attendue** (`.env` local), identique à avant |

**Ce qui n'a pas changé** : aucun fichier du bot, aucun message affiché dans Discord, aucun score, aucune
donnée, aucun prix, aucun lien. Le pack IA se construit à l'identique (75 230 octets, 11 fichiers,
`pack_ia_mousediscord.zip`, comme avant la correction). Aucun résultat publié ne dépend de cette
correction : elle ne touche que la façon dont les outils **répondent à une erreur d'usage**.

### 26.21 Un état bricolé bloquait le parcours ou lui donnait un résultat absurde (C51)

Les deux passes précédentes ont rendu le fichier d'état **tolérant** : illisible, il vaut « aucun état »
(C45, C46), et un âge négatif est ramené à zéro (C38). Restait le cas d'un fichier **lisible mais
incohérent** — celui qu'on obtient en l'ouvrant à la main, ou après une corruption partielle qui laisse
du JSON valide. Le parcours l'acceptait tel quel, et la suite dépendait de ce qu'il contenait :

| Ce que le fichier contenait | Ce que le membre vivait |
|---|---|
| `hand_length_mm: 0` (ou négatif) | `compute_selection` lève (« Les mesures de la main doivent être strictement positives ») → le membre lit **« ⚠️ Les données des souris sont momentanément illisibles. Réessayez dans un instant »** : un message qui accuse le catalogue, ne dit rien de la vraie cause, et **ne se résout jamais** (le même à chaque essai) |
| `hand_length_mm: NaN` | pire : toute comparaison avec `NaN` étant fausse, **chaque souris passe pour « dans la plage »** — le membre reçoit un résultat absurde, présenté sans aucune réserve, sous un récapitulatif annonçant « `nan × nan mm` » |
| `hand_length_mm: 900`, `hand_width_mm: 400` | score calculé contre des cibles impossibles → « Aucun match classable » (message honnête, mais pour une main qui n'existe pas) |
| `budget_mode: "custom"` **sans** `max_budget_eur` | même impasse que la première ligne : erreur du moteur, message « données illisibles », sans issue |
| `budget_mode: "custom"` avec `max_budget_eur: NaN` (ou infini) | **le budget est ignoré en silence** : aucune souris n'est écartée (`prix > NaN` est faux), le résultat est celui d'un budget illimité alors que le récapitulatif annonce « Budget personnalisé » |

La règle appliquée est celle qui existe déjà dans ce fichier — **une valeur illisible est écartée, le
reste du parcours reprend** (c'est écrit et testé pour le budget : « budget texte », cas `CAS_RECUPERES`) —
appliquée aux deux endroits qui y échappaient :

- **les mesures de la main** ne sont restaurées que si elles sont des nombres **finis** dans les bornes du
  formulaire (`utils/validation.py` : 100–260 mm et 50–130 mm, les deux ensemble — le formulaire valide le
  couple). Sinon elles valent **réponse absente** : le parcours reprend à l'étape « Vos mesures » ;
- **« Budget personnalisé »** n'est conservé qu'avec un plafond fini dans les bornes du formulaire
  (10–5 000 €). Sinon le mode redevient « aucune gamme choisie » et la question est reposée.

Aucune valeur **saisissable** n'est touchée : un membre ne peut produire que des nombres finis dans ces
bornes (`parse_hand_measures` / `parse_budget` les refusent autrement), donc tout ce qu'un membre a
réellement répondu est restauré à l'identique. Aucun score, aucun seuil, aucune donnée du catalogue,
aucun texte affiché au membre n'est modifié par cette correction : c'est un filtre d'entrée, sur le seul
fichier que le bot écrit lui-même.

Preuves (les deux filtres retirés font échouer 9 puis 8 cas — vérifié par mutation) :

| Contrôle | Résultat |
|---|---|
| `tests/test_session.py` | **57 passed** (+24 cas : 8 mesures impossibles, 4 mesures du formulaire, 8 plafonds, 2 non-régressions, 1 comparaison de parcours) |
| Mutation — mesures restaurées sans contrôle | **9 échecs** · restauré → 57 passed |
| Mutation — mode `CUSTOM` conservé sans plafond | **8 échecs** · restauré → 57 passed |
| Matrix des états restaurés (17 états bricolés) | **aucune exception inattendue** avant comme après ; après correction, « mesures nulles / négatives / inversées / énormes » reprennent comme un parcours sans mesures |
| `pytest -q` | **623 passed** |
| `tools/qa_flow_matrix.py` (grille complète, 27 170 profils, après la correction) | **Problèmes détectés : 0** — 0 place 2 561 · 1 place 182 · 2 places 1 287 · 3 places 23 140 (85,17 %) · idéal partiel 3 118 · repli « même coque » 631 · ordre non garanti 70 (0,26 %) : **identique** aux chiffres documentés au §25.1 |
| `pyflakes` · `tools/privacy_scan.py` | 0 avertissement · 0 violation |

**Ce qui n'a pas changé** : le barème, la sélection, le catalogue, les prix, les liens, les illustrations,
les textes affichés et les trois aperçus. La correction ne concerne que la **restauration** d'un parcours
après un redémarrage.

### 26.22 Une coque partagée ne citait aucune source (C53)

`shell_id` est le champ qui empêche **deux variantes du même moule** d'occuper deux places du même résultat
(11e, 13e, 14e passes : coque A9 pleine taille, U2 Mini, F1, X1 / X3, familles Pulsar X2 et X2H). C'est donc,
comme un prix ou une cote, une décision qui change ce que le membre voit — et c'était pourtant le **seul
champ renseigné du catalogue absent de l'inventaire de provenance** vérifié par la machine (C23 : les seize
champs de `CHAMPS_TRAÇABLES`). Mesure du 2026-10-13 : sur **23 entrées portant un `shell_id`, 21 ne citaient
aucune source** déclarant le champ. Seules les deux entrées de la paire Pulsar X2 Medium (14e passe) le
faisaient : la convention existait, elle n'était simplement **exigée par rien**.

Pourquoi ce n'est pas cosmétique :

| Si… | Ce qui se passe, faute de verrou |
|---|---|
| un `shell_id` disparaît | deux entrées du même moule redeviennent candidates ensemble : 92 profils montraient deux fois la même souris avant la 11e passe, et 4 555 profils sur 27 170 (**16,8 %**) montraient deux fois la même coque avant la 13e |
| un `shell_id` est inventé | une souris est écartée d'un résultat pour une raison qui n'existe pas, sans que rien ne le signale |
| deux entrées reçoivent la même coque par erreur | le canari existant ne le voit pas : `test_two_entries_with_identical_dimensions_share_their_shell` vérifie l'autre sens (deux cotes identiques ⇒ même coque), pas « ces deux-là n'ont rien à faire ensemble » |

`shell_id` était resté hors de l'inventaire parce qu'une souris **sans jumelle** n'a aucune preuve externe à
citer (« aucune autre entrée ne partage ce moule » est une phrase sur le catalogue, pas sur la souris). La
règle retenue sépare donc les deux cas, et c'est elle qui est désormais verrouillée :

- **coque partagée par au moins deux entrées** : chacune cite la source qui l'atteste (`sources[].fields`),
  cette source doit appartenir au **fabricant** (`atk.store`, `eu.pulsar.gg`…) ou à un **document du projet**
  (cahier des charges du propriétaire, mesure), et **son libellé dit ce qui la justifie** (« même coque »,
  « un seul moule », « cotes publiées identiques », « série / famille »). Un guide de prise tiers ne peut pas
  attester un moule : il ne le connaît pas ;
- **coque d'une seule entrée** : rien à citer — et donc rien à inventer.

Le catalogue appliquait déjà cette règle à la paire X2 Medium ; elle est maintenant écrite, appliquée aux
**16 entrées** qui ne la respectaient pas, et verrouillée par
`tests/test_data.py::test_chaque_coque_partagee_declare_la_source_qui_l_atteste`.

| Coque | Entrées | Ce que la source déclarante énonce |
|---|---|---|
| `atk_a9_large` | A9 Plus, A9 Ultimate, A9 Air, A9 NB | « Coque ATK A9 pleine taille (`shell_id` « `atk_a9_large` ») » : un seul moule, celui de l'A9 Plus 2.0 du propriétaire ; cotes de la série 125 × 63,5 × 40 mm |
| `atk_f1` | F1 V3 Ultimate, F1 V2 | « Coque ATK F1 (`shell_id` « `atk_f1` ») » ; cotes publiées 118,2 × 62,4 × 38,8 mm |
| `atk_ghost` | GHOST Ultimate, GHOST Extreme | le fabricant publie les deux variantes sous **une seule fiche produit** (deux identifiants de variante) ; cotes identiques 121 × 61,3 × 38 mm |
| `atk_u2_mini` | U2 V2 Mini, U2 Mini | collection U2 (119,5 × 63 × 38,5 mm) et « le store ne liste pas de U2 V2 Mini séparé » |
| `atk_x1` | X1 V2 Ultra Max, VXE X3 | cotes publiées 127 × 64 × 40 mm, **identiques au dixième de millimètre** sur les deux fiches ATK |
| `pulsar_x2_mini` | X2 v3 Mini, X2 CrazyLight Mini | cotes publiées 115,6 × 61 × 36,6 mm sur les deux fiches officielles ; « Same Size as the X2 Size 1 » côté CrazyLight |
| `pulsar_x2h_mini` | X2H v3 Mini, X2H CrazyLight Mini | cotes publiées 115,6 × 62 × 38 mm sur les deux fiches officielles |
| `pulsar_x2_medium` | X2A v3, X2 CrazyLight Medium | série « X2 » taille « Medium » de la fiche officielle (14e passe) |

**Ce qui n'a pas changé** : aucune cote, aucun prix, aucun verdict de prise, aucune bosse, aucun poids,
aucun capteur, aucun `shell_id`. Seules **seize listes de champs** et **huit libellés de sources** ont été
complétés ; l'empreinte SHA-256 des 36 entrées projetées sur les 27 champs qui pèsent sur un score, un prix,
un affichage ou un regroupement de coque est **identique avant / après** (`c0278240…`), le nombre de sources
par souris est inchangé (aucune source ajoutée), et aucune note n'a bougé. Rien ne change à l'écran : les
`fields` ne sont pas lus par le moteur de score, et les libellés de sources ne sont jamais affichés au membre.

Preuves (le verrou tombe sur les trois formes du défaut — vérifié par mutation) :

| Contrôle | Résultat |
|---|---|
| `tests/test_data.py` | **90 passed** (+1 cas : les huit coques partagées, source déclarante, hôte autorisé, libellé qui dit pourquoi) |
| Mutation A — déclaration retirée de la X3 | **1 échec** · restauré → 1 passed |
| Mutation B — source déclarante remplacée par un guide tiers | **1 échec** · restauré → 1 passed |
| Mutation C — coque unique rattachée à une coque partagée sans preuve | **1 échec** · restauré → 1 passed |
| `pytest -q` | **624 passed** |
| `tools/privacy_scan.py` | 0 violation |

### 26.23 Deux lectures de fichiers faisaient échouer tout le parcours (C54, C55)

Le parcours lit cinq fichiers : le fichier de sessions, `mouse_db.json`, `data/commercial_links.json`,
`assets/images.json` et l'état du `!setup_finder`. Trois d'entre eux étaient déjà tolérants — un fichier
absent, tronqué, non UTF-8 ou remplacé par un dossier y vaut « rien à lire » (règle écrite deux fois dans
le code : `utils/session.py` et `cogs/mouse_finder.py`, passes 44e bis et suivantes). Les deux autres ne
l'étaient pas, et le défaut ne se voyait pas au même endroit selon le fichier :

| Fichier | Ce qui se passait avant le 2026-10-13 | Ce que le membre recevait |
|---|---|---|
| `data/commercial_links.json` (C54) | un **fichier tronqué** (`JSONDecodeError`), un chemin qui est un **dossier** (`IsADirectoryError`), des droits refusés : l'exception remontait **après** le calcul, hors de la garde « catalogue illisible » — le chargeur ne prévoyait que le fichier absent et la mauvaise forme du JSON | « ⚠️ Une erreur inattendue est survenue. Rien n'est perdu : refaites l'action… » — alors que la recommandation était déjà calculée, et que « refaire l'action » ne pouvait pas aboutir tant que le fichier restait cassé |
| `assets/images.json` (C55) | un **octet non UTF-8** (`UnicodeDecodeError`) : la garde du chargeur couvrait le JSON invalide et les erreurs d'E/S, mais pas le décodage du texte. Ce chargeur est appelé par **chaque** étape (bannière, illustrations) | « ⚠️ Une erreur inattendue est survenue » **dès le premier message** : le test ne pouvait pas démarrer du tout |

Pourquoi ces deux fichiers peuvent réellement être abîmés : ils sont modifiés **à la main** (prix, liens,
images) et transférés par FTP vers le serveur — un transfert interrompu, un fichier enregistré dans un
autre encodage (Latin-1, UTF-16) ou un dossier téléversé à la place du fichier produisent exactement ces
erreurs-là. Un fichier **absent** était déjà sans effet : c'est l'asymétrie, et non l'hypothèse, qui était
le défaut.

La correction est la règle de la maison, appliquée aux deux chargeurs : **`OSError` et `ValueError`**
couvrent tout ce qu'un fichier peut subir (`ValueError` inclut `JSONDecodeError` **et**
`UnicodeDecodeError`), l'erreur est journalisée, et le parcours continue. Concrètement :

- liens d'achat illisibles → le résultat s'affiche **entier**, les boutons cèdent la place au rappel
  désactivé « Liens à venir » (comportement qui existait déjà pour une souris sans lien) ;
- images illisibles → les étapes et le résultat s'affichent **sans image** (comportement qui existait déjà
  pour une clé d'image vide) ;
- dans les deux cas, le journal du bot porte la cause exacte (`Fichier de liens illisible (… : Is a
  directory)`, `Configuration d'images illisible (… : 'utf-8' codec can't decode byte 0xff…)`).

Preuves — le défaut est reproduit avant correction, et la garde retirée refait tomber les verrous :

| Contrôle | Avant correction | Après correction |
|---|---|---|
| `tests/test_flow.py::test_un_fichier_de_liens_casse_ne_prive_pas_le_membre_de_son_resultat` | `JSONDecodeError` non gérée (résultat jamais affiché) | résultat entier + « Liens à venir » |
| `tests/test_data.py::test_un_fichier_de_liens_illisible_est_ignore_comme_un_fichier_absent` | tronqué / non UTF-8 / dossier : exception | `{}` dans les trois cas |
| `tests/test_flow.py::test_un_fichier_d_images_illisible_ne_bloque_pas_la_premiere_etape` | `UnicodeDecodeError` : étape 1 inaccessible | étape 1 affichée, sans bannière |
| `tests/test_catalog_hardening.py::test_un_fichier_d_images_illisible_n_empeche_pas_le_parcours` | non UTF-8 : exception | aucune image dans les trois cas |
| Reproductions directes avant correction | `load_commercial_links` → `JSONDecodeError` / `IsADirectoryError` ; `load_image_urls` → `UnicodeDecodeError` | — |
| Mutations (garde retirée, puis restaurée) | — | C54 : **2 échecs** → 2 passed ; C55 : **2 échecs** → 2 passed |

**Ce qui n'a pas changé** : aucun calcul, aucune donnée, aucun texte affiché dans le cas normal — la
sortie d'un parcours complet est identique (mêmes souris, mêmes pourcentages, mêmes prix). Seuls les
chemins de panne changent. `pytest -q` : **628 passed** · `pyflakes` : 0 · `tools/privacy_scan.py` :
0 violation.

### 26.24 Un lien plus long que la limite de Discord faisait perdre le résultat (C56)

C40 avait appris au chargeur de liens à écarter une adresse **inutilisable** dans un bouton — schéma
absent, espace, tabulation, saut de ligne, caractère de contrôle : Discord refuse alors le composant, et
c'est le **message entier** qui échoue. Il restait un cas que ce contrôle ne voyait pas : la **longueur**.
La référence des composants de Discord borne le champ `url` d'un bouton de style lien à **512 caractères**
(le libellé, lui, à 80 — déjà borné côté affichage par `BUTTON_LABEL_MAX`). Au-delà, Discord refuse le
composant de la même façon : le membre lit « ⚠️ Une erreur inattendue est survenue » au lieu de ses souris.

Le cas n'est pas théorique : les liens du catalogue sont des liens de boutique, souvent copiés depuis un
navigateur ou un tableau d'affiliation — une URL de suivi collée telle quelle dans
`data/commercial_links.json` dépasse facilement 512 caractères, et **rien** ne le signalait : le fichier
était valide, tous les tests passaient, et la panne n'apparaissait qu'au moment où cette souris-là était
recommandée, pour un seul membre et un seul profil.

La règle retenue est celle de C40/C54 — **écarter ce seul lien, jamais le résultat** — appliquée à la
longueur, sur la valeur en caractères telle que Discord la compte :

| Contrôle | Résultat |
|---|---|
| `tests/test_data.py::test_un_lien_trop_long_pour_discord_est_ecarte_et_les_autres_survivent` | 512 caractères **accepté** (limite exacte), 513 écarté, les autres liens du même fichier conservés |
| Mutation (garde de longueur retirée) | **1 échec** · restauré → 1 passed |
| Les 36 liens du catalogue | tous **bien en dessous** de la limite (le plus long fait moins d'un dixième des 512 caractères) : aucune donnée n'est écartée par cette règle aujourd'hui |

Le membre dont la souris a un lien trop long voit le rappel désactivé « Liens à venir » à la place du
bouton, et l'administrateur lit la raison exacte dans les journaux
(`Lien ignoré pour <souris> : URL invalide`). Aucun autre comportement ne change : le lien écarté n'est
jamais remplacé ni raccourci — une adresse tronquée mènerait ailleurs, ce que le projet s'interdit.
`pytest -q` : **629 passed** · `pyflakes` : 0.

### 26.25 Une traçabilité qui affirmait plus que l'audit, et un invariant de bosse non vérifié (C57)

**a) Deux libellés disaient « un seul moule » là où l'audit dit « rien ne le prouve encore ».** La passe
précédente (§26.22) a fait déclarer le partage de coque par une source, sur chaque entrée concernée. Pour
la paire `atk_x1` (ATK X1 V2 Ultra Max ↔ VXE Dragonfly X3), le libellé écrit alors concluait « un seul
moule » — alors que le **constat n° 12** de `docs/audit/AUDIT.md` dit exactement le contraire : la X3
partage les **cotes** (127 × 64 × 40 mm) mais ni sa bosse ni sa hauteur de boutons ne lui sont propagées,
parce que la bosse de l'X1 est elle-même contestée (« Back - minimal » chez EloShapes contre « Mid » du
propriétaire) et que **rien ne prouve encore que la X3 reprend la même pièce de plastique**. Les deux
libellés sont réécrits pour dire ce que le catalogue dit réellement (« coque de la famille X1 », deux
entrées jamais proposées ensemble, valeurs non propagées, renvoi au constat n° 12).

Pour que l'ensemble parle la même langue, les **six autres libellés** qui concluaient « un seul moule »
(GHOST Ultimate, U2 Mini, les deux X2 Mini, les deux X2H Mini) ont été ramenés à la **règle écrite du
catalogue** — « coque partagée (règle du catalogue : cotes publiées identiques, deux entrées jamais
proposées ensemble) ». Les deux libellés qui gardent « un seul moule » (coque A9 pleine taille, coque F1)
sont ceux où le catalogue **propage réellement des valeurs** entre jumelles (§14.2) : là, l'unicité du
moule est la base même de la propagation.

Pourquoi c'est signalé alors qu'aucun membre ne le voit : un libellé de source **est** l'enregistrement de
traçabilité. Un test peut vérifier qu'un fait est **déclaré** ; aucun test ne peut vérifier qu'une
déclaration est **vraie**. Une affirmation plus forte que ce que la source établit est donc un faux
témoignage silencieux — la seule façon de le trouver est de confronter les deux documents, ce qui est
fait ici. Les valeurs du catalogue, elles, n'ont pas changé (la X3 reste « à vérifier », jamais
recommandée).

**b) La bosse d'une coque n'était surveillée par aucun test.** L'invariant « deux entrées d'une même coque
ne peuvent pas annoncer deux hauteurs de boutons » existait (`test_no_shell_mixes_two_button_heights`) ;
son jumeau pour la **position de la bosse** n'existait pas. Le catalogue est conforme aujourd'hui (les
sept coques partagées hors exception sont alignées), mais rien n'aurait signalé une dérive — ni deux
bosses différentes, ni une jumelle laissée « Inconnu » alors que l'autre publie sa bosse (cas qui, lui,
produit un score partiel injustifié et deux conseils différents pour la même pièce de plastique).
`tests/test_data.py::test_aucune_coque_ne_melange_deux_bosses` comble le trou, avec la même exception
documentée que les boutons (VXE X3) et un garde-fou d'inventaire (au moins huit coques examinées).

| Contrôle | Résultat |
|---|---|
| Catalogue, 8 coques partagées | **conforme** : aucune divergence de bosse hors l'exception documentée |
| Mutation A — une jumelle de la coque A9 annonce « Rear » | **1 échec** · restauré → 1 passed |
| Mutation B — une jumelle Pulsar laisse sa bosse « Inconnu » | **1 échec** · restauré → 1 passed |
| `tests/test_data.py` | **93 passed** (+1 cas) |
| `pytest -q` · `pyflakes` · `tools/privacy_scan.py` | **630 passed** · 0 · 0 violation |

### 26.26 Passe guidée par la couverture : 90 lignes ramenées à 11, dont aucune sans raison (2026-10-13)

La consigne « perfectionner la totalité du code » a été traitée par la **mesure**, pas par l'impression :
couverture en processus des quatre paquets du bot (`coverage run --source=bot,config,cogs,utils -m pytest`).
État de départ : **95 %** — 1 667 instructions, **90 lignes jamais exécutées par les 630 tests**, dont
**67 % pour `bot.py`** et **82 % pour `cogs/mouse_finder.py`**, les deux modules les moins couverts du
dépôt. Les 90 lignes ont été lues une par une : ce sont presque toutes des **chemins d'échec** (message
d'erreur, repli, garde) et non du code mort — c'est-à-dire exactement les endroits qu'un membre ou un
administrateur voit le jour où quelque chose va mal, et que rien ne vérifiait.

**a) Les chemins d'échec du parcours (`cogs/finder_flow.py`, 95 % → 99 %).** Quatorze tests ajoutés dans
`tests/test_flow.py` :

| Garantie verrouillée | Ce qui se passerait sans elle |
|---|---|
| Un prix absent s'affiche « prix non renseigné » | Ligne de prix vide, ou montant inventé |
| Sans candidat classable : conseil concret (« autre gamme ou budget plus élevé ») | Le membre reste sur un écran vide |
| Catalogue illisible entre deux clics : « momentanément illisibles » + quoi faire | « erreur inattendue », ou résultat vide |
| Parcours incomplet (redémarrage) : reprise **à l'étape manquante** | Tout recommencer, ou écran figé |
| Interaction déjà répondue : édition par la réponse d'origine, sinon message de suivi | Second message en double, ou clic muet |
| Message supprimé par le membre : nouveau message privé | Le parcours s'arrête sans rien dire |
| `_show_private` et `_send_ephemeral` ne lèvent **jamais** | Erreur technique au milieu d'une interaction |
| Variante de Claw, thénar ou plafond de budget cliqués **hors parcours** | Clic sans réponse (trois composants) |
| Sans gamme choisie : « Classement morphologique », aucun budget affiché | Le récapitulatif invente une gamme |
| Parcours incomplet : aucun repère de taille ni conseil de boutons inventé | Un conseil fondé sur des mesures par défaut |
| Titre de la 2e place quand la règle du moteur n'est pas fournie | « Autre piste » sans raison, ou plantage |
| Un seul bouton d'achat par souris, même si elle est affichée deux fois | Deux boutons identiques dans le message |

**b) La commande d'administration (`cogs/mouse_finder.py`, 82 % → 100 %).** Cinq tests ajoutés dans
`tests/test_setup_command.py` : `!setup_finder #salon` (l'argument explicite était le **seul** chemin de la
commande jamais exécuté), refus d'un salon non textuel (rien n'est publié, aucun état enregistré),
verrouillage impossible (le salon reste ouvert **et c'est dit**, la publication a bien lieu), bot sans droit
d'écriture (cause exacte, aucun état écrit, jamais « publié »), et les **quatre branches** du gestionnaire
d'erreur (permission, serveur requis, salon invalide, erreur inattendue).

**c) Le démarrage (`bot.py`, 67 % → 91 %).** Nouveau fichier `tests/test_bot_runtime.py`, cité dans le
README : purge périodique des parcours expirés (minimisation — rien ne s'accumule en mémoire ni dans le
fichier d'état) et son **silence** quand rien n'a expiré, erreur d'événement journalisée sans arrêter le bot,
commande inconnue **totalement muette** (règle de confidentialité : une faute de frappe ne publie rien et ne
laisse aucune trace), erreur de commande réelle tracée sans rien publier dans le salon, message de connexion
(compte, parcours en cours, emplacement du stockage), démarrage refusé sans jeton avec message lisible, et
chemin de démarrage normal.

**d) Les contrats de conservation du parcours (`utils/session.py`, 95 % → 99 %).** Quatre tests ajoutés dans
`tests/test_session.py` et `tests/test_privacy.py` :

- **aller-retour complet** `to_state` → `from_state` : tout ce qui est écrit se relit, **variante de Claw
  comprise** — c'était le seul champ de réponse jamais vérifié en boucle, alors qu'il s'affiche dans le
  récapitulatif et dans le guide de bosse ; le retirer de `from_state` aurait fait perdre une réponse du
  membre au redémarrage sans qu'un seul test bronche ;
- **fichier d'état bricolé à deux parcours vivants du même membre** : un seul reste actif, l'autre est
  refusé (jamais un mélange), relancer efface **les deux**, et supprimer l'actif promeut celui qui reste —
  trois chemins (l.353-354, 360, 365) qu'aucune épreuve ne traversait ;
- **`finish` sur un identifiant inconnu** (parcours expiré, bot redémarré, clic tardif) : aucun effet, jamais
  d'exception ;
- **effacement complet des parcours d'un membre** (`discard_user`) : c'est la seule porte d'effacement total
  et l'écriture sur disque qui va avec. Elle n'est appelée nulle part dans le bot aujourd'hui : plutôt que
  de la supprimer, elle est **verrouillée** — un futur « supprimez mes données » ne doit pas la réécrire de
  travers, et elle ne touche jamais un autre membre.

**e) Les gardes du catalogue et des images (`utils/catalog.py` et `utils/assets.py`, 96 % et 95 % → 100 %).**
Quatre formes de catalogue abîmé refusées avec leur message (forme inconnue, statut de prise inconnu,
largeur maximale absente, forme renseignée sans source) et la racine qui n'est pas une liste ; côté images,
l'absence de `config` importable (module utilisé hors du projet) et une entrée vide ou blanche ne produisent
aucune image, jamais d'exception.

**f) Un ménage : quatre accesseurs sans appelant.** `BudgetMode.label`, `Thenar.label`, `ClawVariant.label` et
`Mouse.is_price_known` n'étaient appelés **nulle part** (vérifié sur tout le dépôt, outils et tests compris) :
les trois premiers doublonnaient un dictionnaire que le flux lit directement (`THENAR_LABELS[...]`), le
quatrième répétait `price_eur is not None`. Retirés — un accesseur mort est un piège : il laisse croire
qu'une valeur affichée passe par lui. Aucune valeur, aucun affichage, aucun score ne change.

**g) Ce qui reste non couvert, et pourquoi c'est assumé.** Onze lignes, chacune avec sa raison :

| Lignes | Pourquoi elles restent non exécutées en processus |
|---|---|
| `bot.py` 32-35 et 108 | Configuration invalide et `__main__` : exercés par `tests/test_config.py`, qui lance `bot.py` dans un **vrai sous-processus** — hors de portée d'une mesure en mémoire |
| `config.py` 83, 93 | Les deux gardes de démarrage (`FINDER_CHANNEL_ID` négatif, délai nul) : même mesure, même sous-processus |
| `cogs/finder_flow.py` 461, 463 | Branches « thénar ± » du texte d'explication : **mortes tant que le thénar vaut 0/0/0** — le moteur n'est touché que sur demande explicite du propriétaire (master prompt) |
| `utils/selection.py` 128 · `utils/session.py` 360 | Gardes défensives (la même souris deux fois dans le vivier, suppression d'un identifiant inconnu) : inatteignables tant que les invariants du catalogue et du magasin tiennent — et **ce sont ces invariants que des tests vérifient** désormais |

Aucune ligne du moteur, du catalogue ou des données n'a été modifiée par cette passe : aucune recommandation
ne change.

| Mesure | Avant | Après |
|---|---|---|
| Lignes non exécutées | **90** | **11** |
| Couverture totale (`bot`, `config`, `cogs`, `utils`) | 95 % | **99 %** |
| `bot.py` | 67 % | **91 %** (32-35, 108 : sous-processus) |
| `cogs/mouse_finder.py` | 82 % | **100 %** |
| `cogs/finder_flow.py` | 95 % | **99 %** |
| `utils/session.py` | 95 % | **99 %** |
| `utils/catalog.py` · `utils/assets.py` | 96 % · 95 % | **100 %** · **100 %** |
| `utils/models.py` | 96 % | **100 %** (4 accesseurs morts retirés) |
| `utils/matcher.py` · `utils/validation.py` | 100 % · 100 % | 100 % · 100 % |
| Tests | 630 | **673** |
| Mutations (garanties nouvelles) | — | **41 mutations : 1 échec chacune**, fichiers restaurés |
| `pyflakes` · `tools/privacy_scan.py` | 0 · 0 | **0 · 0** |

Deux mutations ont d'abord été **écartées** parce qu'elles ne prouvaient rien : la suppression d'une ligne
d'affectation casse l'indentation (erreur de syntaxe, pas de comportement), et une mutation de boucle est
passée inaperçue tant que le test ne couvrait pas le cas « deux parcours vivants » — c'est le test qui a été
corrigé, puis la mutation a échoué comme les autres.

### 26.27 Un message qui accusait le catalogue (2026-10-13, C59)

La carte « Aucun match classable » — elle s'affiche pour **4 082 profils sur 27 170** (15,0 %, §25) —
disait : « Aucune souris ne peut être **classée avec les données vérifiées** pour ces critères. » Or, dans
les trois situations réelles où elle apparaît, le catalogue n'est pour rien :

| Situation mesurée le 2026-10-13 | Ce qui bloque vraiment |
|---|---|
| Mesures hors de la plage des 36 souris (260 × 130 mm, 100 × 50 mm) | Aucune souris n'est morphologiquement compatible |
| Budget trop serré (140 × 60 mm en Palm, plafond 10 €) | Des souris **sont** classables ; aucune n'est sous 10 € |
| Gamme sans candidat (aucun gant dans la gamme choisie) | La gamme, pas les données |

Le membre lisait donc une explication fausse : au mieux il attendait une correction de données qui ne
viendrait jamais, au pire il croyait le bot incomplet. Le texte nomme maintenant ce que **lui** a fourni —
« Aucune souris ne peut être retenue avec ces critères. » — suivi du même conseil (autre gamme, budget plus
élevé). Aucune donnée, aucun score, aucun classement ne change ; seule la phrase change.

Verrou dans `tests/test_flow.py::test_le_message_sans_candidat_n_accuse_pas_le_catalogue` : les deux
situations réelles sont exercées, le test exige la phrase nouvelle **et** le conseil, et **refuse les mots
qui accusent le catalogue** (« données vérifiées », « illisible », « non vérifiée », « à vérifier »). Deux
mutations — retour à l'ancien texte, conseil supprimé : **1 échec chacune**, fichier restauré.

Ce que ce contrôle ne peut pas faire : juger une phrase qu'il ne connaît pas. Le test fixe le texte actuel ;
toute reformulation ultérieure devra être relue, pas devinée.

### 26.28 Un tableau du README décrivait deux fois la même clé d'image (2026-10-13, C60)

Le tableau « Clé / Affichée à / Illustration livrée » du README portait **deux lignes** pour
`illustration_grip_relaxed`, avec deux textes différents (« Étape « variante de Claw » et résultat (variante
relâchée) » et « Résultat, prise Claw — variante « Claw relâchée » »). L'exploitant qui personnalise ses
illustrations ne savait plus laquelle était la bonne, et l'autre clé n'était décrite qu'une fois par chance :
une clé ajoutée à `assets/images.json` pouvait rester invisible.

Le code dit la vérité une seule fois : `claw_variant_step_embed()` (l'étape « Votre variante de Claw »)
affiche `illustration_grip_relaxed`, et `_claw_variant_embeds()` la réutilise dans le résultat **quand la
variante déclarée est « Claw relâchée »** — d'où la ligne unique, réécrite en une phrase. Les deux autres
variantes (agressive, pincée) n'apparaissent que dans le résultat, comme le tableau le dit déjà.

Verrou : `tests/test_doc_references.py::test_le_tableau_des_images_du_readme_decrit_chaque_cle_une_seule_fois`
— il compare le tableau à `assets/images.json` **dans les deux sens**, exige une seule ligne par clé, et
vérifie que le fichier cité existe dans `assets/illustrations/` (et qu'une clé vide est bien annoncée « vide »).
Quatre mutations — clé décrite deux fois, clé du fichier absente du tableau, fichier cité inexistant, clé
pourvue annoncée « vide » : **1 échec chacune**, fichier restauré.

### 26.29 Le rapport statistique du dépôt est reproductible — et le contrôle rapide ne l'écrase plus (2026-10-13, C61)

Le rapport `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` (grille complète, **18 522 profils**) est
un artefact de mesure : il est régénéré par `tools/recommendation_stats.py`, jamais édité à la main. Deux
vérifications faites le 2026-10-13 :

- **Reproductibilité au caractère près.** `python tools/recommendation_stats.py --sortie /tmp/stats.md`
  (grille complète) puis `diff` contre le fichier du dépôt : **aucune différence**. Les chiffres publiés
  correspondent donc exactement au catalogue et au moteur du jour — la commande `--sortie` permet de le
  vérifier **sans** toucher au dépôt.
- **Le contrôle rapide n'écrase plus le rapport de référence.** Le module proposait `--rapide` sans
  `--sortie` dans son exemple d'usage : suivre l'exemple remplaçait le rapport de référence par un rapport
  de **420 profils**, sans avertissement — l'artefact publié devenait un autre document, sous le même nom.
  `--rapide` avec le chemin par défaut sort désormais en **code 2** avec une phrase qui dit quoi faire
  (`--sortie /tmp/stats_rapide.md`) ; un `--sortie` explicite reste accepté, y compris le chemin du dépôt.

Verrou : `tests/test_tools_usage_errors.py::test_rapide_n_ecrase_pas_le_rapport_statistique_du_depot` — il
lit le rapport avant, lance `--rapide`, vérifie le code 2, la phrase sur la sortie d'erreur, **et que le
fichier n'a pas bougé** ; puis il vérifie que le contrôle rapide écrit bien son rapport ailleurs. Une mutation
(garde retirée) : **1 échec**, fichier restauré.

### 26.30 « Ces liens ouvrent-ils vraiment le modèle annoncé ? » — le contrôle devient un outil (C62, 2026-10-13)

Demande du propriétaire (2026-10-13) : « vérifie si les liens que je t'ai envoyés correspondent bien au
modèle », puis « mets à jour les prix sur tous les modèles ». La relecture avait déjà été faite à la main
le matin même (37e passe, six prix). Elle a été refaite l'après-midi, **lien par lien**, avec la méthode la
moins coûteuse par boutique — `products/<handle>.json?country=FR` donne toutes les variantes et leurs prix
en euros, `variants/<id>.json?country=FR` donne **la** variante que le bouton ouvre.

**Ce que la relecture a changé** (le détail daté est le §8 de
`docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`) :

1. **Quatre noms de modèles ne se retrouvaient pas sur la page ouverte** — c'est le cœur de la question.
   « A9 Plus 2.0 » n'existe pas (la série A9 vend « A9 SE », « A9 », « A9 Plus », « A9 Pro », « A9 Pro
   Max », « A9 Ultra ») ; « Z1 V2 Ultra » non plus (la page vend « Ultimate » et « Ultimate+ ») ; « F1 V3
   Ultimate » non plus (elle vend « Ultimate+ » et « Extreme+ ») ; « X1 V2 Ultra Max » désigne en fait
   « X1 V2 Ultra Max **2.0** ». Le membre qui cherchait sur la page le nom affiché par le bot ne le
   trouvait pas. **Corrigé dans `data/mouse_db.json`**, donc dans les six endroits qui l'affichent.
2. **Deux prix** : l'**A9 Plus** publiait 45,00 € (cahier des charges, non daté) alors que la variante que
   son bouton ouvre — « A9 Plus / White » — est vendue **27,95 €** (prix normal 36,95 €) ; l'**A9 NB** est
   passé de 73,95 € à **72,95 €** dans la journée. Les 32 autres prix sont **identiques** au relevé du
   matin.
3. **Une note qui ne décrivait pas ce que le bouton ouvre** (A9 Air : « Shadow White », un coloris de
   revendeur, alors que le lien fige « Air / Black ») et **une note qui affirmait plus que le lien ne
   faisait** (F1 V2 : « celle que le bouton d'achat ouvre », alors qu'aucune variante n'était figée — la
   fiche vend trois éditions, 41,95 € / 54,95 € / 77,95 €). Le lien de la F1 V2 est désormais **figé** sur
   la variante vendue : le prix publié et l'édition achetée sont la même.
4. **Deux traces qui se contredisaient** : la source du 2026-10-13 de l'A9 Plus disait encore « prix du
   catalogue NON adopté (45,00 €) » une fois le prix adopté, et cinq libellés de source disaient
   « relevé du 2026-10-13 … inchangé depuis le relevé du 2026-10-13 » — un relevé comparé à lui-même ne
   prouve rien ; la comparaison portait sur la veille.

**Le contrôle est devenu un outil** : `tools/check_links.py` ouvre, pour chaque souris, la fiche de la
boutique (`products/<handle>.json?country=FR`, ou la variante figée), et compare le prix affiché au prix
publié. Trois sorties distinctes, parce que les confondre ferait mentir l'outil : **0** tout concorde,
**1** au moins un écart, **2** rien n'a pu être vérifié (réseau bloqué, boutique indisponible, lien
inexploitable) — un réseau qui bloque les boutiques n'est pas un catalogue faux. Une fiche en dollars
(Scyrox) est signalée « hors comparaison » et **aucune conversion n'est faite**.

**Le test a rattrapé un bug de l'outil lui-même**, et c'est le meilleur argument pour l'avoir écrit :
`Verdict.echec` comparait la phrase entière (« ❌ variante introuvable — variante absente de la fiche ») à
la liste des statuts d'échec, et le statut **composé** n'y figurait pas — l'outil aurait rendu **0** sur une
variante disparue. Le statut est maintenant stocké **à part** du détail.

**Ce que le test verrouille** : `tests/test_liens_achat.py` (17 cas) relit le tableau §8.1 dans les deux
sens — chaque lien doit ouvrir le handle annoncé et figer la variante annoncée (ou aucune), chaque prix
publié doit être celui de la fiche et chaque prix hors euros doit être justifié dans la note — et essaie
l'outil **hors réseau** sur une fausse boutique (cohérent, variante disparue, prix changé, fiche en
dollars, réseau bloqué, lien bricolé, souris inconnue) — plus un verrou des **quatre noms de modèles**
relevés sur la boutique, et un contrôle du **résumé** (« 0 écart » ne doit pas cacher des fiches
injoignables). Dix mutations (statut d'échec retiré, devise ignorée, variante ignorée, code de sortie
neutralisé, tableau §8.1 faussé sur la variante, sur le prix, sur le handle, nom « A9 Plus 2.0 » réintroduit,
résumé qui ne compte plus les fiches injoignables) : **1 échec chacune**, fichiers restaurés à l'octet près.

**Limites dites franchement** : l'outil a besoin de joindre les boutiques — depuis le bac à sable de
développement (réseau restreint) il sort en **2** avec la phrase « le contrôle n'a pas eu lieu », il ne
produit aucun verdict ; et le format `products/<handle>.json` **ne porte pas la disponibilité**, qui reste
constatée à part (MAD R épuisée, Xlite v4 Medium et Large épuisées, Xlite v4 Mini en stock…).

### 26.31 La couverture atteint 100 % — ce que les onze dernières lignes cachaient (C63, 2026-10-13)

Le §26.26 avait ramené les lignes non mesurées de 90 à **11**, et les avait toutes justifiées (chacune
était « soit dans un vrai sous-processus, soit morte tant que le thénar est en pause »). Une justification
n'est pas une couverture : les onze lignes ont été mesurées une par une, et **deux défauts réels sont
apparus en le faisant**.

1. **`bot.py` 32-35 (configuration invalide) et 108 (`__main__`)** et **`config.py` 83, 93 (les deux
   bornes)** : ces lignes n'étaient exécutées que dans un **sous-processus** (`tests/test_config.py`
   lance `bot.py` comme un vrai script) — un vrai test, mais que la mesure en mémoire ne voit pas.
   Elles sont désormais **rejouées dans le processus de test** : `runpy.run_path("bot.py",
   run_name="__main__")` avec une **configuration relue de l'environnement** (le module `config` est
   retiré du cache puis rechargé, et remis en place après le test). Deux cas : jeton vide → phrase
   « DISCORD_TOKEN est vide » + code 1 ; `SESSION_TTL_SECONDS=0` → « Configuration invalide —
   SESSION_TTL_SECONDS doit être supérieur à 0 » + code 1. Le vrai sous-processus reste testé.
2. **Le défaut trouvé là, et corrigé** : sur les quatre messages de `config.py`, celui de
   `FINDER_CHANNEL_ID` était **le seul** à ne pas dire où corriger (pas de « Corrigez-la dans le fichier
   `.env`. ») ni à rappeler que **0 = le salon où la commande est tapée** — l'exploitant lisait « doit
   être un identifiant positif » sans savoir quoi mettre. Message aligné sur les trois autres.
3. **`cogs/finder_flow.py` 461, 463 (les deux phrases du thénar)** : mortes tant que le barème du thénar
   est à **0/0/0** (décision du propriétaire : thénar en pause). Un test fabrique maintenant un barème et
   distingue **trois** cas : thénar défavorable (la phrase s'affiche), favorable (elle doit tenir dans les
   trois « points forts » que le bilan garde — c'est la règle de concision), **neutre** (aucun mot sur le
   thénar). Observation consignée : le bilan ne garde que **trois** points forts, donc un thénar favorable
   arrivé **quatrième** resterait muet ; sans effet aujourd'hui (thénar à zéro), à revoir le jour où le
   barème thénar est réactivé — **le moteur n'est pas modifié sans demande du propriétaire**.
4. **`utils/selection.py` 128** : `_same_shell` se décide d'abord sur l'**identifiant** (même souris deux
   fois — le garde-fou né du bug « l'alternative = la même souris »). Couverte par un test unitaire, y
   compris le cas d'une souris **sans** coque partagée renseignée.
5. **`utils/session.py` 360** : `_remove` sur un identifiant **inconnu** (clic rejoué sur un parcours déjà
   retiré, purge concurrente) doit être ignoré en silence, sans toucher au parcours vivant d'à côté.

**Mesure** : `.venv/bin/python -m coverage run --source=cogs,utils,bot,config -m pytest -q` puis
`coverage report -m` → **1 655 instructions, 0 non exécutée (100 %)**, 704 tests verts. C'est la première
fois que le dépôt n'a plus aucune ligne non mesurée dans son périmètre.

**Vérifié par mutation** — six cas, un par garantie ajoutée (message de `FINDER_CHANNEL_ID` privé de sa
consigne, point d'entrée qui ne traduit plus l'erreur de configuration, `main()` retiré du bloc
`__main__`, les deux phrases du thénar échangées, `_same_shell` qui ne reconnaît plus le même identifiant,
`_remove` qui ne tolère plus un identifiant inconnu) : **1 échec chacun**, fichiers restaurés à l'octet
près.

**Limites dites quand même** : la mesure est **en cours de processus**. Ce qui n'y est pas mesurable le
reste : une vraie connexion Discord (`MouseBot().run()` est simulé : jeton et classe remplacés), et les
outils (`tools/`) qui ont leur propre contrat, testé par `tests/test_tools_usage_errors.py`. Le vrai
démarrage en sous-processus, lui, continue d'être vérifié par `tests/test_config.py`.

## 26.32 48e passe — les chiffres recourants et quatre noms publiés (2026-10-13)

### 26.32.1 Deux mesures citées comme « recourantes » ne suivaient personne

Le master prompt, le déploiement et l'audit publiaient deux mesures qui **bougent avec les prix** du
catalogue, figées à la 35e passe :

| Mesure | Valeur écrite | Valeur du 2026-10-13 (48e passe) |
|---|---|---|
| Places portant « (prix non vérifié) » | 4 373 (16,09 % des 27 170 profils) | **3 332 (12,26 %)** |
| Profils où l'ordre des pourcentages n'est pas garanti | 84 (0,31 %), puis 70 (0,26 %) à la 37e | **28 (0,10 %)** |

Ce n'est pas une erreur de mesure : ces deux chiffres **dépendent des prix et du nombre de souris non
attestées**. Entre la 35e et la 48e passe, l'**A9 Plus est passée de 45,00 € (prix du cahier des charges) à
27,95 € attestés** sur la boutique officielle (47e passe). Moins chère, elle entre dans des fenêtres de
budget où le plafond de score ne laissait auparavant **aucun** candidat — d'où 84 → 70 → **28** profils —, et
elle ne porte plus le marqueur de prix non attesté : il ne reste que la **Scyrox V6**, dont la boutique vend
en dollars (jamais convertis).

**Ce qui a changé dans l'outillage** : `tools/qa_flow_matrix.py` *vérifiait* le marqueur place par place
(« prix non vérifié affiché sans le dire ») mais ne le **comptait** pas — le chiffre publié venait donc d'un
relevé manuel. Il le compte désormais (`places_au_prix_non_verifie`, fonction pure, un test dans
`tests/test_qa_flow_matrix.py`, une mutation → 1 échec) et l'affiche : « Places portant « (prix non
vérifié) » : … ». Les documents datent leur chiffre et renvoient à cette sortie.

**Mesure de la passe** (`python tools/qa_flow_matrix.py`, grille complète, 1 min 33) : 27 170 profils,
**0 problème**, trois places dans 23 140 profils (85,17 %), marqueur de prix **3 332 places (12,26 %)**,
ordre non garanti **28 profils (0,10 %)**, replis de coque 1 136 profils, match idéal partiel 3 109.

### 26.32.2 Quatre libellés périmés traînaient dans les documents de travail

Le tri des noms publiés (boutique ⇄ cahier des charges) avait été fait dans `README.md` et dans
`tests/test_compare_profiles.py` ; deux documents **de travail** portaient encore les anciens :

- `docs/LISTE_LIENS_SPONSORISES_2026-10-11.md` : « F1 V3 Ultimate », « X1 V2 Ultra Max », « Z1 V2 Ultra »
  et « A9 Plus 2.0 » → **« F1 V3 Ultimate+ », « X1 V2 Ultra Max 2.0 », « Z1 V2 Ultimate », « A9 Plus »**,
  et la gamme U2 complétée (« Blazing Sky U2 / U2 Plus / U2 Ultimate »). C'est la liste qui sert à
  **fabriquer les liens** : un libellé qui n'existe pas sur la boutique y est un défaut, pas une archive.
- `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` §2 : **instantané daté** (« état des liens au
  2026-10-11 ») — il n'est **pas réécrit** ; une ligne ajoutée sous le tableau dit quels noms ont été
  alignés depuis et renvoie au §8.3.

Restent volontairement en l'état les **journaux datés** (`docs/audit/…`, `RECHERCHE_PRIX_EUR_…`,
`REPORTE_DESIGN.md`, `docs/audit/matrice_profils.md`) et les **libellés de sources** de
`data/mouse_db.json`, qui doivent reproduire le titre exact du revendeur.

## 26.33 49e passe — la liste de travail envoyait sur l'ancienne page de deux souris (2026-10-13)

### 26.33.1 Le défaut

La relecture des liens (47e passe) avait recâblé deux souris sur la page **U2 V2** — c'est la fiche que
leur bouton ouvre depuis la correction du §3 (point 6) de `VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` —
l'inventaire du §8.1 la relit lien par lien :

| Souris | Page corrigée | Ancienne page |
|---|---|---|
| `atk_u2_v2_ultimate` | `atk-blazing-sky-u2-v2-superlight-wireless-gaming-mouse` | `atk-blazing-sky-u2-series-wireless-mouse` |
| `atk_u2_v2_mini` | `atk-blazing-sky-u2-v2-superlight-wireless-gaming-mouse` | `atk-blazing-sky-u2-mini-superlight-wireless-gaming-mouse` |

Les deux documents d'audit portent la bonne page (`VERIFICATION` §8.1, `LIENS_AFFILIES_2026-10-12.md` :
comparaison automatique, **0 écart**). Mais `docs/LISTE_LIENS_SPONSORISES_2026-10-11.md` — la liste qui sert
à **fabriquer** les liens, la première qu'on ouvre pour ajouter une souris au fichier des liens — donnait
encore l'ancienne page pour ces deux-là. Conséquence concrète : un lecteur qui reconstruisait le lien du
**U2 V2 Mini** à partir d'elle envoyait le membre sur la fiche du **U2 Mini** — un autre modèle, **77,95 €**
au lieu des **59,95 €** publiés.

**Pourquoi personne ne l'avait vu** : seul le tableau §8.1 était relu par un test
(`tests/test_liens_achat.py`), et il l'était dans les deux sens contre `data/commercial_links.json`. La
liste de travail, elle, n'était vérifiée que par relecture humaine — la même relecture qui avait corrigé les
liens sans repasser sur elle.

### 26.33.2 La correction

- Les lignes **12 à 15** de la liste sont recâblées sur les pages réellement installées, chacune disant sa
  variante figée (`47201864974554` pour la V2 Ultimate, `47204034150618` pour la V2 Mini) et le risque de
  confusion : « la page « U2 Mini » est le modèle **non-V2** », « le U2 V2, lui, a sa page dédiée ».
- Un test relit désormais la colonne « page produit » de la liste contre `data/commercial_links.json`
  (comparaison des **identifiants de fiche**, paramètres d'affiliation ignorés) : **26 lignes** exactement —
  si le tableau change de forme au point de ne plus être lu, le test le dit au lieu de passer à vide. Les
  dix Pulsar ne sont pas dans ce tableau (ils sont dans `docs/audit/LIENS_AFFILIES_2026-10-12.md`, lui aussi
  relu).
- **Mutation** : remettre l'ancienne page sur la ligne 12 → **1 échec**.

**Mesure** : 706 tests verts (un test de plus), `pyflakes` 0, `privacy_scan` 0 violation. Aucun fichier du
bot n'est touché : la liste de travail et un test.

### 26.33.3 Trouvé en chemin : une note de prix justifiée par une section qui n'existe pas

En relisant les renvois du document, la note de prix du **U2 V2 Mini** est apparue suspecte : elle justifie sa
correction par « `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md` **§6.6** ». Ce document n'a pas de §6.6 —
son §6 est l'addendum d'affiliation Pulsar, sans sous-section ; la réponse est au **§3 (point 6)** (« la
variante Mini s'affiche à 59,95 € sur la page FR, alors que la base porte 77,95 € »).

Pourquoi le défaut avait dormi : `tests/test_doc_references.py` relit les renvois « document + §numéro » de
tous les documents, tests, outils et modules — **pas des fichiers de `data/`**. Un renvoi mort y était donc
invisible. Corrigé, et le contrôle couvre désormais `data/*.json` avec la même règle, un test dédié qui refuse
de passer à vide (aucun fichier trouvé = échec, pas succès silencieux) — et une mutation le prouve.

**Mesure finale de la passe** : 707 tests verts, `pyflakes` 0, `privacy_scan` 0 violation. Fichiers à envoyer
sur le serveur : **`data/mouse_db.json`** (la note corrigée ; le fichier est relu à chaque interaction, aucun
redémarrage). Rien d'autre.

## 26.34 50e passe — les deux artefacts générés ne suivaient plus leur script (2026-10-13)

### 26.34.1 Le rapport statistique « de référence » était un rapport de grille resserrée

`docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` est décrit partout comme **l'artefact de
référence — grille complète, 18 522 profils** : le README le cite comme la source du tableau statistique, le
guide de déploiement le liste dans les fichiers à garder, et la correction C61 (46e passe) a été écrite pour
empêcher un `--rapide` de l'écraser.

Le fichier versionné, lui, était **un rapport de grille resserrée : 420 profils**, 44 fois moins, et il
portait encore quatre anciens noms de modèles (« ATK A9 Plus 2.0 », « ATK Z1 V2 Ultra », « ATK F1 V3
Ultimate », « ATK X1 V2 Ultra Max ») — donc **antérieur** à leur correction, alors que son en-tête annonçait
« rapport régénéré le 2026-10-13 sur le catalogue du même jour ». Le contrôle de C61 vérifiait que le fichier
**survivait** à un `--rapide` ; personne ne vérifiait qu'il était le bon rapport.

**Second défaut de la même famille** : `docs/audit/matrice_profils.md` — qui dit en toutes lettres « Ne pas
modifier à la main : relancer le script » — se déclarait « généré le 2026-10-13 » et portait les mêmes
anciens noms sur **34 lignes** : le script n'avait pas été relancé après la correction des quatre libellés.

### 26.34.2 Les deux artefacts sont régénérés, et deux tests les tiennent

| Artefact | Avant | Après (2026-10-13) |
|---|---|---|
| `STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` | 420 profils, anciens noms | **18 522 profils**, libellés à jour |
| `matrice_profils.md` | anciens noms sur 34 lignes | **identique à la sortie du script** |

Chiffres du rapport régénéré (grille complète, moteur réel) : **252 profils sans aucun résultat (1,4 %)** —
budget inférieur à la souris qui convient la moins chère —, **1 262 profils où deux places montrent la même
coque (6,8 %)** — repli documenté, paires `atk_a9_plus` + `atk_a9_ultimate` 786, `pulsar_x2_crazylight_mini`
+ `pulsar_x2_v3_mini` 210, `atk_f1_ultimate` + `atk_f1_v2` 164, `pulsar_x2h_crazylight_mini` +
`pulsar_x2h_v3_mini` 96, `atk_ghost_extreme` + `atk_ghost_ultimate` 6 —, 16 050 profils à trois places
(86,65 %), troisième place « ➕ L'autre option » 9 563 · « 💸 L'économie » 4 908 · « 🔎 Autre piste » 1 579.

**Les deux verrous** (`tests/test_tools_usage_errors.py`) :

- le rapport versionné doit annoncer le nombre de profils **compté** par le module
  (`sum(1 for _ in profiles(fast=False))`) — pas un chiffre recopié — et ne plus contenir les quatre anciens
  libellés ;
- la matrice versionnée doit être **égale à la sortie du script relancé** (`tools/compare_profiles.py`,
  0,3 s), les dates de génération mises de côté pour que le test reste valable les jours suivants.

**Mutations** : remettre « 420 profils » dans le rapport → **1 échec** ; remettre « ATK Z1 V2 Ultra » dans la
matrice → **1 échec**. **Mesure de la passe** : 709 tests verts, `pyflakes` 0, `privacy_scan` 0 violation.
Aucun fichier du bot n'est touché (deux documents générés, deux tests) : **rien à envoyer** sur le serveur,
les deux rapports sont des copies de référence si vous les voulez.

## 26.35 50e passe (suite) — l'aperçu du mode « Peu importe le prix » montrait un nom périmé (2026-10-13)

### 26.35.1 Le défaut

Les trois aperçus versionnés (`docs/apercu_parcours.png`, `docs/apercu_resultat.png`,
`docs/apercu_prix_libre.png`) servent à valider la mise en page **sans lancer le bot**. Le troisième
montrait encore « **Z1 V2 Ultra** » — un libellé qui n'existe plus depuis la correction du 2026-10-13 —,
et l'ancien nom apparaissait aussi dans un bouton d'achat.

Un document d'image ne se relit pas comme une ligne de texte : rien, dans la suite de tests, ne regardait
son contenu. Le fichier est régénérable en trois secondes — mais rien ne disait qu'il fallait le faire.

### 26.35.2 La correction : l'aperçu dit de quand il date

`tools/render_preview.py` inscrit désormais dans les **métadonnées PNG** de chaque aperçu une **empreinte
des sources** (`azemouse-empreinte`) : SHA-256 du contenu du catalogue, des liens d'achat, du fichier des
images et des sept modules qui composent le message (dont lui-même). La sortie dit l'empreinte écrite :

```
Écrit : docs/apercu_resultat.png (620×4973, 417 Ko, empreinte f5a46051c0ea)
```

`tests/test_apercus.py` (3 tests paramétrés + 2 cas) relit la métadonnée et la recalcule : un aperçu plus
vieux que les données qu'il montre est refusé, avec la commande à relancer. L'empreinte ne dépend ni du
navigateur, ni de la police, ni de l'heure — seulement des sources.

**Contre-épreuves** (mutation) : un octet ajouté à `assets/images.json` → **3 échecs**, message
« relancez `python tools/render_preview.py` » ; et le test vérifie lui-même que l'empreinte **change** quand
une source change (sur une copie temporaire : aucun fichier du dépôt n'est écrit pendant les tests).

**Mesure** : 715 tests verts, `pyflakes` 0, `privacy_scan` 0 violation. **Rien à envoyer sur le serveur** :
l'outil, un test et trois images de documentation.

## 26.36 52e passe — la couverture de **branches**, une décision à la fois (2026-10-13)

### 26.36.1 Ce que la couverture de lignes ne dit pas

Le §26.31 annonçait **1 655 instructions, 0 non exécutée**. Une instruction peut être exécutée sans que
**l'autre** chemin d'une décision ne le soit jamais : `couverture de branches` (`coverage run --branch`)
compte les 508 décisions du périmètre. Mesure du 2026-10-13 : **22 branches jamais prises**, toutes dans
quatre fichiers — dont **aucune n'était un défaut visible** : c'étaient des cas que le catalogue
d'aujourd'hui ne produit plus (aucune souris sans longueur ni largeur, aucune souris sans capteur, aucune
souris sans poids) ou des relectures défensives. Une branche jamais prise est un piège pour le code futur,
et souvent une garantie annoncée mais non vérifiée.

### 26.36.2 Les vingt-deux, une par une

| Fichier | Décision jamais prise | Ce qu'en fait la 52e passe |
|---|---|---|
| `bot.py` 61 | `setup_hook` appelé alors que la purge tourne déjà | **test** : démarrage rejoué deux fois dans le même processus, la purge ne repart pas (sinon « Task is already running ») |
| `session.py` 243, 248 | `discard` / `discard_user` sur un identifiant ou d'un membre inconnus | **2 tests**, avec l'écriture du fichier d'état **surveillée** : rien ne bouge ⇒ rien n'est réécrit (et non plus seulement « rien ne change », qui ne prouvait pas l'absence d'écriture) |
| `session.py` 332 | Fichier d'état lu avec les deux parcours dans l'ordre inverse | **test** : c'est l'âge qui tranche, pas l'ordre du fichier |
| `session.py` 361 | `_remove` d'un parcours qui n'a pas la main | **test** : purger l'ancien ne détache pas le vivant |
| `finder_flow` 330, 332 | Souris sans longueur, puis sans largeur | **test** sur les formateurs (`_size_text`) — une cote absente disparaît, jamais « None » |
| `finder_flow` 400 | Rappel d'un parcours où rien n'est encore répondu | **test** : le récapitulatif est vide, il n'invente rien |
| `finder_flow` 495-501 | Souris sans capteur / fréquence / switchs / MCU | **test** sur `atk_u2`, dont le MCU manque vraiment (onze souris du catalogue) |
| `finder_flow` 525, 531 | Souris sans poids documenté / sans forme connue | **test** sur les formateurs (poids absent ⇒ pas de séparateur orphelin) |
| `finder_flow` 540 | Ligne « Peu importe le prix » sans composant documenté | **test** : pas de « ⚙️ » orphelin |
| `finder_flow` 691, 1077, 1081, 1085 | Résultat réduit à **une seule place** (cas réel : 1 086 profils de la grille complète) | **test** : une seule ligne affichée, aucune place vide ; et **contre-épreuve** sur la garde d'illustration |
| `finder_flow` 1096, 1105 | `_dimensions_embed` / `_buttons_guide_embed` qui déclinent | **test de garde** (voir ci-dessous) |
| `finder_flow` 1252 | Le membre revalide la **même** prise | **test** : le thénar et la variante ne sont pas effacés (l'autre sens l'était déjà) |

### 26.36.3 Les deux branches « impossibles par construction », gardées et testées

`results_embeds` sort plus tôt quand la prise ou les mesures manquent : au moment d'empiler les blocs,
`_dimensions_embed` et `_buttons_guide_embed` **ne peuvent pas** renvoyer ``None`` aujourd'hui — c'est
prouvé par un test dédié (les deux blocs sont présents pour les trois prises, vraies souris du catalogue).
Les deux gardes du rendu restent donc pour ce qui viendra après (une règle qui supprimerait un bloc) et
sont testées **comme gardes** : en simulant un bloc qui décline, on vérifie que la carte n'empile pas de
bloc absent et que le **pied de message ne renvoie pas** à un bloc disparu — le défaut exact corrigé le
2026-10-13 (§24.3, C27).

### 26.36.4 Une mutation survivante qui a mené à une garantie réelle

Sur les quatorze mutations de cette passe, **une a survécu** : remplacer `if image_key:` par `if True:`
dans `results_embeds` ne change rien à l'affichage (`_image` ignore une clé absente)… mais fait relire
`assets/images.json` une fois de plus **par résultat**, alors que le projet n'a **aucun cache** (le
chargement est à chaud partout). La garantie était donc mesurable autrement : un test compare le nombre de
lectures du fichier des images entre deux parcours identiques, l'un avec une souris illustrée, l'autre avec
une souris dont la hauteur de boutons est « Inconnu » en Fingertip — **une lecture de moins**, et la
mutation redevient détectable. Les quatorze mutations échouent désormais (14 × « 1 failed »).

**Mesure finale** : **1 655 instructions / 0 manquante** et **508 branches / 0 manquante (100 % des deux
côtés)**, **732 tests verts**, `pyflakes` 0, `privacy_scan` 0 violation. Aucun fichier du bot n'est modifié
(des tests et des documents seulement) : **rien à envoyer** sur le serveur.
