from src.ingestion.job_lead import JobLead


def test_is_valid_true_when_required_fields_present():
    lead = JobLead(
        company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
        location=None, jd_excerpt=None, source="screenshot", source_ref="/tmp/shot.png",
    )
    assert lead.is_valid() is True


def test_is_valid_false_when_apply_link_missing():
    lead = JobLead(
        company="Acme", role="Backend Engineer", apply_link="",
        location=None, jd_excerpt=None, source="email", source_ref="msg-123",
    )
    assert lead.is_valid() is False
