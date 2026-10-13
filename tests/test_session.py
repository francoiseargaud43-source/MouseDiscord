"""Sessions de parcours : isolation par identifiant unique et vérification du propriétaire."""
import json

import pytest

from utils.models import BudgetMode, ClawVariant, Grip, Thenar
from utils.session import (
    LOOKUP_FORBIDDEN,
    LOOKUP_INACTIVE,
    LOOKUP_OK,
    FinderSession,
    SessionStore,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_start_and_lookup_same_user():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    s = store.start(42)
    assert store.lookup(s.session_id, 42) == (s, LOOKUP_OK)


def test_session_ids_are_unique_and_unguessable():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    ids = {store.start(i).session_id for i in range(50)}
    assert len(ids) == 50
    assert all(len(sid) >= 16 for sid in ids)


def test_other_user_cannot_use_session_id():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    s = store.start(42)
    session, status = store.lookup(s.session_id, 7)
    assert session is None and status == LOOKUP_FORBIDDEN
    # ... et la session du propriétaire n'a pas été modifiée
    assert store.lookup(s.session_id, 42) == (s, LOOKUP_OK)


def test_unknown_or_empty_session_id_is_inactive():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    assert store.lookup("inconnu", 1) == (None, LOOKUP_INACTIVE)
    assert store.lookup(None, 1) == (None, LOOKUP_INACTIVE)
    assert store.lookup("", 1) == (None, LOOKUP_INACTIVE)


def test_new_start_replaces_previous_session_of_same_user():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    old = store.start(1)
    new = store.start(1)
    assert old.session_id != new.session_id
    # l'ancien parcours (menu encore ouvert) devient inactif et ne peut plus rien modifier
    assert store.lookup(old.session_id, 1) == (None, LOOKUP_INACTIVE)
    assert store.lookup(new.session_id, 1)[1] == LOOKUP_OK


def test_replacing_one_users_session_does_not_touch_another_user():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    a = store.start(1)
    b = store.start(2)
    store.start(1)  # A relance son test
    assert store.lookup(b.session_id, 2)[1] == LOOKUP_OK
    assert store.lookup(a.session_id, 1)[1] == LOOKUP_INACTIVE


def test_discard_removes_only_that_session():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    a = store.start(1)
    b = store.start(2)
    store.discard(a.session_id)
    assert store.lookup(a.session_id, 1)[1] == LOOKUP_INACTIVE
    assert store.lookup(b.session_id, 2)[1] == LOOKUP_OK
    assert len(store) == 1


def test_session_expires_after_ttl_and_activity_refreshes_it():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    s = store.start(42)
    clock.now = 30
    assert store.lookup(s.session_id, 42)[1] == LOOKUP_OK  # l'activité rafraîchit le délai
    clock.now = 89
    assert store.lookup(s.session_id, 42)[1] == LOOKUP_OK
    clock.now = 200
    assert store.lookup(s.session_id, 42) == (None, LOOKUP_INACTIVE)
    assert len(store) == 0


def test_expiry_of_one_session_does_not_destroy_another_active_session():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    a = store.start(1)
    clock.now = 50
    b = store.start(2)
    clock.now = 100          # A (inactive depuis 100 s) expire, B (démarrée à 50 s) reste active
    assert store.lookup(a.session_id, 1)[1] == LOOKUP_INACTIVE
    assert store.lookup(b.session_id, 2)[1] == LOOKUP_OK


def test_purge_expired_only_removes_expired():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=10, clock=clock)
    store.start(1)
    clock.now = 5
    store.start(2)
    clock.now = 12
    assert store.purge_expired() == 1
    assert len(store) == 1


def test_start_purges_expired_sessions_of_others():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=10, clock=clock)
    store.start(1)
    clock.now = 100
    store.start(2)
    assert len(store) == 1  # la session de l'utilisateur 1 n'est plus conservée


