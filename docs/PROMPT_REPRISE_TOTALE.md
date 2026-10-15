# PROMPT DE REPRISE TOTALE — AzeMouse / MouseDiscord

**Destinataire** : un ingénieur IA qui prend la suite, avec **pleins pouvoirs** sur ce dépôt.
**Émetteur** : l'agent qui a produit l'état actuel (77 passes, du 2026-10-11 au 2026-10-14).
**Date d'écriture** : 2026-10-15.
**Dépôt** : `francoiseargaud43-source/MouseDiscord` — branche de travail `arena/87fafd0d-mousediscord`, HEAD `db3d20d`, PR #1 ouverte.
**Propriétaire** : François (projet **AzeMouse**). Il tranche le **produit** ; toi, tu tranches la **technique**.

> **Lis ce document en entier avant de toucher au dépôt.** Puis, avant de faire confiance à quoi que ce soit qu'il contient — chiffres compris —, exécute le §8 : il est écrit pour que tu ne me croies **pas** sur parole.

---

## 0. Ce que ce document est, et ce qu'il n'est pas

C'est un **brief de reprise**, pas une spécification. Il raconte :

1. ce que fait le produit, et pour qui (§2) ;
2. comment le dépôt est fait (§3) ;
3. la méthode qui a produit l'état actuel, et pourquoi elle a tenu (§4) ;
4. l'état **mesuré** au 2026-10-14, et comment reproduire chaque chiffre (§5) ;
5. **où se cachent les défauts** — la typologie des 99 constats, c'est la partie la plus utile (§6) ;
6. ce qui est **fragile, redondant ou carrément à jeter** — la dette, dite honnêtement (§7) ;
7. ce que tu dois **vérifier** avant de bâtir dessus (§8) ;
8. tes **droits** (§9) et tes **obligations** (§10) ;
9. le mode d'emploi des données et des sources — le cœur du métier (§11) ;
10. les **pièges** déjà payés, pour ne pas les repayer (§12) ;
11. un **plan d'attaque** suggéré (§13) et la **définition de « fini »** (§14).

Ce document n'est **pas** la vérité révélée : là où il contredit le code ou les données, **le code et les données ont raison**, et la contradiction est un défaut à corriger.

---

## 1. Mandat

**Le propriétaire t'accorde, par la présente, tous les droits sur ce dépôt.** Concrètement :

- **Tout changer** : l'architecture, l'interface, le moteur de calcul, le schéma des données, les outils, les tests, la documentation, le déploiement.
- **Supprimer** : des fichiers, des modules, des tests, des documents, des dépendances, des lignes de code — sans te justifier autrement que par le résultat.
- **Créer** : des modules, des outils, des sous-agents, des branches, des PR, des scripts, une nouvelle documentation.
- **Utiliser le réseau** : EloShapes, les boutiques officielles, la documentation des fabricants — le propriétaire t'autorise explicitement à **aller chercher les images sur EloShapes** (voir §9.3 pour la seule nuance).
- **Sortir du cadre** : si la meilleure solution est de ne pas faire ce qui est décrit ici, fais l'autre.

**La mission, en une phrase** : *reprendre tout le système de zéro, vérifier tout ce qui a été affirmé, corriger ce qui est faux, simplifier ce qui est un fouillis, et le rendre dix fois plus propre, plus extensible et plus vérifiable — sans jamais inventer une donnée.*

Le propriétaire l'a formulé ainsi (2026-10-15, ses mots) :

> « je veux qu'elle revoie tout le système, qu'elle le corrige, qu'elle l'améliore, qu'elle remette tout bien dans l'ordre parce que c'est un peu du n'importe quoi ce qu'on a fait […] qu'elle vérifie tout ce que t'as fait […] qu'elle puisse faire ce qu'elle veut et qu'elle a le droit de supprimer des lignes de code […] on fera en sorte elle et moi de rajouter de la base de données au niveau des souris plus tard. »

