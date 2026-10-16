# Audit de déploiement — Mouse Discord sur Alwaysdata

Diagnostic réalisé avant mise en ligne. Le guide opérationnel est dans
[`docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`](../DEPLOYMENT_ALWAYSDATA_FILEZILLA.md).

## Livrable A — Diagnostic avant déploiement

### A.1 Version concernée

| Élément | État constaté |
|---|---|
| Branche à déployer | **`arena/33e33710-mousediscord`** (HEAD au moment de l'audit : voir `git log -1` ; l'audit porte sur le commit qui contient ce fichier) |
| Branche `main` | `543879e` « Initial commit » : **ne pas déployer** (ne contient pas les évolutions) |
| Pull Request | Aucune ouverte |
| Visibilité du dépôt | **Privé** (téléchargement ZIP et `git clone` nécessitent un accès GitHub) |
| Modifications non terminées | Aucune dans le code. Points de données restant à la décision du propriétaire (A.7) |

### A.2 Fichier de démarrage et structure

- Point d'entrée : `bot.py` (`python bot.py`). Vérifié : le démarrage fonctionne depuis un répertoire différent du projet.
- Structure réelle : identique à l'arborescence indicative, avec en plus `utils/selection.py`, `tools/` (2 outils de développement et
  `check_deployment.py` ajouté), `docs/` et `tests/` (plus `test_config.py` et `test_deployment_check.py`).
- Dossier créé à l'exécution : `state/` (message d'accueil publié, `state/finder_message.json`).

### A.3 Python et dépendances

| Élément | Constat |
|---|---|
| Version Python minimale | **3.10** : `python-dotenv` 1.2.4 exige `>=3.10` (métadonnées installées) |
| Version testée | **3.11.2** (environnement local) ; une version 3.12+ n'a pas été testée ici |
| `requirements.txt` | `discord.py>=2.4,<3`, `python-dotenv>=1.0,<2` (aucune version figée) |
| Versions installées pour la copie de production | `discord.py` 2.7.1, `python-dotenv` 1.2.4 |
| `requirements-dev.txt` | `-r requirements.txt` + `pytest`, `pytest-asyncio` (non nécessaires en production) |
| Mise à jour des dépendances | Aucune : les plages existantes suffisent |

### A.4 Chemins de fichiers

- `config.py` ancre tous les chemins sur `ROOT_DIR = Path(__file__).parent` : `data/mouse_db.json`, `data/commercial_links.json`,
  `assets/images.json`, `state/finder_message.json`. **Indépendant du répertoire de lancement** (vérifié).
- `bot.py` charge `cogs.mouse_finder` par nom de module : fonctionne car `python bot.py` place le dossier du script dans `sys.path`
  (vérifié depuis `/tmp`).
- **Modification effectuée** : `load_dotenv()` était appelé sans chemin. Il est désormais appelé avec `ROOT_DIR/.env`
  (le fichier lu ne dépend plus de la méthode de recherche de python-dotenv).

### A.5 Variables d'environnement (lues dans le code, aucune autre)

| Variable | Obligatoire | Défaut | Rôle | Comportement vérifié |
|---|---|---|---|---|
| `DISCORD_TOKEN` | **Oui** | — | Token du bot | Vide : journal `DISCORD_TOKEN est vide`, sortie code 1 (vérifié) |
| `FINDER_CHANNEL_ID` | Non | `0` | Salon de `!setup_finder` ; `0` = salon de la commande | Non numérique : **désormais** `ConfigError` explicite (vérifié) ; avant, trace peu lisible |
| `COMMAND_PREFIX` | Non | `!` | Préfixe des commandes | — |
| `LOCK_FINDER_CHANNEL` | Non | `true` | Verrouille `@everyone` sur le salon au setup | Valeurs vraies : `1 true yes on oui` |
| `SESSION_TTL_SECONDS` | Non | `1800` | Inactivité avant expiration de session | Non numérique : `ConfigError` explicite ; vide : défaut |

Aucune autre variable n'est lue. Les valeurs vides sont traitées comme absentes.

### A.6 Lecture de `.env`, JSON, images et liens

- `.env` : lu par `python-dotenv` au chargement de `config.py`. **Une variable déjà présente dans l'environnement du processus n'est pas
  écrasée** (comportement par défaut de `load_dotenv`). Un service Alwaysdata qui définit `DISCORD_TOKEN` prime donc sur `.env`.
- JSON relus **à chaque usage** (pas de cache) :
  - `mouse_db.json` : à chaque sélection (`load_catalog` dans `finder_flow.py`) ;
  - `commercial_links.json` : à chaque résultat ;
  - `images.json` : à chaque affichage d'image.
  Un changement de ces trois fichiers prend effet **sans redémarrage**.
