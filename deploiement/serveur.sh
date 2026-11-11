#!/usr/bin/env bash
# Exécuté SUR le serveur Alwaysdata : deploiement/executer.sh l'envoie par SSH (« bash -s »).
# N'affiche jamais la valeur d'un secret : du .env, seuls les noms des variables sortent.
set -eu

etape="${1:?étape manquante}"
projet="$HOME/MouseDiscord"
sauvegardes="$HOME/MouseDiscord_sauvegardes"
python_venv="$projet/.venv/bin/python"
# Journaux d'Alwaysdata : services/ si le bot est un service, jobs/ s'il est lancé par une tâche planifiée.
journaux="$HOME/admin/logs/services $HOME/admin/logs/jobs"

titre() { printf '\n=== %s ===\n' "$1"; }

# Processus bot.py lancés depuis le dossier du projet (un autre bot du même compte n'est pas touché).
pids_du_bot() {
  local pid ici
  ici="$(readlink -f "$projet")"
  for pid in $(pgrep -u "$(id -u)" -f 'bot\.py' || true); do
    if [ "$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)" = "$ici" ]; then
      echo "$pid"
    fi
  done
}

# Fin du journal le plus récent qui parle du bot (logger « mouse_discord »).
journal_du_bot() {
  local lignes="${1:-40}" fichier dossier
  # shellcheck disable=SC2086
  fichier="$(grep -rls 'mouse_discord' $journaux 2>/dev/null | xargs -r ls -t 2>/dev/null | head -n 1 || true)"
  if [ -z "$fichier" ]; then
    echo "(aucun journal ne mentionne mouse_discord)"
    for dossier in $journaux; do
      if [ -d "$dossier" ]; then
        echo "--- $dossier"
        ls -lt "$dossier" | head -n 6 || true
      fi
    done
    return 0
  fi
  echo "--- fin de $fichier"
  tail -n "$lignes" "$fichier" | cut -c1-300
}

etat() {
  titre "Serveur"
  date '+%Y-%m-%d %H:%M:%S %Z'
  echo "dossier personnel : $HOME"
  python --version 2>&1 || true

  titre "Dossier du projet"
  if [ ! -d "$projet" ]; then
    echo "ABSENT : $projet"
    ls -la "$HOME" | head -n 40 || true
    return 0
  fi
  ls -la "$projet"
  if [ -f "$projet/VERSION" ]; then
    echo "version déployée (commit) : $(cat "$projet/VERSION")"
  else
    echo "pas de fichier VERSION : dernier envoi fait à la main"
  fi

  titre ".env (noms des variables seulement)"
  if [ -f "$projet/.env" ]; then
    ls -l "$projet/.env"
    awk '/^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=/ {
           cle = $0; sub(/=.*/, "", cle); gsub(/[[:space:]]/, "", cle)
           valeur = substr($0, index($0, "=") + 1)
           print cle "=" (valeur == "" ? "(vide)" : "(renseigné)")
         }' "$projet/.env"
    grep -E '^IMAGES_BASE_URL=' "$projet/.env" || echo "IMAGES_BASE_URL absent"
  else
    echo ".env ABSENT"
  fi

  titre "Environnement Python du projet"
  if [ -x "$python_venv" ]; then
    "$python_venv" --version
    "$python_venv" -c "import discord, dotenv; print('discord.py', discord.__version__)" 2>&1 || true
  else
    echo "venv ABSENT : $python_venv"
  fi

  titre "Processus du bot"
  local pids
  pids="$(pids_du_bot | tr '\n' ' ')"
  if [ -n "$pids" ]; then
    # shellcheck disable=SC2086
    ps -o pid,lstart,etime,cmd -p $pids | cut -c1-200
  else
    echo "AUCUN processus bot.py lancé depuis $projet"
  fi
  echo "--- tous les processus du compte"
  ps -u "$(id -u)" -o pid,etime,cmd | cut -c1-160 | head -n 30 || true

  titre "Images publiées"
  local cible="$HOME/www/illustrations"
  if [ -L "$cible" ]; then
    echo "$cible -> $(readlink "$cible") (lien symbolique)"
    ls "$cible/" | head -n 40 || true
  elif [ -d "$cible" ]; then
    ls -la "$cible" | head -n 40 || true
  else
    echo "ABSENT : $cible"
    ls -la "$HOME/www" 2>/dev/null | head -n 20 || true
  fi

  titre "Contrôle de déploiement"
  if [ -x "$python_venv" ] && [ -f "$projet/tools/check_deployment.py" ]; then
    (cd "$projet" && "$python_venv" tools/check_deployment.py) || echo "(le contrôle signale des erreurs)"
  else
    echo "(contrôle impossible : venv ou tools/check_deployment.py absent)"
  fi

  titre "Journal du bot"
  journal_du_bot 40

  titre "Sauvegardes"
  ls -lt "$sauvegardes" 2>/dev/null | head -n 8 || echo "(aucune)"
}

sommes() {
  cd "$projet"
  find . \( -path ./.venv -o -path ./venv -o -path ./env -o -path ./state -o -path ./.git -o -name __pycache__ \) -prune \
    -o -type f ! -name .env ! -name VERSION -print0 | sort -z | xargs -0 -r sha256sum | head -n 3000
}

