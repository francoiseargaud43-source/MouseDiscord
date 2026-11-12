#!/usr/bin/env bash
# Exécuté SUR le serveur Alwaysdata : deploiement/executer.sh l'envoie par SSH (« bash -s »).
# N'affiche jamais la valeur d'un secret : du .env, seuls les noms des variables sortent.
set -eu

etape="${1:?étape manquante}"
projet="$HOME/MouseDiscord"
sauvegardes="$HOME/MouseDiscord_sauvegardes"
python_venv="$projet/.venv/bin/python"
# Journal écrit par tools/run_bot.sh : chaque lancement y note « AAAA-MM-JJ HH:MM:SS démarrage du bot ».
journal="$projet/bot.log"
# Fichiers envoyés par executer.sh, pas encore en service.
attente="$HOME/MouseDiscord_envoi"
# Journaux d'Alwaysdata : services/ si le bot est un service, jobs/ s'il est lancé par une tâche planifiée.
journaux="$HOME/admin/logs/services $HOME/admin/logs/jobs"
# Dossier où la bascule range les fichiers qu'elle remplace ou retire (fixé par « activer »).
garde=""

titre() { printf '\n=== %s ===\n' "$1"; }

# Processus bot.py lancés depuis le dossier du projet (un autre bot du même compte n'est pas touché).
pids_du_bot() {
  local pid ici
  ici="$(readlink -f "$projet")"
  for pid in $(pgrep -u "$(id -u)" -f 'bot\.py' || true); do
    if [ "$(readlink -f "/proc/$pid/cwd" 2> /dev/null || true)" = "$ici" ]; then
      echo "$pid"
    fi
  done
}

# Ce qui sort d'ici est lu dans le journal GitHub, qui est PUBLIC (dépôt public) : tout ce qui ressemble
# à un secret est masqué (jeton Discord, mot de passe dans une adresse, valeur d'une clé ou d'un jeton,
# longue suite de caractères), et les lignes sont coupées à 300 caractères.
masquer() {
  sed -E \
    -e 's#://[^/[:space:]:@]+:[^@[:space:]]+@#://(masqué)@#g' \
    -e 's/(Session ID: )[0-9a-f]+/\1(masqué)/g' \
    -e 's/([Aa][Pp][Ii]_?[Kk][Ee][Yy]|[Tt][Oo][Kk][Ee][Nn]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Bb][Ee][Aa][Rr][Ee][Rr])([[:space:]]*[=:][[:space:]]*|[[:space:]]+)[^[:space:]]+/\1\2(masqué)/g' \
    -e 's/[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}/(jeton masqué)/g' \
    -e 's/[A-Za-z0-9+_-]{32,}/(longue suite masquée)/g' \
    | cut -c1-300
}

# Fin d'un journal, masquée.
fin_de() {
  tail -n "$2" "$1" | masquer
}

# Fin du journal le plus récent qui parle du bot (logger « mouse_discord »), puis du bot.log du projet.
journal_du_bot() {
  local lignes="${1:-40}" fichier
  # shellcheck disable=SC2086
  fichier="$(grep -rls 'mouse_discord' $journaux 2> /dev/null | xargs -r ls -t 2> /dev/null | head -n 1 || true)"
  if [ -n "$fichier" ]; then
    echo "--- fin de $fichier (modifié le $(date -r "$fichier" '+%Y-%m-%d %H:%M'))"
    fin_de "$fichier" "$lignes"
  else
    echo "(aucun journal d'Alwaysdata ne mentionne mouse_discord)"
  fi
  # Journal écrit dans le dossier du projet par tools/run_bot.sh (bot lancé par une tâche planifiée).
  if [ -f "$journal" ]; then
    echo "--- fin de $journal (modifié le $(date -r "$journal" '+%Y-%m-%d %H:%M'), $(du -h "$journal" | cut -f1))"
    fin_de "$journal" "$lignes"
  fi
}

