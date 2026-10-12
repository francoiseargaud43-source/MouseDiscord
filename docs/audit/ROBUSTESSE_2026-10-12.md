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

**La troisième place (« 💸 L'économie ») n'apparaît que dans 0,1 % des profils** (1 sur 960 au banc
d'essai). Vérification faite : ce n'est pas un bug de calcul, mais un effet de seuil — la zone de
compatibilité du mode est étroite (±2 points sur 40) et l'alternative prend déjà la meilleure des
souris moins chères ; il reste donc rarement une souris encore moins chère **et** toujours dans la
zone. Deux options, à trancher par le propriétaire (cela changerait une règle de présentation) :

1. laisser ainsi : la place apparaît quand elle existe vraiment ;
2. élargir la zone de la seule ligne « économie » (par exemple jusqu'à 5 points sous le meilleur
   score), avec une mention du type « un peu moins compatible, mais moins chère ».