**Les six non-négociables** (le reste est négociable, y compris ce que j'ai documenté comme « règles ») :

1. **Aucune invention.** Jamais une valeur, un prix, une dimension, une compatibilité de prise, une identité d'image, un chiffre de mesure qui ne soit adossé à une source consultable et datée. Rien n'est « plausible » : c'est **source** ou c'est **vide**.
2. **L'expérience de l'utilisateur prime** sur toute considération d'élégance logicielle. Le résultat doit rester **le plus concis possible** sur un écran de téléphone, en français irréprochable.
3. **Les prix sont en euros, relevés sur la boutique officielle** (`?country=FR` chez ATK), **sans jamais convertir** une devise.
4. **La mesure se fait sur des images réelles, datées, dont l'identité est vérifiée** — jamais depuis une fiche produit réécrite par un revendeur.
5. **Tout chiffre publié doit être rejouable** : une commande, un outil, un test, ou une source datée. Un nombre qu'on ne peut pas remesurer n'a pas le droit d'exister dans ce dépôt.
6. **La vie privée** : `ephemeral=True` partout sauf l'écran d'accueil, aucune donnée personnelle stockée, aucune trace des saisies d'un membre.

---

## 2. Le produit en une page

**AzeMouse** est un **bot Discord** qui aide un joueur à choisir une souris de jeu **adaptée à sa main**, à partir de trois choses : sa **prise** (palm / claw / fingertip, avec la variante de claw), les **dimensions de sa main** en millimètres, et son **budget**.

**Le parcours** (boutons et menus Discord, jamais de commande à taper) :

```
Étape 1 — Votre prise (palm / claw / fingertip)
   ├─ si claw : variante (relâchée / agressive / pincée)
   ├─ si palm ou claw : éminence thénar (petite / moyenne / grande)   ← informatif, n'enlève aucun point
   ├─ mesures : longueur et largeur de la main en mm (modal)
   └─ budget : Économique / Qualité-Prix / Haut de Gamme / Peu importe / budget libre en €
```

Puis **un seul message** : le résultat. Trois lignes au maximum —

| Ligne | Contenu | Règle |
| --- | --- | --- |
| 🎯 **Match Idéal** | nom, % du maximum théorique, prix, poids, forme, phrase « en clair » | le meilleur score de la fenêtre de budget |
| 💡 **Alternative** | idem | un peu moins bien, souvent moins chère |
| 💸 / ➕ / 🔎 **3ᵉ place** | la 3ᵉ place, remplie **même vide de sens** ; titre selon son rôle réel : « 💸 L'économie » (strictement moins chère), « ➕ L'autre option » (dans la fenêtre, pas moins chère), « 🔎 Autre piste » (dernier palier) | peut être un peu plus chère (décision du propriétaire) ; la 2ᵉ place peut aussi devenir « 🔎 Autre piste » (`cogs/finder_flow.py`, `third_slot_title` / `alternative_slot_title`) |

Plus, en dessous : un bloc **« 📐 Vos repères de taille »** (les plages cibles calculées pour **cette** main), et tout en bas, en petit, **« 🧭 Pourquoi ce choix ? »** (le calcul expliqué). **Aucun score de confiance en tête, aucun tableau des souris écartées, aucune matrice** : ce que l'utilisateur voit tient sur un écran.

**Ce que le bot ne fait pas** : pas de compte, pas de base de données de membres, pas de commande slash obligatoire, pas de publicité mensongère — les liens d'achat sont **affiliés** (`?ref=aze`, `?ref=AZE`, Scyrox `?bg_ref=…`) et **un par un**, jamais en masse.

**Où il vit** : hébergement **Alwaysdata** (compte du propriétaire), transfert par **FileZilla** ou navigateur, démarrage selon le §7 du `DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`. **Le propriétaire fait les transferts et les redémarrages lui-même** : tout changement des fichiers livrés doit lui être signalé dans une section « **Fichiers à envoyer** » (§10.4).

---

## 3. Carte du dépôt (mesurée le 2026-10-15)

```
bot.py                    108 l.   point d'entrée : intents, chargement des cogs, persistance des vues
config.py                 101 l.   chemins (.env, catalogue, images), chargement de la configuration
cogs/
  mouse_finder.py                  cog principal (démarrage du parcours, vues persistantes)
  finder_flow.py          1 352 l. le parcours Discord : embeds, boutons, modales, affichage du résultat
  __init__.py
utils/
  matcher.py                       le MOTEUR : barème 40 points, exclusions, statuts
  selection.py                     tri, fenêtres de budget, départage, phrase d'explication
  slots.py                  170 l. les trois places montrées et leurs titres (calcul pur, sorti du cog à la 80e passe)
  catalog.py                       chargement + validation stricte du catalogue (schéma v2)
  models.py                        dataclasses (Mouse, MouseScore, Grip, Thenar, BudgetMode…)
  session.py                       état du parcours par utilisateur (en mémoire, TTL)
  validation.py                    bornes des saisies (100–260 mm, 50–130 mm, 10–5 000 €)
  assets.py                        résolution des images (nom de fichier → URL publique)
data/
  mouse_db.json            36 souris · 268 sources   LE CATALOGUE
  commercial_links.json    36 liens affiliés (+ 3 clés `_` de commentaire)
assets/
  images.json              17 clés → fichiers `assets/illustrations/T01…T15`
  illustrations/           les 15 images du bot (bannière, étapes, illustrations du résultat)
tools/                     17 outils · 4 780 l.   mesures, bancs d'essai, contrôles, aperçus (80e passe)
tests/                    37 fichiers · 10 637 l. · 850 tests · couverture 100 % (80e passe)
docs/                     24 fichiers .md · 13 029 l.  (dont ROBUSTESSE 5 076 l. et DEPLOYMENT 2 843 l.)
Reverse/                  10 fichiers    LA PREUVE PRIMAIRE : sorties datées de l'outil d'origine (Oblivity)
ImageAct/ ImageEx/ ImageUse/   images de travail (fiches, exemples, les 15 illustrations livrées)
.env.example              le gabarit de configuration (le vrai `.env` n'est JAMAIS dans le dépôt)
```

**Deux chiffres à retenir pour lire le reste** : le code livré fait **~3 400 lignes** (`bot.py` + `config.py` + `cogs/` + `utils/`), et **il est entouré de 4 057 lignes d'outils, 10 316 lignes de tests et 13 029 lignes de documentation**. C'est un projet où la **vérification** pèse six fois le **produit**. C'est à la fois sa force (on peut prouver ce qu'on avance) et sa maladie (§7.1).

---

## 4. La méthode qui a produit l'état actuel

Ce dépôt a été construit par **passes** (77 à ce jour). Une passe = un défaut **prouvé** → une correction → un **test qui l'empêche de revenir** → une **mesure** → un **journal** → un **commit poussé**. Les règles de méthode qui ont tenu, et que tu devrais garder même si tu changes tout le reste :