# --- Démarrages du bot, lus dans bot.log ---------------------------------------------------------------
# Sur Alwaysdata, la tâche planifiée lance le bot sur une autre machine que celle du SSH : son processus
# n'est pas visible d'ici. Ce qui se voit, c'est bot.log, où tools/run_bot.sh note chaque démarrage.

nombre_de_demarrages() {
  if [ -f "$journal" ]; then
    grep -c 'démarrage du bot$' "$journal" || true
  else
    echo 0
  fi
}

# Tout ce que le bot a écrit depuis son dernier démarrage.
depuis_le_dernier_demarrage() {
  if [ -f "$journal" ]; then
    tac "$journal" | sed '/démarrage du bot$/q' | tac
  fi
}

# Les heures de bot.log viennent de la machine qui lance le bot, dont l'horloge peut être réglée sur un
# autre fuseau que celle du SSH (relevé du 2026-11-11 : bot.log en UTC, SSH en CET). Le décalage se
# déduit de la dernière heure écrite dans bot.log et de l'heure de modification du fichier, arrondi au
# quart d'heure.
decalage_horloge() {
  local derniere ecart
  derniere="$(tail -n 50 "$journal" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' | tail -n 1 || true)"
  if [ -z "$derniere" ]; then
    echo 0
    return 0
  fi
  ecart=$(($(date -r "$journal" +%s) - $(date -d "$derniere" +%s 2> /dev/null || date -r "$journal" +%s)))
  echo $(((ecart + (ecart >= 0 ? 450 : -450)) / 900 * 900))
}

# « heure période » du prochain démarrage attendu (secondes depuis 1970) quand les trois derniers
# démarrages sont espacés régulièrement et que le dernier date de moins d'une période. Rien sinon.
prochain_demarrage() {
  local t=() quand periode ecart maintenant decalage
  [ -f "$journal" ] || return 0
  decalage="$(decalage_horloge)"
  while read -r quand; do
    t+=("$(($(date -d "$quand" +%s 2> /dev/null || echo 0) + decalage))")
  done < <(grep 'démarrage du bot$' "$journal" | tail -n 3 | cut -c1-19)
  [ "${#t[@]}" -eq 3 ] || return 0
  periode=$((t[2] - t[1]))
  ecart=$((periode - (t[1] - t[0])))
  if [ "$periode" -lt 60 ] || [ "$periode" -gt 3600 ] || [ "${ecart#-}" -gt 5 ]; then return 0; fi
  maintenant="$(date +%s)"
  if [ "$maintenant" -lt "${t[2]}" ] || [ $((maintenant - t[2])) -gt $((periode + 20)) ]; then return 0; fi
  echo "$((t[2] + periode)) $periode"
}

# Quand le bot est relancé à heure fixe, la bascule se fait dans la minute qui précède la relance :
# l'ancien code ne tourne ainsi presque pas avec les nouvelles données, et la relance ne tombe pas
# au milieu de la bascule.
# Écrit « attente relance période » : secondes à attendre avant de basculer, heure de la relance visée
# (secondes depuis 1970) et période des relances. Rien si aucune relance régulière n'est repérée.
periode_des_relances=""
creneau_de_bascule() {
  local prevu="" periode="" reste attente_utile=0
  read -r prevu periode < <(
    prochain_demarrage
    echo
  ) || true
  [ -n "$prevu" ] || return 0
  reste=$((prevu - $(date +%s)))
  # Moins de 20 s avant la relance : trop juste, on vise la suivante.
  if [ "$reste" -lt 20 ]; then
    prevu=$((prevu + periode))
    reste=$((prevu - $(date +%s)))
  fi
  if [ "$reste" -gt 60 ]; then attente_utile=$((reste - 45)); fi
  echo "$attente_utile $prevu $periode"
}

# Étape « creneau » : une seule ligne, le nombre de secondes à attendre avant de lancer « activer ».
# executer.sh attend de son côté, sans garder de connexion ouverte pendant ce temps.
creneau() {
  local pause="" prevu="" periode=""
  read -r pause prevu periode < <(
    creneau_de_bascule
    echo
  ) || true
  echo "${pause:-0}"
}

