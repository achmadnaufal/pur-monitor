"""
Blue Carbon Stock Calculator for Coastal Ecosystem Projects.

Blue carbon refers to carbon captured by coastal and marine ecosystems —
primarily mangroves, seagrasses, and tidal marshes. These ecosystems store
carbon in both living biomass and sediment at rates far exceeding tropical forests.

This module implements blue carbon quantification following:
- IPCC Wetlands Supplement (2013)
- Verra VCS VM0033 (Methodology for Tidal Wetland and Seagrass Restoration)
- Howard et al. (2014) "Coastal Blue Carbon" measurement guide

Author: github.com/achmadnaufal
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Default emission factors (tCO2e/ha/yr) from IPCC Wetlands Supplement Table 4.9
# ---------------------------------------------------------------------------

SEQUESTRATION_RATES: Dict[str, Dict[str, float]] = {
    # Ecosystem → zone → mean annual carbon accumulation (tCO2e/ha/yr)
    "mangrove": {
        "equatorial": 7.4,
        "tropical": 6.1,
        "subtropical": 4.8,
        "temperate": 3.2,
    },
    "seagrass": {
        "equatorial": 2.9,
        "tropical": 2.4,
        "subtropical": 1.8,
        "temperate": 1.2,
    },
    "tidal_marsh": {
        "equatorial": 3.8,
        "tropical": 3.2,
        "subtropical": 2.6,
        "temperate": 1.9,
    },
}

# Biomass carbon density (tC/ha) — above + belowground
BIOMASS_DENSITY: Dict[str, Dict[str, float]] = {
    "mangrove": {
        "equatorial": 180.0,
        "tropical": 145.0,
        "subtropical": 110.0,
        "temperate": 75.0,
    },
    "seagrass": {
        "equatorial": 18.0,
        "tropical": 14.0,
        "subtropical": 10.0,
        "temperate": 6.5,
    },
    "tidal_marsh": {
        "equatorial": 55.0,
        "tropical": 42.0,
        "subtropical": 32.0,
        "temperate": 22.0,
    },
}

# Soil organic carbon top 1m (tC/ha)
SOIL_CARBON_DENSITY: Dict[str, float] = {
    "mangrove": 386.0,
    "seagrass": 139.7,
    "tidal_marsh": 162.0,
}

# CO2 to C conversion factor
C_TO_CO2 = 44 / 12  # 3.667


@dataclass
class BlueCarbonPlot:
    """
    Represents a single surveyed blue carbon plot.

    Attributes:
        plot_id: Unique identifier for the plot.
        ecosystem: Ecosystem type (``mangrove`` / ``seagrass`` / ``tidal_marsh``).
        climate_zone: Climate zone for emission factor selection.
        area_ha: Plot area in hectares.
        restoration_year: Year in which restoration or protection started.
        canopy_cover_pct: Canopy or vegetation cover percent (0–100).
        soil_depth_cm: Measured sediment/soil depth (cm); used for stock estimation.
        notes: Optional field notes.
    """

    plot_id: str
    ecosystem: str
    climate_zone: str
    area_ha: float
    restoration_year: int
    canopy_cover_pct: float = 80.0
    soil_depth_cm: float = 100.0
    notes: str = ""

    VALID_ECOSYSTEMS = set(SEQUESTRATION_RATES.keys())
    VALID_ZONES = {"equatorial", "tropical", "subtropical", "temperate"}

    def __post_init__(self) -> None:
        if self.ecosystem not in self.VALID_ECOSYSTEMS:
            raise ValueError(
                f"ecosystem '{self.ecosystem}' invalid. Choose from {self.VALID_ECOSYSTEMS}"
            )
        if self.climate_zone not in self.VALID_ZONES:
            raise ValueError(
                f"climate_zone '{self.climate_zone}' invalid. Choose from {self.VALID_ZONES}"
            )
        if self.area_ha <= 0:
            raise ValueError("area_ha must be positive.")
        if not (0 <= self.canopy_cover_pct <= 100):
            raise ValueError("canopy_cover_pct must be between 0 and 100.")
        if self.soil_depth_cm <= 0:
            raise ValueError("soil_depth_cm must be positive.")


class BlueCarbonCalculator:
    """
    Estimates carbon stocks and annual sequestration for blue carbon plots.

    Implements a simplified Tier 1 approach consistent with IPCC Wetlands
    Supplement, suitable for project-level MRV (Measurement, Reporting,
    and Verification) reporting.

    Attributes:
        plots (list[BlueCarbonPlot]): Registered plots for this calculator.

    Example::

        calc = BlueCarbonCalculator()
        calc.add_plot(BlueCarbonPlot(
            plot_id="MNG-ID-001",
            ecosystem="mangrove",
            climate_zone="tropical",
            area_ha=45.5,
            restoration_year=2020,
            canopy_cover_pct=72.0,
        ))
        stock = calc.total_carbon_stock()
        print(f"Total stock: {stock['total_tCO2e']:.1f} tCO2e")
        print(f"Annual seq: {calc.annual_sequestration()['total_tCO2e_yr']:.1f} tCO2e/yr")
    """

    def __init__(self) -> None:
        self.plots: List[BlueCarbonPlot] = []

    # ------------------------------------------------------------------
    # Plot management
    # ------------------------------------------------------------------

    def add_plot(self, plot: BlueCarbonPlot) -> None:
        """
        Register a surveyed plot.

        Args:
            plot: A :class:`BlueCarbonPlot` instance.

        Raises:
            ValueError: If a plot with the same ID already exists.
        """
        if any(p.plot_id == plot.plot_id for p in self.plots):
            raise ValueError(f"Plot '{plot.plot_id}' already exists.")
        self.plots.append(plot)

    def remove_plot(self, plot_id: str) -> bool:
        """
        Remove a plot by ID.

        Args:
            plot_id: ID of the plot to remove.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        before = len(self.plots)
        self.plots = [p for p in self.plots if p.plot_id != plot_id]
        return len(self.plots) < before

    # ------------------------------------------------------------------
    # Carbon calculations
    # ------------------------------------------------------------------

    def _biomass_stock_tCO2e(self, plot: BlueCarbonPlot) -> float:
        """
        Estimate biomass carbon stock for a plot.

        Applies a canopy-cover correction: stock scales linearly with cover
        as a proxy for stand density.

        Returns:
            Carbon stock in tCO2e.
        """
        base_density = BIOMASS_DENSITY[plot.ecosystem][plot.climate_zone]
        cover_factor = plot.canopy_cover_pct / 100.0
        tC = base_density * cover_factor * plot.area_ha
        return round(tC * C_TO_CO2, 2)

    def _soil_stock_tCO2e(self, plot: BlueCarbonPlot) -> float:
        """
        Estimate soil organic carbon stock for a plot.

        Scales linearly with measured soil depth relative to the IPCC default
        reference depth of 100 cm.

        Returns:
            Soil carbon stock in tCO2e.
        """
        base_density = SOIL_CARBON_DENSITY[plot.ecosystem]
        depth_factor = min(plot.soil_depth_cm / 100.0, 2.5)  # cap at 2.5×
        tC = base_density * depth_factor * plot.area_ha
        return round(tC * C_TO_CO2, 2)

    def plot_carbon_stock(self, plot_id: str) -> Dict:
        """
        Calculate total carbon stock breakdown for a single plot.

        Args:
            plot_id: ID of the target plot.

        Returns:
            dict with keys:

            - ``plot_id`` – plot identifier
            - ``biomass_tCO2e`` – above + belowground biomass stock
            - ``soil_tCO2e`` – soil organic carbon stock (0–100 cm)
            - ``total_tCO2e`` – sum of biomass + soil stocks

        Raises:
            KeyError: If plot_id is not found.
        """
        plot = next((p for p in self.plots if p.plot_id == plot_id), None)
        if plot is None:
            raise KeyError(f"Plot '{plot_id}' not found.")
        biomass = self._biomass_stock_tCO2e(plot)
        soil = self._soil_stock_tCO2e(plot)
        return {
            "plot_id": plot_id,
            "ecosystem": plot.ecosystem,
            "area_ha": plot.area_ha,
            "biomass_tCO2e": biomass,
            "soil_tCO2e": soil,
            "total_tCO2e": round(biomass + soil, 2),
        }

    def total_carbon_stock(self) -> Dict:
        """
        Aggregate carbon stocks across all registered plots.

        Returns:
            dict with keys:

            - ``n_plots`` – number of plots
            - ``total_area_ha`` – combined area
            - ``biomass_tCO2e`` – aggregate biomass stock
            - ``soil_tCO2e`` – aggregate soil stock
            - ``total_tCO2e`` – aggregate total stock
            - ``by_ecosystem`` – breakdown per ecosystem type
        """
        if not self.plots:
            return {"n_plots": 0, "total_area_ha": 0.0, "total_tCO2e": 0.0}

        by_ecosystem: Dict[str, Dict] = {}
        total_biomass = total_soil = total_area = 0.0

        for plot in self.plots:
            b = self._biomass_stock_tCO2e(plot)
            s = self._soil_stock_tCO2e(plot)
            total_biomass += b
            total_soil += s
            total_area += plot.area_ha
            eco = plot.ecosystem
            if eco not in by_ecosystem:
                by_ecosystem[eco] = {"area_ha": 0.0, "biomass_tCO2e": 0.0,
                                     "soil_tCO2e": 0.0, "total_tCO2e": 0.0}
            by_ecosystem[eco]["area_ha"] += plot.area_ha
            by_ecosystem[eco]["biomass_tCO2e"] += b
            by_ecosystem[eco]["soil_tCO2e"] += s
            by_ecosystem[eco]["total_tCO2e"] += b + s

        return {
            "n_plots": len(self.plots),
            "total_area_ha": round(total_area, 2),
            "biomass_tCO2e": round(total_biomass, 2),
            "soil_tCO2e": round(total_soil, 2),
            "total_tCO2e": round(total_biomass + total_soil, 2),
            "by_ecosystem": {
                eco: {k: round(v, 2) for k, v in vals.items()}
                for eco, vals in by_ecosystem.items()
            },
        }

    def annual_sequestration(self) -> Dict:
        """
        Calculate annual carbon sequestration for all plots.

        Returns:
            dict with keys:

            - ``n_plots`` – number of plots
            - ``total_area_ha`` – combined area
            - ``total_tCO2e_yr`` – aggregate annual sequestration
            - ``by_ecosystem`` – sequestration breakdown per ecosystem
        """
        if not self.plots:
            return {"n_plots": 0, "total_tCO2e_yr": 0.0}

        by_ecosystem: Dict[str, float] = {}
        total_seq = total_area = 0.0

        for plot in self.plots:
            rate = SEQUESTRATION_RATES[plot.ecosystem][plot.climate_zone]
            cover_factor = plot.canopy_cover_pct / 100.0
            seq = round(rate * cover_factor * plot.area_ha, 2)
            total_seq += seq
            total_area += plot.area_ha
            eco = plot.ecosystem
            by_ecosystem[eco] = round(by_ecosystem.get(eco, 0.0) + seq, 2)

        return {
            "n_plots": len(self.plots),
            "total_area_ha": round(total_area, 2),
            "total_tCO2e_yr": round(total_seq, 2),
            "by_ecosystem": by_ecosystem,
        }

    def project_lifetime_credits(
        self, project_years: int = 30, discount_rate: float = 0.05
    ) -> Dict:
        """
        Project carbon credit generation over the project lifetime.

        Uses the annual sequestration rate and a simple discount to account
        for uncertainty/leakage (``discount_rate`` deducted from gross credits).

        Args:
            project_years: Project duration in years (default 30).
            discount_rate: Fraction deducted for uncertainty/leakage (0–1).

        Returns:
            dict with:

            - ``gross_tCO2e`` – undiscounted total credits over project life
            - ``net_tCO2e`` – discounted total (after uncertainty deduction)
            - ``annual_tCO2e_yr`` – annual gross credits
            - ``project_years`` – duration used
            - ``discount_rate`` – discount rate applied
        """
        if project_years <= 0:
            raise ValueError("project_years must be positive.")
        if not (0 <= discount_rate < 1):
            raise ValueError("discount_rate must be in [0, 1).")

        seq = self.annual_sequestration()["total_tCO2e_yr"]
        gross = round(seq * project_years, 2)
        net = round(gross * (1 - discount_rate), 2)
        return {
            "gross_tCO2e": gross,
            "net_tCO2e": net,
            "annual_tCO2e_yr": seq,
            "project_years": project_years,
            "discount_rate": discount_rate,
        }

    def ecosystem_summary(self) -> List[Dict]:
        """
        Return a per-ecosystem summary sorted by total carbon stock descending.

        Returns:
            List of dicts, each with ecosystem name, area, stocks, and sequestration.
        """
        stock = self.total_carbon_stock().get("by_ecosystem", {})
        seq = self.annual_sequestration().get("by_ecosystem", {})
        summaries = []
        for eco, stocks in stock.items():
            summaries.append({
                "ecosystem": eco,
                "area_ha": stocks["area_ha"],
                "total_stock_tCO2e": stocks["total_tCO2e"],
                "annual_seq_tCO2e_yr": seq.get(eco, 0.0),
            })
        return sorted(summaries, key=lambda x: x["total_stock_tCO2e"], reverse=True)

    def __len__(self) -> int:
        return len(self.plots)

    def __repr__(self) -> str:
        return f"BlueCarbonCalculator(plots={len(self.plots)})"