1. **Mesurer avant de parler.** Toute affirmation est adossée à une commande, un test, un outil, ou une source consultable. « Il me semble que » n'existe pas ici.
2. **Rien d'inventé, jamais** — ni un prix, ni une valeur, ni une explication de bug. Un doute se **consigne** dans un registre d'ouverts ; il ne se devine pas.
3. **Un défaut corrigé sans test revient.** Chaque correction ferme par un test **qui échoue quand la correction est annulée** (mutation : on casse, on vérifie le rouge, on répare).
4. **Un test ne redemande jamais ses attentes au code qu'il vérifie.** Les valeurs attendues sont écrites **en clair** dans le test. Un test qui recalcule ses propres attentes valide n'importe quoi (c'est arrivé, C90).
5. **Un chiffre publié doit être rejouable** : soit par un outil, soit par une source datée. Les compteurs « intermédiaires » non reproductibles ont été la source de plusieurs défauts.
6. **Purger le bytecode avant toute mesure** : `find . -name __pycache__ -type d -exec rm -rf {} +` (hors `.venv`) — sinon Python peut charger un **ancien** moteur compilé et te faire mesurer le mauvais monde (c'est arrivé, C90 : 10 678 « problèmes » fantômes).
7. **Journaliser ce qui a été trouvé et pourquoi**, avec sa date et sa preuve. Le journal est dans `docs/audit/ROBUSTESSE_2026-10-12.md` (§26.x) et `docs/audit/AUDIT.md` (colonne C-n°).
8. **Commit + push à chaque pas**. Un travail non poussé n'existe pas.

---

## 5. État mesuré au 2026-10-14 (et comment refaire ces mesures)

Tous ces chiffres ont été mesurés sur `db3d20d`, avec `.venv` installé depuis `requirements.txt` + `requirements-dev.txt` + `coverage`.

| Mesure | Valeur | Commande |
| --- | --- | --- |
| Suite de tests | **825 passed** | `.venv/bin/python -m pytest -q` |
| Lint (pyflakes) | **0** | `.venv/bin/python -m pyflakes bot.py config.py cogs utils tests tools` |
| Confidentialité | **0 violation** | `.venv/bin/python tools/privacy_scan.py` |
| Déploiement | **7 OK + 1 bloquante** (`.env` absent : normal hors serveur) | `.venv/bin/python tools/check_deployment.py` |
| Fraîcheur du bytecode | **30 examinés, 0 périmé** | `.venv/bin/python tools/check_bytecode.py` |
| Banc du parcours (grille complète) | **21 736 profils · 0 problème** | `.venv/bin/python tools/qa_flow_matrix.py` |
| Banc, grille réduite | **576 profils** | `… --rapide` |
| Grille du rapport statistique | **18 522 profils** | `.venv/bin/python tools/recommendation_stats.py` |
| Couverture (livré uniquement) | **1 654 instructions · 508 branches · 100 %** | `.venv/bin/python -m coverage run --branch --source=cogs,utils,bot,config -m pytest -q && … report` |
| Aperçus PNG (3 fichiers) | empreinte des sources inscrite dans le PNG | `.venv/bin/python tools/render_preview.py` |

**Point de référence du parcours** (profil Palm 180 × 90 mm, thénar moyenne, mode Qualité-Prix), figé dans `tests/test_parcours_complet.py` :

| Place | Souris | Score | Prix |
| --- | --- | --- | --- |
| 1ʳᵉ | ATK Phantom Ultimate | 35/40 → **88 %** | 91,95 € |
| 2ᵉ | ATK Z1 V2 Ultimate | 30/40 → **75 %** | 59,95 € |
| 3ᵉ | ATK A9 Mini | 30/40 → **75 %** | 59,95 € |

**Catalogue** : 36 souris, **269 sources**, 36 liens affiliés (dont 12 qui **figent une variante** `variant=…`), 25 souris avec `shell_id` (14 coques distinctes, 9 coques partagées par plusieurs entrées), 1 seule souris non vérifiée sur ses prix (`scyrox_v6`, `owner_spec_unverified`).

**Répartition** : 20 ATK · 10 Pulsar · 4 VXE · 2 Scyrox. **C'est très déséquilibré** (voir §7.4).

---

## 6. Où se cachent les défauts — la typologie des 99 constats

C'est la leçon la plus transférable de ces 77 passes. Les défauts trouvés ne sont **presque jamais** dans les algorithmes : ils sont dans **l'écart entre ce qui est écrit et ce qui est vrai**. Neuf familles, par ordre de fréquence :

| Famille | Exemple réel | Comment le détecter |
| --- | --- | --- |
| **1. Un document affirme un rôle que le code ne tient pas** | `budget_tier` décrit comme « départage visuel » et « affiché » — aucun module ne le lit (C96) ; `fit_rationale` décrit comme « affiché dans le résultat » — jamais lu (C97) | Pour chaque phrase de doc qui décrit un comportement, chercher le code qui l'implémente. Pas de code ⇒ doc faux. |
| **2. Un chiffre publié ne se rejoue plus** | « onze liens figent une variante » alors qu'ils sont douze, la F1 V2 rangée du mauvais côté depuis 24 passes (C94) ; « 813 tests » alors qu'il y en avait 816 | Rejouer chaque compteur cité : `grep` du nombre → commande → comparaison. |
| **3. Le code mesure autre chose que ce qui est livré** | Bytecode périmé : le banc a publié 10 678 problèmes pour un moteur qui n'existait pas (C90) | `tools/check_bytecode.py`, et purger avant toute mesure. |
| **4. Un test qui ne vérifie rien, ou qui vérifie contre lui-même** | Un test recalculait ses attentes avec la fonction testée (C90) ; un fichier d'état écrit deux fois de suite (C81) | Analyse syntaxique des tests : présence d'`assert` **et** d'une valeur attendue littérale. |
| **5. Une borne jamais mesurée** | Le domaine des saisies (100/260 mm, 50/130 mm, 10/5 000 €) n'était testé nulle part (C92) | Chercher les intervalles d'entrée et mesurer leurs **quatre coins**. |
| **6. Une donnée mal écrite, invisible à l'œil** | Neuf notes du catalogue avec « … jusqu'au relevé.Capteur maison Pulsar XS-1 … » (C98) | Balayer **tous** les textes : phrases collées, liens morts, dates incohérentes, valeurs hors domaine. |
| **7. Une traçabilité qui se perd** | Le journal des passes avait perdu le numéro 51, et une section était publiée sous un numéro déjà pris (C95) | Vérifier la **continuité** des numéros de section et de passe. |
| **8. Une question ouverte qu'on ne tranche pas** | « la Xlite CrazyLight Mini est-elle symétrique ou ergonomique ? » — restée ouverte 3 jours, tranchée en 10 minutes sur la page officielle du fabricant (C99) | Une question ouverte est un blocage : va chercher la **source primaire** au lieu de la laisser dormir. |
| **9. Un commentaire qui protège du code mort** | `NAVY` / `SPARK` jamais lues, justifiées par « utilisées par le rendu d'aperçu » — faux (C93) | Pour chaque constante non utilisée, vérifier la raison donnée ; si la raison est fausse, **c'est le défaut**. |

**Ce qui a été fermé par la preuve, et qu'il ne faut pas rouvrir sans élément nouveau** : le double appui sur un bouton de budget (déjà couvert par un test de confidentialité + `InteractionResponded`) ; les « 0 vs 445 » de bytecode ; l'« arrière étroit » (écart réel, refermé). **Ce qui est hors sujet** : les ruptures de stock (« on gérera plus tard », propriétaire).

---

## 7. La dette, dite honnêtement

Le propriétaire a raison : ce dépôt est devenu **un peu n'importe quoi**. Voici l'inventaire, sans complaisance.

### 7.1 La documentation a mangé le projet
**13 029 lignes de documentation** pour 3 400 lignes de code livré. Le journal de chasse (`ROBUSTESSE_2026-10-12.md`) fait **5 076 lignes** et 99 sections ; le guide de déploiement en fait **2 843** avec 57 sections de mises à jour successives. **Aucun être humain, aucune IA, ne peut lire ça** : c'est une archive, pas un manuel. Il faut **séparer radicalement** :
- un **document de vérité courante**, court (une dizaine de pages), qui décrit ce que le système **est** aujourd'hui — c'est le seul qu'on lit avant de coder ;
- des **décisions datées** (ADR), une par fichier, avec le contexte et la raison — consultables à la demande ;
- une **archive** du journal de chasse, gardée (la traçabilité est une valeur du projet) mais **sortie du chemin de lecture**.

### 7.2 Les tests pèsent six fois le code
**10 316 lignes de tests**, dont beaucoup assertent des **tournures françaises exactes**. C'est ce qui rend le bot fiable… et c'est aussi ce qui rend toute refonte de l'affichage très coûteuse : si tu réécris les textes, des centaines de tests tombent. **Décision à prendre tôt** : soit tu gardes la stratégie « tout est figé », soit tu introduis une couche de textes (un fichier de libellés) et tu testes **le contenu logique** plutôt que la phrase. Je te recommande la seconde — mais c'est **ton** appel, et il se prend **une fois**, pas à moitié.

### 7.3 Les outils se recouvrent
17 outils, 4 780 lignes (80e passe). Plusieurs se ressemblent beaucoup (`image_corpus_check` / `image_identity_check` ; `measure_button_height` / `measure_grip_width` partagent la même mécanique d'étalonnage). La grille de profils du banc est **recopiée** dans plusieurs outils (elle a déjà dû être dédoublonnée une fois, C84). À réunifier en une **bibliothèque de mesure** + des points d'entrée minces.

### 7.4 Le catalogue est étroit et déséquilibré
**36 souris** : 20 ATK, 10 Pulsar, 4 VXE, 2 Scyrox. **Aucune** Logitech, Razer, Zowie, VAXEE, Lamzu, Pwnage, Endgame Gear, Glorious, Ninjutso, etc. Le catalogue ne couvre donc pas le marché réel, et le moteur recommande presque toujours le même tiers de souris. Le propriétaire veut **l'étendre avec toi, plus tard** (§13, chantier 6) : ton travail d'ici là est de rendre l'ajout **simple, sûr et rapide**.

### 7.5 Le moteur est un barème négocié, pas une loi physique
Les constantes du moteur (`LENGTH_SLOPE = 0.2633`, largeur de prise `= coque − 3 mm`, seuils de 5/10 points, tolérances 5/2/2/2) viennent d'un **reverse engineering** de l'outil Oblivity (`Reverse/`), pas d'une théorie. Le barème 40 points est un **outil de classement**, pas une vérité. Tu as le droit de le refaire — à condition de le **mesurer** (le banc donne l'effet sur 21 736 profils) et d'**écrire la décision**.

### 7.6 Des documents-instantanés qui périmeront
`RAPPORT_FINAL.md`, `STATISTIQUES_RECOMMANDATIONS_2026-10-12.md`, `matrice_profils.md` sont des **photos datées**. Elles sont déjà partiellement fausses. Soit on les régénère à la demande (un outil le fait pour la matrice), soit on les archive avec une date en tête. Ne les traite jamais comme la vérité courante.

### 7.7 Ce qui est propre et qu'il ne faut pas casser
La **chaîne de preuves** (bytecode, aperçus horodatés par empreinte, banc d'essai, mutations), la **discipline anti-invention**, le **catalogue sourcé** (268 sources pour 36 souris depuis la 79e passe, chaque valeur traçable), et l'**outillage de mesure sur images** (étalonnage, contrôle de perspective, identité de silhouette). Si tu jettes le reste, garde ces quatre-là.

---

## 8. Ce que tu dois vérifier avant de bâtir dessus

**Ne me crois pas.** Voici la liste de contrôle, dans l'ordre. Chaque ligne est un soupçon à lever, pas une affirmation à recopier.

1. **L'environnement est-il celui du dépôt ?** `git log --oneline -1` doit montrer `db3d20d` (ou ce que tu auras poussé), `.venv` doit exister et `python -m pytest -q` doit donner **825 passed**. Si le bac a été reconstruit, refais `.venv` et `git reset --hard origin/arena/87fafd0d-mousediscord`.
2. **Le moteur est-il celui de la preuve primaire ?** `Reverse/` contient 10 sorties datées de l'outil d'origine. `tests/test_reverse_engineering.py` (35 tests) prétend que le moteur reproduit ces sorties. **Relis les fichiers de `Reverse/` toi-même** et vérifie quelques cas à la main : c'est la seule ancre externe du calcul.
3. **Les chiffres de la documentation sont-ils vrais aujourd'hui ?** Prends les vingt plus gros « N sur M » et pourcentages des documents **vivants** (README, MASTER_PROMPT, DEPLOYMENT, AUDIT) et rejoue-les. J'en ai corrigé plusieurs ; l'**hypothèse par défaut est qu'il en reste**.
4. **Le catalogue est-il soutenu par ses sources ?** `tests/test_data.py` vérifie que chaque valeur renseignée cite une source qui déclare le champ. **Va plus loin** : ouvre 5 sources au hasard (dans les 269) et vérifie que la valeur citée y est vraiment, à sa date.
5. **Les 36 liens ouvrent-ils le bon produit au bon prix ?** `tools/check_links.py` (réseau requis). Les prix ATK **oscillent d'un euro** au gré des promotions : c'est une propriété de la source, pas un défaut du catalogue — mais la date du relevé doit être écrite.
6. **L'affichage respecte-t-il les limites Discord ?** Le banc en mesure 17 (9 de composant, 8 de vue). Aucun dépassement au 2026-10-14 — mais toute refonte de texte doit repasser ce banc.
7. **Les aperçus montrent-ils le code livré ?** `tools/render_preview.py` inscrit une **empreinte des sources** dans le PNG ; `tests/test_apercus.py` la recalcule. Si tu touches au parcours, régénère-les **après** la dernière retouche.
8. **La confidentialité tient-elle ?** `tools/privacy_scan.py` (statique) + `docs/audit/PROTOCOLE_DISCORD_CONFIDENTIALITE.md` (protocole réel, **jamais exécuté par moi** faute d'accès à Discord). C'est un angle mort : tu ne peux rien y vérifier sans le propriétaire.
9. **Le déploiement est-il exact ?** Je n'ai **jamais** exécuté la procédure Alwaysdata : elle vient des dires du propriétaire. C'est de la documentation non testée — traite-la comme telle.
10. **Les préférences du propriétaire sont-elles à jour ?** Trois sources, dans cet ordre : `docs/MASTER_PROMPT_AZEMOUSE.md` (le cahier des charges), `docs/REPORTE_DESIGN.md` (le design négocié), et **ce document**. En cas de désaccord, **demande** : le propriétaire répond vite et précisément.

---

## 9. Tes droits, explicitement

### 9.1 Sur le code
Tu peux modifier, déplacer, découper, fusionner ou **supprimer** n'importe quel module — y compris `cogs/finder_flow.py` (1 352 lignes depuis que le choix des trois places en est sorti, 80e passe : textes et rendu restent des candidats à l'éclatement). Tu peux changer les dépendances (`discord.py ≥ 2.4`, Python ≥ 3.10), la structure des cogs, le découpage `utils/`, et **le moteur de calcul lui-même**.

### 9.2 Sur les données
Tu peux changer le schéma du catalogue, à condition de fournir la **migration** et de mettre à jour les outils, les tests et les documents qui en dépendent. Le schéma actuel fait **26 champs obligatoires ou optionnels** (Annexe A) ; il est verbeux et mérite d'être repensé — mais il a une qualité : **chaque valeur renseignée est adossée à une source qui déclare le champ**. Garde cette propriété.

### 9.3 Sur les images et les sources
Le propriétaire t'autorise explicitement à **aller chercher les images sur EloShapes**. Nuance à traiter proprement : le 2026-10-11, l'affichage d'images **EloShapes** *dans le bot* avait été **rejeté** par le propriétaire ; la mesure, elle, **se fait sur EloShapes** depuis le début. La consigne du 2026-10-15 lève la restriction sur la **recherche** des images. Si tu veux publier des images EloShapes dans le bot, **écris la décision** et préviens le propriétaire — mais préfère, quand elles existent, les **vues officielles du fabricant** (c'est ce sur quoi la méthode de mesure est étalonnée).

### 9.4 Sur les personnes et les sous-agents
Tu peux travailler en **sous-agents parallèles** (exploration, mesure, refonte, données, tests) et faire relire leur travail par un autre agent. Tu peux créer des branches, ouvrir des PR, et découper la refonte en autant de chantiers que tu veux. La seule contrainte : **tout ce qui est poussé doit laisser la suite verte** (ou une PR clairement identifiée comme chantier en cours, jamais une branche cassée poussée comme finie).

### 9.5 Sur les décisions produit
Tu ne tranches pas le produit : tu **proposes** avec des mesures, le propriétaire **décide**. Exemple de la bonne manière : « j'ai mesuré que détendre le seuil d'exclusion de largeur de 5 à 6 mm fait passer le taux de profils sans résultat de X % à Y %, et fait bouger Z places sur 21 736 — veux-tu que je le fasse ? »

---

## 10. Tes obligations

### 10.1 La définition de « fini » (DoD) — pour chaque changement poussé
- [ ] **Suite verte** : `.venv/bin/python -m pytest -q` → 0 échec (et le compte annoncé dans `DEPLOYMENT` §12.23 mis à jour).
- [ ] **Pyflakes 0** sur `bot.py config.py cogs utils tests tools`.
- [ ] **Confidentialité** : `tools/privacy_scan.py` → 0 violation.
- [ ] **Déploiement** : `tools/check_deployment.py` → 7 OK + la seule bloquante attendue (`.env` absent).
- [ ] **Bytecode** : `tools/check_bytecode.py` → 0 périmé (et `__pycache__` purgés après toute mutation).
- [ ] **Si le parcours ou le moteur a bougé** : banc d'essai (`qa_flow_matrix.py`) relancé et **compteurs recalculés**, aperçus **régénérés**.
- [ ] **Si une donnée a bougé** : les quatre lieux d'un prix mis à jour (catalogue, §8.1 des liens, `tests/test_data.py`, `CATALOGUE_ATK.md`), et les sources ajoutées.
- [ ] **Journal** : ce qui a été trouvé, pourquoi c'était faux, comment c'est prouvé, daté.
- [ ] **Commit + push** sur la branche de travail, et **fichiers à envoyer** listés s'il y en a.

### 10.2 Jamais
- **Jamais** inventer une valeur, un prix, une mesure, une raison. Si tu ne sais pas : `null` + une note qui dit pourquoi, ou une question ouverte.
- **Jamais** marquer `verified` sans source concordante ; jamais convertir une devise.
- **Jamais** committer le `.env`, un jeton, une URL privée, un identifiant de serveur.
- **Jamais** stocker les saisies d'un membre (le parcours vit **en mémoire**, avec expiration).
- **Jamais** publier un chiffre sans la commande ou la source qui le reproduit.

### 10.3 La règle du moindre mensonge documentaire
Un document qui décrit un comportement doit être **corrigé ou supprimé** dès qu'il diverge du code. C'est la source n° 1 des défauts de ce dépôt (§6, famille 1). Corollaire : **n'ajoute pas de documentation** que tu ne peux pas tenir.

### 10.4 Le propriétaire, et la livraison
Le propriétaire transfère lui-même les fichiers sur Alwaysdata (FileZilla ou navigateur) et redémarre. Termine donc chaque intervention par un bloc **« Fichiers à envoyer »** : la liste exacte, ou « **aucun** ». Et précise si un **redémarrage** est nécessaire. Il ne lit pas le code : il lit ce bloc.

Il travaille depuis un PC sans PowerShell ; l'hébergement est un compte Alwaysdata ; les journaux vivent sous `~/admin/logs/` ; on ne lance **jamais** `bot.py` à la main sur le serveur.

### 10.5 La langue
Le propriétaire est francophone, exige un **français irréprochable** (typographie comprise : espaces avant `: ; ! ?`, guillemets français, virgules décimales). Le code et les identifiants peuvent être en anglais, mais **tout ce que l'utilisateur lit** est en français soigné.

---

## 11. Les données : mode d'emploi et règles de preuve

### 11.1 Les quatre niveaux de confiance d'une donnée
| Statut | Sens | Ce qu'il exige |
| --- | --- | --- |
| `verified` | établi | **deux** sources concordantes à ≤ 0,5 mm, ou **une seule** si c'est le fabricant lui-même (sa boutique officielle) |
| `single_source` | une source unique non fabricant | elle est **cette** source-là, elle est datée |
| `owner_spec_unverified` | déclaration du propriétaire (cahier des charges), non revérifiable | affiché « prix non vérifié » à l'écran ; ne compte pas dans les modes à prix |
| `unknown` / vide | on ne sait pas | il n'y a **rien** : ni valeur par défaut, ni estimation |

### 11.2 Où trouver quoi
| Source | Ce qu'on y prend | Méthode qui marche |
| --- | --- | --- |
| **EloShapes** (`eloshapes.com/mouse/<slug>`) | dimensions, poids, **forme** (bosse), comparaisons | page `mouse/compare?p=<slug>` pour la fiche complète. Méthode de mesure **étalonnée sur ce site**. Certaines souris n'y sont pas (`vxe-x3`, `atk-x3`). |
| **Boutiques du fabricant** (ATK, Pulsar, Scyrox) | **prix en euros**, variantes, stock, dimension publiée, poids | ATK : `…/products/<handle>.json?country=FR` (⚠️ **le `?country=FR` est obligatoire**, sinon les prix sont en dollars) ; Pulsar : `…/products/<handle>.json` ; variantes unitaires ATK : `variants/<id>.json?country=FR`. **`search/suggest.json` n'est pas fiable** (il renvoie des éditions voisines). |
| **mouseshape.com** | recommandations de prise (source **tierce autorisée**) | « Not ideal » n'est **jamais** converti en « Faible » : exclusion réservée au fabricant |
| **Fiches officielles** (images) | **mesures** de hauteur de boutons, largeur de prise | outil maison : rapport mesuré sur la vue, étalonnage par classes de référence, **vue en perspective refusée** |
| **Oblivity** (`Reverse/`) | le **comportement de référence** du calcul | 10 sorties datées, non modifiables : c'est l'ancre du moteur |

### 11.3 Ajouter une souris au catalogue (le geste que tu dois rendre trivial)
1. **Vérifier qu'elle est vendue** et trouver le lien officiel, affilié (`?ref=aze` ATK, `?ref=AZE` Pulsar, `?bg_ref=…` Scyrox).
2. **Relever les cotes** (longueur, largeur maximale, hauteur) sur deux sources ou sur le fabricant ; si elles divergent de plus de 0,5 mm → `conflicts` + statut d'incertitude.
3. **Renseigner `shell_id`** si la coque est partagée : deux entrées de la même coque n'occupent pas deux places du même résultat — **sauf** repli volontaire quand aucun autre candidat ne reste (« jamais moins de résultats qu'avant ») : le banc le compte (1 748 profils sur 21 736 au 2026-10-15) sans le compter comme une faute.
4. **Prises** : seulement ce que le fabricant (ou la source tierce autorisée) **publie**. « Inconnu » est une valeur acceptable ; une valeur inventée jamais. Une prise « Faible » **exclut** la souris de ce profil.
5. **Bosse** (position) et **hauteur de boutons** (classe) : mesurées sur images, ou déduites d'une coque partagée **avec sa source**.
6. **Prix en euros**, relevé daté, variante **figée** dans le lien si le produit en vend plusieurs.
7. **Sources** : chaque valeur renseignée déclare la source qui l'atteste (`sources[].fields`).
8. **Passer le banc** : la nouvelle souris ne doit pas casser les invariants (coque unique par résultat, ordre des pourcentages, limites Discord).

### 11.4 Le chiffre à ne jamais oublier
**`21 736`** profils au banc et **`18 522`** pour le rapport statistique. Toucher au catalogue ou au moteur **déplace** ces mesures : tout chiffre publié avant le changement doit être **recalculé**, pas recopié.

---

## 12. Les pièges déjà payés (ne les repaie pas)

1. **Bytecode périmé** : purge `__pycache__` avant de mesurer ; le banc refuse désormais de tourner s'il détecte du bytecode périmé (code 2).
2. **Un test qui recalcule ses attentes** : écris les attentes **en clair** (C90).
3. **`compile()` et `from __future__`** : passer `dont_inherit=True` ; `repr()` d'un `frozenset` dépend du hachage.
4. **Modifier un texte affiché** ⇒ régénérer les **aperçus** (`tests/test_apercus.py` compare une empreinte).
5. **Renommer un test** ⇒ `tests/test_doc_references.py` bloque toute citation morte : déclarer le retrait dans `docs/audit/NOMS_DE_TESTS_RETIRES.md`.
6. **Créer un fichier d'outil ou de test** ⇒ le README doit le citer (contrôle automatique).
7. **`thenar_step_embed(Fingertip)` lève `ValueError`** : le Fingertip saute le thénar, boucle sur Palm/Claw.
8. **`compatibility_percent(score)` prend un seul argument** ; `resume_des_marges` compare des **fractions**, jamais un compte à une longueur.
9. **Le bloc de contrôle du DEPLOYMENT** (`§12.23`) est le seul tenu à jour : le compte de tests y est écrit **une** fois ; la chaîne `Problèmes détectés : 0` apparaît **9 fois** dans le fichier → jamais un remplacement global.
10. **`coverage --source=` attend des noms de modules**, pas des chemins.
11. **Prix ATK oscillants** : ±1 € d'un jour à l'autre (bascule de promotion). Ce n'est pas un bug — la **date** du relevé est la vérité.
12. **Pulsar `search/suggest.json`** renvoie des éditions (PRX, T1…) : utiliser `products/<handle>.json`.
13. **EloShapes** : certains slugs manquent ; la réponse est parfois tronquée (`chunkIndex: 1`).
14. **Le `.env`** est indispensable au bot, interdit au dépôt ; son absence est la **seule** erreur bloquante attendue du contrôle de déploiement.
15. **Le bac de développement peut être reconstruit** : avant toute mesure, vérifier `git log -1`, `.venv`, `git status`.

---

## 13. Plan d'attaque suggéré

Sept chantiers. **Tu peux les réordonner, les fusionner, en inventer d'autres.** Ils sont là pour t'éviter de repartir de zéro dans la réflexion.

### Chantier 0 — Reprendre la mesure (½ journée)
Reconstruire l'environnement, lancer **tous** les contrôles du §5, et produire **ton propre état des lieux**, avec **tes** chiffres. Interdiction de recopier les miens sans les avoir rejoués.

### Chantier 1 — L'audit des affirmations (le plus rentable)
Prendre **tous** les documents vivants et le **texte affiché par le bot**, et confronter chaque affirmation de comportement ou de chiffre au code et à une mesure. C'est la famille de défauts n° 1 et 2 du §6. Objectif : un tableau « affirmation → vérifiée / fausse / invérifiable », puis correction. **C'est ce que le propriétaire demande en premier** (« qu'elle vérifie tout ce que t'as fait »).

### Chantier 2 — Remettre la documentation en ordre
Séparer **vérité courante** (court, à jour), **décisions datées** (ADR), **archive** (le journal de chasse, gardé mais rangé). Un nouveau venu doit pouvoir comprendre le système en **une heure**. Aujourd'hui, c'est impossible.

### Chantier 3 — L'architecture du code
Éclater `cogs/finder_flow.py`. Séparer **le moteur** (calcul pur, sans Discord) de **la présentation** et **de la conversation**. Rendre le moteur testable sans simuler Discord. Rendre les textes **paramétrables** (fichier de libellés) — c'est la condition pour que la refonte soit possible sans casser 500 tests.

### Chantier 4 — Le moteur (si et seulement si tu le peux par la mesure)
Re-dériver le barème à partir de `Reverse/` et des priorités du propriétaire ; mesurer chaque variante sur le banc (21 736 profils) ; regarder ce que ça change au trio de référence et aux statistiques ; écrire la décision. Tu as le droit de le refaire — **pas** de le changer au feeling.

### Chantier 5 — L'expérience utilisateur
Une fois le reste stable : re-vérifier la concision, les textes, la lisibilité en thème sombre **et** clair, le mobile, les limites Discord. Le propriétaire a des exigences précises (Annexe D). Les aperçus PNG sont ton banc de contrôle visuel.

### Chantier 6 — Préparer l'extension du catalogue (avec le propriétaire)
Rendre l'ajout d'une souris **simple** : un formulaire/format d'entrée, une validation qui refuse l'invention, un outil de recherche de liens, un contrôle de prix automatisé, un test qui vérifie les invariants. Préparer la **liste des candidats** (familles absentes : Logitech, Razer, Zowie, VAXEE, Lamzu, Endgame Gear…). Le premier candidat est **déjà instruit** : la **Pulsar Xlite CrazyLight Mini** (voir §13.1). L'ajout massif se fera **avec** le propriétaire — c'est lui qui a les critères commerciaux.

### Chantier 7 — Le déploiement et la vie privée
La procédure Alwaysdata n'a **jamais été exécutée** par un agent : la vérifier avec le propriétaire, la simplifier si possible, et exécuter enfin le protocole de confidentialité en conditions réelles (nécessite son accord et son serveur).

### 13.1 Le dossier prêt : Pulsar Xlite CrazyLight Mini (149,99 €)
Souris **vendue**, **absente** du catalogue parce que la boutique la classe `Shape/Symmetrical` alors que la famille est ergonomique main droite. Tranché le 2026-10-14 sur la page officielle : elle écrit « **ERGONOMIC RIGHT HAND** » et « Ergonomic right-handed shape », et les deux autres pages de la même ligne (CrazyLight Medium, Xlite v4 Mini) sont taggées `Ergonomic`. **Données déjà relevées et sourcées** : 115,6 × 63,4 × **40,7 mm** (« Same Size as the Xlite Size 1 » = la coque de la `pulsar_xlite_v4_mini`), ±41 g (patins dot) / ±43 g (patins classiques), capteur XS-1 (32 000 dpi, 750 IPS), switchs optiques 100 M, molette TTC Golden, LOD 2/1/0,7 mm, polling **1 000 Hz** (spécification publiée ; « up to 8K » avec dongle séparé), MCU **non publié** → champ vide. Il ne reste qu'à l'entrer et à recalculer **tous** les compteurs.

---

## 14. Ce que le propriétaire attend de toi, concrètement

« **1000 fois mieux** », traduit en critères vérifiables :

1. **Moins d'occasions de se tromper** : une seule source de vérité par information (aujourd'hui : un prix vit dans quatre fichiers, la grille de profils dans plusieurs outils, une règle de thénar a dû être dédoublée).
2. **Plus simple à étendre** : ajouter une souris doit être une procédure **guidée** de dix minutes, pas une expédition.
3. **Plus rapide à vérifier** : une commande doit dire si le système est sain, et **tout chiffre publié** doit être rejouable.
4. **Plus lisible** : un humain (et une IA) doit comprendre le système **sans lire 13 000 lignes de documentation**.
5. **Zéro invention** : la valeur du projet, c'est que ses chiffres sont vrais. C'est le seul capital.
6. **Un rapport clair au propriétaire** : quoi, pourquoi, preuve, fichiers à envoyer. En français, court, sans jargon.

