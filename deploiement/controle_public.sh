#!/usr/bin/env bash
# Contrôle public, SANS aucun identifiant : ce que n'importe quel visiteur voit du serveur.
#   1. chaque illustration du dépôt est-elle publiée, à la même taille, à l'adresse publique ?
#   2. quelle est la clé publique du serveur SSH (à épingler dans deploiement/cle_serveur.txt) ?
# Lecture seule : des requêtes HEAD et une poignée de main SSH. Ne fait jamais échouer le déploiement.
set -uo pipefail

cd "$(dirname "$0")/.."

valeur_de() {
  sed -n "s/^$1:[[:space:]]*//p" deploiement/serveur.txt 2>/dev/null | head -n 1 | tr -d '[:space:]'
}

hote="${AD_HOST:-$(valeur_de hote)}"
images="$(valeur_de images)"

printf '=== Illustrations publiées (%s) ===\n' "${images:-adresse absente de deploiement/serveur.txt}"
if [ -n "$images" ]; then
  publiees=0
  a_envoyer=0
  for fichier in assets/illustrations/*; do
    [ -f "$fichier" ] || continue
    nom="$(basename "$fichier")"
    attendu="$(stat -c %s "$fichier")"
    entetes="$(curl -sS -I -L --max-time 20 "$images/$nom" 2>&1 || true)"
    code="$(printf '%s\n' "$entetes" | awk 'toupper($1) ~ /^HTTP\// { code = $2 } END { print code }')"
    taille="$(printf '%s\n' "$entetes" | awk -F': *' 'tolower($1) == "content-length" { gsub(/\r/, "", $2); t = $2 } END { print t }')"
    if [ "$code" = 200 ] && [ "$taille" = "$attendu" ]; then
      publiees=$((publiees + 1))
      echo "  = $nom"
    elif [ "$code" = 200 ]; then
      a_envoyer=$((a_envoyer + 1))
      echo "  ~ $nom (en ligne : ${taille:-?} octets, dépôt : $attendu octets)"
    else
      a_envoyer=$((a_envoyer + 1))
      echo "  + $nom (pas en ligne : réponse ${code:-aucune})"
    fi
  done
  echo "identiques : $publiees ; à envoyer : $a_envoyer"
fi

printf '\n=== Clé publique du serveur SSH ===\n'
if [ -n "$hote" ] && command -v ssh-keyscan > /dev/null; then
  cles="$(ssh-keyscan -T 15 -t ed25519,ecdsa,rsa "$hote" 2> /dev/null | awk '{print $2, $3}' | sort)"
  if [ -n "$cles" ]; then
    printf '%s\n' "$cles"
    if grep -qE '^(ssh-|ecdsa-)' deploiement/cle_serveur.txt 2> /dev/null; then
      if [ "$(grep -E '^(ssh-|ecdsa-)' deploiement/cle_serveur.txt | sort)" = "$cles" ]; then
        echo "identique à deploiement/cle_serveur.txt"
      else
        echo "::warning::La clé du serveur ne correspond pas à deploiement/cle_serveur.txt."
      fi
    else
      echo "(pas encore épinglée dans deploiement/cle_serveur.txt)"
    fi
  else
    echo "(serveur SSH injoignable ou muet)"
  fi
else
  echo "(hôte absent de deploiement/serveur.txt)"
fi
exit 0
