"""Sessions de parcours : isolation par identifiant unique et vérification du propriétaire."""
import pytest

from utils.session import LOOKUP_FORBIDDEN, LOOKUP_INACTIVE, LOOKUP_OK, SessionStore


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


def test_un_age_negatif_ne_rend_pas_la_session_immortelle():
    """Horloge reculée de 5 s : la session repart « vue à l'instant » et expire après le délai."""
    import json
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