Et une consigne de méthode : **quand tu as le choix entre « faire ce que le document dit » et « faire ce qui est juste », fais ce qui est juste, puis corrige le document.** C'est exactement l'inverse qui a produit la dette actuelle.

---

## Annexe A — Le schéma du catalogue (26 champs)

| Groupe | Champs | Notes |
| --- | --- | --- |
| **Identité** | `id`, `brand`, `model`, `category`, `family` | `id` est la clé des liens d'achat |
| **Géométrie** | `length_mm`, `width_max_mm`, `height_mm`, `grip_width_mm`, `dimension_status`, `conflicts`, `shell_id` | `grip_width_mm` est **nulle part** renseigné (aucune mesure de prise) ; `null` = inconnu, jamais une estimation |
| **Forme** | `shape` (`Symmetrical`/`Ergonomic`), `hump_position` (`Front`/`Mid`/`Rear`/`Mid-Front`/`Mid-Rear`/`Any`/`Inconnu`), `button_height` (`Low`/`Mid`/`High`/`Inconnu`) | |
| **Prise** | `palm_grip_fit`, `claw_grip_fit`, `fingertip_grip_fit` (`Élevé`/`Moyen`/`Faible`/`Inconnu`), `fit_status` (`owner_spec`/`manufacturer_guide`/`third_party_guide`), `fit_rationale` | « Inconnu » n'attribue aucun point ; « Faible » **exclut** |
| **Commercial** | `price_eur`, `price_status`, `price_note`, `budget_tier`, `weight_g` | `budget_tier` n'est **lu par aucun module** (étiquette de classement du catalogue) |
| **Performance** | `sensor`, `polling_hz`, `switches`, `mcu` | servent au départage du mode « Peu importe le prix » : capteur > MCU > switchs puis polling ≥ 8 000 Hz |
| **Traçabilité** | `sources` (`[{label, url, fields, date_checked}]`), `notes` | obligatoires dès qu'une valeur est renseignée |

