"""Shared Mem0 client and helpers."""
import os
import time
from typing import Any

from mem0 import MemoryClient

_client = None


def get_client() -> MemoryClient:
    """Return a singleton Mem0 client. Reads MEM0_API_KEY from environment."""
    global _client
    if _client is None:
        api_key = os.environ.get("MEM0_API_KEY")
        if not api_key:
            raise RuntimeError("MEM0_API_KEY not set in environment")
        _client = MemoryClient(api_key=api_key)
    return _client


def clean_user(
    user_id: str,
    run_ids: list[str] | None = None,
    verification_queries: list[str] | None = None,
    max_verify_attempts: int = 3,
) -> None:
    """Delete test-scoped memories and fail if stale memories still surface."""
    client = get_client()
    client.delete_all(user_id=user_id)

    for run_id in run_ids or []:
        client.delete_all(user_id=user_id, run_id=run_id)

    stale = []
    for _ in range(max_verify_attempts):
        stale = []
        for query in verification_queries or []:
            results = search_memories(query, filters={"user_id": user_id}, threshold=0.0)
            stale.extend(results)

        if not stale:
            return

        seen_ids = set()
        for result in stale:
            if not isinstance(result, dict):
                continue
            memory_id = result.get("id")
            if memory_id and memory_id not in seen_ids:
                client.delete(memory_id)
                seen_ids.add(memory_id)

        time.sleep(2)

    stale_texts = [memory_text(item) for item in stale]
    raise RuntimeError(f"Cleanup failed for {user_id}; stale memories remain: {stale_texts}")


def extract_results(response: Any) -> list:
    """Return the memory list from current and older Mem0 response shapes."""
    if response is None:
        return []
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        results = response.get("results", [])
        return results if isinstance(results, list) else []
    return []


def search_memories(query: str, **kwargs) -> list:
    """Search Mem0 and normalize the Platform response to a list of memories."""
    return extract_results(get_client().search(query, **kwargs))


def memory_text(memory: Any) -> str:
    """Return memory text from a result object without assuming exact shape."""
    if isinstance(memory, dict):
        return str(memory.get("memory", ""))
    return str(memory)


def rank_containing(results: list, *needles: str) -> int | None:
    """Return the 1-based rank of the first result containing all needles."""
    lowered_needles = [needle.lower() for needle in needles]
    for rank, result in enumerate(results, start=1):
        text = memory_text(result).lower()
        if all(needle in text for needle in lowered_needles):
            return rank
    return None


def wait_for_search(
    query: str,
    timeout_s: float = 30.0,
    interval_s: float = 2.0,
    contains: str | None = None,
    **kwargs,
) -> list:
    """Poll search until memories are visible, optionally requiring a text match."""
    deadline = time.monotonic() + timeout_s
    last_results = []

    while True:
        last_results = search_memories(query, **kwargs)
        matched = bool(last_results)
        if contains is not None:
            needle = contains.lower()
            matched = any(needle in memory_text(item).lower() for item in last_results)
        if matched or time.monotonic() >= deadline:
            return last_results
        time.sleep(interval_s)


def make_result(test_name: str, status: str, findings: list, raw=None) -> dict:
    """Standard result shape returned by each test."""
    return {
        "test":     test_name,
        "status":   status,  # PASS | FAIL | PARTIAL | INCONCLUSIVE
        "findings": findings,
        "raw":      raw or {},
    }


# Per-test user IDs to keep memories isolated
USER_IDS = {
    "test_01": "mem0_eval_01_cross_session",
    "test_02": "mem0_eval_02_score_calibration",
    "test_03": "mem0_eval_03_name_variation",
    "test_04": "mem0_eval_04_ambiguity",
    "test_05": "mem0_eval_05_alias",
    "test_06": "mem0_eval_06_conflict",
    "test_07": "mem0_eval_07_staleness",
}