attendre_le_creneau() {
  local pause="" prevu="" periode=""
  read -r pause prevu periode < <(
    creneau_de_bascule
    echo
  ) || true
  if [ -z "$prevu" ]; then
    echo "pas de relance régulière repérée dans bot.log : bascule immédiate"
    return 0
  fi
  periode_des_relances="$periode"
  echo "le bot est relancé toutes les $periode s ; relance visée : $(date -d "@$prevu" +%H:%M:%S)"
  if [ "$pause" -gt 0 ]; then
    echo "attente de $pause s : la bascule se fait 45 s avant la relance"
    sleep "$pause"
  fi
}

# Attend le prochain démarrage du bot (compté dans bot.log) puis sa connexion à Discord.
# $1 : nombre de démarrages déjà notés ; $2 : attente maximale en secondes.
# Retour : 0 connecté, 4 pas de démarrage dans le délai, 5 démarré mais pas connecté.
attendre_la_relance() {
  local deja="$1" limite="$2" i=0
  echo "attente de la prochaine relance par la tâche planifiée (au plus $limite s)"
  while [ "$(nombre_de_demarrages)" -le "$deja" ]; do
    if [ "$i" -ge "$limite" ]; then
      echo "Aucun démarrage noté dans bot.log en $limite s."
      return 4
    fi
    sleep 3
    i=$((i + 3))
  done
  echo "relance repérée après $i s : $(grep 'démarrage du bot$' "$journal" | tail -n 1 | cut -c1-19)"
  i=0
  until depuis_le_dernier_demarrage | grep -q 'Connecté en tant que'; do
    if [ "$i" -ge 90 ]; then
      echo "Le bot relancé ne s'est pas connecté à Discord en 90 s :"
      depuis_le_dernier_demarrage | masquer | tail -n 40
      return 5
    fi
    sleep 3
    i=$((i + 3))
  done
  sleep 4
  depuis_le_dernier_demarrage | masquer | head -n 30
  return 0
}

# Comment le bot est lancé : lanceur, rythme des démarrages, journaux des tâches planifiées de CE projet,
# erreurs relevées. Lecture seule.
lancement() {
  local fichier n
  echo "--- lanceur de la tâche planifiée"
  if [ -f "$projet/tools/run_bot.sh" ]; then
    ls -l "$projet/tools/run_bot.sh"
    grep -vE '^[[:space:]]*(#|$)' "$projet/tools/run_bot.sh" | masquer
  else
    echo "tools/run_bot.sh ABSENT"
  fi
  if command -v crontab > /dev/null 2>&1; then
    echo "--- tâches du compte (crontab)"
    (crontab -l 2>&1 || true) | grep -vE '^[[:space:]]*(#|$)' | masquer | head -n 10
  fi
  if [ -f "$journal" ]; then
    echo "--- démarrages notés dans bot.log : $(nombre_de_demarrages) en tout, par jour :"
    grep 'démarrage du bot$' "$journal" | cut -c1-10 | uniq -c | tail -n 8
    echo "--- douze derniers démarrages"
    grep 'démarrage du bot$' "$journal" | tail -n 12 | cut -c1-19 | tr '\n' ';'
    echo
    echo "--- erreurs dans bot.log (2 000 dernières lignes, par type)"
    tail -n 2000 "$journal" | grep -E '^([A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Forbidden|NotFound|HTTPException)[A-Za-z]*:| *[0-9-]+ [0-9:,]+ (ERROR|CRITICAL) )' \
      | sed -E 's/^ *[0-9-]+ [0-9:,]+ //' | masquer | cut -c1-160 | sort | uniq -c | sort -rn | head -n 8
    echo "(fin de la liste)"
  fi
  echo "--- journaux des tâches planifiées qui concernent ce bot"
  n=0
  for fichier in $(ls -t "$HOME"/admin/logs/jobs/*/*.log 2> /dev/null | head -n 6); do
    if grep -qs 'MouseDiscord\|run_bot\|bot\.py' "$fichier"; then
      n=$((n + 1))
      if [ "$n" -le 2 ]; then
        echo "--- $fichier ($(wc -l < "$fichier") lignes) : formes de lignes les plus fréquentes"
        masquer < "$fichier" | sed -E 's/[0-9]+/N/g' | cut -c1-140 | sort | uniq -c | sort -rn | head -n 6
        echo "--- fin de ce journal"
        fin_de "$fichier" 14
      fi
    else
      echo "(autre tâche, non affichée : $fichier, $(wc -l < "$fichier") lignes)"
    fi
  done
  echo "--- journaux de services les plus récents"
  for fichier in $(ls -t "$HOME"/admin/logs/services/*/*.log 2> /dev/null | head -n 2); do
    if grep -qs 'MouseDiscord\|mouse_discord\|bot\.py' "$fichier"; then
      echo "--- $fichier (modifié le $(date -r "$fichier" '+%Y-%m-%d %H:%M'))"
      fin_de "$fichier" 8
    else
      echo "(autre service, non affiché : $fichier)"
    fi
  done
}