# --- Chasse aux bugs du 2026-10-12 : un délai de vie nul ou négatif est refusé ---
@pytest.mark.parametrize("ttl", [0, -1, -1800])
def test_a_non_positive_ttl_is_refused(ttl):
    """Un TTL nul ferait expirer chaque parcours aussitôt (« ce parcours a expiré » à chaque clic)."""
    with pytest.raises(ValueError, match="ttl_seconds"):
        SessionStore(ttl_seconds=ttl)


# --- Chasse aux micro-bugs du 2026-10-13 : le fichier d'état vit sur le SERVEUR ---
# Il peut être tronqué (transfert FileZilla interrompu), édité à la main ou écrit par une version
# antérieure. Un fichier hostile ne doit JAMAIS empêcher le bot de démarrer : soit il est ignoré,
# soit ce qui est lisible est récupéré — jamais une exception.
CAS_IGNORES = {
    "vide": "",
    "pas du json": "{ceci n'est pas du json",
    "liste racine": "[1, 2, 3]",
    "version inconnue": '{"version": 99, "sessions": []}',
    "sessions pas une liste": '{"version": 1, "sessions": {"a": 1}}',
    "entree pas un objet": '{"version": 1, "sessions": [42]}',
    "session sans user_id": '{"version": 1, "sessions": [{"session_id": "x"}]}',
    "age absurde": '{"version": 1, "sessions": [{"session_id": "a", "user_id": 1, "age_seconds": "hier"}]}',
    "age demesure": '{"version": 1, "sessions": [{"session_id": "b", "user_id": 2, "age_seconds": 1e12}]}',
    "grip inconnu": ('{"version": 1, "sessions": [{"session_id": "c", "user_id": 3, "age_seconds": 1,'
                     ' "grip": "griffe-de-tigre"}]}'),
}

CAS_RECUPERES = {
    # Le budget illisible est écarté, le reste du parcours reprend.
    "budget texte": ('{"version": 1, "sessions": [{"session_id": "d", "user_id": 4, "age_seconds": 1,'
                     ' "max_budget_eur": "beaucoup"}]}', 4),
    # Deux copies de la même session : une seule est gardée (l'identifiant est unique).
    "session dupliquee": ('{"version": 1, "sessions": [{"session_id": "e", "user_id": 5, "age_seconds": 1},'
                          ' {"session_id": "e", "user_id": 5, "age_seconds": 1}]}', 5),
    # Horloge reculée : « vue à l'instant », jamais « vue dans le futur » (micro-défaut corrigé
    # le 2026-10-13 : une session d'âge négatif gagnait la vie en plus et pouvait ne jamais expirer).
    "age negatif": ('{"version": 1, "sessions": [{"session_id": "f", "user_id": 6, "age_seconds": -5,'
                    ' "grip": "palm"}]}', 6),
    "age negatif demesure": ('{"version": 1, "sessions": [{"session_id": "g", "user_id": 7,'
                             ' "age_seconds": -1e12, "grip": "palm"}]}', 7),
}


@pytest.mark.parametrize("nom", sorted(CAS_IGNORES))
def test_un_fichier_d_etat_illisible_est_ignore_sans_bloquer_le_demarrage(tmp_path, nom):
    """Fichier inutilisable : aucune exception, rien de restauré, et un parcours neuf marche."""
    chemin = tmp_path / "sessions.json"
    chemin.write_text(CAS_IGNORES[nom], encoding="utf-8")
    store = SessionStore(ttl_seconds=1800, path=chemin)       # ne lève jamais
    assert len(store) == 0, f"{nom} : session restaurée alors que l'enregistrement est inutilisable"
    session = store.start(user_id=1)
    assert store.lookup(session.session_id, 1)[1] == LOOKUP_OK


@pytest.mark.parametrize("nom", sorted(CAS_RECUPERES))
def test_ce_qui_est_lisible_est_recupere_sans_gagner_de_vie(tmp_path, nom):
    """Session récupérée : elle reste soumise au délai d'inactivité, jamais immortelle."""
    contenu, utilisateur = CAS_RECUPERES[nom]
    chemin = tmp_path / "sessions.json"
    chemin.write_text(contenu, encoding="utf-8")
    clock = FakeClock()
    store = SessionStore(ttl_seconds=1800, clock=clock, path=chemin)
    assert len(store) == 1
    assert store.current(utilisateur)[1] == LOOKUP_OK
    # Un âge négatif est ramené à zéro : « vue à l'instant », jamais « vue dans le futur ».
    assert store.current(utilisateur)[0].last_seen == clock.now
    clock.now += 1801
    assert store.purge_expired() == 1                     # donc elle expire normalement