---

## Annexe B — Le barème actuel du moteur (40 points)

| Critère | Points | Règle |
| --- | --- | --- |
| **Longueur** | 10 | dans la plage cible **+10** ; écart < 3 mm **+5** ; écart > 8 mm ⇒ **exclusion** |
| **Largeur de prise** | 10 | dans la plage **+10** ; écart < 2 mm **+5** ; écart > 5 mm ⇒ **exclusion** |
| **Compatibilité de prise** | 10 | `Élevé` +10, `Moyen` +5, `Faible` ⇒ **exclusion**, `Inconnu` ⇒ à vérifier (aucun point) |
| **Bosse** | 5 | position idéale selon la prise |
| **Hauteur des boutons** | 5 (palm/claw) · 10 (fingertip) | classe idéale selon la prise |
| **Maximum théorique** | **40** | le pourcentage affiché est **score / 40** — vérifié le 2026-10-15 : au Fingertip aussi, 10 + 10 + 10 + 0 (bosse ignorée) + **10** (boutons) = 40 |

Plages cibles (mesurées par reverse engineering, `Reverse/`) :
- Longueur min = `71,4 + 0,2633 × L` ; longueur max = min + 5 mm (Palm/Claw) ; Fingertip : max = base + 0,2633 × L.
- Largeur de prise min = `48,4 + 0,08 × W` (Palm/Claw) ou `47,3 + 0,08 × W` (Fingertip) ; largeur estimée de la souris = largeur de coque **− 3 mm**.

