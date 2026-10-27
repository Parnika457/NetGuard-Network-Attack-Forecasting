from pydantic import ValidationError
import pytest
from app.schemas import AnalyzeRequest, ConditionalOnset, HorizonForecast

BUNDLE = {"h5": .1, "h10": .25, "h15": .35, "model_name": "stacked_lstm_v2"}
FAMILY = {"family_if_onset": "DOS_DDOS", "family_probability_if_onset": .75,
          "conditional_eta_minutes": 12.5, "p_onset_within_15": .2,
          "conditioning_horizon_minutes": 15, "model_name": "competing_risk_lstm"}


def test_preserves_separate_onset_and_conditional_contracts():
    req = AnalyzeRequest(question="Explain the forecast", forecast_bundle=BUNDLE, family_eta=FAMILY)
    assert req.forecast_bundle.h10 == .25
    assert req.family_eta.family_probability_if_onset == .75
    assert req.family_eta.p_onset_within_15 == .2
    assert req.family_eta.conditional_eta_minutes == 12.5


def test_rejects_invalid_horizon_order():
    with pytest.raises(ValidationError):
        HorizonForecast(h5=.5, h10=.1, h15=.8, model_name="stacked_lstm_v2")


def test_rejects_unsupported_future_family():
    with pytest.raises(ValidationError):
        ConditionalOnset(**{**FAMILY, "family_if_onset": "DoS"})


def test_rejects_family_without_onset_forecast():
    with pytest.raises(ValidationError):
        AnalyzeRequest(question="Explain estimate", family_eta=FAMILY)


def test_rejects_unconditional_eta_language_contract():
    with pytest.raises(ValidationError):
        ConditionalOnset(**{**FAMILY, "conditional_eta_minutes": 23})


def test_legacy_any_attack_request_still_accepted():
    req = AnalyzeRequest(question="Explain", forecast={"target": "any_attack", "probability": .328, "horizon_minutes": 10, "model_name": "stacked_lstm_v2"})
    assert req.forecast.probability == .328
