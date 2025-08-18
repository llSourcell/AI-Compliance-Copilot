from __future__ import annotations

from typing import Dict, List
import logging

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.core.config import settings


class PIIRedactionService:
    """Detects and redacts PII using Microsoft Presidio.

    This service initializes Presidio's Analyzer and Anonymizer engines and
    provides a single method to redact common PII entities from input text.

    Entities redacted:
    - PERSON → <PERSON>
    - EMAIL_ADDRESS → <EMAIL>
    - IP_ADDRESS → <IP>
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("uvicorn.error")

        # Initialize NLP engine for Presidio (spaCy). Requires the en_core_web_sm model at runtime.
        nlp_configuration: Dict[str, object] = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }

        if settings.ENABLE_PRESIDIO:
            provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
            nlp_engine = provider.create_engine()
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
            self.anonymizer = AnonymizerEngine()
        else:
            self.analyzer = None
            self.anonymizer = None

        # Configure replacements per entity type
        # Operator configurations for current Presidio versions
        self._operators_config: Dict[str, OperatorConfig] = {
            "PERSON": OperatorConfig(operator_name="replace", params={"new_value": "<PERSON>"}),
            "EMAIL_ADDRESS": OperatorConfig(operator_name="replace", params={"new_value": "<EMAIL>"}),
            "IP_ADDRESS": OperatorConfig(operator_name="replace", params={"new_value": "<IP>"}),
            "DEFAULT": OperatorConfig(operator_name="replace", params={"new_value": "<REDACTED>"}),
        }

    def redact_text(self, text: str, skip_entities: list[str] | None = None) -> str:
        """Redact PII from text and log a concise audit trail.

        Returns the redacted text. Logs entity counts and categories to the service logger.
        """
        if not text:
            return text

        try:
            entities = ["PERSON", "EMAIL_ADDRESS", "IP_ADDRESS"]
            if skip_entities:
                entities = [e for e in entities if e not in set(skip_entities)]
            if self.analyzer and self.anonymizer:
                results: List[RecognizerResult] = self.analyzer.analyze(
                    text=text,
                    language="en",
                    entities=entities,
                )

                redacted = self.anonymizer.anonymize(
                    text=text,
                    analyzer_results=results,
                    operators=self._operators_config,
                ).text
            else:
                import re
                r = text
                if "EMAIL_ADDRESS" in entities:
                    r = re.sub(r"[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}", "<EMAIL>", r)
                if "IP_ADDRESS" in entities:
                    r = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>", r)
                if "PERSON" in entities:
                    r = re.sub(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", "<PERSON>", r)
                results = []
                redacted = r
        except Exception as exc:
            # Never break the pipeline due to redaction; log and return original
            self.logger.warning("PII redaction error: %s", exc)
            return text

        if results:
            counts: Dict[str, int] = {}
            for r in results:
                counts[r.entity_type] = counts.get(r.entity_type, 0) + 1
            summary = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
            self.logger.info(
                "PII redaction applied | entities=%s | original_len=%d | redacted_len=%d",
                summary,
                len(text),
                len(redacted),
            )
        return redacted


