import os

from src.services.pii_service import PIIRedactionService


def test_redact_text_regex_fallback_person_email_ip():
    # Force regex path (no Presidio reliance)
    os.environ["ENABLE_PRESIDIO"] = "false"
    service = PIIRedactionService()

    text = "John Doe emailed john.doe@example.com from 192.168.0.1 yesterday."
    redacted = service.redact_text(text)

    assert "<EMAIL>" in redacted
    assert "<IP>" in redacted
    # Simple PERSON pattern replaces first/last name
    assert "<PERSON>" in redacted


def test_redact_text_skip_person():
    os.environ["ENABLE_PRESIDIO"] = "false"
    service = PIIRedactionService()

    text = "Alice Smith wrote to bob@example.com"
    redacted = service.redact_text(text, skip_entities=["PERSON"])  # allow names

    # Email must be redacted, names kept
    assert "<EMAIL>" in redacted
    assert "Alice Smith" in redacted

