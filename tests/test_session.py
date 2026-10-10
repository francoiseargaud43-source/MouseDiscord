"""Gestion des sessions en mémoire (session_id = user_id)."""
from utils.session import SessionStore


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_start_and_get_same_user():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    s = store.start(42)
    assert store.get(42) is s
    assert store.get(7) is None


def test_session_expires_after_ttl():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    store.start(42)
    clock.now = 30
    assert store.get(42) is not None  # l'activité rafraîchit le délai
    clock.now = 89
    assert store.get(42) is not None
    clock.now = 200
    assert store.get(42) is None
    assert len(store) == 0


def test_start_resets_previous_session():
    store = SessionStore(ttl_seconds=60, clock=FakeClock())
    first = store.start(1)
    first.grip = None
    store.get(1).hand_length_mm = 180
    second = store.start(1)
    assert second.hand_length_mm is None


def test_purge_expired():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=10, clock=clock)
    store.start(1)
    clock.now = 5
    store.start(2)
    clock.now = 12
    assert store.purge_expired() == 1
    assert len(store) == 1