- Liens : fichier absent ou vide → aucun lien ; URL invalide → ignorée avec un avertissement ; sans lien, **un seul** bouton
  informatif désactivé « Liens à venir » (depuis le 2026-10-11 : plus un bouton grisé par souris — tests
  `test_missing_commercial_link_shows_disabled_placeholder_button`, `test_real_link_creates_purchase_button_without_placeholder`).
- Images : URL `https://` uniquement ; vide ou invalide → aucune image, sans erreur (testé).
  Depuis le 2026-10-11, un **nom de fichier** (repris de `assets/illustrations/`) est résolu avec `IMAGES_BASE_URL`
  (le schéma doit être `https://`, sinon la valeur est ignorée avec un avertissement).

### A.7 Données et points à décider par le propriétaire

| Fichier | Constat | Décision |
|---|---|---|
| `data/commercial_links.json` | Contient `"scyrox_v8": "https://url.com/v8"` et `"atk_a9_plus": "https://url.com/a9"` : **URL d'exemple**, pas vos liens | **Non modifié** (instruction : ne pas toucher aux liens non fournis). À remplacer ou à vider avant mise en ligne publique. Signalé par `check_deployment.py` (`ATTENTION`) |
| `assets/images.json` | **2026-10-11** : les 15 illustrations livrées sont référencées par leur nom de fichier ; il reste à les publier et à renseigner `IMAGES_BASE_URL` (guide de déploiement §2.7) | Sans `IMAGES_BASE_URL` : aucune image affichée, aucun plantage. Signalé par `check_deployment.py` (`ATTENTION`) |

### A.8 Discord : intents et permissions

- Intents : `guilds` et **`message_content`** (privilégié, requis par `!setup_finder`). Aucun autre intent privilégié.
- Slash commands : aucune (`applications.commands` inutile).
- Permissions de bot (valeurs calculées avec discord.py) : `84992` (View Channels, Send Messages, Embed Links, Read Message History) ;
  `268520448` si *Gérer les permissions* au niveau du salon (verrouillage). **Aucune permission Administrateur requise.**
- **Correction** : le README demandait *Manage Channels* ; le code n'en a pas besoin. Le README est corrigé.

### A.9 Limitations sur un hébergement distant

| Point | Constat |
|---|---|
| Processus persistant | Alwaysdata : les **Services** sont relancés automatiquement, mais **réservés aux offres payantes** (documentation officielle). À vérifier sur votre compte |
| Ports | Le bot n'écoute sur aucun port (connexion sortante uniquement) |
| Sessions | En mémoire : perdues à chaque redémarrage (documenté) |
| Instance unique | Obligatoire : deux instances avec le même token se disputent les interactions (documenté) |
| Écriture | `state/` doit être inscriptible (vérifié par `check_deployment.py`) |
| Secrets | `.env` : hors dépôt (`.gitignore`), à créer sur le serveur, droits `600` recommandés |
| Chemins | Ne jamais placer le projet dans `www/` (dossier servi au web) |

### A.10 Tests disponibles

- `pytest` : 219 tests à la date de la finalisation (dont 5 pour la configuration et 9 pour le script de contrôle de déploiement ; 14 scénarios de confidentialité ; 24 cas du contrôle statique ; 17 vérifications de références documentaires, paramétrées). Aucun ne se connecte à Discord.
- `pyflakes` : propre.
- Vérification de déploiement réalisée sur une **copie de production** (uniquement les fichiers de production, venv et `pip install -r requirements.txt`).

---

## Livrable B — Liste des fichiers à transférer

Voir `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` §2.2 (arborescence) et §2.3 (tableau complet).

Vérifié sur copie propre : **aucun** fichier de production n'importe `tests/`, `tools/` (sauf `check_deployment.py` optionnel) ou `docs/`.

---

## Livrable C — Modifications préalables

### C.1 Modifications réalisées

| Fichier | Modification | Justification | Tests |
|---|---|---|---|
| `config.py` | `.env` lu depuis `ROOT_DIR/.env` (chemin explicite) ; `FINDER_CHANNEL_ID` et `SESSION_TTL_SECONDS` parsés par `_env_int` avec erreur explicite ; valeur vide = défaut | Lecture fiable de `.env` ; diagnostic lisible dans les journaux | `tests/test_config.py` (5) |
| `tools/check_deployment.py` (nouveau) | Contrôle lecture seule : Python, fichiers obligatoires, token (non affiché), entiers, catalogue, liens d'exemple, images, `state/` | Vérifications sur l'hébergement avant lancement | `tests/test_deployment_check.py` (9) |
| `.gitignore` | `.env.*` ignoré, `!.env.example` | Éviter qu'une variante de `.env` soit versionnée | — |
| `README.md` | Permissions corrigées ; modèle de session corrigé (`session_id`) ; section déploiement et architecture à jour | Documentation exacte | — |
| `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` (nouveau) | Guide complet | Livrables D, E, G | — |
| `docs/audit/RAPPORT_FINAL.md` | Compteurs de tests mis à jour (165) | Cohérence | — |
| `cogs/finder_flow.py` | Aucune modification dans ce lot. La docstring (référence à un fichier inexistant remplacée) était déjà corrigée dans le commit `30cdcb8` | — | — |