sauvegarde() {
  titre "Sauvegarde"
  if [ ! -d "$projet" ]; then
    echo "Projet absent : rien à sauvegarder, création de $projet"
    mkdir -p "$projet"
    return 0
  fi
  mkdir -p "$sauvegardes"
  chmod 700 "$sauvegardes"
  local nom
  nom="$sauvegardes/avant_$(date +%Y%m%d_%H%M%S).tgz"
  tar -czf "$nom" -C "$HOME" --exclude='MouseDiscord/.venv' --exclude='__pycache__' MouseDiscord
  chmod 600 "$nom"
  echo "état précédent gardé dans $nom ($(du -h "$nom" | cut -f1))"
  # Seules les cinq dernières sauvegardes sont conservées.
  ls -t "$sauvegardes"/avant_*.tgz | tail -n +6 | xargs -r rm -f
}

restaurer() {
  local derniere
  derniere="$(ls -t "$sauvegardes"/avant_*.tgz 2>/dev/null | head -n 1 || true)"
  if [ -z "$derniere" ]; then
    echo "aucune sauvegarde à restaurer"
    return 0
  fi
  tar -xzf "$derniere" -C "$HOME"
  echo "état précédent restauré depuis $derniere"
}

publier_images() {
  local cible="$HOME/www/illustrations" fichier nom ajoutees=0 conservees=0
  if [ -L "$cible" ]; then
    echo "lien symbolique vers $(readlink "$cible") : rien à copier"
  elif [ -d "$HOME/www" ]; then
    mkdir -p "$cible"
    # Une image déjà en ligne n'est jamais remplacée : Discord garde longtemps en mémoire une image
    # déjà affichée, donc une nouvelle version se publie sous un NOUVEAU nom (assets/images.json).
    for fichier in "$projet"/assets/illustrations/*; do
      [ -f "$fichier" ] || continue
      nom="$(basename "$fichier")"
      if [ ! -e "$cible/$nom" ]; then
        cp "$fichier" "$cible/$nom"
        ajoutees=$((ajoutees + 1))
        echo "  + $nom"
      elif ! cmp -s "$fichier" "$cible/$nom"; then
        conservees=$((conservees + 1))
        echo "  ~ $nom : la version en ligne est différente, elle est conservée"
      fi
    done
    echo "$ajoutees image(s) ajoutée(s), $conservees différente(s) conservée(s), $(ls "$cible" | wc -l) fichier(s) dans $cible"
  else
    echo "pas de dossier ~/www : images non publiées"
  fi
}

# Étape à part, lancée AVANT l'envoi de assets/images.json : le bot en marche relit ce fichier à chaque
# interaction, une image doit donc être en ligne avant d'y être nommée.
publier() {
  titre "Images publiées"
  publier_images
}

redemarrer() {
  titre "Redémarrage du bot"
  local avant apres="" pid encore i
  avant="$(pids_du_bot | tr '\n' ' ')"
  if [ -z "$avant" ]; then
    echo "AUCUN processus du bot en cours : le service ou la tâche planifiée est à l'arrêt."
    echo "À relancer dans l'administration Alwaysdata (Advanced > Services, ou Tâches planifiées)."
    journal_du_bot 30
    exit 3
  fi
  echo "arrêt du processus $avant(Alwaysdata le relance tout seul : service, ou tâche planifiée au créneau suivant)"
  # shellcheck disable=SC2086
  kill -TERM $avant 2>/dev/null || true
  for i in $(seq 1 10); do
    sleep 1
    encore=""
    for pid in $avant; do
      if kill -0 "$pid" 2>/dev/null; then encore="$encore $pid"; fi
    done
    [ -z "$encore" ] && break
  done
  for pid in $avant; do
    if kill -0 "$pid" 2>/dev/null; then kill -KILL "$pid" 2>/dev/null || true; fi
  done
  # Une tâche planifiée « toutes les 5 minutes » peut mettre jusqu'à 5 minutes à relancer le bot.
  for i in $(seq 1 110); do
    sleep 3
    apres="$(pids_du_bot | tr '\n' ' ')"
    if [ -n "$apres" ] && [ "$apres" != "$avant" ]; then break; fi
    apres=""
  done
  if [ -z "$apres" ]; then
    echo "Le bot n'a pas été relancé au bout de 5 minutes 30."
    journal_du_bot 40
    exit 4
  fi
  echo "nouveau processus : $apres(relancé après environ $((i * 3)) s)"
  sleep 12
  journal_du_bot 25
}

activer() {
  cd "$projet"
  titre "Dépendances"
  if [ ! -x "$python_venv" ]; then
    echo "création de l'environnement virtuel"
    python -m venv .venv
    "$python_venv" -m pip install -q --upgrade pip
  fi
  "$python_venv" -m pip install -q -r requirements.txt
  echo "dépendances à jour"

  titre "Contrôle de déploiement"
  if ! "$python_venv" tools/check_deployment.py; then
    echo "ÉCHEC du contrôle : le bot n'est pas redémarré."
    restaurer
    exit 1
  fi
  redemarrer
}

case "$etape" in
  etat | sommes | sauvegarde | publier | activer | redemarrer) "$etape" ;;
  *)
    echo "Étape inconnue : $etape"
    exit 2
    ;;
esac
