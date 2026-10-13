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

1. **Quelle branche déployer ?** Déployez la branche **`arena/87fafd0d-mousediscord`**, pas `main`.
   La branche `main` ne contient que le commit « Initial commit » (`543879e`) ; toutes les évolutions
   (moteur, confidentialité, guide) sont sur la branche `arena/87fafd0d-mousediscord`.
   Une Pull Request (`#1`) est ouverte de cette branche vers `main` : elle ne bloque pas le
   déploiement, vous pouvez déployer la branche telle quelle.
2. **Le dépôt GitHub est privé.** Le téléchargement ZIP ne fonctionne que si vous êtes connecté à GitHub
   avec un compte ayant accès au dépôt. Le `git clone` demande vos identifiants GitHub (sur votre PC uniquement).
3. **Le fonctionnement permanent passe par « Services » d'Alwaysdata.** D'après la documentation officielle
   (https://help.alwaysdata.com/en/docs/web-hosting/services/), cette fonctionnalité est **réservée aux offres payantes**.
   Vérifiez que le menu **Advanced > Services** est accessible dans votre tableau d'administration avant de continuer.
   Si ce menu n'est pas disponible, le bot ne peut pas être maintenu en continu sur votre offre avec cette méthode :
   ne poursuivez pas et demandez au support Alwaysdata quelle option correspond à votre compte.
4. **Ne placez jamais le projet dans `www/`.** Ce dossier sert les fichiers au web public : votre `.env`
   (qui contient le token) pourrait y être téléchargé. Le dossier du projet doit être
   **`/home/[compte]/MouseDiscord`**, c'est-à-dire directement dans votre dossier personnel.
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
| Accès au dépôt GitHub | Compte GitHub invité sur `francoiseargaud43-source/MouseDiscord` | Vous voyez la branche `arena/87fafd0d-mousediscord` |
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

## 2. Ce qui doit se trouver dans `MouseDiscord`

### 2.1 Où se trouve `MouseDiscord`

| Côté | Chemin | Remarque |
|---|---|---|
| Votre PC | Le dossier local que vous avez préparé (ex. `Documents\MouseDiscord`) | Contient le code extrait de GitHub (§3) |
| Serveur | **`/home/[compte]/MouseDiscord`** | Dossier racine du projet. Dans FileZilla : `/home/[compte]/MouseDiscord` |

`MouseDiscord` existe **sur les deux côtés** : votre PC reçoit le code GitHub, le serveur reçoit une copie de la partie
« production » de ce code. Le dossier distant doit être créé à la racine de votre dossier personnel, **pas** dans `www/`.

**Règle essentielle** : le contenu du dépôt doit être placé **directement dans `MouseDiscord`**, sans dossier intermédiaire
(pas de `MouseDiscord/MouseDiscord-…/bot.py`, pas de `MouseDiscord/MouseDiscord/bot.py`). Après transfert, le fichier `bot.py`
doit se trouver exactement à `/home/[compte]/MouseDiscord/bot.py`.

### 2.2 Arborescence finale attendue sur le serveur

```
/home/[compte]/MouseDiscord/
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
│   ├── images.json             ← clé -> nom de fichier ou URL https (requis ; peut être vide)
│   └── illustrations/          ← les 15 images T01–T15 (facultatif : sans elles, aucun embed n'affiche d'image)
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
| `data/commercial_links.json` | Oui | Oui (fichier) | Liens d'achat officiels (36 souris au 2026-10-12) | Relu à chaque résultat. **Voir §2.5** |
| `assets/images.json` | Oui | Oui (fichier) | Images des étapes et du résultat | Peut être vide (aucune illustration, sans erreur) |
| `assets/illustrations/` | Oui | Non (recommandé) | Les 15 images `T01`–`T15` prêtes à publier | **Voir §2.7** |
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

Le fichier `data/commercial_links.json` **du dépôt est prêt à l'emploi** : au 2026-10-12, il contient les
**liens d'achat officiels des 36 souris du catalogue (36 sur 36)**, tous liens affiliés et vérifiés un par un
(clé = `id` de la souris dans `data/mouse_db.json` ; liens relevés un par un le 2026-10-11,
`docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`, les dix Pulsar complétés le 2026-10-12 ;
contrôle automatique : `python tools/check_deployment.py`).

```json
{
  "_lisez_moi": "… clés commençant par _ : ignorées par le bot …",
  "scyrox_v8": "https://scyrox.com/products/scyrox-v8?bg_ref=Q0rHhhBRNv",
  "atk_a9_nb": "https://www.atk.store/en-fr/products/atk-dragonfly-a9-nb-lightweight-wireless-mouse?country=FR&ref=aze"
}
```

- Les clés qui commencent par `_` (`_lisez_moi`, `_affiliation`, `_sans_lien`) sont de la documentation : le bot les ignore.
- `?country=FR` force l'affichage en euros chez `atk.store` ; `ref=aze` (atk) et `bg_ref=…` (Scyrox) sont les codes d'affiliation.
- Le bot **ne plante pas** si une URL est vide ou absente : le résultat affiche un bouton informatif
  « 🔗 Liens à venir » à la place. Aucun lien n'est inventé par le code.
- Pour retirer ou remplacer un lien : éditez le fichier (FileZilla, clic droit > **Afficher/Éditer**) ou laissez la
  clé de côté. Le fichier est relu à chaque résultat : **aucun redémarrage** n'est nécessaire.

### 2.6 Le `.gitignore`

Le fichier `.gitignore` **est déjà présent dans le dépôt** (il n'y a rien à ajouter). Il protège le dépôt Git
(secrets, environnements virtuels, caches, `state/`). Il ne contrôle pas FileZilla : seul votre choix de fichiers
détermine ce qui est transféré.

### 2.7 Les illustrations : publier les images et renseigner `IMAGES_BASE_URL`

Les 15 images livrées dans `assets/illustrations/` (bannière, triptyques de prises, schémas de bosse et de boutons)
sont référencées par `assets/images.json` **par leur nom de fichier**. Discord exige des adresses publiques en `https://` :
il faut donc les publier, puis indiquer au bot où les trouver.

1. Copier le dossier `assets/illustrations/` dans votre espace web (Alwaysdata sert par défaut le dossier `~/www/`) :

   ```bash
   mkdir -p ~/www/illustrations
   cp ~/MouseDiscord/assets/illustrations/*.png ~/www/illustrations/
   ```

   Variante par lien symbolique (les mises à jour du dépôt sont alors reprises automatiquement) :

   ```bash
   ln -s ~/MouseDiscord/assets/illustrations ~/www/illustrations
   ```

2. Vérifier qu'une image est bien accessible en `https://[compte].alwaysdata.net/illustrations/T08_azemouse_banniere.png`
   (ouvrez l'adresse dans votre navigateur : l'image doit s'afficher, même hors connexion Discord).

3. Dans `.env`, renseigner la base publique (une seule variable, voir §6.5) :

   ```
   IMAGES_BASE_URL=https://[compte].alwaysdata.net/illustrations/
   ```

4. Contrôler : `python tools/check_deployment.py` doit afficher `images configurées : 15/15`.
   Sinon, les `ATTENTION` indiquent la cause exacte (base absente, schéma non `https://`, fichier manquant).

Sans `IMAGES_BASE_URL`, le bot fonctionne normalement mais **aucun embed n'affiche d'image** (aucune erreur, aucun plantage).
Le fichier `assets/images.json` (et le `.env`) est relu à chaque interaction : **aucun redémarrage** n'est nécessaire après
une modification.

---

## 3. Récupérer le code depuis GitHub

Deux méthodes équivalentes. Dans les deux cas, **la branche est `arena/87fafd0d-mousediscord`**.

### Méthode A — Archive ZIP (la plus simple, sans Git)

1. Ouvrez https://github.com/francoiseargaud43-source/MouseDiscord (connecté à votre compte GitHub).
2. Cliquez sur le sélecteur de branche (à gauche, affiche `main` par défaut) et choisissez **`arena/87fafd0d-mousediscord`**.
3. Bouton vert **Code** > **Download ZIP**.
4. Extrayez le ZIP (clic droit > *Extraire tout…* sous Windows). Le dossier obtenu s'appelle en général
   `MouseDiscord-arena-87fafd0d-mousediscord` (le nom exact peut varier : repérez le dossier qui contient `bot.py`).
5. **Dossier racine du projet = le dossier qui contient directement `bot.py`, `config.py`, `cogs/`, `utils/`.**
   C'est ce dossier dont vous transférez le **contenu**.

### Méthode B — `git clone` (si Git est installé sur votre PC)

```bash
git clone --branch arena/87fafd0d-mousediscord https://github.com/francoiseargaud43-source/MouseDiscord.git MouseDiscord-prod
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
| `assets/images.json` | Rien à faire : les 15 images sont déjà référencées par leur nom de fichier | Non |
| `assets/illustrations/` | Transférer le dossier, puis publier les images et renseigner `IMAGES_BASE_URL` (§2.7) | Recommandé |
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
2. Clic droit > **Créer un répertoire** > nom : `MouseDiscord` (si le dossier n'existe pas déjà). Double-cliquez dessus.
   **Vérifiez la barre de chemin : `/home/[compte]/MouseDiscord`.**
3. Dans le panneau gauche, ouvrez le dossier racine du projet (celui qui contient `bot.py`).
4. Sélectionnez **les éléments à transférer** (voir §2.3) :
   - `bot.py`, `config.py`, `requirements.txt`, `README.md`, `.env.example`
   - les dossiers `cogs`, `utils`, `data`, `assets`, `tools`
   - **Ne sélectionnez pas** : `.git`, `tests`, `docs`, `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `.venv`, `state`,
     `__pycache__`, `.pytest_cache`, `.env`.
5. Clic droit sur la sélection > **Téléverser** (ou glisser-déposer vers le panneau droit, dans `/home/[compte]/MouseDiscord`).
   Les dossiers sont transférés **récursivement** (avec leur contenu).
6. Si FileZilla demande quoi faire pour les fichiers existants : **Écraser** (sur un premier déploiement).
7. **Ne pas** utiliser « Synchroniser les répertoires » pour ce transfert : cette fonction peut supprimer des fichiers distants.

> Piège fréquent : sélectionner le dossier `MouseDiscord-…` lui-même au lieu de son contenu crée
> `MouseDiscord/MouseDiscord-…/bot.py`. Le bot ne démarrera pas (voir §11, « No such file or directory »).

### 5.4 Vérifier le transfert

1. Dans le panneau droit, vérifiez que `/home/[compte]/MouseDiscord` contient : `bot.py`, `config.py`, `requirements.txt`,
   `cogs/`, `utils/`, `data/`, `assets/`, `tools/`.
2. Ouvrez `cogs/` : il doit contenir `finder_flow.py` et `mouse_finder.py` (et non un sous-dossier supplémentaire).
3. Consultez l'onglet **File d'attente** (en bas) : aucun transfert ne doit être en erreur (« Échec » ou « Erreur »).
   Relancez les éléments en échec.
4. Taille de contrôle : `data/mouse_db.json` fait environ 122 Ko (36 souris, sources datées incluses).

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
ls ~/MouseDiscord
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
cd ~/MouseDiscord
python -m venv .venv
```

- `cd ~/MouseDiscord` : se placer dans le dossier du projet (`~` = `/home/[compte]`).
- `python -m venv .venv` : crée le dossier `.venv/` (la commande `python` est celle d'Alwaysdata).
- Pour une version précise : `PYTHON_VERSION=3.11 python -m venv .venv`.

Si `.venv/` existe déjà et doit être recréé : `rm -rf ~/MouseDiscord/.venv` puis relancez la commande.

Vérifiez :

```bash
~/MouseDiscord/.venv/bin/python --version
```

### 6.4 Installer les dépendances

Utilisez **le Python de l'environnement virtuel**, avec son chemin complet (ne dépendez pas de l'activation) :

```bash
~/MouseDiscord/.venv/bin/python -m pip install --upgrade pip
~/MouseDiscord/.venv/bin/python -m pip install -r ~/MouseDiscord/requirements.txt
```

- Le premier `pip install --upgrade pip` met seulement à jour l'outil d'installation.
- Le second installe `discord.py` (2.x) et `python-dotenv` (1.x), selon `requirements.txt`.
- Les versions installées sont celles qui satisfont les plages du fichier (ex. `discord.py` 2.7.1 en local).
  Ne mettez pas à jour les dépendances sans raison.
- Pour vérifier :
  ```bash
  ~/MouseDiscord/.venv/bin/python -m pip show discord.py python-dotenv
  ```

Les outils de test (`requirements-dev.txt`) ne sont **pas** nécessaires sur le serveur.

### 6.5 Créer le fichier `.env` sur le serveur

**Méthode recommandée : copier le modèle sur le serveur, puis l'éditer dans FileZilla.**

1. Dans le terminal SSH : `cp ~/MouseDiscord/.env.example ~/MouseDiscord/.env`.
2. Dans FileZilla, panneau droit, ouvrez `/home/[compte]/MouseDiscord` (rafraîchissez la liste si besoin).
3. Clic droit sur `.env` > **Afficher/Éditer**. Remplacez les valeurs par les vôtres, enregistrez, et acceptez le téléversement
   de la version modifiée. (FileZilla édite une copie temporaire locale : fermez-la ensuite et ne la conservez pas.)
   Le contenu à obtenir :

```
DISCORD_TOKEN=[token]
FINDER_CHANNEL_ID=[id-salon]
COMMAND_PREFIX=!
LOCK_FINDER_CHANNEL=true
SESSION_TTL_SECONDS=1800
IMAGES_BASE_URL=https://[compte].alwaysdata.net/illustrations/
```

- `DISCORD_TOKEN` : **obligatoire**. Sans lui, le bot quitte immédiatement avec le message « DISCORD_TOKEN est vide ».
- `FINDER_CHANNEL_ID` : facultatif. Vide ou `0` = `!setup_finder` publie dans le salon où vous tapez la commande.
  Un identifiant non numérique bloque le démarrage avec un message explicite.
- `COMMAND_PREFIX` : facultatif, `!` par défaut.
- `LOCK_FINDER_CHANNEL` : facultatif, `true` par défaut (voir §8.3 pour ses effets).
- `SESSION_TTL_SECONDS` : facultatif, `1800` par défaut (30 min d'inactivité).
- `IMAGES_BASE_URL` : facultatif, mais **nécessaire pour afficher les illustrations** (voir §2.7). Doit commencer par
  `https://` et se terminer par `/`. Sans elle, aucun embed n'affiche d'image (aucun plantage).
- Pas d'espaces autour du `=`, pas de guillemets, une variable par ligne.

**Méthode alternative (terminal)** : éditez `~/MouseDiscord/.env` avec `nano` si l'éditeur est installé (`which nano` pour le vérifier), sinon `vi`.

4. Restreignez les droits du fichier (lisible par vous seul) :

```bash
chmod 600 ~/MouseDiscord/.env
ls -l ~/MouseDiscord/.env
```

La sortie doit commencer par `-rw-------`.

**Option** : vous pouvez aussi définir `DISCORD_TOKEN` dans le champ **variables d'environnement** du service (§7).
Si la même variable est définie aux deux endroits, la valeur de l'environnement du service **prime** sur `.env`.
Choisissez **un seul** endroit pour éviter la confusion.

### 6.6 Contrôler la configuration

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
```

Résultat attendu (exemple de lecture) :
- `[OK]` partout, dont `images configurées : 15/15` si l'étape §2.7 est faite ;
- `[ATTENTION]` pour les liens d'exemple `url.com` (§2.5) et pour `IMAGES_BASE_URL` manquant (§2.7) :
  n'empêche pas le lancement ;
- **`0 erreur(s) bloquante(s).`** : condition pour continuer.

Le script n'affiche jamais la valeur du token. Il contrôle la présence de `DISCORD_TOKEN`, pas sa validité :
la validité est vérifiée par Discord au premier lancement.

---

## 7. Démarrage permanent : Alwaysdata « Services »

Un lancement dans le terminal (`python bot.py`) **s'arrête à la fermeture de votre session SSH**. Pour un fonctionnement
permanent, deux solutions :

- déclarer le bot comme **service** (documentation : https://help.alwaysdata.com/en/docs/web-hosting/services/) —
  fonctionnalité **réservée aux offres payantes**, détaillée aux §7.1–7.6 ;
- ou créer une **tâche planifiée** relançant le bot au premier plan (**Avancé > Tâches planifiées**), disponible sur
  toutes les offres : voir §7.7.

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
| Commande (*command*) | `/home/[compte]/MouseDiscord/.venv/bin/python bot.py` |
| Répertoire de travail (*working directory*) | `/home/[compte]/MouseDiscord` |
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

### 7.5 Le bot est hors ligne / le service est « arrêté » ou « désactivé »

Le redémarrage se fait **dans l'administration Alwaysdata** (ce n'est ni FileZilla, ni le terminal SSH) :

1. Connectez-vous sur `https://admin.alwaysdata.com` > **Advanced > Processes > Services**
   (selon la version de l'interface : **Advanced > Services**). L'entrée `MouseDiscord` et son état sont affichés.
2. Selon l'état :
   - **En cours d'exécution** → action **Redémarrer** (le bot revient en ligne en quelques secondes).
   - **Arrêté** → action **Démarrer**.
   - **Désactivé** → action **Activer**, puis **Démarrer**. Alwaysdata désactive automatiquement un service qui échoue
     plusieurs fois de suite : la cause est à chercher dans les journaux avant de relancer, sinon il retombera.
3. Vérifier dans le journal du service (§7.2) la ligne de démarrage réussie
   (`INFO mouse_discord : Connecté en tant que …`). Le bot apparaît alors **en ligne** dans Discord.
4. Un redémarrage vide les sessions en cours (les menus éphémères répondent « session expirée ») : le message d'accueil
   persistant, lui, reste opérationnel et `state/` est conservé.

Causes de démarrage immédiatement interrompu (les journaux les nomment) :

| Message dans le journal | Cause | Correction |
|---|---|---|
| `DISCORD_TOKEN est vide` | `.env` absent ou ligne vide sur le serveur | Renseigner `DISCORD_TOKEN` (§6.5) |
| `Improper token` / `401 Unauthorized` | Token erroné ou révoqué | Recopier le token depuis le portail développeur Discord |
| `No such file or directory` | Répertoire de travail ou commande du service incorrects | `/home/[compte]/MouseDiscord` et chemin absolu du `.venv` (§7.1) |
| `ModuleNotFoundError` | Dépendances non installées dans le venv | §6.4 |

> Ne lancez **pas** en même temps un `python bot.py` dans le terminal SSH et le service : deux instances du même bot
> se disputent Discord (§9).

### 7.6 Toutes les commandes SSH utiles (relancer et vérifier)

À copier-coller dans le terminal SSH (`ssh aze129@ssh-aze129.alwaysdata.net`). Remplacez `aze129` par votre compte
et `APIKEY` par un token créé dans l'administration (**Profil > Tokens**).

**A. Vérifications avant de relancer**

```bash
cd ~/MouseDiscord

# 1. Une seule instance tourne-t-elle ? (une seule ligne attendue)
ps -ef | grep "[b]ot.py"

# 2. Version de Python du venv et dépendances importables
.venv/bin/python -V
.venv/bin/python -c "import discord, dotenv; print('discord.py', discord.__version__)"

# 3. Contrôle complet : fichiers, token (jamais affiché), catalogue, liens, images, state/
.venv/bin/python tools/check_deployment.py       # attendu : 0 erreur(s) bloquante(s)

# 4. Les 15 illustrations sont-elles en place, et le .env est-il protégé ?
ls assets/illustrations | wc -l                  # attendu : 15
ls -l .env                                       # attendu : -rw-------  (et non rw-r--r--)

# 5. JSON valides (une erreur de syntaxe ne fait pas tomber le bot mais bloque le parcours)
for f in data/mouse_db.json data/commercial_links.json assets/images.json; do   .venv/bin/python -m json.tool "$f" > /dev/null && echo "OK   $f" || echo "ERREUR $f"; done
```

**B. Vérifier que le jeton Discord est valide (le token n'est jamais affiché)**

```bash
cd ~/MouseDiscord
set -a; . ./.env; set +a
curl -s -H "Authorization: Bot $DISCORD_TOKEN" https://discord.com/api/v10/users/@me   | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print('Bot joignable :', d.get('username'), '(id', str(d.get('id')) + ')') if 'username' in d else print('REFUS DE DISCORD :', d)"
unset DISCORD_TOKEN
```

- `Bot joignable : …` : le token est bon, Discord accepte le bot.
- `REFUS DE DISCORD : {'message': '401: Unauthorized', …}` : token erroné ou révoqué → `Reset Token` dans le portail,
  puis mettre à jour `.env` (§6.5) et reprendre en B.

**C. Relancer le service depuis SSH (API Alwaysdata)**

```bash
# 1. Trouver l'identifiant du service et son état
curl -s --basic --user "APIKEY account=aze129:" https://api.alwaysdata.com/v1/service/   | .venv/bin/python -m json.tool

# 2. Redémarrer (remplacer 1234 par l'« id » trouvé ci-dessus)
curl -X POST --basic --user "APIKEY account=aze129:" https://api.alwaysdata.com/v1/service/1234/restart/

# 3. Si le service est désactivé, le réactiver d'abord
curl -X PATCH --basic --user "APIKEY account=aze129:"   -d "is_disabled=false" https://api.alwaysdata.com/v1/service/1234/
```

La même opération est disponible sans SSH dans l'administration : **Advanced > Processes > Services** (§7.5).

**D. Suivre le démarrage**

```bash
ls -lt ~/admin/logs/services/ | head            # repérer le fichier le plus récent
tail -n 50 ~/admin/logs/services/[fichier]      # attendu : INFO mouse_discord : Connecté en tant que …
tail -f ~/admin/logs/services/[fichier]         # suivi en direct (Ctrl+C pour quitter)
```

**E. Vérifier que les illustrations sont bien publiées**

```bash
ls -l ~/www/illustrations | head                # attendu : les 15 fichiers T0*.png
curl -s -o /dev/null -w "%{http_code}
" https://aze129.alwaysdata.net/illustrations/T08_azemouse_banniere.png
# attendu : 200
```

Un `404` signifie que le dossier `www/illustrations` est mal placé (il doit être à la racine de votre compte, à côté de
`www`) ou mal nommé. Un `403` vient en général des droits : `chmod 755 ~/www ~/www/illustrations`.

**F. Test manuel en avant-plan (uniquement service ARRÊTÉ)**

```bash
pkill -f "bot.py"                              # sécurité : aucune instance ne doit rester
cd ~/MouseDiscord && .venv/bin/python bot.py   # lance le bot au premier plan : les erreurs s'affichent ici
# Ctrl+C pour arrêter, puis relancer le service (§7.5 ou commande C)
```

> Ne lancez jamais ce test pendant que le service tourne : deux instances du même bot se disputent Discord (§9).
> Un service qui se fait tuer sans raison remonte tout seul ; s'il échoue plusieurs fois, Alwaysdata le **désactive**.

### 7.7 Mode « tâches planifiées » (sans service)

Si le compte n'utilise pas de **service** (fonctionnalité payante) mais une **tâche planifiée**
(**Avancé > Tâches planifiées**, démon `aljob`), le fonctionnement est le suivant :

| Point | Conséquence |
|---|---|
| La tâche exécute en boucle `…/MouseDiscord/.venv/bin/python bot.py` **au premier plan** | Tant que le bot tourne, son exécution est « en cours » |
| `aljob` **ignore** un nouveau lancement si l'exécution précédente n'est pas terminée | C'est ce qui empêche deux instances du même bot de tourner en parallèle |
| Si le bot s'arrête (plantage), la prochaine occurrence de la tâche le relance | Une fréquence courte (toutes les minutes / 5 minutes) = **redémarrage automatique** |
| Les journaux sont dans `~/admin/logs/jobs/` (et non `services/`) | `ls -lt ~/admin/logs/jobs/ | head` puis `tail -n 60 ~/admin/logs/jobs/[fichier]` |
| Les processus en cours sont listés dans **Avancé > Processus > Tâches planifiées** | Contrôle visuel équivalent à `ps -ef | grep "[b]ot.py"` |

**Commandes utiles**

```bash
# Le bot tourne-t-il ? (une seule ligne attendue)
ps -ef | grep "[b]ot.py"

# Que disent les journaux de la tâche ? (démarrage, sortie du bot, arrêt)
ls -lt ~/admin/logs/jobs/ | head
tail -n 60 ~/admin/logs/jobs/[fichier-le-plus-recent]
```

**Arrêter / relancer le bot**

| Objectif | Marche à suivre |
|---|---|
| **Redémarrer** (après une mise à jour du code) | `pkill -f "bot.py"` en SSH, puis attendre la prochaine occurrence de la tâche (≤ 1 min si la fréquence est « toutes les minutes ») |
| **Forcer un lancement immédiat** | Mettre temporairement la fréquence de la tâche sur « toutes les minutes » dans **Avancé > Tâches planifiées**, enregistrer, puis attendre la minute en cours |
| **Arrêter durablement** | Désactiver la tâche dans l'administration puis `pkill -f "bot.py"` |
| **Ne jamais faire** | Lancer `python bot.py` à la main pendant que la tâche est active : `aljob` ne voit pas ce processus et lancerait une **seconde** instance au prochain créneau (§9) |

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
`~/MouseDiscord/state/finder_message.json` : ce dossier doit rester sur le serveur (ne pas le supprimer, §12.1).

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
cd ~/MouseDiscord
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
- [ ] Les boutons d'achat **sans lien** : un seul bouton « 🔗 Liens à venir » (désactivé), aucune erreur.
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
| `DISCORD_TOKEN est vide` | `.env` absent, mal nommé ou token non renseigné | Vérifiez `ls -l ~/MouseDiscord/.env` et son contenu (§6.5). Le fichier doit s'appeler exactement `.env` |
| `LoginFailure` / « Improper token » | Token incorrect ou révoqué | Reset Token dans le portail, mettez à jour `.env`, redémarrez |
| `PrivilegedIntentsRequired` | Message Content Intent désactivé dans le portail | Activez-le (§8.1), redémarrez |
| `ConfigError` / « doit être un nombre entier » | `FINDER_CHANNEL_ID` ou `SESSION_TTL_SECONDS` mal saisi | Corrigez `.env` (chiffres seulement) |
| `ModuleNotFoundError: No module named 'discord'` | Service lancé avec le mauvais Python, ou dépendances non installées | Utilisez `/home/[compte]/MouseDiscord/.venv/bin/python` ; réinstallez (§6.4) |
| `No such file or directory: 'bot.py'` ou `can't open file` | Commande ou répertoire de travail incorrect ; ou dossier intermédiaire (§5.3) | Vérifiez §7.1 et que `bot.py` est directement dans `MouseDiscord` |
| `Cannot connect to host discord.com` | Pas d'accès réseau sortant au moment du démarrage | Relancez le service ; si le problème persiste, contactez le support Alwaysdata |
| `Forbidden` / « Le bot ne peut pas écrire » | Permissions du bot insuffisantes dans le salon | Vérifiez les permissions du salon et du rôle du bot (§8.2) |
| `Impossible de verrouiller le salon` (dans le message de `!setup_finder`) | Permission « Gérer les permissions » absente au niveau du salon | Ajoutez-la au bot sur ce salon, ou mettez `LOCK_FINDER_CHANNEL=false` |
| `Permission denied` sur `state/` | Droits d'écriture insuffisants | `mkdir -p ~/MouseDiscord/state && chmod u+rwx ~/MouseDiscord/state` |
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

> **Lire les « attendu : N passed » comme des repères datés.** Chaque section `12.x` décrit la mise à jour de son jour, avec le nombre de tests de ce jour-là : le compteur **augmente** au fil des mises à jour (391 → 395 → 403 → 409 → 488 aujourd'hui). Seul le compteur de la **dernière** section est le bon ; dans les sections plus anciennes, ce n'est pas une erreur si votre `pytest -q` affiche davantage de tests.

### 12.1 Ce qui ne doit JAMAIS être écrasé

| Élément sur le serveur | Pourquoi le protéger |
|---|---|
| `~/MouseDiscord/.env` | Token et réglages propres au serveur |
| `~/MouseDiscord/data/commercial_links.json` | **Liens d'achat** : depuis le 2026-10-11, le dépôt contient les liens officiels vérifiés (36 depuis le 2026-10-12) — c'est donc le fichier du dépôt qu'il faut installer (§12.9). Ne l'écrasez avec une version plus ancienne que si vous y avez ajouté vos propres liens à la main (comparez d'abord, §2.5) |
| `~/MouseDiscord/assets/images.json` | Conservé **seulement** si vous y avez mis vos propres URL. Depuis le 2026-10-11, le fichier du dépôt contient les clés attendues et les noms de fichiers des 15 illustrations : c'est **lui** qu'il faut installer (voir §12.5) |
| `~/MouseDiscord/state/` | Mémoire du message d'accueil (évite les doublons) |
| `~/MouseDiscord/.venv/` | Environnement Python du serveur |

### 12.2 Procédure pas à pas

1. **Sauvegarde** (sur le serveur, SSH) :
   ```bash
   mkdir -p ~/backup-mousediscord
   cp -a ~/MouseDiscord ~/backup-mousediscord/MouseDiscord-$(date +%Y-%m-%d)
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
   `data/commercial_links.json`, `data/mouse_db.json` ou `assets/images.json`, ce sont des **données mises à jour dans le dépôt**
   (liens, catalogue, images) : elles se transfèrent comme le reste, **sans redémarrage** (§12.3). Le raccourci pour la mise à jour
   du 2026-10-11 est au §12.9.
4. **Transférer** : FileZilla, panneau gauche (nouvelle version) > panneau droit (`~/MouseDiscord`), uniquement les fichiers modifiés,
   en « Écraser ». Ne pas « Synchroniser ».
5. **Dépendances** : si `requirements.txt` a changé :
   ```bash
   ~/MouseDiscord/.venv/bin/python -m pip install -r ~/MouseDiscord/requirements.txt
   ```
6. **Contrôle** : `~/MouseDiscord/.venv/bin/python ~/MouseDiscord/tools/check_deployment.py` → `0 erreur(s)`.
7. **Redémarrage** : nécessaire si vous avez modifié **un fichier Python** (`bot.py`, `config.py`, `cogs/`, `utils/`), **`.env`**,
   ou `requirements.txt`.
   - **Service** : action *Redémarrer* (§7.3).
   - **Tâche planifiée** : `pkill -f "bot.py"` puis attendre le prochain créneau (≤ 1 min si la tâche est « toutes les
     minutes ») : le nouveau code est alors chargé (§7.7).
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
| `bot.py`, `cogs/*.py`, `utils/*.py` | Non : chargés au démarrage | **Redémarrer** (service : §7.3 ; tâche planifiée : `pkill -f "bot.py"` puis attente du prochain créneau, §7.7) |
| `requirements.txt` | Non | Installer (§12.2 étape 5) puis **redémarrer** |
| Texte du message d'accueil (code) | Non : publié dans Discord | Redémarrer puis `!setup_finder` |

Un fichier JSON **invalide** modifié à chaud ne fait pas tomber le bot, mais les parcours concernés affichent une erreur
jusqu'à correction : vérifiez toujours avec `check_deployment.py` avant d'enregistrer un JSON modifié.

### 12.7 Transférer sans FileZilla : `scp` depuis Windows (méthode de secours)

Windows 10/11 intègre le client `scp` : une seule commande PowerShell remplace un glisser-déposer complet, ce qui évite
les transferts partiels (cause typique de l'erreur `ImportError: cannot import name …`).

1. Ouvrez **PowerShell** et placez-vous dans le dossier téléchargé (celui qui contient `bot.py`) :
   ```powershell
   cd "$env:USERPROFILE\Downloads\"
   dir MouseDiscord*        # repérez le nom exact du dossier téléchargé
   cd .\MouseDiscord-arena-87fafd0-…    # Tabulation complète le nom
   dir bot.py, cogs, utils, assets, config.py, tools   # les 6 éléments doivent apparaître
   ```
2. Envoyez uniquement les éléments de la mise à jour (jamais `.env`, `state/`, `.venv/`) :
   ```powershell
   scp -r cogs utils assets config.py tools data aze129@ssh-aze129.alwaysdata.net:/home/aze129/MouseDiscord/
   ```
   `data` ne se justifie que si le catalogue ou les liens ont changé (c'est le cas de la mise à jour
   du 2026-10-11, §12.9) ; `scp -r` **fusionne** les dossiers et n'efface rien d'autre.
   - Mot de passe : celui de votre **utilisateur SSH** Alwaysdata (pas le mot de passe du compte).
   - Au premier essai : `Are you sure you want to continue connecting?` → tapez `yes`.
   - `scp -r` **fusionne** les dossiers et remplace les fichiers ; il ne supprime rien d'autre.
3. Contrôlez le résultat avec les six `grep` du §12.6 : les six lignes doivent afficher `OK`.
4. Puis : `IMAGES_BASE_URL` dans `.env` (§2.7), `.venv/bin/python tools/check_deployment.py`, redémarrage du service (§7.5).

Si `scp` n'est pas reconnu (« n'est pas reconnu en tant que commande »), utilisez la méthode FileZilla du §12.5 :
les fichiers de ce dossier doivent être vus dans le **panneau droit, à l'intérieur de `MouseDiscord`**.

### 12.8 Transférer sans aucun outil PC (navigateur uniquement)

Utile si `scp`/PowerShell ne sont pas disponibles et que le glisser-déposer pose problème : il suffit d'un navigateur.
Alwaysdata ne propose **pas** de gestionnaire de fichiers web ; l'accès aux fichiers se fait par FTP/SFTP/SSH.

Principe : faire héberger temporairement le fichier par Discord (déjà utilisé pour le bot), puis le télécharger sur le
serveur par une commande `curl`.

1. Dans Discord, ouvrez un salon ou un message privé et **joignez le fichier** (par exemple `models.py`).
2. Clic droit sur le fichier envoyé > **Copier le lien** (mobile : appui long > « Copier le lien »).
   Le lien ressemble à `https://cdn.discordapp.com/attachments/…/models.py?ex=…&is=…&hm=…`.
3. Dans le terminal SSH web (`https://ssh-[compte].alwaysdata.net`) :

   ```bash
   cd ~/MouseDiscord
   curl -Lo utils/models.py "COLLEZ_ICI_LE_LIEN"      # guillemets obligatoires : le lien contient des « & »
   ```

   Répétez pour chaque fichier en adaptant le chemin de destination (`utils/models.py`, `utils/session.py`,
   `utils/assets.py`, `assets/images.json`).
4. Contrôlez immédiatement avec les six `grep` du §12.6 : ce qui a été récupéré doit afficher `OK`.

Limites : les liens Discord sont **temporaires** (quelques heures à 24 h) et publics tant qu'ils sont valides — ne
partagez pas ces URL, et supprimez le message Discord une fois le transfert terminé. Pour un transfert durable, préférez
FileZilla (§12.5), `scp` (§12.7) ou la sauvegarde Alwaysdata.

### 12.4 Retour arrière

En cas de problème : arrêtez le service, recopiez le dossier sauvegardé (§12.2 étape 1) à la place de `~/MouseDiscord`
(en conservant `.env`, vos liens et `state/` si vous ne les avez pas modifiés), puis redémarrez le service.

---

### 12.5 Refonte visuelle du 2026-10-11 : quels éléments glisser dans FileZilla (raccourci)

Cas concerné : `~/MouseDiscord` **existe déjà** et fait tourner une version antérieure. **Ne glissez pas le dossier
téléchargé tel quel** dans la racine du serveur : cela créerait `~/MouseDiscord-arena-…/` à côté du dossier utilisé par le
service, qui continuerait d'exécuter l'ancien code (piège classique, voir §5.3).

1. Panneau **droit** : double-cliquez sur `MouseDiscord` (le dossier existant) ; la barre de chemin doit indiquer
   `…/MouseDiscord`.
2. Panneau **gauche** : ouvrez le dossier téléchargé (celui qui contient `bot.py`).
3. Sélectionnez et glissez **six éléments seulement**, directement dans `MouseDiscord`.

| Élément | Transférer ? | Raison |
|---|---|---|
| `bot.py`, `config.py` | Oui | Configuration et point d'entrée à jour |
| `cogs/`, `utils/` | Oui | Parcours 4 étapes, charte, résolution des images |
| `assets/` | Oui | `images.json` (nouvelles clés) **et** `illustrations/` (les 15 PNG) |
| `tools/` | Oui (recommandé) | `check_deployment.py` contrôle la nouvelle variable `IMAGES_BASE_URL` |
| `data/` | **Non** | Inchangé par cette mise à jour ; le transférer écraserait vos liens d'achat |
| `README.md`, `requirements.txt` | Non (facultatif) | Documentation ; dépendances inchangées |
| `docs/`, `tests/`, `ImageAct/`, `ImageEx/`, `ImageUse/`, `Reverse/`, `pytest.ini`, `requirements-dev.txt` | **Non** | Utiles au développement seulement (**≈ 10 Mo** mesurés le 2026-10-13, inutiles sur le serveur) |
| `.env`, `.venv/`, `state/`, `__pycache__/`, `bot.log` | **Jamais** | Secrets, environnement Python et mémoire du panneau, propres au serveur |

4. Conflits de fichiers : **Écraser**, en cochant « Toujours utiliser cette action » (jamais « Synchroniser les répertoires »).

Puis, dans cet ordre :

1. **Publier les illustrations** : panneau droit, clic droit sur `www` > **Créer un répertoire** `illustrations`, puis
   glissez-y les 15 fichiers de `assets\illustrations`. Vérifiez dans un navigateur que l'image s'affiche :
   `https://[compte].alwaysdata.net/illustrations/T08_azemouse_banniere.png`.
2. **`.env`** : clic droit sur `.env` > **Afficher/Éditer**, ajoutez la ligne
   `IMAGES_BASE_URL=https://[compte].alwaysdata.net/illustrations/`, enregistrez et acceptez le téléversement.
   Ne remplacez jamais ce fichier par celui du dépôt (il ne contient pas votre token).
3. **Redémarrer le service** (§7.3) : le code Python et `.env` sont lus au démarrage.
4. Dans Discord, taper **une fois** `!setup_finder` : le message d'accueil existant est **édité** (nouvelle bannière
   `T08`), sans créer de doublon.

Contrôle final (SSH) : `~/MouseDiscord/.venv/bin/python ~/MouseDiscord/tools/check_deployment.py` doit afficher
`images configurées : 15/15` et `0 erreur(s) bloquante(s)`.

### 12.6 Contrôle de cohérence après un transfert (éviter un transfert partiel)

Un transfert incomplet ne se voit pas tout de suite : le service démarre alors sur un mélange d'anciens et de nouveaux
fichiers, puis échoue avec une erreur du genre
`ImportError: cannot import name 'THENAR_LABELS' from 'utils.models'`
(nouveau `cogs/finder_flow.py` + ancien `utils/models.py`). Après **tout** transfert de mise à jour, lancez ce contrôle :

```bash
cd ~/MouseDiscord
grep -q THENAR_LABELS utils/models.py         && echo "OK   utils/models.py (thénar)"        || echo "ANCIEN utils/models.py"
grep -q thenar utils/session.py               && echo "OK   utils/session.py (thénar)"       || echo "ANCIEN utils/session.py"
grep -q IMAGES_BASE_URL config.py             && echo "OK   config.py (IMAGES_BASE_URL)"    || echo "ANCIEN config.py"
grep -q build_image_url utils/assets.py       && echo "OK   utils/assets.py (résolution)"   || echo "ANCIEN utils/assets.py"
grep -q step2_thenar assets/images.json       && echo "OK   assets/images.json (clés)"      || echo "ANCIEN assets/images.json"
grep -q thenar_step_embed cogs/finder_flow.py && echo "OK   cogs/finder_flow.py (étapes)" || echo "ANCIEN cogs/finder_flow.py"
grep -q "Vos repères de taille" cogs/finder_flow.py && echo "OK   cogs/finder_flow.py (résultat épuré)" || echo "ANCIEN cogs/finder_flow.py (résultat)"
grep -q claw_variant_embed cogs/finder_flow.py && echo "OK   cogs/finder_flow.py (variante de Claw)" || echo "ANCIEN cogs/finder_flow.py (variante)"
grep -q SHAPES utils/models.py                && echo "OK   utils/models.py (forme de coque)" || echo "ANCIEN utils/models.py (forme)"
grep -q claw_variant utils/session.py         && echo "OK   utils/session.py (variante de Claw)" || echo "ANCIEN utils/session.py (variante)"
grep -q "SHAPES" utils/catalog.py             && echo "OK   utils/catalog.py (forme sourcée)" || echo "ANCIEN utils/catalog.py (forme)"
grep -q PEU_IMPORTE_PRIX utils/selection.py   && echo "OK   utils/selection.py (peu importe le prix)" || echo "ANCIEN utils/selection.py (modes)"
grep -q ResultsView bot.py                     && echo "ANCIEN bot.py (vue supprimée — à remplacer)" || echo "OK   bot.py"
```

Les **treize lignes** doivent afficher `OK`. Une ligne `ANCIEN …` signale un fichier non transféré : reprenez le transfert
du dossier correspondant (`utils/`, `assets/`, `cogs/`, `config.py`) avant de démarrer le service. Le contrôle
`tools/check_deployment.py` complète ce diagnostic (fichiers, token, JSON, images, `state/`).

### 12.9 Mise à jour du 2026-10-11 : catalogue enrichi, prix en euros, liens d'achat (raccourci)

Cas concerné : `~/MouseDiscord` tourne déjà la refonte visuelle, et vous voulez la mise à jour
« catalogue enrichi · prix officiels en euros · liens d'achat · boutons alignés sur la vidéo Oblivity »
(26 souris et 26 liens le 2026-10-11 ; **36 et 36** depuis l'ajout des dix Pulsar le 2026-10-12, voir le bloc
« Nouveauté 2026-10-12 » plus bas).

**1. Ce qui a changé depuis la refonte visuelle**

| Élément | Nature | Redémarrage nécessaire ? |
|---|---|---|
| `bot.py` | Code : supprime l'enregistrement de la vue persistante des boutons retirés — **obligatoire** : l'ancien `bot.py` référence `ResultsView.persistent()`, qui n'existe plus | **Oui** |
| `cogs/finder_flow.py` | Code : parcours (étape « variante de Claw » en plus), résultat épuré (recommandation courte, puis blocs illustrés : repères de taille, arrière étroit, bosse et forme, variante de Claw, hauteur des boutons), boutons d'achat uniquement | **Oui** |
| `utils/models.py`, `utils/session.py` | Code : forme de coque (`shape`), variante de Claw (collectée, jamais notée) | **Oui** |
| `utils/catalog.py` | Code : une forme de coque renseignée doit citer la source qui l'atteste | **Oui** |
| `utils/selection.py` | Code : **cinquième mode « Peu importe le prix »** (la forme d'abord, puis les composants documentés ; le prix n'est jamais exigé) | **Oui** |
| `utils/matcher.py` | Code : barème des boutons aligné sur Oblivity ; ajustement thénar **en pause (0 / 0 / 0, bosse arrière) depuis le 2026-10-12** — voir §12.11 | **Oui** |
| `data/mouse_db.json` | Données : 36 souris vendues (26 ATK/VXE/Scyrox + 10 Pulsar), prix en euros, forme de coque sourcée, sources datées | Non (relu à chaque recherche) |
| `data/commercial_links.json` | Données : 36 liens officiels (les URL `https://url.com/…` ont disparu) | Non (relu à chaque résultat) |
| `tools/check_deployment.py` | Outil de contrôle | Non |

`assets/images.json` (libellés des 15 illustrations) accompagne `data/mouse_db.json` : sans lui, les blocs illustrés
du résultat ne trouvent pas leurs images. `config.py`, les autres fichiers de `utils/` et `requirements.txt` sont
**inchangés** : inutile de les retransférer.

**2. FileZilla — onze fichiers à glisser dans `~/MouseDiscord`**

Ouvrez le dossier téléchargé à gauche, `~/MouseDiscord` à droite, puis glissez (conflits : **Écraser**,
jamais « Synchroniser les répertoires ») :

```
bot.py
cogs/finder_flow.py
utils/catalog.py
utils/matcher.py
utils/models.py
utils/selection.py
utils/session.py
data/mouse_db.json
data/commercial_links.json
assets/images.json
tools/check_deployment.py
```

> Doute sur la version qui tourne sur le serveur ? Glissez aussi `bot.py`, `config.py`, `utils/` et `assets/`
> (transfert complet : il ne casse rien, il écrase par des fichiers identiques ou plus récents).

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 0 erreur(s) bloquante(s)
```

**4. Redémarrage** (nécessaire : plusieurs fichiers Python ont changé) — mode tâche planifiée :

```bash
pkill -f "bot.py"                 # la tâche planifiée relance le bot au prochain créneau (≤ 1 min)
ps -ef | grep "[b]ot.py"          # une seule ligne = une seule instance
ls -lt ~/admin/logs/jobs/ | head  # le journal du jour confirme le redémarrage
```

Aucun `!setup_finder` n'est nécessaire : le texte et le bouton du message d'accueil n'ont pas changé.

> **Résultat** : « ✖️ Fermer », « 🔄 Refaire le test » et « 🔍 Détails » ont été **retirés** (2026-10-11) : ces
> boutons interactifs pouvaient cesser de répondre après un redémarrage du bot (« AzeMouse n'a pas répondu à
> temps »). Le résultat ne porte plus que les boutons d'achat — des **liens** gérés par Discord, qui fonctionnent
> toujours. Le contenu de l'ancien onglet « Détails » n'est pas perdu : il s'affiche **dans le même message, plus
> bas**, en petits blocs illustrés (repères de taille, arrière étroit si thénar « Petite », bosse, variantes de
> Claw, hauteur des boutons). Un résultat affiché **avant** la mise à jour garde ses anciens boutons : relancez un
> test pour obtenir un message à jour.
>
> **Nouveauté 2026-10-11 (4ᵉ passe)** : le parcours Claw gagne une étape « variante » (2/5) et le résultat un bloc
> « ⛰️ La bosse et la forme » (forme symétrique/ergonomique, bosse adaptée à la variante). `utils/session.py` et
> `data/mouse_db.json` font donc partie du transfert.
>
> **Nouveauté 2026-10-11 (6ᵉ passe)** : le catalogue documente désormais les **switchs**, le **MCU**
> et le **poids** des souris (36/36 pour le poids) ; le poids s'affiche sur la ligne du match idéal et de
> l'alternative, et le départage du mode « Peu importe le prix » suit capteur → MCU → switchs → fréquence.
> `data/mouse_db.json`, `utils/models.py`, `utils/selection.py` et `cogs/finder_flow.py` sont à jour dans la liste.
>
> **Nouveauté 2026-10-11 (5ᵉ passe)** : le menu de l'étape budget gagne **« Peu importe le prix »**
> (la forme d'abord ; à score égal, les composants documentés, puis le prix le plus bas — le montant
> s'affiche en tout petit). Le bot démarre sans `utils/selection.py` à jour, mais l'option répondrait
> « Aucune souris éligible » : ce fichier fait partie du transfert.
>
> **Nouveauté 2026-10-12 (9ᵉ passe)** : dix souris **Pulsar** entrent au catalogue (X2 v3 Mini, X2H v3 Mini,
> X2A v3, X2 CrazyLight Medium et Mini, X2H CrazyLight Mini, Xlite CrazyLight Medium, Xlite v4 Mini,
> Medium et Large), relevées sur la fiche officielle de chaque modèle (dimensions, poids, capteur XS-1,
> fréquence publiée, switchs, forme, recommandations de prise).
> `data/mouse_db.json`, `data/commercial_links.json`, `utils/models.py` (statut `manufacturer_guide`) et
> `utils/selection.py` (rang du capteur Pulsar XS-1, départage uniquement) sont à jour dans la liste.
> Le contrôle attend alors **36 souris / 36 liens** ; le profil Palm 180 × 90 mm ne change pas de résultat,
> mais le Claw et le Fingertip proposent désormais des Pulsar.
>
> **Le fichier `utils/catalog.py` fait partie du transfert** depuis cette mise à jour : il vérifie qu'une forme de
> coque renseignée s'appuie sur une source. Sans lui, `data/mouse_db.json` se charge encore (la forme est ignorée) :
> le bot démarre, mais le bloc « ⛰️ La bosse et la forme » annonce « non vérifiée » pour toutes les souris.

### 12.10 Mise à jour du 2026-10-12 : plus d'impasse dans le parcours (raccourci)

**Ce que corrige cette mise à jour.** Des pannes constatées en usage réel : après un redémarrage du bot (ou après
un certain temps), un menu du parcours ne répondait plus, ou répondait « ce parcours n'est plus actif », et il fallait
tout recommencer depuis le panneau. Causes trouvées et corrigées : composants des étapes non enregistrés au démarrage
et identifiants aléatoires, parcours gardés en mémoire seulement, seul le bouton du panneau avait un gestionnaire
d'erreur — donc toute erreur ailleurs restait silencieuse. Analyse complète, preuves et liste de contrôle :
`docs/audit/ROBUSTESSE_2026-10-12.md`. **Aucun barème, prix, donnée de souris ni texte de résultat n'a changé.**

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
bot.py
config.py
cogs/finder_flow.py
cogs/mouse_finder.py
utils/session.py
utils/catalog.py
utils/assets.py
utils/validation.py
.env.example
docs/audit/ROBUSTESSE_2026-10-12.md        (facultatif : documentation)
docs/audit/AUDIT_CONFIDENTIALITE.md        (facultatif : documentation)
README.md                                  (facultatif : documentation)
tools/qa_flow_matrix.py                    (facultatif : banc d'essai du moteur, 0 problème constaté)
```

`data/mouse_db.json`, `data/commercial_links.json` et `assets/images.json` **ne changent pas** dans cette mise à jour.

**2. Rien à ajouter au `.env`** (la valeur par défaut suffit) — mais voici la nouvelle variable si vous voulez la fixer :

```bash
SESSION_PERSIST=true        # true (défaut) = un parcours commencé survit à un redémarrage du bot
                            # false          = tout en mémoire, comme avant
```

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 0 erreur(s) bloquante(s)

# le fichier d'état doit pouvoir s'écrire (dossier state/ ignoré par Git, créé au besoin)
grep -q SESSION_PERSIST config.py && echo "OK   config.py (persistance des parcours)" || echo "ANCIEN config.py"
grep -q "state/sessions" config.py >/dev/null && echo "OK   chemin state/sessions.json" || echo "ANCIEN config.py"
grep -q "persistent_views" bot.py && echo "OK   bot.py (composants durables)" || echo "ANCIEN bot.py"
grep -q "storage_path" utils/session.py && echo "OK   utils/session.py (nouveau magasin)" || echo "ANCIEN utils/session.py"
```

**4. Redémarrage** (nécessaire : plusieurs fichiers Python ont changé)

```bash
pkill -f "bot.py"                 # la tâche planifiée relance le bot au prochain créneau (≤ 1 min)
ls -lt ~/admin/logs/jobs/ | head  # le journal doit afficher « Composants durables enregistrés : 8 »
```

**5. Vérification en 60 secondes dans Discord** (les quatre cas qui échouaient)

1. Lancer un parcours avec le bouton du panneau → **le premier menu doit s'afficher**.
2. Choisir une prise, puis, **sans terminer**, redémarrer le bot (`pkill -f "bot.py"`, attendre la relance) et
   cliquer dans le menu affiché → **la question suivante doit s'afficher** (avant : « plus actif » ou silence).
3. Terminer le parcours, puis **cliquer deux fois** sur le dernier menu → **le même résultat deux fois**, sans
   message d'expiration.
4. Laisser un parcours de côté plus de 30 minutes, puis cliquer dans son menu → message **« Ce parcours a expiré »**
   avec le **bouton de reprise** juste en dessous : un clic et le parcours repart, sans revenir au panneau.

> Sur le cas 4, la reprise se fait dans le message lui-même : aucun retour au panneau du salon n'est nécessaire.
> Si un cas échoue, le journal (`~/admin/logs/jobs/` ou `~/admin/logs/services/`) contient la raison exacte
> (chaque incident est tracé avec le parcours, l'étape et l'action).

---

### 12.11 Mise à jour du 2026-10-12 (2e) : le thénar ne modifie plus le score, coques corrigées

**Ce que corrige cette mise à jour.** Deux défauts trouvés dans le résultat lui-même (détail, preuves et
mesures : `docs/audit/ROBUSTESSE_2026-10-12.md` §7) :

1. **Le thénar modifiait le score et la recommandation** alors que le README, le `MASTER_PROMPT` §7.6 et
   l'audit promettent « aucun effet sur le score ». Mesure : **537 profils sur 2 805 (19,1 %)** changeaient
   de réponse selon la taille de thénar déclarée. Les trois valeurs de l'ajustement sont désormais **à 0** :
   le thénar reste demandé, affiché et expliqué, mais il ne change plus rien au calcul (après correction :
   **0 profil sur 2 805**).
2. **Deux entrées de la même coque pouvaient être proposées ensemble** (« le match idéal » puis
   « l'alternative » = la même souris) : **92 profils** concernés (A9 Plus 2.0 + A9 NB Ultra ; X2A v3 +
   X2 CrazyLight Medium). Les coques déjà documentées sont maintenant enregistrées dans le catalogue.

> **Les résultats peuvent donc changer** par rapport à la version en ligne : c'est précisément l'objet de la
> correction. Les barèmes de longueur, de largeur, de prise, de bosse et de boutons sont **inchangés**, ainsi
> que les prix et les liens d'achat.

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
utils/matcher.py                     (décisif : l'ajustement thénar passe à 0 / 0 / 0)
cogs/finder_flow.py                  (décisif : textes de l'étape thénar et du bloc « arrière étroit »)
data/mouse_db.json                   (décisif : coques partagées enregistrées — 36 souris)
tools/build_mouse_db.py              (facultatif : garde-fou, le script ne peut plus écraser le catalogue)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : documentation, §7)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md   (facultatif : tableau statistique complet)
docs/REVERSE_ENGINEERING_OBLIVITY.md (facultatif : la décision de pause y est consignée)
```

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 0 erreur(s) bloquante(s)

# l'ajustement thénar doit être en pause (0 / 0 / 0)
grep -q "THENAR_WIDTH_ADJUSTMENT = {Thenar.PETITE: 0" utils/matcher.py \
  && echo "OK   utils/matcher.py (thénar sans effet sur le score)" || echo "ANCIEN utils/matcher.py"

# les coques partagées doivent être enregistrées (23 souris sur 36, 14 coques distinctes)
.venv/bin/python -c "import json; d=json.load(open('data/mouse_db.json')); \
  print(sum(1 for m in d if m.get('shell_id')), 'souris avec shell_id')"   # attendu : 23
```

**4. Redémarrage**

```bash
pkill -f "bot.py"                 # la tâche planifiée relance le bot au prochain créneau (≤ 1 min)
```

**5. Vérification en 60 secondes dans Discord**

1. Faire un parcours en choisissant « Thénar Petite » puis, avec les **mêmes mesures**, un second parcours
   avec « Thénar Grande » → **les deux réponses doivent être identiques** (avant : elles pouvaient différer).
2. À l'étape du thénar, le texte doit dire **« le thénar ne modifie pas le score »** (avant : « Effet borné à
   ±2 points »).
3. Sur une main 190 × 105 en **Palm**, puis en recliquant sur le même profil → **jamais deux fois la même
   souris** dans les deux ou trois places (le cas « A9 Plus 2.0 » + « A9 NB Ultra » ne doit plus apparaître).

---

### 12.12 Mise à jour du 2026-10-12 (3e) : les trois places ont chacune leur fenêtre, prix de la boutique officielle

**Ce que change cette mise à jour** (détail, mesures et décisions : `docs/audit/ROBUSTESSE_2026-10-12.md` §10) :

1. **Troisième place (économie) enfin utile** : elle avait la même fenêtre que le reste (±2 points sur 40) et
   n'apparaissait donc que dans **0,3 %** des profils (80 sur 23 569). Elle a désormais **sa propre fenêtre
   de ±5 points**, et doit rester **strictement moins chère** que les deux souris affichées : elle apparaît
   dans **26,1 %** des profils qui ont au moins une place (6 148 sur 23 569), soit **22,63 %** des
   27 170 profils de la grille complète — mesure par `tools/flow_effect.py`, avant/après. *(Pourcentages
   explicités le 2026-10-13 : cette phrase annonçait « 22,63 % » à côté d'un décompte sur 23 569 — voir
   `ROBUSTESSE_2026-10-12.md` §26.18.)*
2. **Moins de « deux fois la même souris »** : quand la zone du mode ne contient que des variantes de la
   même coque, l'alternative cherche une **autre forme** jusqu'à 5 points plus bas, **jamais plus chère**
   que le match idéal. Les profils à deux places de même coque passent de **4 040 à 2 097**.
3. **Le match idéal ne change jamais** : 0 profil sur 23 569. Le classement, le barème et les textes sont
   intacts.
4. **Prix : la boutique officielle** (règle donnée le 2026-10-12). L'**A9 Air** passe de 89,90 €
   (revendeur Maxesport) à **59,95 €** (boutique ATK) ; la **VXE MAD R** entre au catalogue à
   **40,95 €** avec la prise publiée par son fabricant (« Perfect Fit for Claw and Palm Grips »), donc
   classable en Palm et en Claw.

> **Les résultats changent** : c'est l'objet de la mise à jour. La troisième ligne peut apparaître là où
> elle était absente, la deuxième peut proposer une autre forme, et deux souris changent de prix.

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
cogs/finder_flow.py                  (décisif : fenêtres de l'alternative et de l'économie)
data/mouse_db.json                   (décisif : prix A9 Air 59,95 €, VXE MAD R 40,95 € → **41,95 € depuis le
                                     2026-10-13**, §12.19 — + prise fabricant)
tools/qa_flow_matrix.py              (facultatif : banc d'essai durci, chaque place contrôlée dans SA fenêtre)
tools/flow_effect.py                 (facultatif : mesure avant/après des trois places)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : documentation, §8.8, §9.5 et §10)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md  (facultatif : tableau statistique régénéré)
docs/RECHERCHE_PRIX_EUR_2026-10-11.md (facultatif : addendum « prix de la boutique officielle »)
README.md                            (facultatif : liste des outils complétée)
```

`utils/matcher.py`, `utils/selection.py`, `utils/catalog.py`, `cogs/mouse_finder.py` et
`data/commercial_links.json` **ne changent pas** dans cette mise à jour (le thénar est déjà à 0 / 0 / 0).

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 1 erreur attendue (.env sur le serveur)

# les deux fenêtres doivent être en place
grep -q "ALTERNATIVE_EXTENSION_POINTS = 5" cogs/finder_flow.py \
  && echo "OK   cogs/finder_flow.py (élargissement de l'alternative)" || echo "ANCIEN cogs/finder_flow.py"
grep -q "ECONOMY_SLOT_TOLERANCE_POINTS = 5" cogs/finder_flow.py \
  && echo "OK   cogs/finder_flow.py (fenêtre de l'économie)" || echo "ANCIEN cogs/finder_flow.py"

# le nouveau prix officiel de l'A9 Air doit être en base
.venv/bin/python -c "import json; d={m['id']: m for m in json.load(open('data/mouse_db.json'))}; \
  print(d['atk_a9_air']['price_eur'], '€ A9 Air ·', d['vxe_mad_r']['price_eur'], '€ MAD R')"
# attendu : 59.95 € A9 Air · 40.95 € MAD R
```

**4. Redémarrage**

```bash
pkill -f "bot.py"                 # la tâche planifiée relance le bot au prochain créneau (≤ 1 min)
```

**5. Vérification en 60 secondes dans Discord**

1. Faire un parcours en **Palm** avec des mesures courantes (ex. 185 × 85) : la troisième ligne « 💰
   Économie » doit apparaître beaucoup plus souvent qu'avant (une souris d'une autre forme, strictement
   moins chère), et jamais deux fois la même souris dans les deux premières lignes.
2. Dans « Peu importe le prix », l'alternative ne doit **jamais** coûter plus cher que le match idéal.
3. Vérifier que l'A9 Air s'affiche à **59,95 €** et la VXE MAD R à **40,95 €** quand elles sortent.

---

### 12.13 Mise à jour du 2026-10-12 (4e) : la troisième place est toujours remplie, et son titre dit la vérité

**Ce que change cette mise à jour** (décisions, mesures et preuves : `docs/audit/ROBUSTESSE_2026-10-12.md`
§19 ; mesure des boutons : `docs/audit/MESURE_BOUTONS_2026-10-12.md` §16 et §17) :

1. **Troisième place toujours remplie** (décision du propriétaire, 2026-10-12). Avant, elle disparaissait
   dès que plus rien n'était moins cher que le match idéal — le cas courant depuis que la **VXE V3**
   (13,95 €, la moins chère du catalogue) est publiée. Désormais la place prend **l'option la moins chère
   de sa fenêtre (±5 points)**, même un peu plus chère. Mesure sur le banc du parcours (27 170 profils) :
   **3 places 6 185 → 20 171 profils (22,76 % → 74,24 %)** ; 0 place inchangé (2 561, budgets trop serrés).
2. **Le libellé suit le prix réel** : « 💸 L'économie » quand la souris est moins chère que les deux
   affichées, « ➕ L'autre option » sinon (4 233 « économie » / 10 505 « autre option » sur la grille
   statistique). Plus de troisième ligne qui s'annonce « économie » sans l'être.
3. **Jamais deux fois la même coque — sur les trois places.** La troisième ne montre une variante d'une
   coque déjà affichée que si aucune autre coque n'existe dans sa fenêtre : **2 175 → 1 095 profils**
   (13,0 % → 5,9 %) à deux places de même coque, dont 837 où il n'y a réellement rien d'autre à montrer.
4. **Deux hauteurs de boutons publiées** (mesurées sur les visuels officiels, protocole calibré) :
   **VXE Dragonfly V3 = Mid** et **ATK Blazing Sky U2 / U2 V2 Ultimate = High**. Elles sortent donc de
   « Jeu partiel » : l'U2 passe de 3 177 à 6 141 sorties et les profils à score partiel baissent de 39 %.
5. **Prix promotionnels d'Halloween** intégrés (20 souris sur 36), prix normal conservé dans la note.

> **Les résultats changent** : c'est l'objet de la mise à jour. La troisième ligne apparaît presque
> toujours, elle peut être plus chère que le match idéal (c'est alors écrit « L'autre option »), et deux
> souris affichent une hauteur de boutons documentée au lieu de « non documentée ».

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
cogs/finder_flow.py                  (décisif : troisième place + libellés, coques distinctes)
data/mouse_db.json                   (décisif : V3 Mid, U2 High, prix promotionnels)
tests/test_flow.py                   (facultatif : verrouille les nouvelles règles)
tests/test_qa_flow_matrix.py         (facultatif : verrouille le banc d'essai)
tools/qa_flow_matrix.py              (facultatif : banc d'essai corrigé, 0 problème sur 27 170 profils)
tools/recommendation_stats.py        (facultatif : rapport statistique, colonne « 3e place »)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : documentation, §18 et §19)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md  (facultatif : tableau régénéré)
docs/audit/MESURE_BOUTONS_2026-10-12.md (facultatif : protocole et mesures)
README.md, docs/REPORTE_DESIGN.md     (facultatif : libellés de la troisième place)
```

`utils/matcher.py`, `utils/selection.py`, `utils/catalog.py`, `cogs/mouse_finder.py` et
`data/commercial_links.json` **ne changent pas** dans cette mise à jour : aucun barème, aucun lien.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 1 erreur attendue (.env sur le serveur)

grep -q "def third_slot_title" cogs/finder_flow.py \
  && echo "OK   cogs/finder_flow.py (libellé honnête de la troisième place)" || echo "ANCIEN cogs/finder_flow.py"

.venv/bin/python -c "import json; d={m['id']: m for m in json.load(open('data/mouse_db.json'))}; \
  print(d['vxe_v3']['button_height'], '· V3', d['atk_u2']['button_height'], '· U2', d['pulsar_x2_v3_mini']['price_eur'], '€ X2 v3 Mini')"
# attendu : Mid · V3 High · U2 119.99 € X2 v3 Mini
```

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"` (le service repart au prochain passage de la tâche).

**5. Vérification en 60 secondes dans Discord**

1. Faire un parcours en **Palm** avec des mesures courantes (ex. 185 × 85) : la troisième ligne doit
   **presque toujours** être là, avec « 💸 L'économie » ou « ➕ L'autre option » selon le prix.
2. Si les trois lignes sont là, vérifier qu'aucune ne montre une souris de la même coque que les autres
   (même forme = même famille : par exemple « A9 Plus » et « A9 Ultimate » ne doivent pas être ensemble).
3. Vérifier que la **VXE V3** ne dit plus « hauteur des boutons non documentée » : elle est notée sur ce
   critère (classe **Mid**).

---

### 12.14 Mise à jour du 2026-10-12 (5e) : trois lignes dès que le budget le permet, titres qui disent la vérité

**Ce que change cette mise à jour** (décision du propriétaire, mesures et preuves :
`docs/audit/ROBUSTESSE_2026-10-12.md` §20) :

1. **Deuxième et troisième lignes toujours remplies** quand une souris est montrable dans le budget :
   3 lignes **74,24 % → 85,50 %** des profils (banc du parcours, 27 170 profils ; grille statistique :
   74,14 % → **87,11 %**). Les trous restants viennent **exclusivement** de budgets épuisés — vérifié
   souris par souris, les deux grilles.
2. **Chaque ligne porte le titre de son rôle réel** : « 🥈 L'alternative », « 💸 L'économie » (moins chère
   que tout ce qui est affiché), « ➕ L'autre option », et **« 🔎 Autre piste »** quand la souris vient du
   dernier palier (zone vide ou budget serré). Le pourcentage affiché à côté du nom montre aussitôt que
   la piste est loin (écart médian de 10 points sur 40).
3. **Le budget reste la règle** : aucune souris au-dessus du plafond n'est jamais montrée.

> **Les résultats changent** : c'est l'objet de la mise à jour. Là où le message n'affichait qu'une ou
> deux lignes, il en affiche trois — avec, quand c'est le cas, la mention « Autre piste ».

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
cogs/finder_flow.py                  (décisif : dernier palier des 2e et 3e places + titres)
tests/test_flow.py                   (facultatif : verrouille la règle)
tools/qa_flow_matrix.py              (facultatif : banc d'essai, contrôles de titre)
tools/recommendation_stats.py        (facultatif : rapport statistique, titres comptés)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : documentation, §20)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md  (facultatif : tableau régénéré)
README.md, docs/REPORTE_DESIGN.md     (facultatif : titres de la troisième place)
```

`data/mouse_db.json`, `utils/matcher.py`, `utils/selection.py`, `utils/catalog.py`,
`cogs/mouse_finder.py` et `data/commercial_links.json` **ne changent pas** : aucun barème, aucun prix,
aucun lien.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 1 erreur attendue (.env sur le serveur)

grep -q "PISTE_TITLE" cogs/finder_flow.py \
  && echo "OK   cogs/finder_flow.py (dernier palier « Autre piste »)" || echo "ANCIEN cogs/finder_flow.py"
grep -q "def alternative_slot_title" cogs/finder_flow.py \
  && echo "OK   cogs/finder_flow.py (titres des deux premières places)" || echo "ANCIEN cogs/finder_flow.py"
```

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"` (le service repart au prochain passage de la tâche).

**5. Vérification en 60 secondes dans Discord**

1. Faire un parcours en **Palm** 150 × 65 avec un **budget personnalisé de 25 €** : les trois lignes
   doivent apparaître (VXE V3, puis ATK U2, puis VXE R1), les deux dernières sous le titre « 🔎 Autre
   piste » — aucune souris au-dessus de 25 €.
2. Faire un parcours ordinaire (ex. 180 × 90, Qualité/Prix) : « 🥇 Le match idéal », « 🥈 L'alternative »
   puis « 💸 L'économie » ou « ➕ L'autre option ».
3. Vérifier qu'aucun titre ne promet une économie qui n'en est pas une : chaque ligne affiche son prix.

---

### 12.15 Mise à jour du 2026-10-12 (6e) : traçabilité vérifiable du catalogue (audit, aucun changement de résultat)

**Ce que change cette mise à jour** (audit complet : `docs/audit/ROBUSTESSE_2026-10-12.md` §21) :

1. **44 valeurs du catalogue étaient sourcées dans les notes mais leur source ne déclarait pas le champ**
   (`sources[].fields`) : la provenance n'était pas vérifiable par la machine. Elle l'est : pages EloShapes
   (bosse), moule de coque (A9 « large », F1) et cahier des charges du propriétaire, avec **9 sources datées
   ajoutées**. **Aucune cote, aucun prix, aucun score ne change.**
2. **Deux écarts de forme consignés** (ATK F1 V3 Ultimate, ATK X1 V2 Ultra Max : bosse « Mid » du propriétaire
   contre « Back - minimal » chez EloShapes) — la valeur du propriétaire reste, l'écart devient lisible.
3. **Règle `verified` précisée** dans la documentation : ≥ 2 sources concordantes à ≤ 0,5 mm, **ou la boutique
   officielle du fabricant** (cas des dix Pulsar). `single_source` = une seule source tierce.
4. **Deux retouches de forme** : « Votre éminence thénar est **petite** » (accord) et les trois titres de la
   troisième place décrits dans `REPORTE_DESIGN.md`.
5. **11 clés `mcu: ""`** remplacées par l'absence de clé (« absent » = « inconnu », une seule écriture).

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
data/mouse_db.json                   (décisif : provenance complétée, clés vides retirées, 2 conflits)
cogs/finder_flow.py                  (décisif : une phrase du bloc « arrière étroit »)
tests/test_data.py                   (facultatif : les 5 invariants d'audit)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : §21, audit complet)
README.md, docs/REPORTE_DESIGN.md    (facultatif : règle « verified », trois titres)
docs/MASTER_PROMPT_AZEMOUSE.md, docs/PROMPT_RECHERCHE_SOURIS_ATK.md,
docs/audit/CATALOGUE_ATK.md          (facultatif : même règle « verified » partout)
```

`utils/matcher.py`, `utils/selection.py`, `utils/catalog.py`, `cogs/mouse_finder.py`,
`data/commercial_links.json` et les fenêtres des trois places **ne changent pas** : aucun barème, aucun
seuil, aucun lien, aucune fenêtre.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 36 souris · liens d'achat valides : 36 · 1 erreur attendue (.env sur le serveur)
.venv/bin/python -m pytest -q        # attendu : 391 passed
.venv/bin/python tools/qa_flow_matrix.py | tail -1   # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"` (le service repart au prochain passage de la tâche).

**5. Vérification en 60 secondes dans Discord** (le résultat doit être **identique** à avant la mise à jour)

1. Faire un parcours en **Palm** 180 × 90, Qualité/Prix : « 🥇 Le match idéal » Phantom Ultimate 91,95 €,
   « 🥈 L'alternative » Z1 V2 Ultra 59,95 €, « ➕ L'autre option » A9 Mini 59,95 €.
2. Faire un parcours en **Claw pincée**, thénar **Petite**, 180 × 100, Qualité/Prix : le bloc « 🖐️ Un arrière
   étroit pour votre thénar » doit commencer par « Votre éminence thénar est **petite** ».
3. Le reste du message ne bouge pas d'un caractère : ni score, ni prix, ni libellé de place.

---

### 12.16 Mise à jour du 2026-10-12 (7e) : trois corrections de données prouvées

**Ce que change cette mise à jour** (audit complet : `docs/audit/ROBUSTESSE_2026-10-12.md` §22) :

1. **La coque A9 pleine taille (125 mm) publiait deux largeurs** — 63,5 mm (souris du propriétaire, fiche
   ATK) et 64,0 mm (EloShapes, pour l'A9 Ultimate et l'A9 Air) : une même pièce, deux cotes. La fiche
   officielle ATK a été relue le 2026-10-12 : elle annonce **« Dimensions 125 x 63.5 x 40 mm »** pour la
   coque pleine taille. **La coque publie 63,5 mm partout**, et l'écart avec EloShapes reste écrit dans
   `conflicts` (jamais effacé).
2. **Deux hauteurs déclarées mais restées vides** : les Scyrox V6/V8 annonçaient `height_mm` dans leur
   source et publiaient `null`. Elles publient **40,0 mm** (valeur déjà écrite dans la source). Sans effet
   sur les scores : la hauteur n'entre dans aucun barème.
3. **Une note qui se contredisait** (ATK X1 V2 Ultra Max : capteur « non renseigné » alors que le champ
   portait « PAW3395 Ultra ») : note réécrite, conflit nommé, **aucune valeur changée** (la page du
   fabricant liste deux capteurs pour six modèles, sans correspondance lisible).

> **Les résultats changent** — c'est l'effet de la correction n° 1, et il est mesuré : **1 043 profils sur
> 27 170 (3,8 %)** changent d'une place, dont **977 (93,7 %) au profit d'une autre variante de la MÊME
> coque**, plus légère et moins chère (l'A9 Ultimate, 41,95 €, remplace l'A9 Plus 2.0, 45,00 €, ou l'A9 NB,
> 72,95 € : forme identique). Les places remplies (85,50 %) et le banc d'essai (**0 problème**) sont
> inchangés. Retour arrière possible en une valeur : `atk_a9_ultimate` et `atk_a9_air`, `width_max_mm`.
>
> **Note du 2026-10-13** : depuis la 37e passe, l'ATK A9 Ultimate n'est plus à 41,95 € mais à **59,95 €**
> (le 41,95 € était le prix d'une autre édition de la même page, que le lien n'ouvre pas — voir §12.19).
> Les 1 043 profils de la correction de largeur restent valides, leur prix a changé depuis.

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
data/mouse_db.json                   (décisif : largeur A9, hauteurs Scyrox, notes et conflits)
tests/test_data.py                   (facultatif : 4 invariants d'audit ajoutés)
tools/qa_flow_matrix.py              (facultatif : le banc lit la tolérance du moteur)
tools/measure_button_height.py       (facultatif : affichage d'une classe non tranchée)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : §21 et §22, l'audit complet)
docs/audit/AUDIT.md                  (facultatif : C10 résolu, C23 à C30)
docs/audit/CATALOGUE_ATK.md, docs/MASTER_PROMPT_AZEMOUSE.md,
docs/audit/RAPPORT_FINAL.md          (facultatif : points ouverts mis à jour)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md,
docs/audit/matrice_profils.md        (facultatif : rapports régénérés)
```

`cogs/`, `utils/`, `assets/`, `data/commercial_links.json` **ne changent pas** : aucun barème, aucun seuil,
aucune fenêtre, aucun prix, aucun lien. Le moteur est identique.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 395 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"`.

**5. Vérification en 60 secondes dans Discord**

1. Parcours **Palm**, main **200 × 110**, **Haut de Gamme** : le match idéal doit être **ATK A9 Ultimate**
   (**59,95 €**), suivi de l'ATK X1 V2 Ultra Max (41,95 €) et de l'ATK A9 Plus 2.0 (45,00 €) — trois souris à
   88 %. Avant la mise à jour de cette section, la première ligne était l'A9 Plus 2.0 au même prix supérieur.
   **Prix remis à jour le 2026-10-13** : l'A9 Ultimate est passée de 41,95 € à 59,95 € (lien ≠ prix, voir
   §12.19) — c'est ce prix-là qui doit s'afficher.
2. Parcours **Palm** 180 × 90, Qualité/Prix : le résultat doit rester **ATK Phantom Ultimate** (91,95 €),
   puis **ATK Z1 V2 Ultra** (59,95 €), puis **ATK A9 Mini** (59,95 €) — exemple documenté du README.
3. Aucun libellé ne doit promettre une économie qui n'en est pas une, et aucune souris au-dessus du budget
   personnalisé ne doit apparaître.

### 12.17 Mise à jour du 2026-10-12 (8e) : code et données remis au propre (aucun résultat ne change)

**Ce que change cette mise à jour** (audit complet : `docs/audit/ROBUSTESSE_2026-10-12.md` §23) :

1. **Un résidu d'édition dans le texte de l'étape thénar** (`cogs/finder_flow.py`) : un guillemet de
   fermeture suivi de trois guillemets collés — une chaîne vide invisible, que ni Python ni `pyflakes` ne
   signalent (le texte affiché restait juste). Résidu retiré ; `tests/test_code_hygiene.py` interdit
   désormais ce motif dans tout le code livré.
2. **Une source comptée deux fois** dans l'ATK Y9 Ultimate (même libellé, même URL, même date) : les deux
   entrées fusionnent en une seule, qui déclare les deux champs (`claw_grip_fit`, `price_eur`).
3. **Trois statuts de cotes sous-estimés** (ATK Duckbill, ATK A9 Air, VXE X3) : elles annonçaient
   « une seule source tierce » alors que la fiche officielle du fabricant attestait déjà leurs cotes →
   statut `verified`, conforme à la règle écrite du README.

> **Aucun résultat ne change** : c'est **mesuré**, pas supposé — la grille complète (27 170 profils) passée
> dans l'ancien et le nouveau catalogue ne montre **aucune différence** (`tools/db_effect.py`, nouveau dans
> cette mise à jour). Les barèmes, seuils, fenêtres, prix et liens sont identiques.

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
cogs/finder_flow.py                  (décisif : le résidu de guillemets retiré)
data/mouse_db.json                   (décisif : source fusionnée, trois statuts de cotes)
tools/db_effect.py                   (facultatif : NOUVEAU, mesure l'effet d'un changement de données,
                                      et d'un retrait de souris avec --retrait)
tests/test_code_hygiene.py           (facultatif : NOUVEAU, hygiène du code livré)
tests/test_db_effect.py              (facultatif : NOUVEAU, verrouille le comparateur de données)
tests/test_data.py                   (facultatif : doublon de source et statuts, contrôlés dans les deux sens)
README.md                            (facultatif : outils et tests nouveaux décrits)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : §23, l'audit complet de la passe)
docs/audit/AUDIT.md                  (facultatif : C31 à C33, points ouverts 12 et 13)
docs/MASTER_PROMPT_AZEMOUSE.md       (facultatif : §17, deux limites mesurées ajoutées)
```

`utils/`, `bot.py`, `assets/`, `data/commercial_links.json` **ne changent pas**. Le moteur est identique :
seul le texte de la source Python est nettoyé, et les trois statuts corrigés n'entrent dans aucun barème.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 403 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
.venv/bin/python tools/db_effect.py --avant /tmp/ancien_mouse_db.json --grille rapide   # attendu : 0,00 %
```

La dernière commande est facultative : elle compare l'ancien catalogue (si vous l'avez conservé) au nouveau
et doit annoncer **0 profil modifié**.

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"`.

**5. Vérification en 60 secondes dans Discord** — le résultat doit être **identique à celui d'avant la mise à
jour** (c'est le point de cette passe) :

1. Parcours **Palm**, main **180 × 90**, Qualité/Prix : **ATK Phantom Ultimate** (91,95 €), puis
   **ATK Z1 V2 Ultra** (59,95 €), puis **ATK A9 Mini** (59,95 €).
2. Parcours **Palm**, main **200 × 110**, Haut de Gamme : **ATK A9 Ultimate** (**59,95 €** depuis le
   2026-10-13, §12.19 ; 41,95 € avant cette date), puis **ATK X1 V2 Ultra Max**, puis **ATK A9 Plus 2.0**.
3. Le parcours démarre et se termine normalement (le clic « Start » ouvre bien l'étape 1/4).

**Retour arrière** : remettre l'ancien `cogs/finder_flow.py` (ou l'ancien `data/mouse_db.json`) par
FileZilla, puis `pkill -f "bot.py"`. Ces corrections ne touchent ni les prix, ni les liens, ni les cotes
publiées : le retour arrière n'a d'effet que sur le nettoyage de source et trois mentions de provenance.

---

### 12.18 Mise à jour du 2026-10-13 (9e) : trois décisions du propriétaire (résultat visible)

**Ce que change cette mise à jour** (audit complet : `docs/audit/ROBUSTESSE_2026-10-12.md` §24) — ce sont des
changements **visibles**, donc à déployer ensemble :

1. **L'ordre des pourcentages est garanti** : une place n'affiche plus un meilleur pourcentage que la place
   du dessus (idéal ≥ alternative ≥ économie). La contrainte s'applique au **choix de la souris**, jamais au
   score : **le match idéal ne change sur aucun profil**. Mesure avant/après sur 24 609 profils : 2 046 →
   **84 profils** (0,34 % de ces 24 609 ; 0,31 % si l'on rapporte les mêmes 84 profils aux 27 170 de la
   grille entière — dénominateurs explicités le 2026-10-13, §26.18) où l'ordre n'est pas garanti — ce sont les profils où le plafond ne laisse **aucun**
   candidat (grande main, budget serré) ; la place reste alors remplie (jamais de trou dans le résultat).
   Deuxième place changée sur 1 615 profils, troisième sur 1 976 ; aucune place perdue ni gagnée.
2. **« (prix non vérifié) » revient à côté du prix** des souris dont le prix n'est pas attesté (Scyrox V6
   74,90 € et ATK A9 Plus 2.0 45,00 €), dans les trois places **et** dans la petite ligne de prix du mode
   « Peu importe le prix » : **16,09 % des profils** l'affichent.
3. **Le pied de message ne renvoie plus à un bloc disparu** : « Comment lire ce résultat » (bloc supprimé le
   2026-10-11) devient **« 🧭 Pourquoi ce choix ? »**, et le renvoi n'apparaît que si ce bloc est bien dans le
   message.
4. **Une souris notée sans le critère des boutons (hauteur non documentée) l'annonce en 2e et 3e place** :
   « · boutons non documentés » à la fin de la ligne. Son pourcentage était calculé sans ce critère (donc
   sous-estimé) sans que rien ne le dise — **8 187 places** sur 27 170 profils (30,1 %). Le match idéal, lui,
   garde la note longue du bloc « 📐 Vos repères de taille » (pas de doublon).

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
cogs/finder_flow.py                  (DÉCISIF : ordre des pourcentages, marqueur de prix, pied de message,
                                      marqueur de score partiel)
tools/qa_flow_matrix.py              (facultatif : contrôle du marqueur et de l'ordre)
tools/flow_effect.py                 (facultatif : compare un changement de moteur avant/après)
tests/test_flow.py                   (facultatif : 6 tests nouveaux sur les quatre décisions)
README.md                            (facultatif : ordre garanti et prix signalés décrits)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : §24, l'audit complet de la passe)
docs/audit/AUDIT.md                  (facultatif : C27 et C34 fermés, points ouverts 13 et 14 tranchés)
docs/MASTER_PROMPT_AZEMOUSE.md       (facultatif : §7.7, les deux règles de présentation)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md (facultatif : rapport régénéré)
docs/audit/matrice_profils.md        (facultatif : matrices régénérées)
docs/apercu_resultat.png             (facultatif : aperçu régénéré)
```

`data/mouse_db.json`, `utils/`, `bot.py`, `assets/` et `data/commercial_links.json` **ne changent pas** :
cette mise à jour ne touche ni les prix, ni les liens, ni les cotes.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 409 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"`.

**5. Vérification en 60 secondes dans Discord** — trois regards suffisent :

1. Parcours **Palm**, main **180 × 90**, **Économique** : les pourcentages descendent bien — **ATK Z1 V2
   Ultra 75 %**, **ATK A9 Mini 75 %**, **ATK GHOST Ultimate 75 %** (avant cette mise à jour, la première
   ligne affichait 63 % sous une deuxième ligne à 75 %).
2. Parcours **Palm**, main **200 × 110**, **Haut de gamme** : la troisième ligne (ATK A9 Plus 2.0) affiche
   **« 45,00 € (prix non vérifié) »** — le marqueur revient.
3. En bas du message privé, le pied de page dit **« … expliqué dans le bloc « 🧭 Pourquoi ce choix ? » »**,
   et non plus « Comment lire ce résultat ».
4. Parcours **Palm**, main **180 × 90**, **Économique** : la 2e et la 3e ligne (ATK A9 Mini, ATK GHOST
   Ultimate) se terminent par **« · boutons non documentés »** — leur pourcentage est calculé sans ce
   critère, et la ligne le dit maintenant.

**Retour arrière** : remettre l'ancien `cogs/finder_flow.py` par FileZilla, puis `pkill -f "bot.py"`. Le
retour arrière remet l'ancienne sélection des 2e et 3e places, masque de nouveau le marqueur de prix et le
marqueur de score partiel — les prix, les liens et les cotes ne sont pas concernés.

---

### 12.19 Mise à jour du 2026-10-13 (10e) : les prix des liens remis sur la page du marchand

**Ce que change cette mise à jour** (audit complet : `docs/audit/ROBUSTESSE_2026-10-12.md` §25) : un lien
d'achat peut figer une **variante** précise (`variant=<id>`), et le contrôle précédent vérifiait le **nom**
de cette variante, pas son **prix** — qui venait d'un relevé « dès X € », donc du modèle le moins cher de
la page. Les **36 liens** ont été repassés un par un sur la page du marchand le 2026-10-13. Résultat :
**six prix étaient faux, trois liens tombaient sur une variante épuisée.**

1. **ATK A9 Ultimate : 41,95 € → 59,95 €.** Le lien ouvre l'édition « Ultimate », vendue 59,95 € ; les
   41,95 € étaient le prix d'une **autre édition** de la même page (« Ultra Max 2.0 »). Le prix est
   désormais celui de la variante que le lien ouvre, source datée à l'appui.
2. **Cinq prix vieillis d'un euro**, tous relevés à nouveau le 13 : **X1 V2 Ultra Max 40,95 → 41,95 €** ·
   **F1 V2 40,95 → 41,95 €** · **MAD R 40,95 → 41,95 €** · **A9 NB 72,95 → 73,95 €** ·
   **Duckbill 81,95 → 82,95 €**. Le catalogue suit la boutique, pas l'ancien relevé.
3. **Trois liens recâblés** vers le coloris **en stock**, au même prix : GHOST Ultimate → **Silver**
   (68,95 €), U2 V2 Ultimate → **Lake Green** (59,95 €), Y9 Ultimate → **Pink** (59,95 €). Les variantes
   précédentes étaient épuisées : le clic n'ouvrait plus rien d'achetable.
4. **A9 Plus : rien n'a changé, une question est posée.** Sa variante liée est l'« A9 Plus / White » à
   27,95 € alors que le catalogue porte 45,00 € : rien ne prouve que ce soit le même produit. Le prix de
   45,00 € est **conservé** en attendant votre réponse.
5. **Les dix liens Pulsar sont justes** (119,99 € / 149,99 € / 149,90 €, prix inchangés). Deux d'entre eux
   (Xlite v4 Medium et Large) ouvrent un produit **en rupture de stock** : aucun coloris de rechange
   n'existe, donc le lien reste tel quel — c'est signalé, pas contourné.

> **Les résultats changent** — mesuré, pas supposé (`tools/db_effect.py --avant … --grille complete`) :
> **6 058 profils sur 27 170 (22,30 %)** changent d'une place (idéale 573 · alternative 2 517 ·
> économique 3 781) ; **0 place gagnée, 91 perdues** — des profils à 45 € ou moins qui voyaient l'A9
> Ultimate à 41,95 € et ne la voient plus à 59,95 €. Le banc d'essai reste à **0 problème**, les places
> remplies sont identiques (85,17 %), et les quatre parcours de référence du README ne bougent pas (seul
> le parcours Claw 180 × 100 affiche la MAD R à 41,95 € au lieu de 40,95 €).

**1. Fichiers à glisser dans `~/MouseDiscord`** (conflits : **Écraser**, jamais « Synchroniser »)

```
data/mouse_db.json                   (décisif : six prix corrigés, notes et 37 relevés datés du 2026-10-13)
data/commercial_links.json           (décisif : les trois liens recâblés vers une variante en stock)
tests/test_data.py                   (facultatif : 3 tests — prix et variante, traçabilité des liens, prix daté)
docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md  (facultatif : §7, le contrôle des 36 liens)
docs/audit/ROBUSTESSE_2026-10-12.md  (facultatif : §25, l'audit et l'effet mesuré)
docs/audit/AUDIT.md                  (facultatif : points ouverts 16 et 17)
docs/audit/CATALOGUE_ATK.md          (facultatif : prix du catalogue et note de lecture)
docs/audit/LIENS_AFFILIES_2026-10-12.md  (facultatif : les trois nouvelles URL)
docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md, docs/audit/matrice_profils.md (facultatif : rapports régénérés)
```

`cogs/`, `utils/`, `bot.py`, `assets/` **ne changent pas** : aucun barème, aucun seuil, aucune fenêtre,
aucun libellé. Le moteur est identique — seules les données d'achat et trois tests ont bougé.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 488 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : comme d'habitude, **jamais `bot.py` à la main** — la tâche planifiée s'en charge ;
sinon `pkill -f "bot.py"`.

**5. Vérification en 60 secondes dans Discord**

1. Parcours **Palm**, main **200 × 110**, **Haut de Gamme** : **ATK A9 Ultimate 59,95 €** (et non plus
   41,95 €), puis **ATK X1 V2 Ultra Max 41,95 €**, puis **ATK A9 Plus 2.0 45,00 € (prix non vérifié)** —
   trois souris à 88 %.
2. Parcours **Claw**, main **180 × 100**, Claw **pincée** : la troisième ligne (VXE MAD R) affiche
   **41,95 €**.
3. Un budget personnalisé de **45 €** avec la main 200 × 110 ne doit plus proposer l'A9 Ultimate (elle est
   au-dessus du plafond) : la ligne du bas prend alors l'A9 Plus.
4. Les boutons « Acheter » ouvrent bien une page avec un coloris **achetable** pour GHOST Ultimate, U2 V2
   Ultimate et Y9 Ultimate.

**Retour arrière** : remettre l'ancien `data/mouse_db.json` **et** l'ancien `data/commercial_links.json`
par FileZilla, puis `pkill -f "bot.py"`. Les deux vont ensemble : les prix et les liens qui les ouvrent ont
été corrigés dans le même mouvement.

---

### 12.20 Mesure du 2026-10-13 (11e) : deux décisions du propriétaire chiffrées (le bot ne change pas)

**Ce que change cette mise à jour** : **rien dans le parcours du bot**. Les deux décisions laissées au
propriétaire par la 37e passe (le prix de l'ATK A9 Plus, le sort des quatre souris en rupture) sont
désormais **mesurées** sur la grille complète, mais **aucune n'est appliquée** : le catalogue, les liens
d'achat, le moteur et les messages sont **identiques** à la mise à jour §12.19.

| Décision en attente | Effet mesuré (grille complète, 27 170 profils) |
|---|---|
| **A9 Plus à 27,95 €** (le prix de la variante que son lien ouvre) | **3 556 profils (13,09 %)** changent d'au moins une place · idéale 1 491 · alternative 2 711 · économie 1 790 · **0 place gagnée, 0 perdue** |
| **Retrait des 4 souris en rupture** (MAD R, Fierce X, Xlite v4 Medium et Large) | **1 682 profils (6,19 %)** changent d'au moins une place · **0 place gagnée, 78 perdues** |

Détail, commandes de reproduction et commentaire : `docs/audit/ROBUSTESSE_2026-10-12.md` §25.6.

**1. Fichiers à envoyer (facultatifs)** — `tools/db_effect.py` (nouvelle option `--retrait`) et
`tests/test_db_effect.py` (deux tests). Ce sont des **outils de mesure** : le bot ne les exécute jamais.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 488 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : inutile — aucune ligne livrée au bot n'a changé. Si les deux fichiers facultatifs ont
été envoyés, un redémarrage ne change rien non plus (aucun code du bot n'y touche).

**5. Rien à vérifier dans Discord** : le résultat affiché est exactement celui décrit au §12.19.

---

### 12.21 Mise à jour du 2026-10-13 (12e) : deux erreurs muettes corrigées (rien de visible ne change)

**Ce que change cette mise à jour** (audit complet : `docs/audit/ROBUSTESSE_2026-10-12.md` §26) :

1. `_step_number` remontait un `KeyError` **muet** quand on lui demandait une étape qui n'existe pas pour
   la prise choisie (le thénar en Fingertip, la variante de Claw hors Claw). Le parcours **n'emprunte
   jamais ce chemin** (`step_kind` saute le thénar en Fingertip) : personne n'a vu d'erreur. L'erreur est
   maintenant lisible — elle nomme la prise, l'étape et les étapes qui existent.
2. Un enregistrement de `state/sessions.json` portant un âge **négatif** (horloge reculée, fichier
   bricolé) faisait repartir le parcours **dans le futur** : il gagnait la vie en plus et pouvait ne plus
   jamais expirer. Un âge négatif est maintenant ramené à zéro (« vue à l'instant »), comme le fait déjà
   l'écriture du fichier. Le bot écrit lui-même un âge positif : ce cas n'arrive qu'avec une horloge
   reculée ou un fichier modifié à la main.

3. Le chargement du catalogue refusait mal trois familles de valeurs : un **poids en texte** (ou en
   liste, ou en objet) faisait échouer l'affichage du résultat — « erreur inattendue » au lieu des souris —,
   tandis qu'un `NaN`, un infini ou un booléen traversaient la validation et s'affichaient tels quels
   (« nan g », « inf € », « 1 Hz »). Un lien d'achat contenant un espace ou un saut de ligne était, lui
   aussi, transmis au bouton alors que Discord le refuse — ce qui aurait fait échouer **tout** le
   résultat. Ces valeurs sont maintenant refusées **au chargement**, avec un message lisible, et un lien
   inutilisable est écarté souris par souris (les autres gardent le leur).

Dans ces trois cas : **aucun texte affiché, aucun score, aucun classement, aucun lien, aucun prix ne
change** — les garde-fous ne se déclenchent que sur un fichier de données abîmé. La même passe a mesuré, plutôt que supposé, trois choses sur le code réellement exécuté : les
**limites Discord** sur les 27 170 profils (**0 violation**, tableau au §26.1), la **typographie** de
15 133 textes affichés (**0 défaut réel**, §26.2) et le comportement de l'affichage sur **162 combinaisons
de données dégradées** (**0 exception**, §26.3), plus **14 contenus hostiles** de fichier d'état
(§26.5) — aucun ne bloque le démarrage.

**1. Fichiers à envoyer (facultatifs)** — `cogs/finder_flow.py`, `utils/session.py`,
`utils/catalog.py`, `utils/assets.py`, `tests/test_flow.py`, `tests/test_session.py`,
`tests/test_data.py` et `tests/test_flow_effect.py`. Facultatifs au sens strict : le bot fonctionne
exactement pareil sans eux (le chemin corrigé n'est jamais emprunté en production, et l'âge négatif
d'un fichier d'état n'arrive qu'avec une horloge reculée). Envoyez-les pour que le serveur
corresponde au dépôt — et supprimez `state/sessions.json` si vous voulez repartir d'un état neuf.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 534 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : inutile (aucun texte affiché ne change) ; si vous envoyez le fichier, redémarrer comme
d'habitude — **jamais `bot.py` à la main** : la tâche planifiée s'en charge, sinon `pkill -f "bot.py"`.

**5. Rien à vérifier dans Discord** : le résultat affiché est identique à celui du §12.20.

### 12.22 Mise à jour du 2026-10-13 (13e) : les numéros d'étapes n'ont plus qu'une seule source

Six défauts trouvés en relisant le parcours, les outils, la commande d'installation et la configuration,
**aucun visible par un membre** : le numéro de l'étape de variante de Claw venait d'une deuxième table
(`variant` au lieu de `claw_variant`, §26.9), le **total** des étapes était écrit en clair au lieu de se
lire dans la même table (§26.11), l'aperçu livré `docs/apercu_prix_libre.png` annonçait « Étape 5/5 »
au-dessus d'un titre « Étape 4/4 » (§26.12), importer l'outil d'aperçu changeait la résolution des images
du bot dans le même processus (§26.13), un **fichier d'état illisible** (dossier à la place du fichier,
octets non UTF-8) faisait répondre « ⚠️ Erreur inattendue » à `!setup_finder` au lieu de publier le
message (§26.15), et un **fichier de parcours tronqué en plein caractère** empêchait carrément le **bot
de démarrer** (§26.16). Les numéros d'étapes, les titres affichés et les légendes d'aperçu ont maintenant
**une seule source**, et les fichiers d'état abîmés sont traités comme absents — comme le fait déjà le
fichier des parcours pour ses propres contenus illisibles.

**À lire avant de mettre à jour** : une valeur **booléenne inconnue** dans le `.env` (par exemple
`SESSION_PERSIST=ture`, faute de frappe) n'est plus interprétée comme « faux » en silence : le bot
**refuse de démarrer** et le message indique les orthographes acceptées (`true`/`false`, et
`1`/`0`, `yes`/`no`, `on`/`off`, `oui`/`non`, `vrai`/`faux`). Avant d'envoyer les fichiers, un coup
d'œil au `.env` : `LOCK_FINDER_CHANNEL` et `SESSION_PERSIST` doivent valoir `true` ou `false` (§26.17).

**Aucun envoi pour la correction documentaire C48** (pourcentages rapportés au bon ensemble, §26.18 de
`ROBUSTESSE_2026-10-12.md`) : elle ne touche que les documents, pas le serveur.

**1. Fichiers à envoyer (facultatifs)** — `config.py`, `utils/session.py`, `cogs/finder_flow.py`,
`cogs/mouse_finder.py`, `tools/render_preview.py`, `tests/test_flow.py`, `tests/test_session.py`,
`tests/test_setup_command.py`, `tests/test_config.py`, `.env.example` et `docs/apercu_prix_libre.png`.
Facultatifs au sens strict : **aucun texte affiché dans Discord ne change** (les trois aperçus régénérés
le prouvent : deux sont identiques à l'octet près, le troisième ne change que sur sa propre légende).
Envoyez-les pour que le serveur corresponde au dépôt.

**2. Rien à ajouter au `.env`** — aucune nouvelle variable.

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 558 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
```

**4. Redémarrage** : inutile (aucun texte affiché ne change) ; si vous envoyez les fichiers, redémarrer
comme d'habitude — **jamais `bot.py` à la main** : la tâche planifiée s'en charge, sinon `pkill -f "bot.py"`.

**5. Rien à vérifier dans Discord** : le parcours et le résultat affichés sont identiques à ceux du §12.21.
Le seul cas qui change est un cas dégradé : un fichier d'état abîmé n'empêche plus `!setup_finder` de
publier le message (et si l'identifiant ne peut pas être enregistré, la réponse le dit au lieu de
laisser croire à un échec alors que le message est bien publié).

---

### 12.23 Mise à jour du 2026-10-13 (14e) : la documentation dit maintenant ce qu'elle mesure

**Aucun fichier du serveur ne change** : cette mise à jour ne corrige que des **documents** (le dossier de
preuve et le README). Elle est décrite ici pour que le contrôle ci-dessous reste juste.

1. **Un pourcentage juste, rapporté au mauvais ensemble** (C48, §26.18 du `ROBUSTESSE`) : deux passages
   annonçaient un pourcentage exact pour un **autre** dénominateur que celui écrit à côté — « 6 148 sur
   23 569 » présenté comme 22,63 % (c'est 26,1 % des 23 569, et 22,63 % des 27 170), et « 84 profils sur
   24 609 » présenté comme 0,31 % (c'est 0,34 % des 24 609, et 0,31 % des 27 170). Les dénominateurs sont
   maintenant nommés partout ; **aucun comptage n'a changé**. Nouveau contrôle
   `tests/test_doc_coherence.py`, qui compare chaque pourcentage à l'ensemble cité sur sa ligne.
2. **Le README avait perdu la fin d'une phrase et douze fichiers** (C49, §26.19) : la description de
   `tests/test_db_effect.py` était coupée en deux par l'ajout d'un autre fichier, et 8 des 26 fichiers
   de tests plus 4 des 14 outils n'étaient cités nulle part. Corrigé, et une garde
   (`tests/test_doc_references.py`) refuse désormais un fichier de `tests/` ou de `tools/` absent du
   README.
3. **Quatre outils répondaient mal à une erreur d'usage** (C50, §26.20) : `measure_button_height.py`
   remontait une trace Python (`FileNotFoundError`, `PIL.UnidentifiedImageError`) en code 1 ;
   `measure_grip_width.py` écrivait sa phrase sur la sortie standard en code 1 ; **`build_ai_bundle.py`
   prenait un `--help` mal orthographié pour un nom de fichier et écrivait une archive de 73 Ko** ;
   `check_deployment.py` et `privacy_scan.py` ignoraient tout argument en silence. Les six cas sortent
   maintenant en code 2 avec une phrase, `--help` fonctionne partout, et
   `tests/test_tools_usage_errors.py` vérifie ce contrat sur les quatorze outils. Ces outils-là servent
   au dépouillement **sur le serveur** (SSH) autant qu'en local : envoyez `tools/` si vous voulez le même
   comportement des deux côtés.
4. **Un fichier de parcours bricolé ne bloque plus le membre** (C51 et C52, §26.21) : `state/sessions.json`
   **lisible mais incohérent** (édité à la main, ou corruption partielle qui laisse du JSON valide) était
   accepté tel quel. Des mesures à `0` ou négatives faisaient afficher « ⚠️ Les données des souris sont
   momentanément illisibles, réessayez dans un instant » — à chaque essai, sans issue ; des mesures `NaN`
   donnaient un résultat absurde présenté sans réserve ; un « Budget personnalisé » sans plafond
   reproduisait la même impasse, et avec un plafond `NaN`/infini **le budget était ignoré en silence**.
   Désormais, ce que le formulaire n'aurait jamais pu écrire vaut **réponse absente** : le parcours
   reprend à l'étape Mesures, ou repose la question de la gamme. **Envoyez `utils/session.py`** (et
   `tests/test_session.py` si vous voulez le contrôle sur le serveur) pour l'avoir des deux côtés.
5. **Traçabilité des coques** (C53, §26.22) : `data/mouse_db.json` gagne, sur 16 entrées, la source qui
   atteste le partage de coque (`shell_id`). **Aucune cote, aucun prix, aucun verdict de prise, aucune
   note ne change** (empreinte des valeurs identique avant/après) et **rien ne change à l'écran**.
   **Aucun envoi obligatoire** ni redémarrage : envoyez le fichier seulement si vous voulez les deux
   côtés identiques au caractère près. Depuis, deux libellés de la coque `atk_x1` ont été reformulés
   (C57, §26.25 : ils affirmaient plus que ce que l'audit établit) — même fichier, même conclusion :
   **aucun envoi obligatoire**.
6. **Deux fichiers abîmés ne bloquent plus le parcours** (C54 et C55, §26.23) : un
   `data/commercial_links.json` **tronqué** (ou un dossier à sa place) faisait échouer le résultat
   entier — « une erreur inattendue » au lieu des trois souris, et « refaites l'action » sans issue ;
   un `assets/images.json` en **octets non UTF-8** cassait le parcours **dès le premier message**. Ces
   deux fichiers sont modifiés à la main et transférés par FTP : le cas se produit (transfert
   interrompu, enregistrement dans un autre encodage). Désormais : le résultat s'affiche entier, les
   boutons d'achat cèdent la place au rappel « Liens à venir », et les étapes s'affichent sans image.
   **Envoyez `utils/catalog.py` et `utils/assets.py`** — c'est le seul changement du jour qui touche le
   comportement du bot — puis redémarrez la tâche planifiée (`pkill -f "bot.py"`).
7. **Un lien d'achat trop long ne fait plus perdre le résultat** (C56, §26.24) : la référence des
   composants de Discord borne l'URL d'un bouton de style lien à **512 caractères** ; au-delà, Discord
   refuse le composant et le message entier échoue. Un lien de boutique ou de suivi collé tel quel dans
   `data/commercial_links.json` peut dépasser cette limite. Désormais ce lien-là est écarté (raison
   exacte dans les journaux) et le résultat s'affiche, avec le rappel « Liens à venir » à la place.
   Même envoi que le point 6 (`utils/catalog.py`).
8. **Les chemins d'échec sont désormais tenus par des tests** (C58, §26.26) : la couverture du code
   passe de 95 % à **99 %** (90 → 11 lignes non exécutées ; les 11 restantes sont mesurées dans un vrai
   sous-processus ou sont des branches mortes aujourd'hui — détail au §26.26). Ce qui était le moins
   couvert n'était pas décoratif : tous les chemins d'erreur de `!setup_finder` (salon non textuel,
   verrouillage impossible, écriture refusée, message d'erreur du gestionnaire), le démarrage (purge des
   parcours expirés, erreur d'événement, commande inconnue, jeton vide) et la conservation du parcours
   (variante de Claw relue au redémarrage, fichier d'état à deux parcours vivants). 42 épreuves et
   41 mutations plus tard, retirer un de ces replis fait échouer la suite au lieu de créer une impasse
   silencieuse. **Aucun fichier du bot n'est modifié par cette passe : rien à envoyer**, elle ne sert
   qu'à la suite de tests et à la documentation.

**Rejeu des blocs de contrôle des §12.19 à §12.22 (2026-10-13, 46e passe)** — les compteurs de tests de ces
blocs sont **datés** (488, 534, 558, 630) : c'est voulu, et la valeur courante est au-dessus. Les deux autres
attendus de ces blocs, eux, sont vérifiables à tout moment et ont été **rejoués** :
`tools/check_deployment.py` → **36 souris, 36 liens, 1 erreur** (le `.env` du serveur, absent sur un poste de
travail) et `tools/qa_flow_matrix.py --rapide` → **0 problème détecté**. Aucun de ces quatre blocs n'avait
besoin d'être corrigé.

9. **Le message « sans candidat » n'accuse plus le catalogue** (C59, §26.27) : sur un profil sans candidat
   — **4 082 profils sur 27 170** (15,0 %) — la carte « Aucun match classable » disait « aucune souris ne
   peut être classée avec les données vérifiées pour ces critères ». Dans les trois situations réelles
   (mesures hors de la plage des 36 souris, budget trop serré, gamme sans candidat), des souris **sont**
   classables et le catalogue n'est pour rien : le membre attendait une correction de données au lieu
   d'essayer une autre gamme. Le texte nomme maintenant ce qu'il a fourni (« Aucune souris ne peut être
   retenue avec ces critères. ») suivi du même conseil. **Envoyez `cogs/finder_flow.py`**, puis redémarrez
   comme d'habitude — **jamais `bot.py` à la main** : la tâche planifiée s'en charge, sinon
   `pkill -f "bot.py"`.

10. **Le rapport statistique est reproductible — et le contrôle rapide ne l'écrase plus** (C61, §26.29) :
   régénérer la grille complète dans un fichier temporaire donne un document **identique au caractère près**
   à `docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md` (les chiffres publiés correspondent donc au
   catalogue et au moteur du jour), et `tools/recommendation_stats.py --rapide` **sans** `--sortie` sort
   désormais en **code 2** au lieu de remplacer ce rapport de référence par un rapport de 420 profils.
   **Fichier facultatif** (`tools/recommendation_stats.py`) : le bot ne l'exécute jamais.

**Fichiers à envoyer** : `utils/session.py` (point 4) et **`cogs/finder_flow.py`** (point 9) — ce sont les
deux fichiers du bot touchés ici — et, si
vous le souhaitez, `tools/` (les quatorze outils, dont quatre qui répondent maintenant correctement à une
erreur d'usage). **Redémarrage** : la tâche planifiée s'en charge (ou `pkill -f "bot.py"`) ; aucun texte
affiché ne change. Le compteur du contrôle ci-dessous passe de 558 (valeur du jour du §12.22) à **676**.
Les compteurs des §12.16 à §12.22 gardent la valeur du jour de leur mise à jour — seul celui-ci est
courant.

```bash
cd ~/MouseDiscord
.venv/bin/python -m pytest -q                      # attendu : 676 passed
.venv/bin/python tools/check_deployment.py         # attendu : 36 souris, 36 liens, 1 erreur (.env du serveur)
.venv/bin/python tools/qa_flow_matrix.py | tail -1 # attendu : Problèmes détectés : 0
# facultatif (~1 min) : le rapport statistique publié est-il toujours celui des données actuelles ?
.venv/bin/python tools/recommendation_stats.py --sortie /tmp/stats.md \
  && diff /tmp/stats.md docs/audit/STATISTIQUES_RECOMMANDATIONS_2026-10-12.md && echo "statistiques identiques"
```

---

## 13. Installation sans FileZilla (option avancée, non vérifiée sur l'hébergement)

Si Git est disponible sur le serveur (`git --version`), vous pourriez cloner le dépôt directement sur Alwaysdata.
Le dépôt étant privé, cela suppose de configurer un accès GitHub depuis le serveur, ce qui sort du périmètre de ce guide.
Cette méthode n'a **pas été vérifiée** sur votre hébergement : utilisez la méthode FileZilla décrite ici.

---

## Annexe : récapitulatif des chemins

| Élément | Chemin sur le serveur |
|---|---|
| Projet | `/home/[compte]/MouseDiscord` |
| Environnement virtuel | `/home/[compte]/MouseDiscord/.venv` |
| Python du service | `/home/[compte]/MouseDiscord/.venv/bin/python` |
| Secrets | `/home/[compte]/MouseDiscord/.env` (droits `600`) |
| Catalogue | `/home/[compte]/MouseDiscord/data/mouse_db.json` |
| Liens d'achat | `/home/[compte]/MouseDiscord/data/commercial_links.json` |
| Images | `/home/[compte]/MouseDiscord/assets/images.json` |
| Mémoire du message d'accueil | `/home/[compte]/MouseDiscord/state/finder_message.json` |
| Parcours en cours (sans les réponses des parcours terminés) | `/home/[compte]/MouseDiscord/state/sessions.json` |
| Journaux du service | `/home/[compte]/admin/logs/services/` |
| Sauvegardes (recommandé) | `/home/[compte]/backup-mousediscord/` |
