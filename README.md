# Mem0 Evaluation Harness

Lightweight Python harness for evaluating Mem0 as a managed memory layer for AI agents.

This project uses a diligence-style screening scenario to test how Mem0 stores, retrieves, and ranks memories under realistic ambiguity. It is not intended to be a production screening system. The goal is to understand Mem0's behavior across persistence, retrieval quality, name variation, aliases, conflicts, and temporal context.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Mem0 API key to `.env`:

```bash
MEM0_API_KEY=your-api-key-here
```

Do not commit `.env`. It is ignored by `.gitignore`.

## Running Tests

Run an individual test:

```bash
.venv/bin/python test_01_cross_session.py
```

Run the full harness:

```bash
.venv/bin/python harness.py
```

The harness prints each result and writes `results.json`, which is ignored by git.

## Test Cases

The harness includes seven focused scenarios:

1. **Cross-Session Persistence**
2. **Score Calibration**
3. **Name Variation Retrieval**
4. **Multi-Entity Ambiguity**
5. **Alias and Name-Change Handling**
6. **Conflict Resolution**
7. **Staleness Handling**

Each test returns a structured result with a status, findings, and raw Mem0 output for inspection.

## Notes

- The harness compares Mem0 behavior across inferred and direct memory-writing modes.
- Tests use isolated user scopes and cleanup helpers to reduce cross-test contamination.
- Generated outputs and local credentials are ignored by git.
