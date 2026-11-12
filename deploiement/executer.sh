#!/usr/bin/env bash
# Lancé par .github/workflows/alwaysdata.yml sur une machine GitHub.
# Lit deploiement/demande.txt puis agit sur le serveur Alwaysdata par SSH.
# Le mot de passe (SSHPASS) ou la clé (AD_KEY) viennent des secrets GitHub : ils ne sont ni affichés ni
# écrits dans le dépôt. L'hôte et l'identifiant viennent des secrets ou, à défaut, de deploiement/serveur.txt.
set -euo pipefail

cd "$(dirname "$0")/.."

action="$(sed -n 's/^action:[[:space:]]*//p' deploiement/demande.txt | head -n 1 | tr -d '[:space:]')"
case "$action" in
  etat | deployer | redemarrer) ;;
  *)
    echo "Action inconnue dans deploiement/demande.txt : « $action »"
    exit 2
    ;;
esac
# Hôte et identifiant : les secrets s'ils existent, sinon deploiement/serveur.txt (valeurs non secrètes).
valeur_de() {
  sed -n "s/^$1:[[:space:]]*//p" deploiement/serveur.txt 2>/dev/null | head -n 1 | tr -d '[:space:]'
}
AD_HOST="${AD_HOST:-$(valeur_de hote)}"
AD_USER="${AD_USER:-$(valeur_de identifiant)}"
: "${AD_HOST:?hôte absent (secret ALWAYSDATA_SSH_HOST ou deploiement/serveur.txt)}"
: "${AD_USER:?identifiant absent (secret ALWAYSDATA_SSH_USER ou deploiement/serveur.txt)}"
case "$AD_HOST$AD_USER" in
  *[!A-Za-z0-9._-]*)
    echo "Hôte ou identifiant invalide : lettres, chiffres, point, tiret et tiret bas seulement."
    exit 2
    ;;
esac
if [ -z "${AD_KEY:-}" ] && [ -z "${SSHPASS:-}" ]; then
  echo "Ni clé (ALWAYSDATA_SSH_KEY) ni mot de passe (ALWAYSDATA_SSH_PASSWORD) dans les secrets."
  exit 2
fi

# --- Clé du serveur : épinglée dans deploiement/cle_serveur.txt dès qu'elle est connue ---
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
connus="$HOME/.ssh/known_hosts_alwaysdata"
: > "$connus"
if grep -qE '^(ssh-|ecdsa-)' deploiement/cle_serveur.txt 2>/dev/null; then
  grep -E '^(ssh-|ecdsa-)' deploiement/cle_serveur.txt | while read -r ligne; do
    echo "$AD_HOST $ligne" >> "$connus"
  done
  verification=yes
else
  verification=accept-new
  echo "::warning::Clé du serveur pas encore épinglée (deploiement/cle_serveur.txt) : première connexion acceptée telle quelle."
fi

options_ssh=(
  -o "StrictHostKeyChecking=$verification"
  -o "UserKnownHostsFile=$connus"
  -o HashKnownHosts=no
  -o ConnectTimeout=20
  -o ServerAliveInterval=15
  -o LogLevel=ERROR
)

# Connexion par clé si le secret ALWAYSDATA_SSH_KEY existe, sinon par mot de passe.
if [ -n "${AD_KEY:-}" ]; then
  cle="$HOME/.ssh/alwaysdata_deploiement"
  printf '%s\n' "$AD_KEY" | tr -d '\r' > "$cle"
  chmod 600 "$cle"
  options_ssh+=(-i "$cle" -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -o BatchMode=yes)
  lanceur=(env)
  echo "connexion par clé"
else
  export SSHPASS
  command -v sshpass > /dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq sshpass; }
  options_ssh+=(-o PreferredAuthentications=password,keyboard-interactive -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1)
  lanceur=(sshpass -e)
  echo "connexion par mot de passe"
fi

distant() {
  "${lanceur[@]}" ssh "${options_ssh[@]}" "$AD_USER@$AD_HOST" "$@"
}

# sur_le_serveur <étape> : exécute deploiement/serveur.sh sur le serveur.
sur_le_serveur() {
  distant "bash -s -- $1" < deploiement/serveur.sh
}

# -c : c'est le contenu qui décide de l'envoi, pas la date ni la taille (un fichier de même taille et de
# même date que celui du serveur, mais au contenu différent, serait sinon laissé tel quel).
envoyer() {
  "${lanceur[@]}" rsync -rltzc -e "ssh ${options_ssh[*]}" "$@"
}

# Copie de travail : exactement ce qui doit se trouver sur le serveur (docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md §2.3).
preparer() {
  prepa="$(mktemp -d)"
  mkdir -p "$prepa/tools"
  cp bot.py config.py requirements.txt README.md .env.example "$prepa/"
  cp -r cogs utils data assets "$prepa/"
  # tools/run_bot.sh : lanceur appelé par la tâche planifiée d'Alwaysdata (docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md §7.7).
  cp tools/check_deployment.py tools/run_bot.sh "$prepa/tools/"
  find "$prepa" -name '__pycache__' -type d -prune -exec rm -rf {} +
  git rev-parse HEAD > "$prepa/VERSION"
}

