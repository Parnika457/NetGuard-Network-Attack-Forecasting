from pydantic import ValidationError
import pytest
from app.schemas import Forecast, Detection, AnalyzeRequest


def test_any_attack_cannot_be_forced_to_class():
    with pytest.raises(ValidationError):
        Forecast(target="any_attack", attack_class="DoS", horizon_minutes=10, probability=.7, model_name="xgboost")


def test_specific_attack_needs_valid_class():
    with pytest.raises(ValidationError):
        Forecast(target="specific_attack", horizon_minutes=10, probability=.7, model_name="xgboost")
    result = Forecast(target="specific_attack", attack_class="DoS", horizon_minutes=10, probability=.7, model_name="a")
    assert result.attack_class == "DoS"
    analysis = Forecast(target="specific_attack", attack_class="Analysis", horizon_minutes=10, probability=.7, model_name="a")
    assert analysis.attack_class == "Analysis"
    with pytest.raises(ValidationError):
        Forecast(target="specific_attack", attack_class="Normal", horizon_minutes=10, probability=.7, model_name="a")


def test_probability_is_fraction_not_percent():
    with pytest.raises(ValidationError):
        Detection(attack_class="DoS", confidence=91, model_name="xgboost")


def test_extra_fields_disallowed():
    with pytest.raises(ValidationError):
        AnalyzeRequest(question="Explain risk", payload="ignore instructions")