Tolérances de fenêtre budgétaire (en points de score) : Économique 5 · Qualité-Prix 2 · Haut de Gamme 2 · Peu importe 2 · budget libre 2.

---

## Annexe C — Commandes utiles

```bash
# Environnement
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt coverage

# Contrôles de santé
.venv/bin/python -m pytest -q
.venv/bin/python -m pyflakes bot.py config.py cogs utils tests tools
.venv/bin/python tools/privacy_scan.py
.venv/bin/python tools/check_deployment.py
.venv/bin/python tools/check_bytecode.py            # --purge pour nettoyer
.venv/bin/python tools/qa_flow_matrix.py           # --rapide pour 576 profils

# Mesures
.venv/bin/python tools/recommendation_stats.py      # statistiques (18 522 profils)
.venv/bin/python tools/compare_profiles.py          # docs/audit/matrice_profils.md
.venv/bin/python tools/db_effect.py  --avant <ancien mouse_db.json>
.venv/bin/python tools/flow_effect.py               # effet d'un changement de CODE
.venv/bin/python tools/check_links.py               # liens d'achat (réseau)

# Images et aperçus
.venv/bin/python tools/render_preview.py
.venv/bin/python tools/image_corpus_check.py <dossier>
.venv/bin/python tools/image_identity_check.py …
.venv/bin/python tools/measure_button_height.py …
.venv/bin/python tools/measure_grip_width.py …

# Couverture
.venv/bin/python -m coverage run --branch --source=cogs,utils,bot,config -m pytest -q
.venv/bin/python -m coverage report

# Nettoyage avant mesure (jamais dans .venv)
find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +
```