# Place occupée : l'offre gratuite d'Alwaysdata est limitée, une mise de côté ne doit pas la remplir.
place() {
  du -sm "$HOME" 2> /dev/null | awk '{print "compte entier : " $1 " Mo"}' || true
  du -sm "$projet" "$projet/.venv" "$projet/utils" "$journal" "$HOME/www" "$HOME/admin/logs" "$sauvegardes" "$attente" 2> /dev/null \
    | awk '{printf "  %5d Mo  %s\n", $1, $2}' || true
  echo "--- dossier utils/ du projet"
  ls -la "$projet/utils" 2> /dev/null | head -n 40 || true
  echo "--- dossier tools/ du projet"
  ls -la "$projet/tools" 2> /dev/null | head -n 20 || true
  echo "--- dossier state/ du projet (noms et tailles seulement)"
  (cd "$projet" && find state -maxdepth 2 -printf '%y %8s %TY-%Tm-%Td %TH:%TM %p\n' 2> /dev/null | sort -k5 | head -n 20) || true
  echo "--- fichiers .env du projet (noms seulement, hors environnement Python)"
  (cd "$projet" && find . -name '.venv' -prune -o -name '.env*' -print 2> /dev/null | sort | head -n 10) || true
}

etat() {
  titre "Serveur"
  date '+%Y-%m-%d %H:%M:%S %Z'
  echo "machine : $(hostname)"
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
  if [ -d "$attente" ]; then
    echo "dossier d'attente présent ($attente) : un envoi n'est pas allé au bout"
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
    echo "AUCUN processus bot.py visible depuis cette machine dans $projet"
    echo "(normal quand le bot est lancé par une tâche planifiée : voir « Lancement du bot »)"
  fi
  echo "--- processus du compte sur cette machine"
  ps -u "$(id -u)" -o pid,etime,cmd | grep -v ' \[' | cut -c1-160 | head -n 20 || true

  titre "Images publiées"
  local cible="$HOME/www/illustrations"
  if [ -L "$cible" ]; then
    echo "$cible -> $(readlink "$cible") (lien symbolique)"
    ls "$cible/" | head -n 40 || true
  elif [ -d "$cible" ]; then
    ls -la "$cible" | head -n 40 || true
  else
    echo "ABSENT : $cible"
    ls -la "$HOME/www" 2> /dev/null | head -n 20 || true
  fi

  titre "Contrôle de déploiement"
  if [ -x "$python_venv" ] && [ -f "$projet/tools/check_deployment.py" ]; then
    (cd "$projet" && "$python_venv" tools/check_deployment.py) || echo "(le contrôle signale des erreurs)"
  else
    echo "(contrôle impossible : venv ou tools/check_deployment.py absent)"
  fi

  titre "Journal du bot"
  journal_du_bot 40

  titre "Lancement du bot"
  lancement

  titre "Place occupée"
  place

  titre "Mises de côté (fichiers remplacés ou retirés par les mises à jour)"
  ls -lt "$sauvegardes" 2> /dev/null | head -n 12 || echo "(aucune)"
}

