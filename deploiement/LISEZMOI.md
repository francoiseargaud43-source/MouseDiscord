# Mise à jour automatique du bot sur Alwaysdata

Ce dossier remplace l'envoi à la main par FileZilla : GitHub se connecte au serveur en SSH,
envoie les fichiers, contrôle l'installation et redémarre le bot. Le guide manuel reste valable
(`docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`) ; les deux méthodes déposent les mêmes fichiers.

## Mise en place (faite le 2026-11-11)

L'accès se fait par une clé réservée au déploiement :

- la clé publique (commentaire `claude-deploiement-azemouse`) est dans `~/.ssh/authorized_keys` du serveur ;
- la clé privée est dans le secret GitHub `ALWAYSDATA_SSH_KEY`
  (<https://github.com/francoiseargaud43-source/mousediscord/settings/secrets/actions>).

L'hôte et l'identifiant ne sont pas des secrets : ils sont lus dans `deploiement/serveur.txt`
(`ssh-aze129.alwaysdata.net`, `aze129`). Les secrets `ALWAYSDATA_SSH_HOST` et `ALWAYSDATA_SSH_USER`, s'ils
existent, passent avant ce fichier. Variante : un secret `ALWAYSDATA_SSH_PASSWORD` (mot de passe SSH) ; si
les deux existent, la clé est utilisée.

Un secret enregistré ne peut plus être relu par personne, et GitHub le masque dans tous les journaux.
**Pour retirer l'accès** : supprimer le secret dans GitHub, puis retirer la ligne
`claude-deploiement-azemouse` de `~/.ssh/authorized_keys` sur le serveur.

Le dépôt est public : son onglet **Actions** l'est aussi. Ce que le serveur renvoie est donc filtré
(`masquer` dans `serveur.sh`) : valeurs du `.env` jamais affichées, jetons, mots de passe et longues
suites de caractères masqués dans les journaux.

Avant toute connexion, chaque exécution fait un **contrôle public**, sans identifiant
(`deploiement/controle_public.sh`) : les illustrations du dépôt sont-elles en ligne à l'adresse publique,
et quelle est la clé publique du serveur SSH.

## Utilisation

Tout passe par `deploiement/demande.txt`. Changer la ligne `action:`, augmenter le numéro de la ligne
`demande:`, puis pousser la branche (`claude/...` ou `arena/...`). Le résultat se lit dans l'onglet
**Actions** du dépôt.

| Action | Effet sur le serveur |
|---|---|
| `etat` | Lecture seule : fichiers comparés au dépôt, lancement du bot (tâche planifiée, démarrages notés dans `bot.log`), images publiées, contrôle, place occupée |
| `deployer` | Envoi dans un dossier d'attente, contrôle, nouvelles images mises en ligne, bascule juste avant une relance du bot, attente de sa reconnexion à Discord |
| `redemarrer` | Relance du bot seulement (ou attente de sa prochaine relance par la tâche planifiée) |

### Comment se passe `deployer`

1. Les fichiers de production partent dans `~/MouseDiscord_envoi` (dossier d'attente) : le bot en
   service n'est pas touché.
2. Contrôle sur le serveur, avec son Python et les réglages du `.env` en service : syntaxe, chargement des
   modules du bot, `tools/check_deployment.py`. En cas d'échec, rien n'a changé et tout s'arrête là.
3. Les illustrations nouvelles sont envoyées et publiées dans `~/www/illustrations`.
4. Bascule : le bot est relancé à heure fixe par une tâche planifiée d'Alwaysdata (toutes les dix minutes
   au 2026-11-11, sur une autre machine que celle du SSH, donc sans processus visible). La bascule se fait
   environ 45 secondes avant la relance suivante. Chaque fichier remplacé ou retiré est **rangé** dans
   `~/MouseDiscord_sauvegardes/avant_AAAAMMJJ_HHMMSS/`, à la même place que dans le projet.
   `cogs/` et `utils/` deviennent identiques au dépôt ; ailleurs, rien n'est retiré.
5. Attente de la relance, lue dans `bot.log` (« démarrage du bot » puis « Connecté en tant que »). Si la
   nouvelle version ne se connecte pas à Discord, l'état précédent est remis et la relance suivante
   reprend l'ancienne version.

## Garde-fous

- Jamais envoyés, remplacés ni affichés : `.env` (seuls les noms de ses variables sortent), `state/`
  (parcours en cours, message du panneau), `bot.log`, `.venv`.
- Rien n'est détruit : un fichier remplacé ou retiré est rangé dans `~/MouseDiscord_sauvegardes/`
  (cinq dernières mises à jour). Si une étape échoue après la bascule, tout est remis comme avant.
- Seul le processus `bot.py` lancé depuis `~/MouseDiscord` peut être arrêté (cas d'un service ou d'une
  tâche visible depuis la machine SSH).
- La clé du serveur est épinglée dans `deploiement/cle_serveur.txt` (relevée le 2026-11-11 par le contrôle
  public) : si le serveur en présente une autre, la connexion est refusée.
- Une image déjà présente sur le serveur n'est jamais remplacée, ni en ligne dans `~/www/illustrations`
  ni dans `~/MouseDiscord/assets/illustrations` (les deux dossiers peuvent n'en faire qu'un, par lien
  symbolique) : Discord garde longtemps en mémoire une image déjà affichée, donc une nouvelle version se
  publie sous un nouveau nom de fichier. Les images absentes du serveur, elles, sont ajoutées.
- Après une mise à jour, le message public du salon ne change qu'une fois `!setup_finder` tapé dans Discord
  par un administrateur.
