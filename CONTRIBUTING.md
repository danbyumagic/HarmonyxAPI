# Contributing

Thanks for looking under the hood.

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -q
```

Python **3.11+** required (music21 10.x).

## Rules of the road

1. **Don’t edit** `tests/test_partwriting.py` to match a broken implementation — those fixtures are the locked part-writing contract. Fix the engine instead.
2. Prefer small, reviewable PRs over mega-diffs.
3. Keep the core loop **deterministic**. LLM features stay optional and API-key-gated; they must not rewrite analysis results.
4. Run the gates you touch:
   - `pytest tests/ -q`
   - `python -m eval.run_eval --min 0.6` (analyzer)
   - `python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0` (generator)

## Where to read first

| File | Why |
|------|-----|
| [`docs/START-HERE.md`](docs/START-HERE.md) | Product status in plain language |
| [`docs/PARTWRITING-RULES.md`](docs/PARTWRITING-RULES.md) | Realizer rule spec |
| [`AGENTS.md`](AGENTS.md) | How automated agents are expected to work in this repo |

Open an issue if you’re unsure where a change belongs — happy to point you at the right chunk.