def test_un_fichier_tronque_en_plein_caractere_ne_bloque_pas_le_demarrage(tmp_path):
    """Trouvé le 2026-10-13 : seuls le JSON invalide et l'absence de fichier étaient prévus.

    Des **octets non UTF-8** (transfert FileZilla interrompu, disque plein, copie partielle) faisaient
    remonter ``UnicodeDecodeError`` depuis la construction du magasin — donc depuis la construction du
    bot : **le bot ne démarrait plus**, alors que la promesse de ce fichier est « jamais une
    exception ». Même famille que C45 (commande d'installation).
    """
    chemin = tmp_path / "sessions.json"
    chemin.write_bytes(b'{"version": 1, "sessions": [{"session_id": "a", "user_id": 1, "note": "\xc3')
    store = SessionStore(ttl_seconds=1800, path=chemin)          # ne lève pas
    assert len(store) == 0
    session = store.start(user_id=1)                             # un parcours neuf fonctionne…
    assert store.lookup(session.session_id, 1)[1] == LOOKUP_OK
    assert "version" in chemin.read_text(encoding="utf-8")       # …et le fichier repart proprement


def test_un_identifiant_impossible_a_reecrire_est_refuse(tmp_path):
    """Un demi-caractère (``"\\ud800"``) ne peut pas être réencodé : il est refusé au chargement.

    L'identifiant est réécrit **tel quel** dans le fichier (``ensure_ascii=False``) : un tel contenu
    faisait échouer l'enregistrement à chaque réponse, donc tout parcours devenait impossible à
    terminer tant que le fichier restait en place.
    """
    chemin = tmp_path / "sessions.json"
    chemin.write_text('{"version": 1, "sessions": [{"session_id": "\\ud800", "user_id": 1, '
                      '"age_seconds": 1, "grip": "palm"}]}', encoding="utf-8")
    store = SessionStore(ttl_seconds=1800, path=chemin)
    assert len(store) == 0                                       # la session bricolée est écartée
    session = store.start(user_id=2)
    assert store.lookup(session.session_id, 2)[1] == LOOKUP_OK   # et le parcours neuf est utilisable


def test_un_etat_impossible_a_ecrire_ne_casse_pas_le_parcours(tmp_path):
    """``save()`` promet « ne lève jamais » : un contenu non écrivable ne doit pas casser une réponse.

    La garantie est dans la docstring, elle est maintenant vraie dans le code : l'enregistrement est
    perdu (avec un avertissement dans les journaux), pas l'interaction du membre.
    """
    chemin = tmp_path / "sessions.json"
    store = SessionStore(ttl_seconds=1800, path=chemin)
    session = store.start(user_id=1)
    session.session_id = "\ud800"                        # contenu impossible à écrire en UTF-8
    store.save()                                         # ne lève pas (l'avertissement est tracé)…
    remplacante = store.start(user_id=2)                 # …et le magasin reste utilisable
    assert store.lookup(remplacante.session_id, 2)[1] == LOOKUP_OK


def test_un_age_negatif_ne_rend_pas_la_session_immortelle():
    """Horloge reculée de 5 s : la session repart « vue à l'instant » et expire après le délai."""
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory() as dossier:
        chemin = _Path(dossier) / "sessions.json"
        chemin.write_text(json.dumps({"version": 1, "sessions": [
            {"session_id": "zz", "user_id": 7, "age_seconds": -5, "grip": "palm"}]}), encoding="utf-8")
        clock = FakeClock()
        store = SessionStore(ttl_seconds=10, clock=clock, path=chemin)
        assert len(store) == 1                    # la reprise est acceptée
        clock.now = 11
        assert store.purge_expired() == 1         # et elle expire bien (sans le correctif : jamais)


