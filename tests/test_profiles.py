from mute.core.profiles import Profile, ProfileStore


def _store(tmp_path):
    return ProfileStore(path=tmp_path / "profiles.json")


def test_upsert_sets_first_profile_active(tmp_path):
    store = _store(tmp_path)
    store.upsert(Profile(name="prod", base_url="https://a"))
    assert store.active_name == "prod"
    assert store.get_active().base_url == "https://a"


def test_active_persists_across_reload(tmp_path):
    store = _store(tmp_path)
    store.upsert(Profile(name="prod", base_url="https://a"))
    store.upsert(Profile(name="test", base_url="https://b"), make_active=True)

    reloaded = ProfileStore(path=tmp_path / "profiles.json")
    assert reloaded.active_name == "test"
    assert set(reloaded.names()) == {"prod", "test"}


def test_delete_reassigns_active(tmp_path):
    store = _store(tmp_path)
    store.upsert(Profile(name="prod", base_url="https://a"), make_active=True)
    store.upsert(Profile(name="test", base_url="https://b"))
    store.delete("prod")
    assert store.active_name == "test"


def test_base_url_trailing_slash_stripped():
    assert Profile(name="p", base_url="https://x/").base_url == "https://x"


def test_auth_method_detection():
    assert Profile("p", "https://x", username="a", password="b").auth_method == "username/password"
    assert Profile("p", "https://x", token="t").auth_method == "token"
    assert Profile("p", "https://x").auth_method == "none"
