"""
Test 3 — Name Variation Retrieval

Evaluates how Mem0's hybrid retrieval handles name variants when the canonical
form is stored.
"""
from client import clean_user, get_client, make_result, rank_containing, search_memories, wait_for_search

TEST_NAME = "03_name_variation"
DIRECT_USER_ID = "mem0_eval_03_name_variation_direct"
INFERRED_USER_ID = "mem0_eval_03_name_variation_inferred"

FACTS = [
    "Elena Vasquez is BLOCKED — financial fraud.",
    "Sarah Patel is CLEARED — no restricted-list match.",
]

QUERIES = [
    ("Elena Vasquez",  "exact"),
    ("E. Vasquez",     "first_initial"),
    ("Elena V.",       "last_initial"),
    ("Vasquez",        "last_only"),
    ("elena vasquez",  "lowercase"),
    ("ELENA VASQUEZ",  "uppercase"),
    ("Elena Vasqez",   "typo"),
    ("Sarah Patel",    "unrelated"),
    ("aaa bbb ccc",    "garbage"),
]

VARIANT_KINDS = [
    "exact",
    "first_initial",
    "last_initial",
    "last_only",
    "lowercase",
    "uppercase",
    "typo",
]


def score_signals(results: list) -> dict:
    """Summarize whether Mem0's exposed scoring signals contributed."""
    signals = {"semantic": False, "bm25": False, "entity": False}
    for result in results:
        if not isinstance(result, dict):
            continue
        breakdown = result.get("score_breakdown") or {}
        for key in signals:
            signals[key] = signals[key] or breakdown.get(key, 0) > 0
    return signals


def add_fact(client, fact: str, user_id: str, infer: bool) -> None:
    """Add the same fact in direct-import or inferred mode."""
    if infer:
        messages = [
            {"role": "user", "content": "Record screening decision."},
            {"role": "assistant", "content": fact},
        ]
    else:
        messages = [{"role": "user", "content": fact}]

    client.add(messages, user_id=user_id, infer=infer)


def run_mode(label: str, user_id: str, infer: bool) -> dict:
    client = get_client()
    clean_user(
        user_id,
        verification_queries=["Elena Vasquez", "Sarah Patel"],
    )

    for fact, wait_query, needle in [
        (FACTS[0], "Elena Vasquez", "Vasquez"),
        (FACTS[1], "Sarah Patel", "Patel"),
    ]:
        add_fact(client, fact, user_id=user_id, infer=infer)
        wait_for_search(
            wait_query,
            filters={"user_id": user_id},
            threshold=0.0,
            contains=needle,
        )

    findings = []
    raw = {}
    observed_signals = {"semantic": False, "bm25": False, "entity": False}

    for query, kind in QUERIES:
        results = search_memories(query, filters={"user_id": user_id}, threshold=0.0)
        top = results[0] if results else {}
        top_score = top.get("score", 0.0) if isinstance(top, dict) else 0.0
        top_memory = top.get("memory", "(none)") if isinstance(top, dict) else "(none)"
        target_rank = rank_containing(results, "Vasquez")
        query_signals = score_signals(results)
        for signal, present in query_signals.items():
            observed_signals[signal] = observed_signals[signal] or present

        raw[kind] = {
            "query": query,
            "target_rank": target_rank,
            "top_score": top_score,
            "top_memory": top_memory,
            "n_results": len(results),
            "signals": query_signals,
            "results": results,
        }
        rank_label = target_rank if target_rank is not None else "not returned"
        findings.append(
            f"  [{label}][{kind:15s}] '{query}' → target_rank={rank_label}, "
            f"top='{top_memory}' (score: {top_score:.3f}, n={len(results)})"
        )

    variant_ranks = {kind: raw[kind]["target_rank"] for kind in VARIANT_KINDS}
    top_ranked_variants = [kind for kind, rank in variant_ranks.items() if rank == 1]
    returned_variants = [kind for kind, rank in variant_ranks.items() if rank is not None]

    if len(top_ranked_variants) == len(VARIANT_KINDS):
        status = "PASS"
        summary = f"{label}: all name variants ranked Elena Vasquez first."
    elif len(returned_variants) == len(VARIANT_KINDS):
        status = "PARTIAL"
        summary = f"{label}: all name variants returned Elena Vasquez, but not always at rank 1."
    else:
        status = "FAIL"
        missing = sorted(set(VARIANT_KINDS) - set(returned_variants))
        summary = f"{label}: missing Elena Vasquez for variants: {missing}."

    return {
        "label": label,
        "status": status,
        "summary": summary,
        "findings": findings,
        "raw": raw,
        "signals": observed_signals,
    }


def run() -> dict:
    direct = run_mode("Direct Import", DIRECT_USER_ID, infer=False)
    inferred = run_mode("Inferred Memory", INFERRED_USER_ID, infer=True)

    statuses = {direct["status"], inferred["status"]}
    if statuses == {"PASS"}:
        status = "PASS"
    elif "FAIL" in statuses:
        status = "FAIL"
    else:
        status = "PARTIAL"

    direct_last_rank = direct["raw"]["last_only"]["target_rank"]
    inferred_last_rank = inferred["raw"]["last_only"]["target_rank"]
    if direct_last_rank == inferred_last_rank:
        comparison = f"Comparison: infer=True did not change last-name-only rank ({direct_last_rank})."
    else:
        comparison = (
            "Comparison: infer=True changed last-name-only rank "
            f"from {direct_last_rank} to {inferred_last_rank}."
        )

    findings = [
        direct["summary"],
        inferred["summary"],
        comparison,
        f"Direct Import scoring signals observed: {direct['signals']}",
        f"Inferred Memory scoring signals observed: {inferred['signals']}",
        *direct["findings"],
        *inferred["findings"],
    ]

    return make_result(
        TEST_NAME,
        status,
        findings,
        raw={
            "direct_import": {
                "status": direct["status"],
                "signals": direct["signals"],
                "results": direct["raw"],
            },
            "inferred": {
                "status": inferred["status"],
                "signals": inferred["signals"],
                "results": inferred["raw"],
            },
        },
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