sommes() {
  cd "$projet"
  find . \( -path ./.venv -o -path ./venv -o -path ./env -o -path ./state -o -path ./.git -o -name __pycache__ \) -prune \
    -o -type f ! -name .env ! -name VERSION -print0 | sort -z | xargs -0 -r sha256sum | head -n 3000
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

# Étape à part, lancée AVANT la mise en service de assets/images.json : le bot en marche relit ce fichier
# à chaque interaction, une image doit donc être en ligne avant d'y être nommée.
publier() {
  titre "Images publiées"
  publier_images
}

# Contrôle du code et des données envoyés, AVANT de toucher au bot en service : syntaxe avec le Python
# du serveur, chargement des modules du bot avec les réglages du .env en service (une valeur refusée par
# le nouveau code se voit ici), puis contrôle de déploiement. Rien n'est écrit dans le projet.
controler_l_envoi() {
  (
    cd "$attente"
    PYTHONDONTWRITEBYTECODE=1 "$python_venv" -u - "$attente" "$projet/.env" << 'PYTHON'
import os
import runpy
import sys
from pathlib import Path

from dotenv import dotenv_values

envoi, fichier_env = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(envoi))
for fichier in sorted(envoi.rglob("*.py")):
    compile(fichier.read_text(encoding="utf-8"), str(fichier), "exec")
print("syntaxe correcte avec Python %d.%d" % sys.version_info[:2])

if fichier_env.is_file():
    for cle, valeur in dotenv_values(fichier_env).items():
        if valeur is not None:
            os.environ.setdefault(cle, valeur)
import bot  # noqa: E402,F401  (lit la configuration : une valeur refusée par le nouveau code arrête ici)
import cogs.finder_flow  # noqa: E402,F401
import cogs.mouse_finder  # noqa: E402,F401
print("modules du bot chargés avec les réglages en service")

controle = runpy.run_path(str(envoi / "tools" / "check_deployment.py"))
resultats = controle["check"](envoi, dict(os.environ))
for niveau, message in resultats:
    if not message.startswith("fichier .env absent"):  # ici, les réglages viennent du .env en service
        print(f"[{niveau:9}] {message}")
erreurs = sum(1 for niveau, _ in resultats if niveau == "ERREUR")
print(f"\n{erreurs} erreur(s) bloquante(s).")
sys.exit(1 if erreurs else 0)
PYTHON
  )
}

# Résume ce que rsync a fait (une ligne par dossier) et note les fichiers AJOUTÉS, pour « restaurer ».
compter() {
  awk -v prefixe="$1" -v liste="${garde:?}.ajouts" '
    /^>f\+\+\+\+\+\+\+\+\+ / { ajoutes++; print prefixe substr($0, 13) >> liste; next }
    /^>f/ { remplaces++; next }
    /^\*deleting / { if ($0 !~ /\/$/) retires++; next }
    END {
      printf "  %-16s %d ajouté(s), %d remplacé(s), %d retiré(s)\n", (prefixe == "" ? "reste du projet" : prefixe), ajoutes, remplaces, retires
    }'
}

# Met en service les fichiers envoyés. Chaque fichier remplacé ou retiré est d'abord RANGÉ dans $garde,
# à la même place que dans le projet : rien n'est détruit, et « restaurer » remet tout comme avant.
# cogs/ et utils/ deviennent identiques au dépôt (ce qui n'y est plus est rangé) ; ailleurs, rien n'est retiré.
# Jamais touchés : .env, state/, bot.log, .venv et les illustrations (envoyées à part, jamais remplacées).
basculer() {
  local dossier
  : > "${garde:?}.ajouts" || return 1
  for dossier in cogs utils; do
    mkdir -p "$projet/$dossier" || return 1
    # /__pycache__/ : le cache de Python de ce dossier reste en place (il se refait tout seul).
    rsync -a -c --delete --backup --backup-dir="$garde/$dossier" --itemize-changes --exclude '/__pycache__/' \
      "$attente/$dossier/" "$projet/$dossier/" < /dev/null | compter "$dossier/" || return 1
  done
  rsync -a -c --backup --backup-dir="$garde" --itemize-changes \
    --exclude '/cogs/' --exclude '/utils/' --exclude '/assets/illustrations/' \
    --exclude '/.env' --exclude '/state/' --exclude '/bot.log' --exclude '__pycache__/' \
    "$attente/" "$projet/" < /dev/null | compter "" || return 1
}

