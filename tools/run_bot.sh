#!/bin/sh
# Lancement du bot comme tâche planifiée Alwaysdata (commande : /bin/sh /home/[compte]/MouseDiscord/tools/run_bot.sh).
#
# Fonctionnement documenté par Alwaysdata : si une exécution de tâche n'est pas terminée,
# la suivante est ignorée. Tant que le bot tourne, les déclenchements suivants ne créent donc
# pas de deuxième instance. Si le bot s'arrête, la prochaine exécution le relance.
#
# Le bot tourne au premier plan de cette tâche (pas de nohup, pas de setsid, pas de &).
# Les messages du bot sont ajoutés à bot.log.

APP_DIR="$HOME/MouseDiscord"
LOG="$APP_DIR/bot.log"

cd "$APP_DIR" || exit 1

# Garde-fou supplémentaire : si une instance tourne déjà (lancée à la main ou par une autre tâche), on ne lance rien.
if pgrep -f "[.]venv/bin/python bot[.]py" > /dev/null 2>&1; then
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') démarrage du bot" >> "$LOG"
exec "$APP_DIR/.venv/bin/python" bot.py >> "$LOG" 2>&1