sommes_locales() {
  (cd "$prepa" && find . -type f ! -name VERSION -print0 | sort -z | xargs -0 sha256sum)
}

comparer() {
  awk '
    function chemin(ligne) { sub(/^[^ ]+ +/, "", ligne); return ligne }
    NR == FNR { depot[chemin($0)] = $1; next }
    { serveur[chemin($0)] = $1 }
    END {
      for (f in depot) {
        if (!(f in serveur)) absent[f] = 1
        else if (depot[f] != serveur[f]) different[f] = 1
        else identiques++
      }
      for (f in serveur) if (!(f in depot)) en_trop[f] = 1
      printf "identiques : %d\n", identiques
      n = 0; for (f in different) n++; printf "différents : %d\n", n
      for (f in different) print "  ~ " f
      n = 0; for (f in absent) n++; printf "absents du serveur : %d\n", n
      for (f in absent) print "  + " f
      n = 0; for (f in en_trop) n++; printf "présents seulement sur le serveur : %d\n", n
      for (f in en_trop) print "  ? " f
    }' "$1" "$2"
}

case "$action" in
  etat)
    preparer
    sur_le_serveur etat
    printf '\n=== Comparaison serveur / dépôt (commit %s) ===\n' "$(git rev-parse --short HEAD)"
    sommes_locales > /tmp/sommes_depot.txt
    if sur_le_serveur sommes > /tmp/sommes_serveur.txt; then
      comparer /tmp/sommes_depot.txt /tmp/sommes_serveur.txt
      printf '\n=== Données : serveur comparé au dépôt ===\n'
      for f in data/commercial_links.json data/mouse_db.json assets/images.json; do
        if distant "cat MouseDiscord/$f" > /tmp/distant.json 2>/dev/null; then
          if cmp -s /tmp/distant.json "$prepa/$f"; then
            echo "$f : identique"
          else
            python3 deploiement/comparer_donnees.py "$f" /tmp/distant.json "$prepa/$f"
          fi
        else
          echo "$f : absent du serveur"
        fi
      done
    else
      echo "(impossible de lister les fichiers du serveur)"
    fi
    ;;
  deployer)
    preparer
    printf '\n=== Envoi des fichiers (commit %s) ===\n' "$(git rev-parse --short HEAD)"
    # Les fichiers partent dans un dossier d'attente : le bot en service n'est pas touché tant qu'ils
    # n'ont pas été contrôlés sur le serveur (deploiement/serveur.sh, étape « controler »).
    distant "mkdir -p MouseDiscord_envoi"
    envoyer --delete --exclude '/assets/illustrations/' --exclude '__pycache__/' "$prepa/" "$AD_USER@$AD_HOST:MouseDiscord_envoi/"
    echo "fichiers envoyés dans ~/MouseDiscord_envoi (dossier d'attente)"
    sur_le_serveur controler
    printf '\n=== Envoi des illustrations ===\n'
    # Les illustrations et leur mise en ligne avant la bascule : le bot en marche relit assets/images.json
    # à chaque interaction, ce fichier ne doit donc entrer en service qu'une fois ses images publiées.
    # Une illustration déjà présente sur le serveur n'est jamais remplacée, pas même dans le dossier du
    # projet : ~/www/illustrations peut être un lien vers ce dossier, et la bannière en ligne n'est pas
    # celle du dépôt (contrôle public du 2026-11-11). Une nouvelle version = un nouveau nom de fichier.
    distant "mkdir -p MouseDiscord/assets/illustrations"
    envoyer --ignore-existing "$prepa/assets/illustrations/" "$AD_USER@$AD_HOST:MouseDiscord/assets/illustrations/"
    echo "illustrations envoyées (seules les nouvelles sont ajoutées)"
    sur_le_serveur publier
    # Le bot est relancé à heure fixe par la tâche planifiée : la bascule se fait juste avant une relance.
    # L'attente se passe ici, sans connexion ouverte ; « activer » revérifie le créneau en arrivant.
    pause="$(sur_le_serveur creneau | tail -n 1 | tr -cd '0-9')"
    if [ "${pause:-0}" -gt 5 ]; then
      printf '\n=== Attente du créneau ===\n'
      echo "prochaine relance du bot dans environ $((pause + 45)) s : attente de $((pause - 5)) s avant la bascule"
      sleep "$((pause - 5))"
    fi
    sur_le_serveur activer
    ;;
  redemarrer)
    sur_le_serveur redemarrer
    ;;
esac

if [ "$verification" = accept-new ] && [ -s "$connus" ]; then
  printf '\n=== Clé(s) du serveur à épingler dans deploiement/cle_serveur.txt ===\n'
  awk '{print $2, $3}' "$connus"
  ssh-keygen -lf "$connus" | awk '{print $1, $2, $NF}'
fi