# Remet le projet dans l'état d'avant la bascule : les fichiers ajoutés sont retirés, les fichiers rangés
# retrouvent leur place (simple changement de dossier : aucune place supplémentaire n'est nécessaire).
restaurer() {
  local f
  if [ -z "$garde" ] || [ ! -d "$garde" ]; then
    echo "rien à restaurer"
    return 0
  fi
  if [ -f "$garde.ajouts" ]; then
    while IFS= read -r f; do
      if [ -n "$f" ]; then rm -f "${projet:?}/${f:?}"; fi
    done < "$garde.ajouts"
  fi
  (cd "$garde" && find . -type f -print0) | while IFS= read -r -d '' f; do
    mkdir -p "$projet/$(dirname "$f")"
    mv -f "$garde/$f" "$projet/$f"
  done
  rm -rf "${garde:?}" "${garde:?}.ajouts"
  echo "état précédent restauré : le projet est comme avant la bascule"
}

# Relance du bot. Processus visible d'ici (service, ou tâche sur la même machine) : il est arrêté et
# Alwaysdata le relance. Sinon : la tâche planifiée le relance d'elle-même, on attend ce démarrage.
# $1 : nombre de démarrages notés dans bot.log avant la relance attendue.
# Retour : 0 relancé, 3 rien à relancer, 4 pas relancé dans le délai, 5 relancé mais pas connecté.
relancer() {
  local deja="$1" avant apres="" pid encore i
  avant="$(pids_du_bot | tr '\n' ' ')"
  if [ -z "$avant" ]; then
    if [ "$(nombre_de_demarrages)" -eq 0 ]; then
      echo "AUCUN processus du bot en cours et aucun démarrage noté dans bot.log :"
      echo "le service ou la tâche planifiée est à l'arrêt, à relancer dans l'administration Alwaysdata"
      echo "(Advanced > Services, ou Tâches planifiées)."
      return 3
    fi
    echo "aucun processus visible depuis cette machine : le bot est lancé ailleurs par la tâche planifiée"
    if [ -n "$periode_des_relances" ]; then i=$((periode_des_relances + 90)); else i=720; fi
    attendre_la_relance "$deja" "$i"
    return $?
  fi
  echo "arrêt du processus $avant(Alwaysdata le relance tout seul : service, ou tâche planifiée au créneau suivant)"
  # shellcheck disable=SC2086
  kill -TERM $avant 2> /dev/null || true
  for i in $(seq 1 10); do
    sleep 1
    encore=""
    for pid in $avant; do
      if kill -0 "$pid" 2> /dev/null; then encore="$encore $pid"; fi
    done
    if [ -z "$encore" ]; then break; fi
  done
  for pid in $avant; do
    if kill -0 "$pid" 2> /dev/null; then kill -KILL "$pid" 2> /dev/null || true; fi
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
    return 4
  fi
  echo "nouveau processus : $apres(relancé après environ $((i * 3)) s)"
  sleep 12
  journal_du_bot 25
  return 0
}

redemarrer() {
  titre "Redémarrage du bot"
  local code=0
  relancer "$(nombre_de_demarrages)" || code=$?
  if [ "$code" -ne 0 ] && [ "$code" -ne 5 ]; then journal_du_bot 30; fi
  exit "$code"
}

