"""HTTP tests for POST /progression (M3 Chunk B)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_progression_happy_path_pac():
    resp = client.post(
        "/progression",
        json={"key": "C major", "length": 8, "cadence": "PAC", "seed": 42},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["key"] == "C major"
    assert data["length"] == 8
    assert data["cadence"] == "PAC"
    assert data["seed"] == 42
    prog = data["progression"]
    assert len(prog) == 8
    assert prog[-2] in ("V", "V7")
    assert prog[-1] == "I"


def test_progression_seed_is_deterministic():
    body = {"key": "C major", "length": 8, "seed": 7}
    a = client.post("/progression", json=body).json()["progression"]
    b = client.post("/progression", json=body).json()["progression"]
    assert a == b


def test_progression_honors_locked_slots():
    resp = client.post(
        "/progression",
        json={
            "key": "C major",
            "length": 6,
            "locked": {"1": "IV", "3": "vi"},
            "seed": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    prog = resp.json()["progression"]
    assert prog[1] == "IV"
    assert prog[3] == "vi"


def test_progression_lock_conflict_returns_422():
    # Final chord locked to IV cannot satisfy PAC.
    resp = client.post(
        "/progression",
        json={
            "key": "C major",
            "length": 4,
            "locked": {"3": "IV"},
            "cadence": "PAC",
            "seed": 0,
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "grammar_failed"


def test_progression_then_generate_chain():
    """Acceptance: /progression → /generate end-to-end."""
    prog_resp = client.post(
        "/progression",
        json={"key": "C major", "length": 4, "seed": 1},
    )
    assert prog_resp.status_code == 200, prog_resp.text
    progression = prog_resp.json()["progression"]

    gen_resp = client.post(
        "/generate",
        json={"key": "C major", "progression": progression},
    )
    assert gen_resp.status_code == 200, gen_resp.text
    data = gen_resp.json()
    assert data["progression"] == progression
    xml = data["musicxml"]
    assert isinstance(xml, str)
    assert "<?xml" in xml or "score-partwise" in xml
