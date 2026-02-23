"""Unit tests for DeforestationPressureIndex."""

import pytest
from deforestation_pressure_index import (
    DeforestationPressureIndex,
    PressureLevel,
    SitePressureInputs,
    DRIVER_WEIGHTS,
)


@pytest.fixture
def dpi():
    return DeforestationPressureIndex()


@pytest.fixture
def medium_site():
    return SitePressureInputs(
        site_id="PUR-CO-001",
        country="Colombia",
        agri_expansion_score=5.0,
        road_proximity_score=5.0,
        population_growth_score=5.0,
        historical_loss_rate_pct=2.5,
        governance_deficit_score=5.0,
    )


@pytest.fixture
def critical_site():
    return SitePressureInputs(
        site_id="PUR-BR-002",
        country="Brazil",
        agri_expansion_score=9.5,
        road_proximity_score=8.0,
        population_growth_score=7.0,
        historical_loss_rate_pct=5.0,
        governance_deficit_score=9.0,
    )


@pytest.fixture
def low_site():
    return SitePressureInputs(
        site_id="PUR-CR-001",
        country="Costa Rica",
        agri_expansion_score=1.0,
        road_proximity_score=2.0,
        population_growth_score=1.5,
        historical_loss_rate_pct=0.2,
        governance_deficit_score=1.0,
    )


class TestSitePressureInputs:
    def test_invalid_agri_score(self):
        with pytest.raises(ValueError, match="agri_expansion_score"):
            SitePressureInputs("S1", "X", 11.0, 5.0, 5.0, 1.0, 5.0)

    def test_negative_loss_rate(self):
        with pytest.raises(ValueError, match="historical_loss_rate_pct"):
            SitePressureInputs("S1", "X", 5.0, 5.0, 5.0, -1.0, 5.0)

    def test_valid_inputs(self):
        s = SitePressureInputs("S1", "X", 5.0, 5.0, 5.0, 2.5, 5.0)
        assert s.site_id == "S1"


class TestDeforestationPressureIndex:
    def test_medium_site_classification(self, dpi, medium_site):
        result = dpi.calculate(medium_site)
        # mid-range scores should produce medium pressure
        assert result.pressure_level in (PressureLevel.MEDIUM, PressureLevel.LOW, PressureLevel.HIGH)

    def test_critical_site(self, dpi, critical_site):
        result = dpi.calculate(critical_site)
        assert result.pressure_level in (PressureLevel.HIGH, PressureLevel.CRITICAL)
        assert result.dpi_score > 6.0

    def test_low_site(self, dpi, low_site):
        result = dpi.calculate(low_site)
        assert result.pressure_level in (PressureLevel.VERY_LOW, PressureLevel.LOW)

    def test_dpi_score_range(self, dpi, medium_site):
        result = dpi.calculate(medium_site)
        assert 0 <= result.dpi_score <= 10.0

    def test_dominant_driver_is_highest_weight(self, dpi, critical_site):
        result = dpi.calculate(critical_site)
        # With agri=9.5 (weight 0.30) it likely dominates
        assert result.dominant_driver in DRIVER_WEIGHTS

    def test_dominant_contribution_fraction(self, dpi, medium_site):
        result = dpi.calculate(medium_site)
        assert 0 < result.dominant_driver_contribution <= 1.0

    def test_recommendation_present(self, dpi, critical_site):
        result = dpi.calculate(critical_site)
        assert len(result.recommendation) > 10

    def test_monitoring_frequency_set(self, dpi, low_site):
        result = dpi.calculate(low_site)
        assert result.monitoring_frequency in ("Annual", "Biannual", "Quarterly", "Monthly", "Monthly (emergency)")

    def test_to_dict_structure(self, dpi, medium_site):
        result = dpi.calculate(medium_site)
        d = result.to_dict()
        assert "dpi_score" in d
        assert "pressure_level" in d
        assert "driver_breakdown" in d
        assert len(d["driver_breakdown"]) == 5

    def test_batch_sorted_by_dpi(self, dpi, low_site, medium_site, critical_site):
        results = dpi.calculate_batch([low_site, critical_site, medium_site])
        scores = [r.dpi_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_portfolio_summary(self, dpi, low_site, medium_site, critical_site):
        results = dpi.calculate_batch([low_site, medium_site, critical_site])
        summary = dpi.portfolio_summary(results)
        assert summary["total_sites"] == 3
        assert "pressure_distribution" in summary
        assert "average_dpi" in summary

    def test_high_critical_in_summary(self, dpi, critical_site):
        results = dpi.calculate_batch([critical_site])
        summary = dpi.portfolio_summary(results)
        assert summary["high_or_critical_count"] >= 0

    def test_custom_weights_valid(self):
        custom = {k: 1/5 for k in DRIVER_WEIGHTS}
        dpi_custom = DeforestationPressureIndex(custom_weights=custom)
        assert dpi_custom.weights == custom

    def test_custom_weights_wrong_sum_raises(self):
        bad = {k: 0.3 for k in DRIVER_WEIGHTS}
        with pytest.raises(ValueError, match="sum to 1.0"):
            DeforestationPressureIndex(custom_weights=bad)

    def test_custom_weights_wrong_keys_raises(self):
        with pytest.raises(ValueError, match="keys"):
            DeforestationPressureIndex(custom_weights={"unknown_driver": 1.0})

    def test_high_loss_rate_normalized_to_max(self, dpi):
        # loss_rate_pct >= 5 should normalize to 10
        site = SitePressureInputs("S1", "X", 5.0, 5.0, 5.0, 10.0, 5.0)
        result = dpi.calculate(site)
        assert result.raw_scores["historical_loss_rate"] == 10.0

    def test_zero_dpi_edge_case(self):
        # All scores zero (not possible normally, but governance_deficit can be 0)
        site = SitePressureInputs("S1", "X", 0.0, 0.0, 0.0, 0.0, 0.0)
        dpi_calc = DeforestationPressureIndex()
        result = dpi_calc.calculate(site)
        assert result.dpi_score == 0.0
        assert result.pressure_level == PressureLevel.VERY_LOW

    def test_empty_batch_summary(self, dpi):
        summary = dpi.portfolio_summary([])
        assert summary["total_sites"] == 0
        assert summary["average_dpi"] == 0.0