# Avant toute modification : dépendances puis contrôle des fichiers envoyés dans le dossier d'attente.
controler() {
  if [ ! -f "$attente/VERSION" ] || [ ! -f "$attente/bot.py" ]; then
    echo "Dossier d'attente incomplet ($attente) : rien n'est fait."
    exit 2
  fi
  mkdir -p "$projet"

  titre "Dépendances"
  if [ ! -x "$python_venv" ]; then
    echo "création de l'environnement virtuel"
    (cd "$projet" && python -m venv .venv && "$python_venv" -m pip install -q --upgrade pip)
    "$python_venv" -m pip install -q -r "$attente/requirements.txt"
    echo "dépendances installées"
  elif ! cmp -s "$attente/requirements.txt" "$projet/requirements.txt"; then
    "$python_venv" -m pip install -q -r "$attente/requirements.txt"
    echo "dépendances mises à jour"
  else
    echo "requirements.txt inchangé : rien à installer"
  fi

  titre "Contrôle des fichiers envoyés (le bot en service n'est pas encore touché)"
  if ! controler_l_envoi; then
    echo "ÉCHEC du contrôle : rien n'a été changé, le bot continue avec sa version actuelle."
    rm -rf "${attente:?}"
    exit 1
  fi
  find "$attente" -name '__pycache__' -type d -prune -exec rm -rf {} +
  rm -rf "${attente:?}/state"
}

activer() {
  local code=0 deja trace vieux
  if [ ! -f "$attente/VERSION" ] || [ ! -f "$attente/bot.py" ]; then
    echo "Dossier d'attente incomplet ($attente) : rien n'est fait."
    exit 2
  fi

  titre "Bascule"
  if [ -z "$(pids_du_bot)" ]; then attendre_le_creneau; fi
  mkdir -p "$sauvegardes"
  chmod 700 "$sauvegardes"
  garde="$sauvegardes/avant_$(date +%Y%m%d_%H%M%S)"
  trace="$garde.txt"
  mkdir "$garde"
  # La bascule ne dépend pas de la connexion : si celle-ci est coupée, elle va au bout (ou restaure) quand même.
  set +e
  (
    set -o pipefail
    trap '' HUP PIPE
    echo "bascule du $(date '+%Y-%m-%d %H:%M:%S') vers la version $(cut -c1-7 "$attente/VERSION")"
    if basculer; then
      echo "fichiers remplacés ou retirés rangés dans $garde"
      echo
      if (cd "$projet" && "$python_venv" tools/check_deployment.py); then exit 0; fi
      echo "ÉCHEC du contrôle après la bascule : retour à l'état précédent."
    else
      echo "ÉCHEC de la bascule (voir le message ci-dessus) : retour à l'état précédent."
    fi
    restaurer
    exit 1
  ) > "$trace" 2>&1
  code=$?
  set -e
  cat "$trace"
  if [ "$code" -ne 0 ]; then
    rm -rf "${attente:?}"
    exit "$code"
  fi
  deja="$(nombre_de_demarrages)"

  titre "Redémarrage du bot"
  relancer "$deja" || code=$?
  case "$code" in
    0) ;;
    5)
      echo "La nouvelle version ne démarre pas : retour à la version précédente."
      restaurer
      rm -rf "${attente:?}"
      exit 5
      ;;
    *)
      echo "Les nouveaux fichiers sont en place et contrôlés ; ils seront chargés au prochain démarrage du bot."
      journal_du_bot 30
      rm -rf "${attente:?}"
      exit "$code"
      ;;
  esac

  rm -rf "${attente:?}"
  # Seules les cinq dernières mises de côté sont conservées.
  for vieux in $(ls -d "$sauvegardes"/avant_*/ 2> /dev/null | sort -r | tail -n +6); do
    vieux="${vieux%/}"
    rm -rf "${vieux:?}" "${vieux:?}.txt" "${vieux:?}.ajouts"
  done
  echo
  echo "version en service : $(cat "$projet/VERSION")"
}

case "$etape" in
  etat | sommes | controler | publier | creneau | activer | redemarrer) "$etape" ;;
  *)
    echo "Étape inconnue : $etape"
    exit 2
    ;;
esac
