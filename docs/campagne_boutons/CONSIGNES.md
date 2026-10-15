# Campagne « hauteur des boutons » — consignes pour l'agent qui a accès à EloShapes

**Pourquoi** : 18 souris sur 36 n'ont pas de hauteur de boutons. Elles perdent les points de ce
critère sans que personne sache si elles les méritaient. Selon ce que vaudront ces 18 hauteurs, le
match idéal peut changer pour **27 % des profils** (mesure du 2026-10-15, 21 736 profils du banc ;
rejouable : `python tools/campagne_boutons.py sensibilite`).
EloShapes dessine toutes les souris de profil, à plat et de la même façon : c'est la source idéale.

**Ton rôle** : collecter **une image de profil latéral par souris** sur EloShapes, puis lancer l'outil
de mesure. En dehors du manifeste (que tu remplis) et du dossier `images/` (que tu crées), tu ne
modifies **rien** dans le dépôt, et tu ne décides **aucune** valeur : l'outil propose, le propriétaire décide.

## 1. Préparer

1. Récupère la branche `arena/87fafd0d-mousediscord` du dépôt `francoiseargaud43-source/MouseDiscord`
   (archive ZIP ou `git clone`).
2. Python 3.10 ou plus, puis : `pip install Pillow` (c'est la seule bibliothèque utile ici).
3. Crée le dossier `docs/campagne_boutons/images/`.

## 2. Collecter les 36 images

Ouvre `docs/campagne_boutons/manifeste.csv` : une ligne par souris. Pour chaque ligne :

1. **Trouve la souris sur EloShapes.** Si la colonne `source` contient une adresse, ouvre-la ; sinon,
   cherche le nom de la colonne `modele` sur https://www.eloshapes.com et vérifie que la page porte
   **exactement ce modèle** (une souris absente d'EloShapes : laisse la ligne telle quelle, l'outil la
   signalera « image introuvable » — c'est une réponse, pas une erreur).
2. **Affiche la vue de profil (côté) de cette souris seule** — jamais une superposition de plusieurs
   souris.
3. **Enregistre l'image** sous `docs/campagne_boutons/images/<id>.png` (le nom est dans la colonne
   `image`). Par ordre de préférence :
   - l'image de profil elle-même (clic droit → enregistrer, ou onglet Réseau des outils de
     développement), en PNG ;
   - à défaut, une **capture d'écran recadrée** sur la souris, en **laissant une marge** tout autour
     (la souris ne doit toucher aucun bord), au plus grand zoom qui la montre entière.
4. **Remplis la ligne** :
   - `avant` : `gauche` ou `droite` — le côté de l'image où se trouvent **les boutons** (l'avant) ;
   - `source` : l'adresse exacte de la page ;
   - `date` : la date du jour (AAAA-MM-JJ) ;
   - `couleur` : **seulement** si l'image est un contour coloré posé sur une grille — la couleur du
     contour en `#RRGGBB`.

Ne redimensionne pas, ne retouche pas, ne compresse pas les images.

## 3. Mesurer

Depuis la racine du dépôt :

```
python tools/campagne_boutons.py campagne docs/campagne_boutons/manifeste.csv --dossier docs/campagne_boutons/images --rapport rapport.md --json releve.json
```

L'outil contrôle chaque image : une silhouette dont les proportions ne collent pas aux cotes du
catalogue (vue de biais, autre souris) est **refusée** ; une bosse mesurée loin de celle du catalogue
déclenche une **alerte** (le plus souvent : `avant` inversé — corrige la ligne et relance).

## 4. Rendre

Renvoie au propriétaire, **sans les résumer** :

1. le contenu complet de `rapport.md` ;
2. le contenu complet de `releve.json` ;
3. le manifeste rempli ;
4. si possible, les images (archive ZIP du dossier `images/`) : elles sont la preuve de la mesure.

## Règles absolues

- Une image = une souris, identifiée par sa page EloShapes. Aucune image d'une autre source.
- Aucune valeur inventée, aucune image « approchante » : une souris introuvable reste sans image.
- Tu ne modifies ni `data/mouse_db.json` ni aucun autre fichier du dépôt, en dehors du manifeste et du
  dossier `images/`.
