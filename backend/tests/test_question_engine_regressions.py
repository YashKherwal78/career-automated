"""
Regression tests for auto-apply answer correctness.

Every case here corresponds to a bug found by running the handlers against a
real live posting during the 2026-08-01 session. Two of them (work
authorization, race) were producing factually false answers that would have
been submitted to a real employer, so they are worth pinning down.

Run:  ./venv/bin/python -m pytest tests/test_question_engine_regressions.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))

from src.applications.question_engine import QuestionEngine, ResponseNormalizer
from src.applications.question_classifier import QuestionClassifier as GateClassifier
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter


def engine(location="Remote"):
    return QuestionEngine(ProfileManager(), RAGClient(), LLMRouter(), "",
                          "Software Engineer", location)


def ask(eng, question, field_type="text", placeholder="", options=None):
    meta = {}
    answer = eng.answer(question=question, field_type=field_type, placeholder=placeholder,
                        options=options or [], label_text=question, required=True, dom_meta=meta)
    return answer, meta.get("confidence")


# --- work authorization must be country-aware -------------------------------
# Was hardcoded "Yes" in the binary-dropdown fast path, so a US posting got
# "Are you authorized to work in the U.S.?" -> Yes while simultaneously
# answering "Will you require sponsorship?" -> Yes. Contradictory, and false.

@pytest.mark.parametrize("location,question,expected", [
    ("Torrance, CA", "Are you authorized to work in the U.S.?", "No"),
    ("Torrance, CA", "Are you legally authorized to work in the United States?", "No"),
    ("Remote", "Are you authorized to work in the UK?", "No"),
    ("Bengaluru, India", "Are you authorized to work in India?", "Yes"),
    # No country named anywhere in the question -> fall back to the job's location.
    ("Bengaluru, India", "Are you authorized to work in this location?", "Yes"),
])
def test_work_authorization_is_country_aware(location, question, expected):
    answer, _ = ask(engine(location), question, "dropdown", options=["Yes", "No"])
    assert answer == expected


@pytest.mark.parametrize("location,question,expected", [
    ("Torrance, CA", "Will you require sponsorship now or in the future?", "Yes"),
    ("Bengaluru, India", "Will you require visa sponsorship?", "No"),
])
def test_sponsorship_answer_matches_location(location, question, expected):
    answer, _ = ask(engine(location), question, "dropdown", options=["Yes", "No"])
    assert answer == expected


# --- EEO decline must never normalise to a substantive category -------------
# "Decline to Self Identify" (profile) vs "Decline to self-identify" (form)
# differ only by a hyphen. The exact match missed, and the fuzzy fallback
# picked the FIRST option — "Hispanic or Latino".

RACE_OPTIONS = [
    "Hispanic or Latino",
    "White (Not Hispanic or Latino)",
    "Black or African American (Not Hispanic or Latino)",
    "Asian (Not Hispanic or Latino)",
    "Decline to self-identify",
]


def test_race_decline_maps_to_decline_option():
    result = ResponseNormalizer.normalize(
        "Decline to Self Identify", "LEGAL", "dropdown", "", "Race", RACE_OPTIONS)
    assert "decline" in str(result).lower()


@pytest.mark.parametrize("decline_option", [
    "I don't wish to answer",
    "I prefer not to say",
    "I do not want to answer",
    "Decline to self-identify",
])
def test_decline_intent_matches_any_phrasing(decline_option):
    options = ["Hispanic or Latino", "Asian (Not Hispanic or Latino)", decline_option]
    result = ResponseNormalizer.normalize(
        "Decline to Self Identify", "LEGAL", "dropdown", "", "Race", options)
    assert result == decline_option


# --- name fields resolve from the profile instead of escalating -------------
# Ashby asks for these as custom questions, not system fields.

@pytest.mark.parametrize("question,expected", [
    ("Legal Name (First Name Last Name)", "Yash Kherwal"),
    ("Preferred Name", "Yash"),
    ("Full Name", "Yash Kherwal"),
])
def test_name_variants_resolve(question, expected):
    answer, confidence = ask(engine(), question)
    assert answer == expected
    assert confidence == 100


def test_name_questions_are_not_escalated_by_the_gate():
    assert GateClassifier.classify("Preferred Name", "input") == "DETERMINISTIC"
    assert GateClassifier.classify("Legal Name (First Name Last Name)", "input") == "DETERMINISTIC"


# --- date widgets need a date, not the word "Immediate" ---------------------

def test_start_date_returns_a_date_for_a_date_picker():
    answer, _ = ask(engine(), "What is the earliest date you are available to start this position?",
                    placeholder="Pick date...")
    assert answer[:2] == "20" and answer.count("-") == 2, answer


def test_start_date_stays_textual_for_a_plain_text_field():
    answer, _ = ask(engine(), "When can you start?", placeholder="")
    assert answer == "Immediate"


# --- escalation boundary ----------------------------------------------------
# Grounded experience questions are answerable from RAG; salary and
# motivation questions must still escalate.

def test_grounded_project_question_is_answerable():
    assert GateClassifier.classify(
        "Share a project you're especially proud of", "textarea") == "DETERMINISTIC"


@pytest.mark.parametrize("question", [
    "What are your salary expectations?",
    "Why are you interested in this role?",
    "Please attach a cover letter",
])
def test_ambiguous_questions_still_escalate(question):
    assert GateClassifier.classify(question, "textarea") == "ESCALATE"