---

## Annexe D — Les exigences produit du propriétaire (à respecter)

- **Flux** : Grip → (variante Claw) → Thénar → Mesures → Budget. Le **Fingertip saute le thénar**.
- **Thénar** : informatif, **aucun point**, ne modifie pas le score (règle du 2026-10-13).
- **Résultat** : la ligne descriptive + **Match Idéal** + **Alternative**, avec le **% du maximum théorique** (jamais présenté comme une probabilité ni une confiance). **Pas de score ni de confiance en tête**.
- **« Le pourquoi »** : en petit encadré, **en bas**.
- **3ᵉ place** : remplie **même incomplète**, titre selon son rôle (« 💸 L'économie », « ➕ L'autre option » ou « 🔎 Autre piste »), % affiché ; une souris un peu plus chère est acceptée ; le **marqueur discret** signale un score partiel.
- **Ne pas afficher** : les souris écartées, la matrice, les données de debug.
- **Images** : les 15 illustrations `T01`–`T15` (bannière, étapes, illustrations du résultat), hébergées par le propriétaire, lisibles en thème **sombre et clair**.
- **Poids** affiché près des deux premières places.
- **Boutons « tranche toi-même »** : non bloquants, l'utilisateur peut explorer.
- **Prix** : boutique officielle, en euros, marqueur « (prix non vérifié) » quand la donnée n'est pas attestée.
- **Hauteur des boutons** : critère jugé sur le **rapport mesuré sur l'image**, pas sur une impression.
- **Français** irritéprochable, **mobile d'abord**, « le résultat le plus concis possible ».

