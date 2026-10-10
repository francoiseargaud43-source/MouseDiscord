# Déploiement de Mouse Discord sur Alwaysdata (GitHub + FileZilla)

Ce guide installe le bot sur un hébergement **Alwaysdata**, le transfère avec **FileZilla**, puis le fait fonctionner
en permanence. Il décrit le code **tel qu'il est dans le dépôt** à la date de rédaction ; en cas de doute,
le code fait foi.

Notation des placeholders : tout ce qui est entre crochets dépend de votre compte.

| Placeholder | Signification | Exemple de forme (ne pas copier tel quel) |
|---|---|---|
| `[compte]` | Nom de votre compte Alwaysdata (apparaît dans l'URL du tableau d'administration) | `monnom-xyz` |
| `[utilisateur-ssh]` | Utilisateur SSH/SFTP que vous créez dans Alwaysdata | `monnom` |
| `[token]` | Token du bot Discord (portail développeur) | à copier depuis Discord, jamais dans le dépôt |
| `[id-salon]` | Identifiant numérique du salon « mouse-shape-finder » | 18 à 19 chiffres |

---

## 0. Ce qu'il faut savoir avant de commencer

1. **Quelle branche déployer ?** Déployez la branche **`arena/33e33710-mousediscord`**, pas `main`.
   La branche `main` ne contient que le commit « Initial commit » (`543879e`) ; toutes les évolutions
   (moteur, confidentialité, guide) sont sur la branche `arena/33e33710-mousediscord`.
   Aucune Pull Request n'est ouverte à ce jour.
2. **Le dépôt GitHub est privé.** Le téléchargement ZIP ne fonctionne que si vous êtes connecté à GitHub
   avec un compte ayant accès au dépôt. Le `git clone` demande vos identifiants GitHub (sur votre PC uniquement).
