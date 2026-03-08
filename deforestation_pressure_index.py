"""
Deforestation Pressure Index (DPI) for reforestation project sites.

Quantifies the risk of deforestation pressure on PUR project areas based on
multiple threat drivers derived from FAO, GFW, and literature:
  - Proximity to agricultural expansion frontier
  - Proximity to roads and infrastructure
  - Population density trends
  - Historical forest loss rate in the landscape
  - Governance quality (law enforcement proxy)

The DPI supports site prioritization, monitoring intensity allocation,
and early warning for project permanence risk.

References:
  - Hansen et al. (2013) Global Forest Change, Science
  - Busch & Ferretti-Gallon (2017) Conservation Biology
  - FAO Global Forest Resources Assessment 2020
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class PressureLevel(str, Enum):
    """Categorical deforestation pressure classification."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Weight matrix for each deforestation driver
# Weights sum to 1.0; higher weight = more influential
DRIVER_WEIGHTS: Dict[str, float] = {
    "agri_expansion": 0.30,     # Agricultural frontier pressure
    "road_proximity": 0.20,     # Accessibility / road density
    "population_growth": 0.15,  # Human population dynamics
    "historical_loss_rate": 0.25, # Past deforestation rate in landscape
    "governance_deficit": 0.10, # Inverse of law enforcement strength
}


@dataclass
class SitePressureInputs:
    """Raw input values for DPI calculation for a single site."""
    site_id: str
    country: str

    # Agricultural expansion score (0–10, 10 = intense frontier pressure)
    agri_expansion_score: float

    # Road density or proximity score (0–10, 10 = dense/close roads)
    road_proximity_score: float

    # Population growth pressure (0–10, 10 = rapid growth)
    population_growth_score: float

    # Historical annual forest loss rate in 50km landscape (%, 0–10+)
    historical_loss_rate_pct: float

    # Governance deficit score (0–10, 10 = very weak governance)
    governance_deficit_score: float

    def __post_init__(self):
        """Validate all input scores are in expected ranges."""
        for attr, lo, hi in [
            ("agri_expansion_score", 0, 10),
            ("road_proximity_score", 0, 10),
            ("population_growth_score", 0, 10),
            ("governance_deficit_score", 0, 10),
        ]:
            val = getattr(self, attr)
            if not (lo <= val <= hi):
                raise ValueError(f"{attr} must be between {lo} and {hi}, got {val}")
        if self.historical_loss_rate_pct < 0:
            raise ValueError("historical_loss_rate_pct must be non-negative")


@dataclass
class DPIResult:
    """Deforestation Pressure Index result for a single site."""
    site_id: str
    country: str
    raw_scores: Dict[str, float]
    weighted_scores: Dict[str, float]
    dpi_score: float              # Composite 0–10 score
    pressure_level: PressureLevel
    dominant_driver: str          # The single highest-contributing driver
    dominant_driver_contribution: float  # Its contribution to total score
    recommendation: str
    monitoring_frequency: str     # Recommended field visit frequency

    def to_dict(self) -> dict:
        return {
            "site_id": self.site_id,
            "country": self.country,
            "dpi_score": round(self.dpi_score, 3),
            "pressure_level": self.pressure_level.value,
            "dominant_driver": self.dominant_driver,
            "dominant_contribution_pct": round(self.dominant_driver_contribution * 100, 1),
            "recommendation": self.recommendation,
            "monitoring_frequency": self.monitoring_frequency,
            "driver_breakdown": {k: round(v, 3) for k, v in self.weighted_scores.items()},
        }