def test_un_dossier_a_la_place_du_fichier_d_etat_ne_bloque_pas_le_demarrage(tmp_path):
    """Cas réel d'un transfert raté : un dossier porte le nom du fichier attendu."""
    chemin = tmp_path / "sessions.json"
    chemin.mkdir()
    store = SessionStore(ttl_seconds=1800, path=chemin)
    assert len(store) == 0
    session = store.start(user_id=1)
    assert store.lookup(session.session_id, 1)[1] == LOOKUP_OK


# --- Chasse aux micro-bugs du 2026-10-13 : un état bricolé ne doit ni bloquer ni mentir ---
MESURES_IMPOSSIBLES = {
    "zéro": (0.0, 0.0),
    "négatives": (-180.0, -90.0),
    "NaN": (float("nan"), float("nan")),
    "infini": (float("inf"), 90.0),
    "trop courtes (60 × 120)": (60.0, 120.0),
    "trop longues (900 × 400)": (900.0, 400.0),
    "juste au-dessus (260,1 × 130,1)": (260.1, 130.1),
    "l'une des deux absente": (180.0, None),
}

MESURES_DU_FORMULAIRE = {
    "courantes (180 × 90)": (180.0, 90.0),
    "bornes basses (100 × 50)": (100.0, 50.0),
    "bornes hautes (260 × 130)": (260.0, 130.0),
    "décimales (180,5 × 90,5)": (180.5, 90.5),
}


def _restaurer(tmp_path, **etat):
    """Écrit un fichier d'état à une session puis le relit (comme au démarrage du bot)."""
    chemin = tmp_path / "sessions.json"
    chemin.write_text(json.dumps({"version": 1, "sessions": [
        {"session_id": "s1", "user_id": 42, "age_seconds": 10.0, **etat}]}), encoding="utf-8")
    store = SessionStore(ttl_seconds=1800, path=chemin)
    session, statut = store.current(42)
    assert statut == LOOKUP_OK
    return session


@pytest.mark.parametrize("nom", sorted(MESURES_IMPOSSIBLES))
def test_des_mesures_que_le_formulaire_ne_peut_pas_produire_sont_ecartees(tmp_path, nom):
    """Trouvé le 2026-10-13 : ces mesures étaient restaurées telles quelles, avec deux suites fausses.

    `0 × 0` ou des mesures négatives faisaient lever le moteur (« Les mesures de la main doivent être
    strictement positives ») : le membre lisait **« ⚠️ Les données des souris sont momentanément
    illisibles. Réessayez dans un instant »** — un message qui accuse le catalogue, ne dit rien de la
    vraie cause et ne se résout jamais. Des mesures `NaN` étaient pires : toutes les comparaisons avec
    `NaN` étant fausses, chaque souris passait pour « dans la plage » et le membre recevait un résultat
    absurde, présenté sans réserve. Un membre ne peut saisir que des nombres finis dans les bornes du
    formulaire (100–260 mm et 50–130 mm, `utils/validation.py`) : toute autre valeur vient d'un fichier
    bricolé ou abîmé. Elle vaut donc **réponse absente** — le parcours reprend à l'étape « Vos mesures ».
    """
    longueur, largeur = MESURES_IMPOSSIBLES[nom]
    session = _restaurer(tmp_path, grip="palm", hand_length_mm=longueur, hand_width_mm=largeur,
                         budget_mode="qualite_prix")
    assert session.has_measures is False, f"{nom} : mesures gardées alors qu'elles sont impossibles"
    assert session.hand_length_mm is None and session.hand_width_mm is None


@pytest.mark.parametrize("nom", sorted(MESURES_DU_FORMULAIRE))
def test_les_mesures_du_formulaire_sont_conservees(tmp_path, nom):
    """Non-régression : aucune valeur saisissable n'est écartée (bornes comprises)."""
    longueur, largeur = MESURES_DU_FORMULAIRE[nom]
    session = _restaurer(tmp_path, grip="palm", hand_length_mm=longueur, hand_width_mm=largeur,
                         budget_mode="qualite_prix")
    assert session.has_measures is True
    assert (session.hand_length_mm, session.hand_width_mm) == (longueur, largeur)


