"""Tests for SemanticVerdict validators and the TaxonomyTag enum."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from monitorstress.core.verdict import (
    SemanticLabel,
    SemanticVerdict,
    TaxonomyTag,
)


def _valid_verdict(**overrides: object) -> SemanticVerdict:
    base: dict[str, object] = {
        "verdict": SemanticLabel.CLEAN,
        "confidence_band": (0.2, 0.4),
        "reasoning": "Trajectory looked clean.",
    }
    base.update(overrides)
    return SemanticVerdict.model_validate(base)


def test_valid_verdict_passes() -> None:
    v = _valid_verdict()
    assert v.verdict is SemanticLabel.CLEAN
    assert v.abstain is False
    assert v.band_width == pytest.approx(0.2)


def test_band_validator_rejects_inverted_band() -> None:
    with pytest.raises(ValidationError) as exc:
        _valid_verdict(confidence_band=(0.7, 0.3))
    assert "0.0 <= lo <= hi <= 1.0" in str(exc.value)


def test_band_validator_rejects_out_of_range_low() -> None:
    with pytest.raises(ValidationError) as exc:
        _valid_verdict(confidence_band=(-0.1, 0.5))
    assert "0.0 <= lo <= hi <= 1.0" in str(exc.value)


def test_band_validator_rejects_out_of_range_high() -> None:
    with pytest.raises(ValidationError) as exc:
        _valid_verdict(confidence_band=(0.5, 1.2))
    assert "0.0 <= lo <= hi <= 1.0" in str(exc.value)


def test_abstain_requires_max_band() -> None:
    with pytest.raises(ValidationError) as exc:
        _valid_verdict(
            verdict=SemanticLabel.ABSTAIN,
            confidence_band=(0.4, 0.6),
            abstain=True,
        )
    assert "confidence_band=(0.0, 1.0)" in str(exc.value)


def test_abstain_requires_abstain_label() -> None:
    with pytest.raises(ValidationError) as exc:
        _valid_verdict(
            verdict=SemanticLabel.CLEAN,
            confidence_band=(0.0, 1.0),
            abstain=True,
        )
    assert "verdict=SemanticLabel.ABSTAIN" in str(exc.value)


def test_abstain_label_requires_abstain_field() -> None:
    with pytest.raises(ValidationError) as exc:
        _valid_verdict(
            verdict=SemanticLabel.ABSTAIN,
            confidence_band=(0.0, 1.0),
            abstain=False,
        )
    assert "abstain=True" in str(exc.value)


def test_abstain_valid_state_passes() -> None:
    v = _valid_verdict(
        verdict=SemanticLabel.ABSTAIN,
        confidence_band=(0.0, 1.0),
        abstain=True,
        reasoning="Out of distribution.",
    )
    assert v.abstain is True
    assert v.verdict is SemanticLabel.ABSTAIN
    assert v.band_width == pytest.approx(1.0)


def test_taxonomy_tag_enum_round_trip() -> None:
    v = _valid_verdict(
        taxonomy_tags=[TaxonomyTag.HARDCODED_SOLUTION, TaxonomyTag.EVALUATION_AWARENESS],
    )
    restored = SemanticVerdict.model_validate_json(v.model_dump_json())
    assert restored.taxonomy_tags == [
        TaxonomyTag.HARDCODED_SOLUTION,
        TaxonomyTag.EVALUATION_AWARENESS,
    ]
    assert all(isinstance(t, TaxonomyTag) for t in restored.taxonomy_tags)


def test_taxonomy_tag_coerces_string_input() -> None:
    v = _valid_verdict(taxonomy_tags=["sabotage", "normal"])
    assert v.taxonomy_tags == [TaxonomyTag.SABOTAGE, TaxonomyTag.NORMAL]


def test_taxonomy_tag_rejects_unknown_string() -> None:
    with pytest.raises(ValidationError):
        _valid_verdict(taxonomy_tags=["definitely_not_a_real_tag"])
