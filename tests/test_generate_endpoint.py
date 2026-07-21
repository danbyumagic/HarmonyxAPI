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