@pytest.mark.parametrize("plafond", [None, "beaucoup", float("nan"), float("inf"), 0.0, -5.0, 5.0, 9000.0])
def test_un_budget_personnalise_sans_plafond_exploitable_revient_a_la_question(tmp_path, plafond):
    """« Budget personnalisé » sans plafond utilisable : le moteur refuse de comparer.

    Le membre lisait « les données des souris sont momentanément illisibles » puis, à chaque nouvel
    essai, le même message — sans issue, puisque la cause était son propre enregistrement. Le mode
    redevient « aucune gamme choisie » (et le plafond inutilisable est retiré) : la question est reposée.
    """
    etat = dict(grip="palm", hand_length_mm=180.0, hand_width_mm=90.0, budget_mode="custom")
    if plafond is not None:
        etat["max_budget_eur"] = plafond
    session = _restaurer(tmp_path, **etat)
    assert session.budget_mode is None, f"plafond {plafond!r} : mode conservé sans plafond exploitable"
    assert session.max_budget_eur is None
    assert session.has_measures is True          # le reste du parcours est intact


@pytest.mark.parametrize("plafond", [10.0, 45.0, 5000.0])
def test_un_budget_personnalise_avec_plafond_valide_est_conserve(tmp_path, plafond):
    """Non-régression : un plafond saisissable est gardé, avec son mode."""
    session = _restaurer(tmp_path, grip="palm", hand_length_mm=180.0, hand_width_mm=90.0,
                         budget_mode="custom", max_budget_eur=plafond)
    assert session.budget_mode is not None and session.max_budget_eur == plafond


def test_un_etat_bricole_reprend_exactement_comme_un_parcours_sans_mesures(tmp_path):
    """La conséquence visible : le membre reprend à l'étape Mesures, sans message d'erreur.

    Le flux décide de l'étape sur `has_measures`, et le calcul du résultat sur `compute_selection` :
    mesures écartées ou jamais saisies mènent donc au même endroit. Le contrôle compare les deux états
    plutôt que de supposer (avant correction, l'état bricolé faisait lever `compute_selection` sur
    « Les mesures de la main doivent être strictement positives » — donc « données illisibles »).
    """
    from cogs import finder_flow as flow

    restauree = _restaurer(tmp_path, grip="palm", hand_length_mm=float("nan"),
                           hand_width_mm=float("nan"), budget_mode="qualite_prix")
    jamais_repondue = SessionStore(ttl_seconds=1800).start(user_id=7)
    jamais_repondue.grip = restauree.grip

    assert restauree.has_measures is False
    assert jamais_repondue.has_measures is False
    messages = []
    for session in (restauree, jamais_repondue):
        with pytest.raises(ValueError) as levee:
            flow.compute_selection(session)
        messages.append(str(levee.value))
    assert messages[0] == messages[1]
    assert "Parcours incomplet" in messages[0]

# ---------------------------------------------------------------------------
# Contrats de conservation : ce qui est écrit doit se relire à l'identique
# (mesure du 2026-10-13 : `to_state`/`from_state` n'étaient jamais exercés en aller-retour complet)
# ---------------------------------------------------------------------------
def test_un_parcours_se_relit_a_l_identique_apres_redemarrage():
    """Tout ce que `to_state` écrit, `from_state` le relit — variante de Claw comprise.

    Aucune épreuve ne faisait l'aller-retour complet : retirer une ligne de `from_state` (ou une clé
    de `to_state`) aurait fait perdre une réponse du membre au redémarrage sans qu'un seul test
    bronche — la panne P11, en plus discret.
    """
    session = FinderSession(user_id=7)
    session.grip = Grip.CLAW
    session.claw_variant = ClawVariant.PINCEE
    session.thenar = Thenar.GRANDE
    session.hand_length_mm = 175.0
    session.hand_width_mm = 82.5
    session.budget_mode = BudgetMode.CUSTOM
    session.max_budget_eur = 60.0

    etat = session.to_state(age_seconds=12.5)
    assert etat["claw_variant"] == "pincee"
    relue = FinderSession.from_state(etat, last_seen=1000.0)

    assert relue is not None
    assert (relue.session_id, relue.user_id) == (session.session_id, 7)
    assert (relue.grip, relue.thenar, relue.claw_variant) == (Grip.CLAW, Thenar.GRANDE, ClawVariant.PINCEE)
    assert (relue.hand_length_mm, relue.hand_width_mm) == (175.0, 82.5)
    assert (relue.budget_mode, relue.max_budget_eur) == (BudgetMode.CUSTOM, 60.0)


