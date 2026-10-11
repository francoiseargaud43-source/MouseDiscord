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
| `data/commercial_links.json` | Oui | Oui (fichier) | Liens d'achat officiels (26 souris au 2026-10-11) | Relu à chaque résultat. **Voir §2.5** |
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

Le fichier `data/commercial_links.json` **du dépôt est prêt à l'emploi** : depuis le 2026-10-11, il contient les
**liens d'achat officiels de 26 souris sur 26**, vérifiés un par un (clé = `id` de la souris dans `data/mouse_db.json`,
détail dans `docs/VERIFICATION_LIENS_SPONSORISES_2026-10-11.md`).

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

### 12.1 Ce qui ne doit JAMAIS être écrasé

| Élément sur le serveur | Pourquoi le protéger |
|---|---|
| `~/MouseDiscord/.env` | Token et réglages propres au serveur |
| `~/MouseDiscord/data/commercial_links.json` | **Liens d'achat** : depuis le 2026-10-11, le dépôt contient les 26 liens officiels vérifiés — c'est donc le fichier du dépôt qu'il faut installer (§12.9). Ne l'écrasez avec une version plus ancienne que si vous y avez ajouté vos propres liens à la main (comparez d'abord, §2.5) |
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
| `docs/`, `tests/`, `ImageAct/`, `ImageEx/`, `ImageUse/`, `image.png`, `pytest.ini`, `requirements-dev.txt` | **Non** | Utiles au développement seulement (≈ 7 Mo inutiles sur le serveur) |
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
grep -q thenar_step_embed cogs/finder_flow.py && echo "OK   cogs/finder_flow.py (4 étapes)" || echo "ANCIEN cogs/finder_flow.py"
grep -q "Comment lire ce résultat" cogs/finder_flow.py && echo "OK   cogs/finder_flow.py (résultat épuré)" || echo "ANCIEN cogs/finder_flow.py (résultat)"
grep -q ResultsView bot.py                     && echo "ANCIEN bot.py (vue supprimée — à remplacer)" || echo "OK   bot.py"
```

Les **huit lignes** doivent afficher `OK`. Une ligne `ANCIEN …` signale un fichier non transféré : reprenez le transfert
du dossier correspondant (`utils/`, `assets/`, `cogs/`, `config.py`) avant de démarrer le service. Le contrôle
`tools/check_deployment.py` complète ce diagnostic (fichiers, token, JSON, images, `state/`).

### 12.9 Mise à jour du 2026-10-11 : catalogue 26 souris, prix en euros, liens d'achat (raccourci)

Cas concerné : `~/MouseDiscord` tourne déjà la refonte visuelle, et vous voulez la mise à jour
« catalogue enrichi · prix officiels en euros · 26 liens d'achat · boutons alignés sur la vidéo Oblivity ».

**1. Ce qui a changé depuis la refonte visuelle**

| Élément | Nature | Redémarrage nécessaire ? |
|---|---|---|
| `bot.py` | Code : supprime l'enregistrement de la vue persistante des boutons retirés — **obligatoire** : l'ancien `bot.py` référence `ResultsView.persistent()`, qui n'existe plus | **Oui** |
| `cogs/finder_flow.py` | Code : parcours, résultat épuré (recommandation puis « ❓ Comment lire ce résultat » + paragraphes illustrés), boutons d'achat uniquement | **Oui** |
| `utils/matcher.py`, `utils/models.py` | Code : barème des boutons aligné sur Oblivity, ajustement thénar borné (±2, bosse arrière) | **Oui** |
| `data/mouse_db.json` | Données : 26 souris vendues, prix en euros, sources datées | Non (relu à chaque recherche) |
| `data/commercial_links.json` | Données : 26 liens officiels (les URL `https://url.com/…` ont disparu) | Non (relu à chaque résultat) |
| `tools/check_deployment.py` | Outil de contrôle | Non |

`config.py`, les autres fichiers de `utils/`, `assets/` et `requirements.txt` sont **inchangés** :
inutile de les retransférer.

**2. FileZilla — sept fichiers à glisser dans `~/MouseDiscord`**

Ouvrez le dossier téléchargé à gauche, `~/MouseDiscord` à droite, puis glissez (conflits : **Écraser**,
jamais « Synchroniser les répertoires ») :

```
bot.py
cogs/finder_flow.py
utils/matcher.py
utils/models.py
data/mouse_db.json
data/commercial_links.json
tools/check_deployment.py
```

> Doute sur la version qui tourne sur le serveur ? Glissez aussi `bot.py`, `config.py`, `utils/` et `assets/`
> (transfert complet : il ne casse rien, il écrase par des fichiers identiques ou plus récents).

**3. Contrôle (SSH)**

```bash
cd ~/MouseDiscord
.venv/bin/python tools/check_deployment.py
# attendu : catalogue lisible : 26 souris · liens d'achat valides : 26 · 0 erreur(s) bloquante(s)
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
> toujours — et le mode d'emploi du score (« ❓ Comment lire ce résultat ») s'affiche dans le même message, plus
> bas. Un résultat affiché **avant** la mise à jour garde ses anciens boutons : relancez un test pour obtenir un
> message à jour.

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
| Journaux du service | `/home/[compte]/admin/logs/services/` |
| Sauvegardes (recommandé) | `/home/[compte]/backup-mousediscord/` |
