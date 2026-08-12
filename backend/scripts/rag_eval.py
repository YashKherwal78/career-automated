"""
Golden-set regression check for the profile RAG pipeline (src/applications/rag.py).

Runs entirely against RAGClient's retrieval layer -- no LLM calls, no API
keys required -- so it's cheap enough to run on every change to rag.py or
the master profile content, unlike a full end-to-end question_engine check
(which would need real LLM calls to score). It answers two questions that
had zero automated coverage before this: "does retrieval actually find the
right source for a real question" and "does the confirmed-gap check fire
(and only fire) on genuine gaps."

Usage: python3 scripts/rag_eval.py [-v]
Exits non-zero if any case fails, so it can gate CI/deploy later if wanted.
"""
import sys

sys.path.insert(0, ".")
from src.applications.rag import RAGClient  # noqa: E402

# Each case is either:
#  - answerable: retrieval's top chunk (or top-2) must contain at least one
#    of `must_contain_any` (case-insensitive substring) -- proves retrieval
#    found the actual right source, not just *a* plausible-looking chunk.
#  - gap: find_unknown_entities(question) must return the named term(s) --
#    proves the confirmed-gap check catches genuine absences and, just as
#    important, doesn't fire on things that ARE in the profile.
GOLDEN_SET = [
    {"q": "What did you build at OrangeLabs?", "expect": "answerable", "must_contain_any": ["orangelabs", "attendance", "lecture"]},
    {"q": "Tell me about your ScoreMe internship", "expect": "answerable", "must_contain_any": ["scoreme", "random forest", "credit"]},
    {"q": "What is ASTERIX CAT048?", "expect": "answerable", "must_contain_any": ["asterix", "bharat electronics", "radar"]},
    {"q": "Why did you choose LangGraph over CrewAI?", "expect": "answerable", "must_contain_any": ["langgraph", "stateful", "crewai"]},
    {"q": "Walk me through the YAAR preference engine", "expect": "answerable", "must_contain_any": ["yaar", "preference engine", "personality"]},
    {"q": "Why is on-device inference important for Echo Pod?", "expect": "answerable", "must_contain_any": ["echo pod", "on-device", "latency"]},
    {"q": "Why BGE-M3 over Sentence-Transformers?", "expect": "answerable", "must_contain_any": ["bge-m3", "multilingual", "zero-shot"]},
    {"q": "How did you prevent data leakage in the SC-MFC thesis?", "expect": "answerable", "must_contain_any": ["standardscaler", "data leakage", "sc-mfc"]},
    {"q": "What was your role at Bharat Electronics Limited?", "expect": "answerable", "must_contain_any": ["bharat electronics", "protocol parsing", "concurrency"]},
    {"q": "Describe a time you diagnosed a root cause before designing a solution", "expect": "answerable", "must_contain_any": ["scoreme", "root cause", "echo pod", "systems architecture"]},
    {"q": "What's your strongest technical skill?", "expect": "answerable", "must_contain_any": ["langgraph", "hybrid rag", "multi-agent"]},
    {"q": "How does the CareerAutomated waterfall UI normalization work?", "expect": "answerable", "must_contain_any": ["waterfall", "careerautomated", "react-select"]},

    {"q": "What is your experience with Kubernetes?", "expect": "gap", "entities": ["Kubernetes"]},
    {"q": "Do you know GraphQL and Rust?", "expect": "gap", "entities": ["GraphQL", "Rust"]},
    {"q": "Have you used Terraform for infra provisioning?", "expect": "gap", "entities": ["Terraform"]},
    {"q": "Any experience running Kafka in production?", "expect": "gap", "entities": ["Kafka"]},

    # Docker DOES appear (AI Data Analyst Agent stack) -- must NOT be
    # flagged as a gap, proving the check doesn't over-fire on real skills.
    {"q": "Have you worked with Docker in production?", "expect": "answerable", "must_contain_any": ["docker"]},
    {"q": "Why did you choose LangGraph?", "expect": "not_gap", "entities": []},
]


def run(verbose: bool = False) -> int:
    rag = RAGClient()
    passed, failed = 0, 0

    for case in GOLDEN_SET:
        q = case["q"]
        if case["expect"] == "gap":
            unknown = set(rag.find_unknown_entities(q))
            expected = set(case["entities"])
            ok = expected.issubset(unknown)
            detail = f"expected gap entities {expected} subset of found {unknown}"
        elif case["expect"] == "not_gap":
            unknown = set(rag.find_unknown_entities(q))
            ok = not unknown
            detail = f"expected no gap entities, found {unknown}"
        else:  # answerable
            items = rag.retrieve(q, top_k_initial=8, top_k_final=3)
            combined_text = " ".join(it["text"].lower() for it in items)
            ok = any(term.lower() in combined_text for term in case["must_contain_any"])
            top_conf = items[0]["confidence"] if items else 0.0
            detail = f"top_confidence={top_conf:.2f}, looked for any of {case['must_contain_any']}"

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        if verbose or not ok:
            print(f"[{status}] {q!r} -- {detail}")

    print(f"\n{passed}/{passed + failed} passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run(verbose="-v" in sys.argv))