class DeforestationPressureIndex:
    """
    Calculate Deforestation Pressure Index (DPI) for reforestation project sites.

    Combines multiple threat drivers using weighted aggregation to produce a
    composite pressure score (0–10). Higher scores indicate greater deforestation
    risk and require more intensive monitoring or protection measures.

    Parameters
    ----------
    custom_weights : dict, optional
        Override default driver weights. Must sum to 1.0 (±0.01 tolerance).

    Examples
    --------
    >>> dpi_calc = DeforestationPressureIndex()
    >>> inputs = SitePressureInputs(
    ...     site_id="PUR-BR-001",
    ...     country="Brazil",
    ...     agri_expansion_score=8.5,
    ...     road_proximity_score=6.0,
    ...     population_growth_score=4.0,
    ...     historical_loss_rate_pct=3.2,
    ...     governance_deficit_score=7.0,
    ... )
    >>> result = dpi_calc.calculate(inputs)
    >>> print(result.pressure_level)
    PressureLevel.HIGH
    """

    _PRESSURE_THRESHOLDS = [
        (2.0,  PressureLevel.VERY_LOW),
        (4.0,  PressureLevel.LOW),
        (6.0,  PressureLevel.MEDIUM),
        (8.0,  PressureLevel.HIGH),
        (10.1, PressureLevel.CRITICAL),
    ]

    _RECOMMENDATIONS = {
        PressureLevel.VERY_LOW: (
            "Annual monitoring sufficient. Site is well-protected from deforestation drivers.",
            "Annual"
        ),
        PressureLevel.LOW: (
            "Biannual monitoring recommended. Engage local community for sentinel observation.",
            "Biannual"
        ),
        PressureLevel.MEDIUM: (
            "Quarterly monitoring required. Implement boundary demarcation and signage.",
            "Quarterly"
        ),
        PressureLevel.HIGH: (
            "Monthly satellite monitoring + quarterly field visits. Coordinate with local authorities.",
            "Monthly"
        ),
        PressureLevel.CRITICAL: (
            "Continuous satellite monitoring + monthly field visits. "
            "Emergency intervention required. Review project permanence buffer allocation.",
            "Monthly (emergency)"
        ),
    }

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None) -> None:
        if custom_weights is not None:
            if set(custom_weights.keys()) != set(DRIVER_WEIGHTS.keys()):
                raise ValueError(f"custom_weights must have exactly these keys: {set(DRIVER_WEIGHTS.keys())}")
            total = sum(custom_weights.values())
            if abs(total - 1.0) > 0.01:
                raise ValueError(f"custom_weights must sum to 1.0, got {total:.3f}")
            self.weights = custom_weights
        else:
            self.weights = DRIVER_WEIGHTS.copy()

    def _normalize_loss_rate(self, loss_pct: float) -> float:
        """Normalize forest loss rate (%) to 0–10 scale. Loss >5%/yr = max 10."""
        return min(loss_pct * 2.0, 10.0)

    def calculate(self, inputs: SitePressureInputs) -> DPIResult:
        """
        Calculate DPI for a single site.

        Parameters
        ----------
        inputs : SitePressureInputs
            Raw threat driver scores for the site.

        Returns
        -------
        DPIResult
        """
        raw = {
            "agri_expansion": inputs.agri_expansion_score,
            "road_proximity": inputs.road_proximity_score,
            "population_growth": inputs.population_growth_score,
            "historical_loss_rate": self._normalize_loss_rate(inputs.historical_loss_rate_pct),
            "governance_deficit": inputs.governance_deficit_score,
        }

        weighted = {k: raw[k] * self.weights[k] for k in raw}
        dpi = sum(weighted.values())

        # Classify pressure level
        pressure = PressureLevel.CRITICAL
        for threshold, level in self._PRESSURE_THRESHOLDS:
            if dpi < threshold:
                pressure = level
                break

        # Identify dominant driver
        dominant_driver = max(weighted, key=weighted.get)
        dominant_contribution = weighted[dominant_driver] / dpi if dpi > 0 else 0.0

        recommendation, monitoring_freq = self._RECOMMENDATIONS[pressure]

        return DPIResult(
            site_id=inputs.site_id,
            country=inputs.country,
            raw_scores=raw,
            weighted_scores=weighted,
            dpi_score=dpi,
            pressure_level=pressure,
            dominant_driver=dominant_driver,
            dominant_driver_contribution=dominant_contribution,
            recommendation=recommendation,
            monitoring_frequency=monitoring_freq,
        )

    def calculate_batch(self, site_inputs: List[SitePressureInputs]) -> List[DPIResult]:
        """Calculate DPI for multiple sites. Returns results sorted by DPI score descending."""
        results = [self.calculate(s) for s in site_inputs]
        return sorted(results, key=lambda r: r.dpi_score, reverse=True)

    def portfolio_summary(self, results: List[DPIResult]) -> Dict:
        """Summarize portfolio-level pressure distribution."""
        level_counts: Dict[str, int] = {p.value: 0 for p in PressureLevel}
        critical_sites = []
        for r in results:
            level_counts[r.pressure_level.value] += 1
            if r.pressure_level in (PressureLevel.HIGH, PressureLevel.CRITICAL):
                critical_sites.append(r.site_id)

        avg_dpi = sum(r.dpi_score for r in results) / len(results) if results else 0.0

        return {
            "total_sites": len(results),
            "average_dpi": round(avg_dpi, 3),
            "pressure_distribution": level_counts,
            "high_or_critical_sites": sorted(critical_sites),
            "high_or_critical_count": len(critical_sites),
        }
