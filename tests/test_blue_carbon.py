"""
Unit tests for BlueCarbonCalculator and BlueCarbonPlot.
"""
import pytest
from blue_carbon import BlueCarbonCalculator, BlueCarbonPlot


@pytest.fixture
def mangrove_plot():
    return BlueCarbonPlot(
        plot_id="MNG-ID-001", ecosystem="mangrove", climate_zone="tropical",
        area_ha=50.0, restoration_year=2020, canopy_cover_pct=80.0, soil_depth_cm=100.0
    )

@pytest.fixture
def seagrass_plot():
    return BlueCarbonPlot(
        plot_id="SEA-TH-001", ecosystem="seagrass", climate_zone="tropical",
        area_ha=20.0, restoration_year=2021, canopy_cover_pct=65.0, soil_depth_cm=80.0
    )

@pytest.fixture
def calc_with_plots(mangrove_plot, seagrass_plot):
    calc = BlueCarbonCalculator()
    calc.add_plot(mangrove_plot)
    calc.add_plot(seagrass_plot)
    return calc


# --- BlueCarbonPlot validation ---

def test_invalid_ecosystem():
    with pytest.raises(ValueError, match="ecosystem"):
        BlueCarbonPlot("x", "coral", "tropical", 10.0, 2020)

def test_invalid_climate_zone():
    with pytest.raises(ValueError, match="climate_zone"):
        BlueCarbonPlot("x", "mangrove", "arctic", 10.0, 2020)

def test_invalid_area():
    with pytest.raises(ValueError, match="area_ha"):
        BlueCarbonPlot("x", "mangrove", "tropical", -5.0, 2020)

def test_invalid_canopy():
    with pytest.raises(ValueError, match="canopy_cover_pct"):
        BlueCarbonPlot("x", "mangrove", "tropical", 10.0, 2020, canopy_cover_pct=120)

def test_invalid_soil_depth():
    with pytest.raises(ValueError, match="soil_depth_cm"):
        BlueCarbonPlot("x", "mangrove", "tropical", 10.0, 2020, soil_depth_cm=0)


# --- BlueCarbonCalculator basic operations ---

def test_add_plot(mangrove_plot):
    calc = BlueCarbonCalculator()
    calc.add_plot(mangrove_plot)
    assert len(calc) == 1

def test_add_duplicate_plot_raises(mangrove_plot):
    calc = BlueCarbonCalculator()
    calc.add_plot(mangrove_plot)
    with pytest.raises(ValueError, match="already exists"):
        calc.add_plot(mangrove_plot)

def test_remove_plot(calc_with_plots):
    removed = calc_with_plots.remove_plot("MNG-ID-001")
    assert removed is True
    assert len(calc_with_plots) == 1

def test_remove_nonexistent_plot(calc_with_plots):
    assert calc_with_plots.remove_plot("UNKNOWN") is False

def test_repr(calc_with_plots):
    assert "BlueCarbonCalculator" in repr(calc_with_plots)


# --- Carbon stock calculations ---

def test_plot_carbon_stock_has_required_keys(calc_with_plots):
    stock = calc_with_plots.plot_carbon_stock("MNG-ID-001")
    assert "biomass_tCO2e" in stock
    assert "soil_tCO2e" in stock
    assert "total_tCO2e" in stock

def test_plot_carbon_stock_total_is_sum(calc_with_plots):
    stock = calc_with_plots.plot_carbon_stock("MNG-ID-001")
    assert abs(stock["total_tCO2e"] - (stock["biomass_tCO2e"] + stock["soil_tCO2e"])) < 0.01

def test_plot_carbon_stock_unknown_raises(calc_with_plots):
    with pytest.raises(KeyError):
        calc_with_plots.plot_carbon_stock("UNKNOWN")

def test_total_carbon_stock_empty():
    calc = BlueCarbonCalculator()
    result = calc.total_carbon_stock()
    assert result["total_tCO2e"] == 0.0

def test_total_carbon_stock_aggregates(calc_with_plots):
    total = calc_with_plots.total_carbon_stock()
    assert total["n_plots"] == 2
    assert total["total_area_ha"] == 70.0
    assert total["total_tCO2e"] > 0

def test_total_carbon_stock_by_ecosystem(calc_with_plots):
    total = calc_with_plots.total_carbon_stock()
    assert "mangrove" in total["by_ecosystem"]
    assert "seagrass" in total["by_ecosystem"]

def test_mangrove_stock_exceeds_seagrass(calc_with_plots):
    total = calc_with_plots.total_carbon_stock()
    assert total["by_ecosystem"]["mangrove"]["total_tCO2e"] > total["by_ecosystem"]["seagrass"]["total_tCO2e"]


# --- Annual sequestration ---

def test_annual_sequestration_empty():
    calc = BlueCarbonCalculator()
    result = calc.annual_sequestration()
    assert result["total_tCO2e_yr"] == 0.0

def test_annual_sequestration_positive(calc_with_plots):
    seq = calc_with_plots.annual_sequestration()
    assert seq["total_tCO2e_yr"] > 0

def test_canopy_cover_affects_sequestration():
    calc_full = BlueCarbonCalculator()
    calc_half = BlueCarbonCalculator()
    calc_full.add_plot(BlueCarbonPlot("p1", "mangrove", "tropical", 10.0, 2020, 100.0))
    calc_half.add_plot(BlueCarbonPlot("p1", "mangrove", "tropical", 10.0, 2020, 50.0))
    assert calc_full.annual_sequestration()["total_tCO2e_yr"] > calc_half.annual_sequestration()["total_tCO2e_yr"]


# --- Lifetime credits ---

def test_lifetime_credits_basic(calc_with_plots):
    result = calc_with_plots.project_lifetime_credits(project_years=20, discount_rate=0.05)
    assert result["gross_tCO2e"] > result["net_tCO2e"]
    assert result["project_years"] == 20

def test_lifetime_credits_invalid_years(calc_with_plots):
    with pytest.raises(ValueError, match="project_years"):
        calc_with_plots.project_lifetime_credits(project_years=0)

def test_lifetime_credits_invalid_discount(calc_with_plots):
    with pytest.raises(ValueError, match="discount_rate"):
        calc_with_plots.project_lifetime_credits(discount_rate=1.5)

def test_lifetime_credits_net_lt_gross(calc_with_plots):
    result = calc_with_plots.project_lifetime_credits(discount_rate=0.1)
    assert result["net_tCO2e"] == round(result["gross_tCO2e"] * 0.9, 2)


# --- Ecosystem summary ---

def test_ecosystem_summary_sorted(calc_with_plots):
    summaries = calc_with_plots.ecosystem_summary()
    stocks = [s["total_stock_tCO2e"] for s in summaries]
    assert stocks == sorted(stocks, reverse=True)

def test_ecosystem_summary_has_seq(calc_with_plots):
    for s in calc_with_plots.ecosystem_summary():
        assert "annual_seq_tCO2e_yr" in s
