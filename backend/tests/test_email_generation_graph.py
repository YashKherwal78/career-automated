from unittest.mock import MagicMock

from src.outreach.email_generation_graph import run_generation_loop


def _fake_engine(bodies):
    """bodies: list of (subject, body) tuples returned on successive calls."""
    engine = MagicMock()
    engine.generate_email.side_effect = bodies
    return engine


def _fake_critic(results):
    """results: list of critic_result dicts returned on successive calls."""
    critic = MagicMock()
    critic.evaluate.side_effect = results
    return critic


def _call(engine, critic, max_attempts=3):
    return run_generation_loop(
        engine, critic, "Jane", "Acme", "Engineer", "", "Tech", "Project X",
        {}, "jane@acme.com", max_attempts=max_attempts,
    )


def test_pass_on_first_attempt_calls_generate_and_critique_once():
    engine = _fake_engine([("Subject", "Body one")])
    critic = _fake_critic([{"status": "PASS", "reason": "Passed."}])

    subject, body, critic_result, passed = _call(engine, critic)

    assert passed is True
    assert subject == "Subject"
    assert body == "Body one"
    assert critic_result["status"] == "PASS"
    assert engine.generate_email.call_count == 1
    assert critic.evaluate.call_count == 1


def test_retries_on_critic_fail_then_passes():
    engine = _fake_engine([("S1", "Body one"), ("S2", "Body two")])
    critic = _fake_critic([
        {"status": "FAIL", "reason": "too generic"},
        {"status": "PASS", "reason": "Passed."},
    ])

    subject, body, critic_result, passed = _call(engine, critic)

    assert passed is True
    assert subject == "S2"
    assert body == "Body two"
    assert engine.generate_email.call_count == 2
    assert critic.evaluate.call_count == 2


def test_retries_on_empty_body_without_calling_critic():
    engine = _fake_engine([("", ""), ("S2", "Body two")])
    critic = _fake_critic([{"status": "PASS", "reason": "Passed."}])

    subject, body, critic_result, passed = _call(engine, critic)

    assert passed is True
    assert body == "Body two"
    assert engine.generate_email.call_count == 2
    # Critic must never be called for the empty-body attempt -- matches the
    # original loop's `if not body: continue`, which skips evaluate()
    # entirely on an empty body.
    assert critic.evaluate.call_count == 1


def test_stops_after_max_attempts_exhausted_on_repeated_critic_fail():
    engine = _fake_engine([("S1", "B1"), ("S2", "B2"), ("S3", "B3")])
    critic = _fake_critic([
        {"status": "FAIL", "reason": "r1"},
        {"status": "FAIL", "reason": "r2"},
        {"status": "FAIL", "reason": "r3"},
    ])

    subject, body, critic_result, passed = _call(engine, critic, max_attempts=3)

    assert passed is False
    assert engine.generate_email.call_count == 3
    assert critic.evaluate.call_count == 3
    assert critic_result["reason"] == "r3"


def test_stops_after_max_attempts_exhausted_on_repeated_empty_body():
    engine = _fake_engine([("", ""), ("", ""), ("", "")])
    critic = _fake_critic([])

    subject, body, critic_result, passed = _call(engine, critic, max_attempts=3)

    assert passed is False
    assert body == ""
    assert engine.generate_email.call_count == 3
    assert critic.evaluate.call_count == 0


def test_mixed_empty_body_then_critic_fail_then_pass_counts_attempts_correctly():
    engine = _fake_engine([("", ""), ("S2", "B2"), ("S3", "B3")])
    critic = _fake_critic([
        {"status": "FAIL", "reason": "r2"},
        {"status": "PASS", "reason": "Passed."},
    ])

    subject, body, critic_result, passed = _call(engine, critic, max_attempts=3)

    assert passed is True
    assert body == "B3"
    # 3 generate calls total (empty-body attempt 1, fail attempt 2, pass
    # attempt 3) but only 2 critique calls -- attempt 1 never reaches the
    # critic. This is the case most likely to expose an attempt-counter
    # bug if it were incremented in the wrong node.
    assert engine.generate_email.call_count == 3
    assert critic.evaluate.call_count == 2