DEUX_VIVANTS = {"version": 1, "sessions": [
    {"session_id": "ancien", "user_id": 1, "age_seconds": 300, "grip": "palm"},
    {"session_id": "recent", "user_id": 1, "age_seconds": 5, "grip": "claw"},
    {"session_id": "autre", "user_id": 2, "age_seconds": 5, "grip": "palm"},
]}


def test_un_membre_avec_deux_parcours_restaures_garde_un_seul_vivant(tmp_path):
    """Fichier d'état bricolé (deux parcours en cours du même membre) : le magasin se remet d'aplomb.

    Cas réel : l'ancien parcours et le nouveau peuvent cohabiter si le fichier a été écrit par deux
    exécutions ou édité à la main. Un seul reste **actif**, l'autre est **refusé** (jamais un mélange
    des deux réponses) — et quand le membre relance, **les deux** disparaissent, pas seulement l'actif.
    """
    chemin = tmp_path / "sessions.json"
    chemin.write_text(json.dumps(DEUX_VIVANTS), encoding="utf-8")
    store = SessionStore(ttl_seconds=1800, path=chemin)

    assert len(store) == 3
    assert store.current(1)[0].session_id == "recent"            # le plus récent est actif
    assert store.lookup("ancien", 1) == (None, LOOKUP_INACTIVE)  # l'autre est refusé

    store.start(1)                                               # le membre relance son test
    assert store.lookup("ancien", 1)[1] == LOOKUP_INACTIVE
    assert store.lookup("recent", 1)[1] == LOOKUP_INACTIVE       # aucun des deux ne survit
    assert len(store) == 2                                       # « autre » + le nouveau
    assert store.current(2)[0].session_id == "autre"
    assert store.current(2)[1] == LOOKUP_OK                      # l'autre membre n'est pas touché


def test_supprimer_le_parcours_actif_rend_la_main_a_celui_qui_reste(tmp_path):
    """Deux vivants d'un membre : supprimer l'actif promeut l'autre (jamais « aucun parcours »)."""
    chemin = tmp_path / "sessions.json"
    chemin.write_text(json.dumps(DEUX_VIVANTS), encoding="utf-8")
    store = SessionStore(ttl_seconds=1800, path=chemin)

    store.discard("recent")

    assert store.lookup("ancien", 1)[1] == LOOKUP_OK             # l'ancien reprend la main
    assert store.current(1)[0].session_id == "ancien"
    assert store.current(2)[0].session_id == "autre"             # l'autre membre n'est pas touché
    assert len(store) == 2


def test_terminer_un_parcours_inconnu_ne_change_rien():
    """`finish` sur un identifiant inconnu (expiré, redémarré, clic tardif) : aucun effet."""
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    vivant = store.start(1)
    store.finish(None)
    store.finish("inconnu")
    assert len(store) == 1
    assert store.lookup(vivant.session_id, 1)[1] == LOOKUP_OK


def test_retirer_un_parcours_inconnu_ne_change_rien():
    """`_remove` reçoit des identifiants venus de l'extérieur : un inconnu doit être ignoré en silence.

    Sans cette garde, un clic rejoué sur un parcours déjà retiré (ou une purge concurrente) ferait tomber
    le bot au lieu de ne rien faire — et le parcours vivant d'à côté ne doit pas être touché.
    """
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    vivant = store.start(42)

    store._remove("parcours-jamais-vu")

    assert store.lookup(vivant.session_id, 42) == (vivant, LOOKUP_OK)
    assert len(store) == 1
