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

envoyer() {
  "${lanceur[@]}" rsync -rltz -e "ssh ${options_ssh[*]}" "$@"
}

# Copie de travail : exactement ce qui doit se trouver sur le serveur (docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md §2.3).
preparer() {
  prepa="$(mktemp -d)"
  mkdir -p "$prepa/tools"
  cp bot.py config.py requirements.txt README.md .env.example "$prepa/"
  cp -r cogs utils data assets "$prepa/"
  cp tools/check_deployment.py "$prepa/tools/"
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
    sur_le_serveur sauvegarde
    printf '\n=== Envoi des fichiers (commit %s) ===\n' "$(git rev-parse --short HEAD)"
    envoyer --delete --exclude '__pycache__/' "$prepa/cogs/" "$AD_USER@$AD_HOST:MouseDiscord/cogs/"
    envoyer --delete --exclude '__pycache__/' "$prepa/utils/" "$AD_USER@$AD_HOST:MouseDiscord/utils/"
    envoyer --exclude 'cogs/' --exclude 'utils/' "$prepa/" "$AD_USER@$AD_HOST:MouseDiscord/"
    echo "fichiers envoyés"
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
