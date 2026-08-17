"""Audit record.

ESMA Guideline 12 (paras 109-112) requires the firm to record the client
information collected and how it was used and interpreted to define the client's
risk profile, the instruments recommended, the suitability report, any change to
the client's profile, and any adaptation of sustainability preferences together
with the reasons for it - in a form that lets failures such as mis-selling be
detected after the event.

The record written here is a single append-only JSON line per assessment. It
carries the configuration versions and a digest of the answers, so a past
decision can be re-run against the configuration that produced it (GL8 para 90
on algorithm change management).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from .models import Outcome


def build_record(
    outcome: Outcome,
    answers: dict[str, Any],
    adviser_ref: str | None = None,
    report_markdown: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": "suitability_assessment",
        "record_version": "1.0.0",
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "client_ref": outcome.client_ref,
        "adviser_ref": adviser_ref,
        "config_versions": outcome.config_versions,
        "answers": answers,
        "answers_digest": outcome.answers_digest,
        "assessment": outcome.to_dict(),
        "suitability_report_provided": report_markdown is not None,
    }
    if report_markdown is not None:
        record["suitability_report_markdown"] = report_markdown
    if extra:
        record["additional"] = extra
    return record


def append(record: dict[str, Any], path: str = "audit/suitability-log.jsonl") -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return path


def profile_change_record(
    client_ref: str,
    prior_band: int,
    new_band: int,
    reason: str,
    changed_answers: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    """A change to a client's profile (ESMA GL5 para 59, GL12 para 111).

    The client must be told when new information changes their profile, in
    either direction. Where the change makes the profile riskier shortly before
    a recommendation, control CC12 will fire on the next assessment.
    """
    return {
        "record_type": "profile_change",
        "record_version": "1.0.0",
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "client_ref": client_ref,
        "prior_band": prior_band,
        "new_band": new_band,
        "direction": "riskier" if new_band > prior_band else "more conservative",
        "reason": reason,
        "changed_answers": changed_answers,
        "actor": actor,
        "client_informed": True,
    }


def sustainability_adaptation_record(
    client_ref: str,
    original_preferences: dict[str, Any],
    adapted_preferences: dict[str, Any],
    explanation_given: str,
    client_decision: str,
    actor: str,
) -> dict[str, Any]:
    """Art. 54(10) DR 2017/565 and ESMA GL8 paras 82-83.

    An adaptation applies to the single piece of advice, not to the client's
    general profile, and both the firm's explanation and the client's decision
    must be recorded.
    """
    return {
        "record_type": "sustainability_preference_adaptation",
        "record_version": "1.0.0",
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "client_ref": client_ref,
        "scope": "this_recommendation_only",
        "original_preferences": original_preferences,
        "adapted_preferences": adapted_preferences,
        "explanation_given": explanation_given,
        "client_decision": client_decision,
        "actor": actor,
    }
