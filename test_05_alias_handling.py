"""
Test 5 — Alias and Name-Change Handling

Evaluates whether Mem0's implicit entity linking connects two names referring to
the same person.
"""
from client import clean_user, get_client, make_result, rank_containing, search_memories, wait_for_search, USER_IDS

TEST_NAME = "05_alias_handling"
USER_ID = USER_IDS["test_05"]


def run() -> dict:
    client = get_client()
    clean_user(
        USER_ID,
        verification_queries=["Vic Harlow", "Victor Harlow"],
    )

    # Store alias relationship + ruling under canonical name
    client.add([
        {"role": "user",      "content": "Note entity relationship."},
        {"role": "assistant", "content": "Vic Harlow is also known as Victor Harlow."},
    ], user_id=USER_ID, infer=True)
    wait_for_search(
        "Vic Harlow Victor Harlow",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="Harlow",
    )

    client.add([
        {"role": "user",      "content": "Screen Victor Harlow."},
        {"role": "assistant", "content": "Victor Harlow is BLOCKED — arms trafficking."},
    ], user_id=USER_ID, infer=True)
    wait_for_search(
        "Victor Harlow blocked",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="block",
    )

    # Search by alias and canonical
    results_alias = search_memories("Vic Harlow ruling", filters={"user_id": USER_ID}, threshold=0.0)
    results_canon = search_memories("Victor Harlow ruling", filters={"user_id": USER_ID}, threshold=0.0)

    findings = []
    findings.append(f"Search 'Vic Harlow ruling':    n={len(results_alias)}, first_score={(results_alias[0].get('score', 0) if results_alias else 0):.3f}")
    findings.append(f"Search 'Victor Harlow ruling': n={len(results_canon)}, first_score={(results_canon[0].get('score', 0) if results_canon else 0):.3f}")

    # Does the BLOCK ruling appear under both queries, and where does it rank?
    alias_block_rank = rank_containing(results_alias, "block")
    canon_block_rank = rank_containing(results_canon, "block")

    findings.append(f"BLOCK ruling rank via alias query:    {alias_block_rank if alias_block_rank is not None else 'not returned'}")
    findings.append(f"BLOCK ruling rank via canonical query: {canon_block_rank if canon_block_rank is not None else 'not returned'}")

    if alias_block_rank == 1 and canon_block_rank == 1:
        status = "PASS"
        findings.append("BLOCK ruling ranked first under both alias and canonical queries.")
    elif canon_block_rank is not None and alias_block_rank is None:
        status = "FAIL"
        findings.append("Implicit entity linking did not surface ruling for alias.")
    else:
        status = "PARTIAL"
        findings.append("BLOCK ruling surfaced, but ranking was weaker or incomplete.")

    return make_result(TEST_NAME, status, findings,
                      raw={"alias_results": results_alias, "canon_results": results_canon})


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
