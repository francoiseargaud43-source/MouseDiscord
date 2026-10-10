#!/bin/sh
# Surveillance du bot Mouse Discord, à lancer par une tâche planifiée Alwaysdata
# (toutes les 5 minutes). Ne lance une instance que si aucune n'est active.
#
# Solution de repli SANS Service (plan Free) : non documentée par Alwaysdata
# pour un processus permanent, à vérifier dans les journaux (bot.log).

APP_DIR="$HOME/MouseDiscord"
PYTHON="$APP_DIR/.venv/bin/python"
LOG="$APP_DIR/bot.log"

cd "$APP_DIR" || exit 1

# Une instance déjà active : on ne fait rien (instance unique).
if pgrep -f "[.]venv/bin/python bot[.]py" > /dev/null 2>&1; then
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') relance du bot" >> "$LOG"
# setsid + nohup : détache le bot du processus de la tâche, pour qu'il ne soit pas arrêté avec elle.
setsid nohup "$PYTHON" bot.py >> "$LOG" 2>&1 < /dev/null &
exit 0