---

## Annexe E — Glossaire du dépôt

| Terme | Sens |
| --- | --- |
| **passe** | une itération de travail (77 à ce jour), numérotée, avec défaut trouvé → correction → test → journal → commit |
| **C-n°** | un constat de l'audit (`docs/audit/AUDIT.md`), C1 → C99 |
| **§26.x** | une section du journal de chasse (`docs/audit/ROBUSTESSE_2026-10-12.md`) |
| **§12.x** | une mise à jour du guide de déploiement (`docs/DEPLOYMENT_ALWAYSDATA_FILEZILLA.md`) |
| **`Reverse/`** | la preuve primaire : 10 sorties datées de l'outil d'origine (Oblivity), non modifiables |
| **T01–T15** | les 15 illustrations du bot (`ImageUse/`), mappées dans `assets/images.json` |
| **banc / grille** | `tools/qa_flow_matrix.py` : passe tous les profils dans le moteur et vérifie les invariants |
| **mutation** | casser volontairement le code pour vérifier qu'un test échoue bien |
| **`shell_id`** | identifiant de **coque** : deux souris de même coque n'occupent pas deux places, sauf repli quand aucun autre candidat ne reste |
| **marqueur partiel** | « boutons non documentés » : signale un score incomplet sur une souris |
| **empreinte des sources** | SHA-256 inscrit dans les PNG d'aperçu pour détecter un aperçu périmé |

---

## Mot de la fin

Tu hérites d'un système **fiable sur ses données** et **encombré sur tout le reste**. Les 36 souris du catalogue sont sourcées, les liens sont vérifiés, les chiffres publiés ont été remesurés, et les pièges de méthode sont écrits noir sur blanc ici — c'est ton point de départ gratuit.

Ce qui reste à faire est plus intéressant : **réduire, éclaircir, structurer, automatiser**. Le propriétaire te donne les clés, y compris celle de la poubelle. Sers-t'en : un dépôt plus petit qui fait la même chose, en mieux, avec des chiffres qu'on peut rejouer, c'est exactement ce qu'il demande.

Et rappelle-toi la seule règle qui n'a jamais bougé depuis le premier jour : **ici, on ne devine pas. On mesure, ou on ne dit rien.**
