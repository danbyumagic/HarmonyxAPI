"""HTTP tests for POST /generate (Milestone 1f)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_happy_path_returns_musicxml():
    resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "IV", "V", "I"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["key"] == "C major"
    assert data["progression"] == ["I", "IV", "V", "I"]
    assert data["time_signature"] == "4/4"
    assert isinstance(data["musicxml"], str)
    assert "score-partwise" in data["musicxml"] or "<?xml" in data["musicxml"]
    playback = data["playback"]
    assert playback["tempo_bpm"] == 75
    # 4 chords × 4 voices = 16 block-chord note events
    assert len(playback["events"]) == 16
    assert all(e["duration"] == 1.0 for e in playback["events"])
    # First beat is a simultaneous block of 4 notes
    beat0 = [e for e in playback["events"] if e["beat"] == 0]
    assert len(beat0) == 4


def test_generate_with_compatible_soprano_returns_200():
    resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "V", "I"],
            "soprano": [72, 71, 72],  # C5 - B4 - C5
        },
    )
    assert resp.status_code == 200, resp.text
    assert "musicxml" in resp.json()


def test_generate_incompatible_soprano_returns_422():
    # C4 (MIDI 60) is not a chord tone of V (G-B-D).
    resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "V"],
            "soprano": [60, 60],
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "incompatible_soprano"
    assert isinstance(detail["mismatches"], list)
    assert len(detail["mismatches"]) >= 1
    assert detail["mismatches"][0]["index"] == 1


def test_generate_soprano_length_mismatch_returns_422():
    resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "V"],
            "soprano": [60],
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "soprano_length_mismatch"


# --- POST /generate/soprano-options -----------------------------------


def test_soprano_options_happy_path_returns_up_to_three_options():
    resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    options = data["options"]
    assert 0 < len(options) <= 3
    for opt in options:
        assert len(opt["soprano"]) == 4
        assert len(opt["pitches"]) == 4
        assert all(isinstance(p, int) for p in opt["soprano"])
        assert all(isinstance(p, str) for p in opt["pitches"])


def test_soprano_options_first_option_pitches_match_soprano_midis():
    resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "V", "I"]},
    )
    assert resp.status_code == 200, resp.text
    first = resp.json()["options"][0]
    # e.g. soprano=[72, 71, 72] -> pitches=["C5", "B4", "C5"]
    assert first["pitches"][0] in ("C5",)  # tonic-triad soprano options include C5
    assert len(first["pitches"]) == len(first["soprano"])


def test_soprano_options_chosen_option_feeds_generate_successfully():
    # The whole point of the split endpoint: an option's soprano array must
    # be directly usable as POST /generate's soprano param.
    options_resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"]},
    )
    chosen = options_resp.json()["options"][-1]["soprano"]

    gen_resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "IV", "V", "I"],
            "soprano": chosen,
        },
    )
    assert gen_resp.status_code == 200, gen_resp.text
