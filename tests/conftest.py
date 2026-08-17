from __future__ import annotations

import copy
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from suitability.config import load_config  # noqa: E402
from suitability.models import ClientCase  # noqa: E402

EXAMPLES = os.path.join(ROOT, "examples", "clients")


@pytest.fixture(scope="session")
def cfg():
    return load_config(os.path.join(ROOT, "config"))


def _load(name: str) -> dict:
    with open(os.path.join(EXAMPLES, name), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture
def base_answers() -> dict:
    """A middle-of-the-road, fully answered, internally consistent client."""
    return copy.deepcopy(_load("04-sustainability-preferences.yaml")["answers"])


@pytest.fixture
def neutral_answers(base_answers) -> dict:
    """The same client, but sustainability-neutral, so that tests of the
    Art. 25(2) machinery are not perturbed by the Art. 2(7) filter."""
    answers = copy.deepcopy(base_answers)
    answers["F1"] = "no"
    for key in ("F2", "F3", "F4", "F5"):
        answers.pop(key, None)
    return answers


@pytest.fixture
def case_factory():
    def make(answers: dict, **kwargs) -> ClientCase:
        return ClientCase(
            client_ref=kwargs.pop("client_ref", "TEST-1"),
            answers=answers,
            assessed_at=kwargs.pop("assessed_at", "2026-03-01T00:00:00+00:00"),
            **kwargs,
        )

    return make


@pytest.fixture
def load_example():
    def load(name: str) -> ClientCase:
        raw = _load(name)
        members = [
            ClientCase(client_ref=m["client_ref"], answers=m["answers"], assessed_at=raw.get("assessed_at", ""))
            for m in raw.get("group_members", [])
        ]
        return ClientCase(
            client_ref=raw["client_ref"],
            answers=raw.get("answers", {}),
            assessed_at=raw.get("assessed_at", ""),
            adviser_ref=raw.get("adviser_ref"),
            previous_final_band=raw.get("previous_final_band"),
            profile_updated_days_ago=raw.get("profile_updated_days_ago"),
            group_members=members,
        )

    return load
