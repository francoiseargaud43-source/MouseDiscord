# Mise à jour automatique du bot sur Alwaysdata

Ce dossier remplace l'envoi à la main par FileZilla : GitHub se connecte au serveur en SSH,
envoie les fichiers, contrôle l'installation et redémarre le bot. Le guide manuel reste valable
(`docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`) ; les deux méthodes déposent les mêmes fichiers.

## Mise en place, une seule fois

Un seul secret est à créer. Ouvrir
<https://github.com/francoiseargaud43-source/mousediscord/settings/secrets/actions/new>
(ou, dans le dépôt, **Settings > Secrets and variables > Actions > New repository secret**), puis :

| Case | Valeur |
|---|---|
| **Name** | `ALWAYSDATA_SSH_PASSWORD` |
| **Secret** | le mot de passe SSH d'Alwaysdata, celui du Gestionnaire de sites de FileZilla |

L'hôte et l'identifiant ne sont pas des secrets : ils sont lus dans `deploiement/serveur.txt`
(`ssh-aze129.alwaysdata.net`, `aze129`). S'ils sont différents dans FileZilla, corriger ce fichier, ou
créer de la même façon les secrets `ALWAYSDATA_SSH_HOST` et `ALWAYSDATA_SSH_USER`, qui passent avant lui.

Variante sans mot de passe : le secret `ALWAYSDATA_SSH_KEY` contient une clé privée réservée au
déploiement, dont la clé publique est dans `~/.ssh/authorized_keys` du serveur. Si les deux secrets
existent, la clé est utilisée.

Un secret enregistré ne peut plus être relu par personne, et GitHub le masque dans tous les journaux.
Pour retirer l'accès : supprimer le secret, puis changer le mot de passe SSH dans Alwaysdata
(**Remote access > SSH**) ou retirer la ligne de la clé dans `~/.ssh/authorized_keys`.

Avant toute connexion, chaque exécution fait un **contrôle public**, sans identifiant
(`deploiement/controle_public.sh`) : les illustrations du dépôt sont-elles en ligne à l'adresse publique,
et quelle est la clé publique du serveur SSH.

## Utilisation

Tout passe par `deploiement/demande.txt`. Changer la ligne `action:`, augmenter le numéro de la ligne
`demande:`, puis pousser la branche (`claude/...` ou `arena/...`). Le résultat se lit dans l'onglet
**Actions** du dépôt.

| Action | Effet sur le serveur |
|---|---|
| `etat` | Lecture seule : fichiers comparés au dépôt, processus du bot, images publiées, contrôle, fin du journal |
| `deployer` | Sauvegarde, envoi des fichiers de production, dépendances, images, contrôle, redémarrage |
| `redemarrer` | Redémarrage du bot seulement |

## Garde-fous

- Le fichier `.env` du serveur n'est jamais envoyé, remplacé ni affiché : seuls les noms de ses variables sortent.
- Avant chaque envoi, l'état précédent est gardé dans `~/MouseDiscord_sauvegardes/` (cinq dernières sauvegardes).
- Si `tools/check_deployment.py` signale une erreur bloquante, l'état précédent est restauré et le bot n'est pas redémarré.
- Seul le processus `bot.py` lancé depuis `~/MouseDiscord` est redémarré.
- La clé du serveur est épinglée dans `deploiement/cle_serveur.txt` (relevée le 2026-11-11 par le contrôle
  public) : si le serveur en présente une autre, la connexion est refusée.
- Une image déjà en ligne dans `~/www/illustrations` n'est jamais remplacée (Discord garde longtemps en
  mémoire une image déjà affichée) : une nouvelle version se publie sous un nouveau nom de fichier.