3. **Le fonctionnement permanent passe par « Services » d'Alwaysdata.** D'après la documentation officielle
   (https://help.alwaysdata.com/en/docs/web-hosting/services/), cette fonctionnalité est **réservée aux offres payantes**.
   Vérifiez que le menu **Advanced > Services** est accessible dans votre tableau d'administration avant de continuer.
   Si ce menu n'est pas disponible, le bot ne peut pas être maintenu en continu sur votre offre avec cette méthode :
   ne poursuivez pas et demandez au support Alwaysdata quelle option correspond à votre compte.
4. **Ne placez jamais le projet dans `www/`.** Ce dossier sert les fichiers au web public : votre `.env`
   (qui contient le token) pourrait y être téléchargé. Le dossier du projet doit être
   **`/home/[compte]/AzeMouse`**, c'est-à-dire directement dans votre dossier personnel.
5. **Le bot n'ouvre aucun port et ne sert aucune page web.** Il se connecte sortant à Discord. Aucune configuration
   de site ni de port n'est nécessaire.
6. **Python : utilisez `python`, jamais `python3`.** Sur Alwaysdata, la documentation indique d'utiliser la commande
   `python` (https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/).
   La version Python du projet doit être **3.10 au minimum** : la version de `python-dotenv` installée par `requirements.txt` (1.2.x) exige Python ≥ 3.10 (`discord.py` 2.7.x exige seulement ≥ 3.8). Cette procédure a été
   testée localement avec **Python 3.11** ; utilisez 3.11 si possible.

---

## 1. Prérequis

| Élément | Où l'obtenir | Vérification |
|---|---|---|
| Offre Alwaysdata payante (Services) | Tableau d'administration Alwaysdata | Menu **Advanced > Services** visible |
| Application Discord + token du bot | https://discord.com/developers/applications | Onglet **Bot** |
| Accès au dépôt GitHub | Compte GitHub invité sur `francoiseargaud43-source/MouseDiscord` | Vous voyez la branche `arena/33e33710-mousediscord` |
| FileZilla (version récente) | https://filezilla-project.org | Installé sur votre PC |
| Un terminal SSH | Windows 10/11 : *Invite de commandes* ou *PowerShell* (client OpenSSH inclus) ; ou PuTTY | `ssh -V` répond une version |
| Un éditeur de texte | Bloc-notes, VS Code… | — |

### 1.1 Créer un utilisateur SSH/SFTP sur Alwaysdata

1. Connectez-vous au tableau d'administration Alwaysdata.
2. Allez dans **Remote access > SSH/SFTP** (documentation : https://help.alwaysdata.com/en/docs/web-hosting/remote-access/sftp/).
3. Créez un utilisateur SSH avec un **shell standard** (pas « SFTP only » : cet accès serait *chrooted*, c'est-à-dire
   enfermé dans un dossier, et ne permettrait pas d'exécuter les commandes de la §6).
4. Activez l'option **password connection** (connexion par mot de passe) ou configurez une clé SSH, selon votre préférence.
5. **Notez les empreintes (fingerprints)** affichées sur cette même page : vous les comparerez à la première connexion (§5.1).

---

## 2. Ce qui doit se trouver dans `AzeMouse`

### 2.1 Où se trouve `AzeMouse`

| Côté | Chemin | Remarque |
|---|---|---|
| Votre PC | Le dossier local que vous avez préparé (ex. `Documents\AzeMouse`) | Contient le code extrait de GitHub (§3) |
| Serveur | **`/home/[compte]/AzeMouse`** | Dossier racine du projet. Dans FileZilla : `/home/[compte]/AzeMouse` |

`AzeMouse` existe **sur les deux côtés** : votre PC reçoit le code GitHub, le serveur reçoit une copie de la partie
« production » de ce code. Le dossier distant doit être créé à la racine de votre dossier personnel, **pas** dans `www/`.

**Règle essentielle** : le contenu du dépôt doit être placé **directement dans `AzeMouse`**, sans dossier intermédiaire
(pas de `AzeMouse/MouseDiscord-…/bot.py`, pas de `AzeMouse/AzeMouse/bot.py`). Après transfert, le fichier `bot.py`
doit se trouver exactement à `/home/[compte]/AzeMouse/bot.py`.

### 2.2 Arborescence finale attendue sur le serveur

```
/home/[compte]/AzeMouse/
├── bot.py                      ← point d'entrée (requis)
├── config.py                   ← configuration et chemins (requis)
├── requirements.txt            ← dépendances à installer (requis)
├── .env                        ← SECRETS : token + réglages (créé sur le serveur, §6.5)
├── .env.example                ← modèle (facultatif)
├── README.md                   ← documentation (facultatif)
├── cogs/                       ← requis
│   ├── __init__.py
│   ├── finder_flow.py
│   └── mouse_finder.py
├── utils/                      ← requis
│   ├── __init__.py
│   ├── assets.py
│   ├── catalog.py
│   ├── matcher.py
│   ├── models.py
│   ├── selection.py
│   ├── session.py
│   └── validation.py
├── data/                       ← requis
│   ├── mouse_db.json           ← catalogue (requis)
│   └── commercial_links.json   ← liens d'achat (requis ; peut être vide)
├── assets/
│   └── images.json             ← URL des images (requis ; peut être vide)
├── tools/
│   └── check_deployment.py     ← contrôle de déploiement (facultatif, recommandé)
├── .venv/                      ← créé SUR LE SERVEUR à l'étape 6 (ne pas transférer)
└── state/                      ← créé automatiquement par !setup_finder (ne pas transférer)
```

### 2.3 Tableau de tri des fichiers du dépôt

Colonne « Transférer ? » : **Oui** = à placer sur le serveur ; **Non** = ne pas transférer ; **Serveur** = à créer
directement sur le serveur.

| Fichier ou dossier | Transférer ? | Obligatoire ? | Rôle | Remarques |
|---|---|---|---|---|
| `bot.py` | Oui | Oui | Point d'entrée, démarrage du bot | Lancé par la commande de la §7.1 |
| `config.py` | Oui | Oui | Lit `.env`, définit les chemins | Ne contient aucun secret |
| `cogs/*.py` (3 fichiers) | Oui | Oui | Commande `!setup_finder` et parcours Discord | Dossier entier |
| `utils/*.py` (8 fichiers) | Oui | Oui | Moteur, catalogue, sessions, validation | Dossier entier |
| `data/mouse_db.json` | Oui | Oui | Catalogue des souris | Relu à chaque recherche |
| `data/commercial_links.json` | Oui | Oui (fichier) | Liens d'achat | Peut contenir `{}`. **Voir §2.5** |
| `assets/images.json` | Oui | Oui (fichier) | URL des images | Peut être vide (aucune illustration, sans erreur) |
| `requirements.txt` | Oui | Oui | Dépendances de production (`discord.py`, `python-dotenv`) | Installé à l'étape 6 |
| `.env` (votre vrai fichier) | **Non** (créez-le sur le serveur) | Oui | Token et réglages | **Secret** : voir §2.4 |
| `.env.example` | Oui | Non | Modèle de `.env` | Ne contient pas de secret |
| `README.md` | Oui | Non | Documentation | Utile pour le diagnostic sur place |
| `tools/check_deployment.py` | Oui | Non (recommandé) | Contrôle avant lancement | Lit `.env`, n'affiche jamais le token |
| `requirements-dev.txt` | Non | Non | Outils de test (`pytest`, `pytest-asyncio`) | Inutile en production |
| `pytest.ini` | Non | Non | Configuration des tests | — |
| `tests/` | Non | Non | Tests automatisés | Exécutés sur votre PC |
| `tools/build_mouse_db.py`, `tools/compare_profiles.py` | Non | Non | Outils de génération/comparaison pour le développement | — |
| `docs/` | Non | Non | Audits et guides | Consultez-les sur GitHub |
| `.gitignore` | Non | Non | Règles Git | Inutile au serveur ; voir §2.6 |
| `.git/` | **Non** | Non | Historique Git | Ne jamais transférer : volumineux et inutile |
| `__pycache__/`, `.pytest_cache/`, `*.pyc` | Non | Non | Caches Python générés | Recréés automatiquement |
| `.venv/`, `venv/`, `env/` | **Non** | Non | Environnement virtuel de votre PC | Un venv Windows ne fonctionne pas sur Linux : créez-le sur le serveur |
| `state/` | Non | Non | Mémoire du message publié | Créé par le bot sur le serveur |
| `*.log` | Non | Non | Journaux locaux | Les journaux du serveur sont dans l'administration (§7.2) |

### 2.4 Le fichier `.env` : secret, à ne jamais publier

- Le token Discord donne le **contrôle total du bot**. Quiconque le possède peut le connecter à votre place.
- Le `.env` **ne doit exister que sur le serveur** (et éventuellement sur votre PC pour les tests), jamais dans GitHub.
- Le dépôt contient `.env` dans `.gitignore` (et désormais `.env.*`, sauf le modèle `.env.example`) : Git **ignore** ce fichier.
  Mais **`.gitignore` n'empêche pas FileZilla de transférer un fichier** : FileZilla envoie ce que vous sélectionnez.
  Ne déposez donc jamais un `.env` local sur le serveur sans l'avoir vérifié (§5.3).
- Si le token a été publié par erreur (dans un message, un commit, une capture d'écran) : **réinitialisez-le immédiatement**
  (Discord Developer Portal > Bot > Reset Token), puis mettez à jour `.env` sur le serveur et redémarrez le service.

### 2.5 Les liens d'achat : point d'attention avant mise en ligne publique

Le fichier `data/commercial_links.json` **contient aujourd'hui deux URL d'exemple** :

```json
{
  "scyrox_v8": "https://url.com/v8",
  "atk_a9_plus": "https://url.com/a9"
}
```

Ces adresses sont des **espaces réservés**, pas vos liens. Tant qu'elles restent en place, le bouton « Acheter … »
envoie vers un site qui n'est pas le vôtre. Le script de contrôle le signale (`ATTENTION`).
Avant la mise en ligne publique, **choisissez** :
- soit remplacer ces URL par vos liens d'achat réels (`https://…`) ;
- soit vider le fichier : `{}` (les souris concernées afficheront alors « Lien bientôt disponible »).

Le bot **ne plante pas** si une URL est vide ou absente : le bouton devient désactivé avec la mention
« Lien bientôt disponible ». Aucun lien n'est inventé par le code.

### 2.6 Le `.gitignore`

Le fichier `.gitignore` **est déjà présent dans le dépôt** (il n'y a rien à ajouter). Il protège le dépôt Git
(secrets, environnements virtuels, caches, `state/`). Il ne contrôle pas FileZilla : seul votre choix de fichiers
détermine ce qui est transféré.

---

## 3. Récupérer le code depuis GitHub

Deux méthodes équivalentes. Dans les deux cas, **la branche est `arena/33e33710-mousediscord`**.

### Méthode A — Archive ZIP (la plus simple, sans Git)

1. Ouvrez https://github.com/francoiseargaud43-source/MouseDiscord (connecté à votre compte GitHub).
2. Cliquez sur le sélecteur de branche (à gauche, affiche `main` par défaut) et choisissez **`arena/33e33710-mousediscord`**.
3. Bouton vert **Code** > **Download ZIP**.
4. Extrayez le ZIP (clic droit > *Extraire tout…* sous Windows). Le dossier obtenu s'appelle en général
   `MouseDiscord-arena-33e33710-mousediscord` (le nom exact peut varier : repérez le dossier qui contient `bot.py`).
5. **Dossier racine du projet = le dossier qui contient directement `bot.py`, `config.py`, `cogs/`, `utils/`.**
   C'est ce dossier dont vous transférez le **contenu**.

### Méthode B — `git clone` (si Git est installé sur votre PC)

```bash
git clone --branch arena/33e33710-mousediscord https://github.com/francoiseargaud43-source/MouseDiscord.git MouseDiscord-prod
cd MouseDiscord-prod
git log -1 --oneline
```

- `git clone --branch …` récupère directement la bonne branche.
- `git log -1 --oneline` affiche le commit déployé : notez-le pour savoir plus tard quelle version tourne.
- Le dossier `.git/` reste sur votre PC : **ne le transférez pas**.
- Le dépôt étant privé, Git vous demandera vos identifiants GitHub ; si l'authentification échoue, reconnectez GitHub
  sur votre PC (et non dans ce guide).

### Vérifier que vous avez la bonne version

Le dossier doit contenir `data/mouse_db.json` et `tools/check_deployment.py`. Sur la branche de déploiement,
`tools/check_deployment.py` existe ; s'il est absent, vous avez probablement téléchargé `main`.

---

## 4. Modifications à faire AVANT le transfert

Aucune modification de code n'est nécessaire pour faire fonctionner le bot. Vérifiez seulement :

| Fichier | Action | Obligatoire |
|---|---|---|
| `data/commercial_links.json` | Remplacer ou vider les URL `https://url.com/…` (§2.5) | Recommandé avant mise en ligne publique |
| `assets/images.json` | Rien à faire si les images ne sont pas prêtes (valeurs vides = pas d'illustration) | Non |
| `.env` | **Ne pas le créer sur votre PC pour le transférer** : vous le créerez sur le serveur (§6.5) | — |

Le code est déjà adapté au déploiement : chemins ancrés sur l'emplacement des fichiers (fonctionne quel que soit le
répertoire de lancement), `.env` lu depuis le dossier du projet, erreurs de configuration explicites.

---

## 5. Configuration FileZilla (SFTP)

### 5.1 Créer la connexion

1. Ouvrez FileZilla > **Gestionnaire de sites** (icône en haut à gauche) > **Nouveau site**.
2. Renseignez :

| Champ | Valeur |
|---|---|
| Protocole | **SFTP - SSH File Transfer Protocol** |
| Hôte | `ssh-[compte].alwaysdata.net` |
| Port | `22` |
| Type d'authentification | **Normale** |
| Identifiant | `[utilisateur-ssh]` |
| Mot de passe | le mot de passe SSH défini en §1.1 |

Source : https://help.alwaysdata.com/en/docs/web-hosting/remote-access/sftp/ (hôte `ssh-[account].alwaysdata.net`, port 22).

3. Cliquez sur **Connexion**. À la première connexion, FileZilla affiche l'**empreinte du serveur** (fingerprint).
   **Comparez-la** avec celle affichée dans Alwaysdata (**Remote access > SSH/SFTP**). Si elles diffèrent, n'acceptez pas.
4. Cochez « Toujours faire confiance à cet hôte » seulement après cette vérification.

> Ne pas utiliser le protocole FTP non chiffré (port 21) : préférez SFTP ou FTP sécurisé (FTPS, port 990 selon
> https://help.alwaysdata.com/en/docs/web-hosting/remote-access/ftp/).

### 5.2 Les deux panneaux

- **Panneau gauche = local** : votre PC (dossier extrait ou cloné, §3).
- **Panneau droit = distant** : le serveur Alwaysdata.
- Le chemin distant est affiché en haut du panneau droit. Il doit commencer par `/home/[compte]`.
  Si le chemin affiché est différent, notez-le : c'est votre répertoire de départ réel. Adaptez alors tous les chemins
  de ce guide.

### 5.3 Transférer le contenu du dépôt

1. Dans le panneau droit, allez dans `/home/[compte]`.
2. Clic droit > **Créer un répertoire** > nom : `AzeMouse` (si le dossier n'existe pas déjà). Double-cliquez dessus.
   **Vérifiez la barre de chemin : `/home/[compte]/AzeMouse`.**
3. Dans le panneau gauche, ouvrez le dossier racine du projet (celui qui contient `bot.py`).
4. Sélectionnez **les éléments à transférer** (voir §2.3) :
   - `bot.py`, `config.py`, `requirements.txt`, `README.md`, `.env.example`
   - les dossiers `cogs`, `utils`, `data`, `assets`, `tools`
   - **Ne sélectionnez pas** : `.git`, `tests`, `docs`, `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `.venv`, `state`,
     `__pycache__`, `.pytest_cache`, `.env`.
5. Clic droit sur la sélection > **Téléverser** (ou glisser-déposer vers le panneau droit, dans `/home/[compte]/AzeMouse`).
   Les dossiers sont transférés **récursivement** (avec leur contenu).
6. Si FileZilla demande quoi faire pour les fichiers existants : **Écraser** (sur un premier déploiement).
7. **Ne pas** utiliser « Synchroniser les répertoires » pour ce transfert : cette fonction peut supprimer des fichiers distants.

> Piège fréquent : sélectionner le dossier `MouseDiscord-…` lui-même au lieu de son contenu crée
> `AzeMouse/MouseDiscord-…/bot.py`. Le bot ne démarrera pas (voir §11, « No such file or directory »).

### 5.4 Vérifier le transfert

1. Dans le panneau droit, vérifiez que `/home/[compte]/AzeMouse` contient : `bot.py`, `config.py`, `requirements.txt`,
   `cogs/`, `utils/`, `data/`, `assets/`, `tools/`.
2. Ouvrez `cogs/` : il doit contenir `finder_flow.py` et `mouse_finder.py` (et non un sous-dossier supplémentaire).
3. Consultez l'onglet **File d'attente** (en bas) : aucun transfert ne doit être en erreur (« Échec » ou « Erreur »).
   Relancez les éléments en échec.
4. Taille de contrôle : `data/mouse_db.json` fait environ 28 Ko.

---

## 6. Préparer le serveur (terminal SSH)

### 6.1 Ouvrir un terminal distant

- Windows : PowerShell ou Invite de commandes :
  ```bash
  ssh [utilisateur-ssh]@ssh-[compte].alwaysdata.net
  ```
  Acceptez l'empreinte (la même que dans §5.1) et saisissez le mot de passe.
- Alternative sans client SSH : `https://ssh-[compte].alwaysdata.net` dans le navigateur (terminal web). La documentation
  la décrit comme moins fiable pour un usage régulier : préférez un client SSH.

Vous êtes dans votre dossier personnel, `/home/[compte]`. Vérifiez :

```bash
pwd
ls ~/AzeMouse
```

`pwd` doit afficher `/home/[compte]` et `ls` doit lister les fichiers transférés (`bot.py`, `cogs`, …).

### 6.2 Vérifier la version de Python

```bash
python --version
```

- Il faut **3.10 ou plus** (3.11 recommandé, testé localement avec 3.11).
- Si `python --version` affiche une version inférieure à 3.10, choisissez une autre version pour l'environnement virtuel :
  ```bash
  PYTHON_VERSION=3.11 python --version
  ```
  La version par défaut se règle dans le tableau d'administration, menu **Environment > Python**
  (https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/). La documentation indique que les
  versions ne sont pas forcément déjà installées ; si la version voulue n'est pas disponible, demandez-le au support.

### 6.3 Créer l'environnement virtuel

Un environnement virtuel isole les dépendances du bot. Il se crée dans le dossier du projet :

```bash
cd ~/AzeMouse
python -m venv .venv
```

- `cd ~/AzeMouse` : se placer dans le dossier du projet (`~` = `/home/[compte]`).
- `python -m venv .venv` : crée le dossier `.venv/` (la commande `python` est celle d'Alwaysdata).
- Pour une version précise : `PYTHON_VERSION=3.11 python -m venv .venv`.

Si `.venv/` existe déjà et doit être recréé : `rm -rf ~/AzeMouse/.venv` puis relancez la commande.

Vérifiez :

```bash
~/AzeMouse/.venv/bin/python --version
```

### 6.4 Installer les dépendances

Utilisez **le Python de l'environnement virtuel**, avec son chemin complet (ne dépendez pas de l'activation) :

```bash
~/AzeMouse/.venv/bin/python -m pip install --upgrade pip
~/AzeMouse/.venv/bin/python -m pip install -r ~/AzeMouse/requirements.txt
```

- Le premier `pip install --upgrade pip` met seulement à jour l'outil d'installation.
- Le second installe `discord.py` (2.x) et `python-dotenv` (1.x), selon `requirements.txt`.
- Les versions installées sont celles qui satisfont les plages du fichier (ex. `discord.py` 2.7.1 en local).
  Ne mettez pas à jour les dépendances sans raison.
- Pour vérifier :
  ```bash
  ~/AzeMouse/.venv/bin/python -m pip show discord.py python-dotenv
  ```

Les outils de test (`requirements-dev.txt`) ne sont **pas** nécessaires sur le serveur.

### 6.5 Créer le fichier `.env` sur le serveur

**Méthode recommandée : copier le modèle sur le serveur, puis l'éditer dans FileZilla.**

1. Dans le terminal SSH : `cp ~/AzeMouse/.env.example ~/AzeMouse/.env`.
2. Dans FileZilla, panneau droit, ouvrez `/home/[compte]/AzeMouse` (rafraîchissez la liste si besoin).
3. Clic droit sur `.env` > **Afficher/Éditer**. Remplacez les valeurs par les vôtres, enregistrez, et acceptez le téléversement
   de la version modifiée. (FileZilla édite une copie temporaire locale : fermez-la ensuite et ne la conservez pas.)
   Le contenu à obtenir :

```
DISCORD_TOKEN=[token]
FINDER_CHANNEL_ID=[id-salon]
COMMAND_PREFIX=!
LOCK_FINDER_CHANNEL=true
SESSION_TTL_SECONDS=1800
```

- `DISCORD_TOKEN` : **obligatoire**. Sans lui, le bot quitte immédiatement avec le message « DISCORD_TOKEN est vide ».
- `FINDER_CHANNEL_ID` : facultatif. Vide ou `0` = `!setup_finder` publie dans le salon où vous tapez la commande.
  Un identifiant non numérique bloque le démarrage avec un message explicite.
- `COMMAND_PREFIX` : facultatif, `!` par défaut.
- `LOCK_FINDER_CHANNEL` : facultatif, `true` par défaut (voir §8.3 pour ses effets).
- `SESSION_TTL_SECONDS` : facultatif, `1800` par défaut (30 min d'inactivité).
- Pas d'espaces autour du `=`, pas de guillemets, une variable par ligne.

**Méthode alternative (terminal)** : éditez `~/AzeMouse/.env` avec `nano` si l'éditeur est installé (`which nano` pour le vérifier), sinon `vi`.

4. Restreignez les droits du fichier (lisible par vous seul) :

```bash
chmod 600 ~/AzeMouse/.env
ls -l ~/AzeMouse/.env
```

La sortie doit commencer par `-rw-------`.

**Option** : vous pouvez aussi définir `DISCORD_TOKEN` dans le champ **variables d'environnement** du service (§7).
Si la même variable est définie aux deux endroits, la valeur de l'environnement du service **prime** sur `.env`.
Choisissez **un seul** endroit pour éviter la confusion.

### 6.6 Contrôler la configuration

```bash
cd ~/AzeMouse
.venv/bin/python tools/check_deployment.py
```

Résultat attendu (exemple de lecture) :
- `[OK]` partout ;
- `[ATTENTION]` pour les liens d'exemple `url.com` (§2.5) : n'empêche pas le lancement ;
- **`0 erreur(s) bloquante(s).`** : condition pour continuer.

Le script n'affiche jamais la valeur du token. Il contrôle la présence de `DISCORD_TOKEN`, pas sa validité :
la validité est vérifiée par Discord au premier lancement.

---

## 7. Démarrage permanent : Alwaysdata « Services »

Un lancement dans le terminal (`python bot.py`) **s'arrête à la fermeture de votre session SSH**. Pour un fonctionnement
permanent, déclarez le bot comme **service** (documentation : https://help.alwaysdata.com/en/docs/web-hosting/services/).

Ce que dit la documentation Alwaysdata, et ce qui en découle :

| Règle Alwaysdata | Conséquence pour Mouse Discord |
|---|---|
| Un service est un programme lancé sans interaction, **relancé automatiquement** s'il s'arrête | Le bot redémarre seul après une erreur |
| Il doit **rester au premier plan** (ne pas se mettre en arrière-plan) | `bot.py` reste au premier plan (aucun `&`, aucun `nohup`) |
| Le **redémarrage** envoie le signal `SIGHUP` | Le bot s'arrête puis redémarre. Les sessions en cours (en mémoire) sont perdues ; le message d'accueil et `state/` persistent |
| Si le service **échoue plusieurs fois rapidement**, il est **désactivé automatiquement** | Une mauvaise configuration (token vide) désactive le service : voir §11 |
| La **surveillance** (*Monitoring command*) relance le service si la commande échoue | **Ne rien renseigner** : le bot n'ouvre aucun port, une surveillance par port le relancerait en boucle |
| Les **journaux** sont dans `/home/[compte]/admin/logs/services/` | Consultables dans l'administration et dans le terminal (§7.2) |
| Les ports 8300-8499 et `services-[compte].alwaysdata.net` sont réservés aux services | Non utilisés par le bot |
| « Aucun filtrage réseau » sur les services | Le bot n'expose rien : il ne doit donc rien écouter |

### 7.1 Déclarer le service

1. Connectez-vous à l'administration Alwaysdata > **Advanced > Services** > créer un service.
2. Renseignez (les libellés exacts peuvent varier selon l'interface : vérifiez-les à l'écran) :

| Champ | Valeur |
|---|---|
| Nom | `MouseDiscord` (libre) |
| Commande (*command*) | `/home/[compte]/AzeMouse/.venv/bin/python bot.py` |
| Répertoire de travail (*working directory*) | `/home/[compte]/AzeMouse` |
| Version de Python | Laissez vide : le venv (§6.3) utilise déjà sa propre version. Le chemin absolu de `.venv/bin/python` est utilisé. |
| Variables d'environnement | Vide, **ou** `DISCORD_TOKEN=[token]` si vous ne voulez pas utiliser `.env` (§6.5) |
| Commande de surveillance (*monitoring command*) | **Vide** |

Pourquoi un chemin absolu vers `.venv/bin/python` : le service ne lance pas votre session SSH, donc
l'environnement virtuel ne doit pas être « activé » : seul le chemin compte.

3. Enregistrez puis **démarrez** le service.

### 7.2 Vérifier le démarrage

Dans le terminal SSH :

```bash
ls -l ~/admin/logs/services/
```

Repérez le fichier du service `MouseDiscord` (le nom exact est généré par Alwaysdata) puis affichez sa fin :

```bash
tail -n 50 ~/admin/logs/services/[nom-du-fichier-de-log]
```

Un démarrage réussi se termine par une ligne de ce type (écrite par le bot) :

```
... INFO mouse_discord : Connecté en tant que [nom du bot] (id=…)
```

Les logs sont aussi visibles dans l'administration : **Advanced > Processes > Services** puis le lien vers les journaux.

### 7.3 Redémarrer le service

- Administration : **Advanced > Services** (ou **Advanced > Processes > Services**) > action **Redémarrer** du service.
- Le redémarrage envoie `SIGHUP` (documentation Alwaysdata) : le bot s'arrête puis redémarre.

### 7.4 Arrêter le service

Administration : **Advanced > Services** > action **Arrêter** (ou désactiver le service). Ne le faites pas en même temps
qu'un lancement manuel (§9, instance unique).

---

## 8. Configuration Discord

### 8.1 Portail développeur

1. https://discord.com/developers/applications > votre application > **Bot**.
2. **Reset Token** (si besoin) > copiez le token **une seule fois** et placez-le dans `DISCORD_TOKEN` (`.env` ou service).
   Ne le collez dans aucun message, aucun fichier du dépôt, aucune capture d'écran.
3. Section **Privileged Gateway Intents** : activez **Message Content Intent**.
   Il est nécessaire à la commande `!setup_finder` (lecture du texte des commandes préfixées).
   Les autres intents privilégiés (Server Members, Presence) **ne sont pas utilisés** : laissez-les désactivés.
   - Si cet intent n'est pas activé alors que le code le demande, le bot **ne se connecte pas** : Discord refuse le démarrage
     (`PrivilegedIntentsRequired`, voir §11).

### 8.2 Inviter le bot sur votre serveur

1. Portail > **OAuth2** > **URL Generator**.
2. **Scopes** : cochez uniquement **`bot`**. (Le bot n'utilise aucune commande « slash » : `applications.commands` n'est pas nécessaire.)
3. **Bot Permissions** : cochez le strict nécessaire :

| Permission (Discord) | Pourquoi | Obligatoire |
|---|---|---|
| View Channels (Voir les salons) | Voir le salon du panneau | Oui |
| Send Messages (Envoyer des messages) | Publier le message d'accueil et répondre à `!setup_finder` | Oui |
| Embed Links (Intégrer des liens) | Les messages utilisent des embeds | Oui |
| Read Message History (Voir l'historique) | Retrouver et éditer le message d'accueil déjà publié | Oui |
| Manage Roles / « Gérer les permissions » **au niveau du salon** | Verrouiller le salon (`LOCK_FINDER_CHANNEL=true`) | Seulement si verrouillage |

Valeurs de permissions (calculées avec la bibliothèque du projet) :
- sans verrouillage : **`84992`** ;
- avec verrouillage : **`268520448`**.

Lien d'invitation : `https://discord.com/oauth2/authorize?client_id=[id-application]&scope=bot&permissions=84992`
(remplacez `[id-application]` par l'identifiant de votre application, visible dans le portail, onglet **General Information**).

**N'accordez pas la permission Administrateur** : elle n'est pas nécessaire.

4. Choisissez votre serveur et autorisez. Le bot apparaît dans la liste des membres (hors ligne tant que le service ne tourne pas).

### 8.3 Salon dédié, `FINDER_CHANNEL_ID` et verrouillage

1. Créez un salon (ex. `#mouse-shape-finder`).
2. Mode développeur Discord : **Paramètres utilisateur > Avancés > Mode développeur**. Clic droit sur le salon > **Copier l'identifiant**.
3. Renseignez `FINDER_CHANNEL_ID=[id-salon]` dans `.env` (ou laissez vide et tapez `!setup_finder` **dans** ce salon).

**`LOCK_FINDER_CHANNEL`** (défaut `true`) : lors de `!setup_finder`, le bot retire pour **`@everyone`** le droit
*Envoyer des messages* et *Ajouter des réactions* **sur ce salon uniquement** (aucune permission du serveur n'est modifiée).
Effets concrets :
- les membres **ne peuvent plus écrire** dans ce salon : c'est voulu (salon de lecture seule) ;
- les **boutons restent cliquables** et les réponses restent privées (à confirmer lors de votre test manuel, §10) ;
- un rôle qui aurait le droit d'écrire dans ce salon **garde ce droit** (les réglages par rôle ne sont pas modifiés) ;
- si le bot n'a pas la permission de gérer les permissions du salon, la commande l'indique par un message d'avertissement
  et publie quand même le message.

Pour désactiver le verrouillage : `LOCK_FINDER_CHANNEL=false`, puis redémarrage du service. Le salon ne sera pas
reverrouillé automatiquement ; rétablissez si nécessaire les permissions de `@everyone` dans les paramètres du salon.

### 8.4 Publier le message d'accueil

Dans Discord, en tant qu'utilisateur ayant la permission **Gérer le serveur** :
- `!setup_finder` (dans le salon voulu, ou sans `FINDER_CHANNEL_ID`) ;
- ou `!setup_finder #mouse-shape-finder`.

La première exécution publie le message ; les suivantes **l'éditent** (aucun doublon). Le message est mémorisé dans
`~/AzeMouse/state/finder_message.json` : ce dossier doit rester sur le serveur (ne pas le supprimer, §12.1).

---

## 9. Une seule instance du bot

**Une seule instance doit tourner à la fois.** Deux instances connectées avec le même token reçoivent les mêmes clics :
une des deux réponses peut échouer, et le comportement devient imprévisible.

- Ne lancez **pas** `python bot.py` manuellement dans SSH pendant que le service tourne (la même identité Discord se connecterait deux fois).
- Vérifiez qu'une seule instance existe :
  ```bash
  ps -ef | grep "[b]ot.py"
  ```
  (la syntaxe `[b]ot.py` évite de compter la commande `grep` elle-même). Une seule ligne doit apparaître.
  Si `ps` n'est pas disponible, vérifiez la liste des processus dans **Advanced > Processes > Services**.
- Si vous avez lancé le bot à la main pour un test : arrêtez-le avec `Ctrl+C` avant de démarrer le service.

---

## 10. Tests après installation

### 10.1 Déjà automatisés (sur votre PC, avant transfert)

| Commande | Ce qu'elle vérifie | Résultat à la date du guide |
|---|---|---|
| `python -m pytest -q` (avec `requirements-dev.txt`) | Moteur, catalogue, validation, sessions, flux, confidentialité, `.env`, script de contrôle | `219 passed` (à la date de la finalisation) |
| `python -m pyflakes bot.py config.py cogs utils tests tools` | Erreurs de code statiques | aucune sortie |
| Copie « production » (sans tests) : chargement des cogs et de la vue persistante | Le bot démarre et charge ses extensions | vérifié |

Ces tests **ne se connectent pas à Discord** : ils ne remplacent pas les tests manuels ci-dessous.

### 10.2 Sur le serveur (automatique)

```bash
cd ~/AzeMouse
.venv/bin/python tools/check_deployment.py
```

Attendu : `0 erreur(s) bloquante(s).`

### 10.3 Dans Discord (manuel, à effectuer par vous)

Cochez chaque point après vérification :

- [ ] Le service est « démarré » et les logs affichent `Connecté en tant que …`.
- [ ] Le bot apparaît **en ligne** dans la liste des membres du serveur.
- [ ] `!setup_finder` fonctionne pour une personne qui a la permission **Gérer le serveur** (réponse « Message de départ publié »).
- [ ] Une personne **sans** cette permission ne peut pas l'utiliser (message « réservée aux membres… »).
- [ ] Le message d'accueil apparaît dans le bon salon, avec le bouton **Start Mouse Shape Finder**.
- [ ] Un membre **ne peut pas écrire** dans ce salon (si `LOCK_FINDER_CHANNEL=true`).
- [ ] Le bouton **Start** ouvre le questionnaire **en privé** (réponse visible par vous seul).
- [ ] L'étape grip (menu) et l'étape mesures (bouton → fenêtre de saisie) fonctionnent.
- [ ] Une saisie invalide (ex. texte à la place d'un nombre) affiche « Saisie invalide » sans faire avancer le parcours.
- [ ] Le budget (menu) fonctionne ; « Budget Personnalisé » ouvre une fenêtre et accepte un prix.
- [ ] Le résultat s'affiche **uniquement** à la personne concernée (aucun message public).
- [ ] Les boutons d'achat **sans lien** affichent « Lien bientôt disponible » (désactivés) et ne provoquent aucune erreur.
- [ ] **Redémarrage du service** puis clic sur le bouton **Start** du message d'accueil : il doit toujours répondre
      (la vue persistante est enregistrée au démarrage).
- [ ] **Fermeture de votre session SSH et de FileZilla** : le bot reste en ligne dans Discord.
- [ ] « Refaire le test » relance un parcours ; « Fermer » retire le résultat.

Ce qui n'a **pas** été testé sur un vrai serveur Discord lors de la rédaction de ce guide est indiqué dans
`docs/audit/DEPLOIEMENT_AUDIT.md` (section F.1 « Vérifications NON réalisées »).

---

## 11. Diagnostic : problèmes fréquents

Consultez d'abord les journaux (§7.2), puis ce tableau.

| Symptôme (dans les logs) | Cause probable | Action |
|---|---|---|
| `DISCORD_TOKEN est vide` | `.env` absent, mal nommé ou token non renseigné | Vérifiez `ls -l ~/AzeMouse/.env` et son contenu (§6.5). Le fichier doit s'appeler exactement `.env` |
| `LoginFailure` / « Improper token » | Token incorrect ou révoqué | Reset Token dans le portail, mettez à jour `.env`, redémarrez |
| `PrivilegedIntentsRequired` | Message Content Intent désactivé dans le portail | Activez-le (§8.1), redémarrez |
| `ConfigError` / « doit être un nombre entier » | `FINDER_CHANNEL_ID` ou `SESSION_TTL_SECONDS` mal saisi | Corrigez `.env` (chiffres seulement) |
| `ModuleNotFoundError: No module named 'discord'` | Service lancé avec le mauvais Python, ou dépendances non installées | Utilisez `/home/[compte]/AzeMouse/.venv/bin/python` ; réinstallez (§6.4) |
| `No such file or directory: 'bot.py'` ou `can't open file` | Commande ou répertoire de travail incorrect ; ou dossier intermédiaire (§5.3) | Vérifiez §7.1 et que `bot.py` est directement dans `AzeMouse` |
| `Cannot connect to host discord.com` | Pas d'accès réseau sortant au moment du démarrage | Relancez le service ; si le problème persiste, contactez le support Alwaysdata |
| `Forbidden` / « Le bot ne peut pas écrire » | Permissions du bot insuffisantes dans le salon | Vérifiez les permissions du salon et du rôle du bot (§8.2) |
| `Impossible de verrouiller le salon` (dans le message de `!setup_finder`) | Permission « Gérer les permissions » absente au niveau du salon | Ajoutez-la au bot sur ce salon, ou mettez `LOCK_FINDER_CHANNEL=false` |
| `Permission denied` sur `state/` | Droits d'écriture insuffisants | `mkdir -p ~/AzeMouse/state && chmod u+rwx ~/AzeMouse/state` |
| Service **désactivé** automatiquement | Échecs répétés rapidement (ex. token vide) | Corrigez la cause dans les logs, puis réactivez le service dans l'administration |
| Bouton « Start » : « Une erreur est survenue » | Exception pendant le traitement (ex. JSON invalide modifié à chaud) | Lancez `tools/check_deployment.py`, consultez les logs, corrigez le fichier JSON |
| Message d'accueil **dupliqué** | `state/finder_message.json` supprimé, ou message supprimé à la main | Supprimez le message en double dans Discord ; `!setup_finder` mémorisera le bon |
| Boutons qui répondent parfois en erreur | Deux instances du bot en même temps | Arrêtez l'instance manuelle (§9) |
| Une souris n'apparaît pas dans les résultats | Données du catalogue incomplètes (voir `docs/audit/AUDIT.md`) | Comportement voulu : rien n'est inventé |

### 11.1 Où lire les erreurs

1. Services : `ls -l ~/admin/logs/services/`, puis `tail -n 100 ~/admin/logs/services/[fichier]`.
2. Administration : **Advanced > Processes > Services** (processus en cours).
3. Le bot journalise sur la sortie d'erreur (stderr) : les messages de démarrage et les exceptions y figurent.

---

## 12. Mise à jour du bot après une modification sur GitHub

### 12.1 Ce qui ne doit JAMAIS être écrasé

| Élément sur le serveur | Pourquoi le protéger |
|---|---|
| `~/AzeMouse/.env` | Token et réglages propres au serveur |
| `~/AzeMouse/data/commercial_links.json` | **Vos liens d'achat** (ils ne sont pas dans le dépôt tant que vous ne les y ajoutez pas) |
| `~/AzeMouse/assets/images.json` | **Vos URL d'images** |
| `~/AzeMouse/state/` | Mémoire du message d'accueil (évite les doublons) |
| `~/AzeMouse/.venv/` | Environnement Python du serveur |

### 12.2 Procédure pas à pas

1. **Sauvegarde** (sur le serveur, SSH) :
   ```bash
   mkdir -p ~/backup-azemouse
   cp -a ~/AzeMouse ~/backup-azemouse/AzeMouse-$(date +%Y-%m-%d)
   ```
   Cela copie tout, y compris `.env`, vos liens et `state/` (le venv est volumineux : vous pouvez l'exclure en le
   copiant séparément si l'espace est limité).
2. **Récupérer la nouvelle version** : ZIP de la branche ou `git pull` sur votre clone local (§3). Notez le commit :
   `git log -1 --oneline`.
3. **Identifier les fichiers modifiés** (avec un clone Git de la méthode B, §3) :
   ```bash
   git diff --name-only [ancien-commit] [nouveau-commit]
   ```
   Ne transférez que les fichiers listés, en veillant à ne **pas** toucher aux fichiers protégés (§12.1). Si la liste inclut
   `data/commercial_links.json` ou `assets/images.json`, c'est une modification du dépôt : n'écrasez **pas** votre version serveur,
   reportez à la main les seules nouveautés de structure.
4. **Transférer** : FileZilla, panneau gauche (nouvelle version) > panneau droit (`~/AzeMouse`), uniquement les fichiers modifiés,
   en « Écraser ». Ne pas « Synchroniser ».
5. **Dépendances** : si `requirements.txt` a changé :
   ```bash
   ~/AzeMouse/.venv/bin/python -m pip install -r ~/AzeMouse/requirements.txt
   ```
6. **Contrôle** : `~/AzeMouse/.venv/bin/python ~/AzeMouse/tools/check_deployment.py` → `0 erreur(s)`.
7. **Redémarrage** : nécessaire si vous avez modifié **un fichier Python** (`bot.py`, `config.py`, `cogs/`, `utils/`), **`.env`**,
   ou `requirements.txt`. Redémarrez le service (§7.3).
8. **Message d'accueil** : si le texte ou le bouton du message d'accueil a changé dans le code (`cogs/finder_flow.py`),
   tapez `!setup_finder` dans Discord pour éditer le message existant.
9. **Vérification** : logs (§7.2) puis checklist Discord (§10.3), au minimum le bouton Start et un parcours complet.

### 12.3 Quand un redémarrage est-il nécessaire ?

| Fichier modifié | Relu à chaud ? | Action |
|---|---|---|
| `data/mouse_db.json` (catalogue) | **Oui** : relu à chaque recherche | Aucun redémarrage (vérifiez d'abord le JSON avec `check_deployment.py`) |
| `data/commercial_links.json` (liens) | **Oui** : relu à chaque résultat | Aucun redémarrage |
| `assets/images.json` (images) | **Oui** : relu à chaque affichage d'image | Aucun redémarrage |
| `.env`, `config.py` | Non : lus au démarrage | **Redémarrer** |
| `bot.py`, `cogs/*.py`, `utils/*.py` | Non : chargés au démarrage | **Redémarrer** |
| `requirements.txt` | Non | Installer (§12.2 étape 5) puis **redémarrer** |
| Texte du message d'accueil (code) | Non : publié dans Discord | Redémarrer puis `!setup_finder` |

Un fichier JSON **invalide** modifié à chaud ne fait pas tomber le bot, mais les parcours concernés affichent une erreur
jusqu'à correction : vérifiez toujours avec `check_deployment.py` avant d'enregistrer un JSON modifié.

### 12.4 Retour arrière

En cas de problème : arrêtez le service, recopiez le dossier sauvegardé (§12.2 étape 1) à la place de `~/AzeMouse`
(en conservant `.env`, vos liens et `state/` si vous ne les avez pas modifiés), puis redémarrez le service.

---

## 13. Installation sans FileZilla (option avancée, non vérifiée sur l'hébergement)

Si Git est disponible sur le serveur (`git --version`), vous pourriez cloner le dépôt directement sur Alwaysdata.
Le dépôt étant privé, cela suppose de configurer un accès GitHub depuis le serveur, ce qui sort du périmètre de ce guide.
Cette méthode n'a **pas été vérifiée** sur votre hébergement : utilisez la méthode FileZilla décrite ici.

---

## Annexe : récapitulatif des chemins

| Élément | Chemin sur le serveur |
|---|---|
| Projet | `/home/[compte]/AzeMouse` |
| Environnement virtuel | `/home/[compte]/AzeMouse/.venv` |
| Python du service | `/home/[compte]/AzeMouse/.venv/bin/python` |
| Secrets | `/home/[compte]/AzeMouse/.env` (droits `600`) |
| Catalogue | `/home/[compte]/AzeMouse/data/mouse_db.json` |
| Liens d'achat | `/home/[compte]/AzeMouse/data/commercial_links.json` |
| Images | `/home/[compte]/AzeMouse/assets/images.json` |
| Mémoire du message d'accueil | `/home/[compte]/AzeMouse/state/finder_message.json` |
| Journaux du service | `/home/[compte]/admin/logs/services/` |
| Sauvegardes (recommandé) | `/home/[compte]/backup-azemouse/` |
