"""
Generate -> critique reflection loop for outreach email drafting, as a
LangGraph StateGraph.

Ports the retry loop previously inlined in OutreachEngine.run_daily_batch()
(draft an email, run it through EmailCritic, retry up to max_attempts if it
fails) into an explicit graph -- this is the one place in the codebase where
a runtime outcome (did the critic pass or fail?) actually decides what
happens next, which is what LangGraph's conditional edges are for. Every
other LLM call in this codebase is a fixed, single-purpose completion with
no such branching, which is why nothing else here has been converted.

Node functions read `engine` (an OutreachEngine) and `critic` (an
EmailCritic) out of `config["configurable"]` rather than closing over them,
so the graph's topology can be compiled ONCE as a process-lifetime
singleton (get_compiled_graph()) independent of which OutreachEngine/
EmailCritic instance a given call uses. This matters because
run_batch.py's run_daily_outreach() calls run_daily_batch() up to 8x/day
(once per candidate Excel file) from scheduler.py's long-running process --
compiling a fresh graph per call or per lead would be wasted structural
validation work repeated for the life of a process that can run for weeks.
"""
from __future__ import annotations

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from src.system.logger import setup_logger

logger = setup_logger("email_generation_graph")


class EmailGenState(TypedDict):
    recruiter_name: str
    company: str
    role: str
    notes: str
    domain: str
    project: str
    intel: dict
    email: str
    subject: str
    body: str
    critic_result: dict
    attempt: int
    max_attempts: int
    passed: bool


def _generate_node(state: EmailGenState, config: RunnableConfig) -> dict:
    engine = config["configurable"]["engine"]
    subject, body = engine.generate_email(
        state["recruiter_name"], state["company"], state["role"], state["notes"],
        state["domain"], state["project"], state["intel"], email=state["email"],
    )
    # Attempt counted here, not in _critique_node -- the original loop's
    # `if not body: continue` still advances `for attempt in range(3)`, so
    # an empty-body generation failure must consume the same budget a
    # critic FAIL does. Counting it only on entry to critique would let
    # empty-body retries loop for free.
    return {"subject": subject, "body": body, "attempt": state["attempt"] + 1}


def _critique_node(state: EmailGenState, config: RunnableConfig) -> dict:
    critic = config["configurable"]["critic"]
    critic_result = critic.evaluate(state["body"], state["company"], state["project"], state["domain"])
    passed = critic_result.get("status") == "PASS"
    if not passed:
        logger.info(f"Critic Rejected Attempt {state['attempt']}: {critic_result.get('reason')}")
    return {"critic_result": critic_result, "passed": passed}


def _route_after_generate(state: EmailGenState) -> str:
    if not state["body"]:
        # Mirrors the original `if not body: continue` -- skip critique
        # entirely on an empty body, same as the plain loop did.
        return "generate" if state["attempt"] < state["max_attempts"] else "end"
    return "critique"


def _route_after_critique(state: EmailGenState) -> str:
    if state["passed"] or state["attempt"] >= state["max_attempts"]:
        return "end"
    return "generate"


_compiled_graph = None


def get_compiled_graph():
    """Process-lifetime singleton -- see module docstring for why this is
    compiled once rather than per run_daily_batch() call or per lead."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = StateGraph(EmailGenState)
        graph.add_node("generate", _generate_node)
        graph.add_node("critique", _critique_node)
        graph.set_entry_point("generate")
        graph.add_conditional_edges("generate", _route_after_generate, {"generate": "generate", "critique": "critique", "end": END})
        graph.add_conditional_edges("critique", _route_after_critique, {"generate": "generate", "end": END})
        _compiled_graph = graph.compile()
    return _compiled_graph


def run_generation_loop(
    engine, critic, recruiter_name: str, company: str, role: str, notes: str,
    domain: str, project: str, intel: dict, email: str, max_attempts: int = 3,
) -> tuple[str, str, dict, bool]:
    """Convenience wrapper matching the original loop's call shape --
    returns (subject, body, critic_result, critic_passed)."""
    initial_state: EmailGenState = {
        "recruiter_name": recruiter_name, "company": company, "role": role, "notes": notes,
        "domain": domain, "project": project, "intel": intel, "email": email,
        "subject": "", "body": "", "critic_result": {}, "attempt": 0,
        "max_attempts": max_attempts, "passed": False,
    }
    result = get_compiled_graph().invoke(
        initial_state, config={"configurable": {"engine": engine, "critic": critic}}
    )
    return result["subject"], result["body"], result["critic_result"], result["passed"]
