"""
Data Drift Detection Module

Implements statistical tests to detect distribution shifts between
reference (training) data and production data:
- Kolmogorov-Smirnov test for numerical features
- Chi-squared test for categorical features
- Population Stability Index (PSI) for overall drift
- Target drift detection (concept drift)
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json

from src.utils.logger import logger


@dataclass
class DriftMetrics:
    """Container for drift detection metrics"""
    feature_name: str
    drift_score: float
    p_value: float
    is_drifted: bool
    test_method: str
    reference_mean: Optional[float] = None
    current_mean: Optional[float] = None
    reference_std: Optional[float] = None
    current_std: Optional[float] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class DriftReport:
    """Comprehensive drift detection report"""
    timestamp: str
    total_features: int
    drifted_features: int
    drift_percentage: float
    overall_drift_detected: bool
    feature_drifts: List[Dict[str, Any]]
    target_drift: Optional[Dict[str, Any]] = None
    recommendation: str = ""
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataDriftDetector:
    """
    Detects distribution shifts between reference and current datasets
    using multiple statistical tests.
    """

    def __init__(
        self,
        significance_level: float = 0.05,
        psi_threshold: float = 0.1,
        drift_threshold_percentage: float = 0.3
    ):
        """
        Args:
            significance_level: P-value threshold for statistical tests (default 0.05)
            psi_threshold: PSI threshold for drift detection (default 0.1)
            drift_threshold_percentage: % of features drifted to trigger alert (default 30%)
        """
        self.significance_level = significance_level
        self.psi_threshold = psi_threshold
        self.drift_threshold_percentage = drift_threshold_percentage

    def kolmogorov_smirnov_test(
        self,
        reference: np.ndarray,
        current: np.ndarray
    ) -> Tuple[float, float]:
        """
        Two-sample Kolmogorov-Smirnov test for numerical features.

        Returns:
            (ks_statistic, p_value): KS statistic and p-value
        """
        # Remove NaN values
        ref_clean = reference[~np.isnan(reference)]
        curr_clean = current[~np.isnan(current)]

        if len(ref_clean) < 2 or len(curr_clean) < 2:
            return 0.0, 1.0

        ks_stat, p_value = stats.ks_2samp(ref_clean, curr_clean)
        return float(ks_stat), float(p_value)

    def chi_squared_test(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        bins: int = 10
    ) -> Tuple[float, float]:
        """
        Chi-squared test for categorical or binned numerical features.

        Returns:
            (chi2_statistic, p_value)
        """
        # Create bins for numerical data
        try:
            combined = np.concatenate([reference, current])
            bin_edges = np.histogram_bin_edges(combined, bins=bins)

            ref_counts, _ = np.histogram(reference, bins=bin_edges)
            curr_counts, _ = np.histogram(current, bins=bin_edges)

            # Add small constant to avoid division by zero
            ref_counts = ref_counts + 1
            curr_counts = curr_counts + 1

            chi2_stat, p_value = stats.chisquare(curr_counts, ref_counts)
            return float(chi2_stat), float(p_value)
        except Exception as e:
            logger.warning(f"Chi-squared test failed: {e}")
            return 0.0, 1.0

    def population_stability_index(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI).

        PSI interpretation:
        - PSI < 0.1: No significant change
        - 0.1 <= PSI < 0.2: Moderate change
        - PSI >= 0.2: Significant change

        Returns:
            PSI score
        """
        try:
            # Create bins based on reference distribution
            ref_clean = reference[~np.isnan(reference)]
            curr_clean = current[~np.isnan(current)]

            if len(ref_clean) < bins or len(curr_clean) < bins:
                return 0.0

            # Use quantiles for binning
            bin_edges = np.percentile(ref_clean, np.linspace(0, 100, bins + 1))
            bin_edges[-1] = bin_edges[-1] + 1e-6  # Ensure last bin includes max

            ref_counts, _ = np.histogram(ref_clean, bins=bin_edges)
            curr_counts, _ = np.histogram(curr_clean, bins=bin_edges)

            # Calculate proportions
            ref_props = ref_counts / len(ref_clean)
            curr_props = curr_counts / len(curr_clean)

            # Add small constant to avoid log(0)
            ref_props = np.where(ref_props == 0, 1e-6, ref_props)
            curr_props = np.where(curr_props == 0, 1e-6, curr_props)

            # Calculate PSI
            psi = np.sum((curr_props - ref_props) * np.log(curr_props / ref_props))
            return float(psi)

        except Exception as e:
            logger.warning(f"PSI calculation failed: {e}")
            return 0.0

    def detect_feature_drift(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        feature_name: str,
        use_psi: bool = True
    ) -> DriftMetrics:
        """
        Detect drift for a single feature using multiple tests.

        Args:
            reference: Reference (training) data for the feature
            current: Current (production) data for the feature
            feature_name: Name of the feature
            use_psi: Whether to use PSI in addition to statistical tests

        Returns:
            DriftMetrics object with detection results
        """
        # KS test
        ks_stat, p_value = self.kolmogorov_smirnov_test(reference, current)

        # PSI
        psi_score = 0.0
        if use_psi:
            psi_score = self.population_stability_index(reference, current)

        # Determine if drift detected
        is_drifted = (p_value < self.significance_level) or (psi_score > self.psi_threshold)

        # Calculate basic statistics
        ref_clean = reference[~np.isnan(reference)]
        curr_clean = current[~np.isnan(current)]

        return DriftMetrics(
            feature_name=feature_name,
            drift_score=max(ks_stat, psi_score),
            p_value=p_value,
            is_drifted=is_drifted,
            test_method="KS+PSI" if use_psi else "KS",
            reference_mean=float(np.mean(ref_clean)) if len(ref_clean) > 0 else None,
            current_mean=float(np.mean(curr_clean)) if len(curr_clean) > 0 else None,
            reference_std=float(np.std(ref_clean)) if len(ref_clean) > 0 else None,
            current_std=float(np.std(curr_clean)) if len(curr_clean) > 0 else None
        )

    def detect_dataset_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        features: List[str],
        target_column: Optional[str] = None
    ) -> DriftReport:
        """
        Detect drift across all features in the dataset.

        Args:
            reference_df: Reference (training) dataset
            current_df: Current (production) dataset
            features: List of feature columns to check
            target_column: Optional target column for concept drift detection

        Returns:
            DriftReport with comprehensive drift analysis
        """
        logger.info(f"Starting drift detection for {len(features)} features...")

        feature_drifts = []
        drifted_count = 0

        # Check each feature
        for feature in features:
            if feature not in reference_df.columns or feature not in current_df.columns:
                logger.warning(f"Feature {feature} not found in one or both datasets")
                continue

            ref_data = reference_df[feature].values
            curr_data = current_df[feature].values

            drift_metrics = self.detect_feature_drift(ref_data, curr_data, feature)
            feature_drifts.append(asdict(drift_metrics))

            if drift_metrics.is_drifted:
                drifted_count += 1
                logger.warning(
                    f"DRIFT DETECTED: {feature} | "
                    f"Score={drift_metrics.drift_score:.4f}, "
                    f"p-value={drift_metrics.p_value:.4f}"
                )

        # Check target drift (concept drift)
        target_drift = None
        if target_column and target_column in reference_df.columns and target_column in current_df.columns:
            ref_target = reference_df[target_column].values
            curr_target = current_df[target_column].values
            target_metrics = self.detect_feature_drift(ref_target, curr_target, target_column)
            target_drift = asdict(target_metrics)

            if target_metrics.is_drifted:
                logger.warning(f"TARGET DRIFT DETECTED: {target_column}")

        # Calculate drift percentage
        drift_percentage = (drifted_count / len(features)) * 100 if features else 0.0
        overall_drift = drift_percentage >= (self.drift_threshold_percentage * 100)

        # Determine severity
        severity = self._determine_severity(drift_percentage, target_drift)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            drift_percentage,
            drifted_count,
            target_drift is not None and target_drift.get("is_drifted", False)
        )

        report = DriftReport(
            timestamp=datetime.now().isoformat(),
            total_features=len(features),
            drifted_features=drifted_count,
            drift_percentage=round(drift_percentage, 2),
            overall_drift_detected=overall_drift,
            feature_drifts=feature_drifts,
            target_drift=target_drift,
            recommendation=recommendation,
            severity=severity
        )

        logger.info(
            f"Drift Detection Complete: {drifted_count}/{len(features)} features drifted "
            f"({drift_percentage:.1f}%) | Severity: {severity}"
        )

        return report

    def _determine_severity(
        self,
        drift_percentage: float,
        target_drift: Optional[Dict[str, Any]]
    ) -> str:
        """Determine severity level based on drift metrics"""
        target_drifted = target_drift is not None and target_drift.get("is_drifted", False)

        if target_drifted or drift_percentage >= 50:
            return "CRITICAL"
        elif drift_percentage >= 30:
            return "HIGH"
        elif drift_percentage >= 15:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_recommendation(
        self,
        drift_percentage: float,
        drifted_count: int,
        target_drifted: bool
    ) -> str:
        """Generate actionable recommendation based on drift analysis"""
        if target_drifted:
            return (
                "URGENT: Target distribution has shifted significantly (concept drift). "
                "Model retraining is strongly recommended immediately."
            )
        elif drift_percentage >= 50:
            return (
                f"CRITICAL: {drift_percentage:.1f}% of features show drift. "
                "Immediate model retraining required to maintain accuracy."
            )
        elif drift_percentage >= 30:
            return (
                f"HIGH: {drift_percentage:.1f}% of features drifted. "
                "Schedule model retraining within 24-48 hours."
            )
        elif drift_percentage >= 15:
            return (
                f"MEDIUM: {drift_percentage:.1f}% of features show drift. "
                "Monitor closely and plan retraining within 1 week."
            )
        else:
            return (
                f"LOW: Only {drifted_count} features drifted. "
                "Continue monitoring. No immediate action required."
            )

    def save_report(self, report: DriftReport, output_path: Path) -> None:
        """Save drift report to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Drift report saved to {output_path}")
