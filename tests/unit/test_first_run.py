import json

from clickforge.services.first_run import FirstRunStore


def test_welcome_defaults_to_not_seen(tmp_path):
    store = FirstRunStore(tmp_path / "ui-state.json")
    assert store.welcome_seen() is False


def test_welcome_marker_round_trips(tmp_path):
    store = FirstRunStore(tmp_path / "nested" / "ui-state.json")
    store.mark_welcome_seen()
    assert store.welcome_seen() is True

    store.reset_welcome()
    assert store.welcome_seen() is False


def test_corrupt_or_non_object_state_is_treated_as_unseen(tmp_path):
    path = tmp_path / "ui-state.json"
    path.write_text("{not json", encoding="utf-8")
    assert FirstRunStore(path).welcome_seen() is False

    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert FirstRunStore(path).welcome_seen() is False


def test_state_file_is_written_as_sorted_json(tmp_path):
    path = tmp_path / "ui-state.json"
    FirstRunStore(path).mark_welcome_seen()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"schema_version": 1, "welcome_seen": True}
    assert path.read_text(encoding="utf-8").endswith("\n")
