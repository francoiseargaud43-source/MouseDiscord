# Mise à jour automatique du bot sur Alwaysdata

Ce dossier remplace l'envoi à la main par FileZilla : GitHub se connecte au serveur en SSH,
envoie les fichiers, contrôle l'installation et redémarre le bot. Le guide manuel reste valable
(`docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`) ; les deux méthodes déposent les mêmes fichiers.

## Mise en place, une seule fois

Dans GitHub, ouvrir le dépôt puis **Settings > Secrets and variables > Actions > New repository secret**
et créer trois secrets. Ce sont les valeurs déjà saisies dans le Gestionnaire de sites de FileZilla.

| Nom du secret | Valeur |
|---|---|
| `ALWAYSDATA_SSH_HOST` | l'hôte, de la forme `ssh-[compte].alwaysdata.net` |
| `ALWAYSDATA_SSH_USER` | l'identifiant SSH |
| `ALWAYSDATA_SSH_PASSWORD` | le mot de passe SSH |

Un secret enregistré ne peut plus être relu par personne, et GitHub le masque dans tous les journaux.
Pour retirer l'accès : supprimer les secrets, ou changer le mot de passe SSH dans Alwaysdata
(**Remote access > SSH**).

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
- La clé du serveur est épinglée dans `deploiement/cle_serveur.txt` dès la première connexion réussie.