### C.2 Ce qui est correct et n'a pas été modifié

- Chemins relatifs au projet (`ROOT_DIR`), chargement des cogs, vue persistante enregistrée au démarrage (`setup_hook`).
- Gestion des liens et images absents (aucune erreur).
- Logique métier, catalogue, règles de recommandation, scores : **inchangés**.
- Pas de dépendance ajoutée ni mise à jour.

### C.3 Modifications obligatoires avant déploiement public (à décider par le propriétaire)

| Élément | Action |
|---|---|
| `data/commercial_links.json` (URL `https://url.com/…`) | Remplacer par vos liens réels **ou** `{}` |
| `.env` | Créer **sur le serveur** uniquement (jamais dans le dépôt) |
| Choix de la branche | Déployer `arena/33e33710-mousediscord`, pas `main` |

### C.4 Améliorations recommandées (non bloquantes)

- Ouvrir une Pull Request de `arena/33e33710-mousediscord` vers `main` pour que `main` contienne la version déployée.
- Figer les versions de dépendances (`requirements.lock`) si la reproductibilité de l'hébergement devient importante.
- Tester sur Python 3.12 si l'hébergeur propose cette version (la version 3.11 seule a été testée).

---

## Livrable F — Résultats des tests (exécutés réellement)

| Vérification | Commande | Résultat |
|---|---|---|
| Suite complète | `pytest -q` (venv local, Python 3.11.2) | **219 passed** à la date de la finalisation (2026-10-10), 1 avertissement (`audioop`, dépendance de discord.py). Le total de 165 indiqué précédemment était antérieur aux tests de confidentialité et de références documentaires. |
| Analyse statique | `pyflakes bot.py config.py cogs utils tests tools` | aucune sortie (propre) |
| Copie de production | `cp` de la liste de production, `python3 -m venv`, `pip install -r requirements.txt` | discord.py 2.7.1, python-dotenv 1.2.4 installés |
| Chargement hors projet | `python /tmp/check_setup.py` depuis `/tmp` (copie de production) | `extensions: ['cogs.mouse_finder']`, `commands: ['setup_finder']`, `persistent views: 1`, token chargé depuis `.env`, images vides OK |
| Démarrage sans token | `bot.py` sans `DISCORD_TOKEN` | journal `DISCORD_TOKEN est vide…`, code de sortie **1** |
| Démarrage avec faux token | `bot.py`, `DISCORD_TOKEN=FAKE…` | atteint la connexion à `discord.com:443` ; **échec de connexion réseau dans ce bac à sable** (accès réseau limité) |
| Entier invalide | `FINDER_CHANNEL_ID=abc bot.py` | `ConfigError : FINDER_CHANNEL_ID doit être un nombre entier (valeur actuelle : 'abc')…`, code **1** |
| Contrôle de déploiement | `tools/check_deployment.py` sur la copie | `0 erreur(s) bloquante(s)`, 2 `ATTENTION` (liens d'exemple `url.com`) |

### F.1 Vérifications NON réalisées (nécessitent votre hébergement ou Discord)

Aucune de ces vérifications n'a été effectuée à distance : la sandbox n'a pas accès à votre compte Alwaysdata ni à votre serveur Discord.


- Connexion réelle à Discord et apparition du bot en ligne.
- Commandes `!setup_finder`, publication, verrouillage du salon (et permissions réelles de votre serveur).
- Bouton persistant après redémarrage du service ; parcours complet en privé ; affichage des résultats.
- Disponibilité de **Services** sur votre offre, comportement exact du redémarrage (SIGHUP) et des logs sur Alwaysdata.
- Création du venv et installation des dépendances **sur Alwaysdata** ; présence de la version Python voulue.
- Accès SFTP/SSH depuis votre PC et empreinte du serveur.
- Que les boutons restent cliquables dans un salon où `@everyone` ne peut pas écrire (attendu d'après le fonctionnement des interactions, à confirmer).
- Protocole complet de validation Discord (10 étapes, deux comptes) : `docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md`. **Non exécuté.**

---

## Livrable H — Diagnostic des prérequis d'hébergement (Alwaysdata)

Date : 2026-10-10. Méthode : lecture de la documentation publique d'Alwaysdata et des métadonnées des paquets installés. **Aucun accès au compte Alwaysdata n'a été utilisé** : rien n'a été installé, lancé, ni redémarré à distance.

| # | Prérequis | Source vérifiée | État | Ce que vous devez contrôler sur votre compte |
|---|---|---|---|---|
| H1 | **Offre payante** : les « Services » (processus persistant) ne sont pas disponibles sur les offres gratuites | Documentation Services : « available on all our paid plans » | Vérifié dans la documentation ; **non vérifié sur votre offre** | Menu **Advanced > Services** visible. Sinon, la méthode retenue ne fonctionne pas et il faut changer d'offre ou de méthode |
| H2 | **Premier plan** : le processus ne doit pas se mettre en arrière-plan (pas de fork) | Documentation Services : « It must runs in foreground, not fork » | Conforme : `bot.py` reste au premier plan, aucun `&` ni `nohup` | — |
| H3 | **Version Python** : 3.10 minimum pour `python-dotenv` 1.2.x ; 3.11 testé | Documentation Python : 3.11 figure dans les versions prises en charge ; « Versions are not necessarily already installed » | Vérifié dans la documentation ; **version installée sur votre compte non vérifiée** | Environment > Python ; `PYTHON_VERSION=3.11 python --version` dans le terminal distant |
| H4 | **Commande `python`** (et non `python3`) pour le venv et le service | Documentation Python : « always use `python` … Never use `python3` » | Conforme au guide (§6.2–6.3) | — |
| H5 | **Aucun port à ouvrir** : le bot ne sert aucune page et n'écoute sur aucun port | Code (`bot.py`, aucun serveur HTTP) | Conforme ; aucune *Monitoring command* ne doit être configurée (elle redémarrerait le service en boucle) | Laisser le champ Monitoring vide |
| H6 | **Connexion sortante vers Discord** (`discord.com:443`, passerelle WebSocket) | Documentation Services : « There is no network filtering » (aucune restriction annoncée) ; le bac à sable de développement n'a pas pu atteindre `discord.com` | **Non vérifié** sur Alwaysdata | Message `Cannot connect to host discord.com` dans les journaux = problème réseau à signaler au support |
| H7 | **Redémarrage automatique** et **désactivation après échecs répétés** | Documentation Services : redémarrage automatique ; désactivation si échecs rapprochés ; redémarrage = signal SIGHUP | Vérifié dans la documentation ; **comportement réel non testé** | Un token invalide peut désactiver le service après plusieurs échecs : corriger `.env` puis réactiver le service |
| H8 | **Journaux** : `/home/[compte]/admin/logs/services/` et onglet Logs de l'administration | Documentation Services | Vérifié dans la documentation ; **non consulté** | Consulter après le premier démarrage (guide §7.2) |
| H9 | **Tâche planifiée** non utilisée comme surveillance | Documentation Tâches | Décision : non retenue (risque de plusieurs instances) | — |
| H10 | **Dépendances** : `discord.py` 2.7.1 (≥ 3.8) et `python-dotenv` 1.2.4 (≥ 3.10), relevées dans les métadonnées installées | Métadonnées des paquets (environnement de développement) | Vérifié localement ; **réinstallation sur Alwaysdata non réalisée** | `pip install -r requirements.txt` dans le venv du serveur |

**Conclusion du diagnostic** : rien, dans la documentation publique, n'interdit la méthode retenue (Service + venv + `.env`) sur une offre payante. Trois points restent à confirmer sur votre compte : l'offre (H1), la version Python installée (H3), et la sortie réseau vers Discord (H6). Aucun de ces points n'est confirmé à ce stade.

---

## Livrable G — Procédure de mise à jour

Voir `docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md` §12 : fichiers protégés, procédure pas à pas, tableau de rechargement à chaud
(JSON relus à chaque usage, code et configuration nécessitant un redémarrage), et retour arrière.

---

## Sources vérifiées (documentation Alwaysdata)

- Python (commande `python`, venv, `pip`, versions proposées) : https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/
- Services (processus persistants, redémarrage SIGHUP, logs, désactivation après échecs répétés, offres payantes) : https://help.alwaysdata.com/en/docs/web-hosting/services/
- SSH (hôte `ssh-[compte].alwaysdata.net`, port 22, terminal web) : https://help.alwaysdata.com/en/docs/web-hosting/remote-access/ssh/
- SFTP (FileZilla, hôte, port 22, utilisateur SFTP « chrooted ») : https://help.alwaysdata.com/en/docs/web-hosting/remote-access/sftp/
- FTP (port 990 FTPS, 21 STARTTLS) : https://help.alwaysdata.com/en/docs/web-hosting/remote-access/ftp/
- Tâches planifiées (non utilisées : une tâche planifiée risquerait de lancer plusieurs instances) : https://help.alwaysdata.com/en/docs/web-hosting/tasks/
