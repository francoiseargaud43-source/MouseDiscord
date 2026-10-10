"""Sessions de parcours : isolation par identifiant unique et vérification du propriétaire."""
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
