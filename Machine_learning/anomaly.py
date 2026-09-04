"""
ML4 - Anomaly Baseline Detection

Computes historical baselines per grid and hour-of-day to detect unusual activity
deviations. This is now possible because the pipeline has accumulated 14+ days of
history (vs NP3 which had only one day).

Key improvement over NP3:
  - NP3 used within-day baseline (median of 24 hours)
  - ML4 uses hour-of-day baseline (what does 14:00 usually look like?)
  - Reuses the baseline function from NP3 with a bucketing parameter
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Tuple
import pickle

logger = logging.getLogger(__name__)

# Anomaly score thresholds
ANOMALY_Z_SCORE_THRESHOLD = 2.0  # Standard deviations from baseline


class AnomalyDetector:
    """
    Simple baseline anomaly detection using hour-of-day patterns.
    
    Approach:
      - For each grid and hour-of-day bucket (e.g., all 14:00s across all days)
      - Compute median baseline activity
      - Compare current activity against baseline
      - Flag as HIGH if deviation > threshold, LOW if < threshold
    """
    
    def __init__(self, baseline_function=None):
        """
        Initialize anomaly detector.
        
        Args:
            baseline_function: Optionally pass in the baseline function from NP3.
                             If None, we define it here.
        """
        self.hourly_summary = None
        self.anomaly_scores = None
        self.baseline_function = baseline_function or self._default_baseline_function
        
    def _default_baseline_function(
        self, 
        data: pd.DataFrame,
        grid_id: int,
        timestamp: pd.Timestamp,
        bucketing_key: str = 'hour_of_day'
    ) -> Tuple[float, float]:
        """
        Compute baseline for a grid at a specific timestamp.
        
        This is a generalized version of the NP3 within-day baseline.
        It can bucket by 'hour_of_day' or other keys.
        
        Args:
            data: Full hourly_grid_summary DataFrame
            grid_id: Grid ID
            timestamp: Current timestamp
            bucketing_key: 'hour_of_day' for hour-of-day baseline,
                          'within_day' for within-day baseline
                          
        Returns:
            (baseline_value, confidence) where confidence is the count of
            observations in the baseline bucket
        """
        grid_data = data[data['grid_id'] == grid_id].copy()
        
        if bucketing_key == 'hour_of_day':
            # Exclude current hour from baseline
            target_hour = timestamp.hour
            baseline_data = grid_data[
                (grid_data['timestamp'].dt.hour == target_hour) &
                (grid_data['timestamp'] != timestamp)
            ]
        elif bucketing_key == 'within_day':
            # Median of other hours same day
            current_date = timestamp.date()
            current_hour = timestamp.hour
            baseline_data = grid_data[
                (grid_data['timestamp'].dt.date == current_date) &
                (grid_data['timestamp'].dt.hour != current_hour)
            ]
        else:
            raise ValueError(f"Unknown bucketing_key: {bucketing_key}")
        
        if len(baseline_data) == 0:
            # Fallback: use all data for this grid
            baseline_data = grid_data[grid_data['timestamp'] != timestamp]
        
        baseline_value = baseline_data['total_activity'].median() if len(baseline_data) > 0 else 0.0
        confidence = len(baseline_data)
        
        return baseline_value, confidence

    def load_data(self, summary_path: str) -> pd.DataFrame:
        """
        Load hourly_grid_summary.
        
        INPUT FILE PLACEHOLDER:
          Path: data/analytics/hourly_grid_summary/
          
        Args:
            summary_path: Path to hourly summary
            
        Returns:
            DataFrame with activity data
        """
        logger.info(f"Loading hourly summary from {summary_path}")
        
        try:
            import pyarrow.parquet as pq
            self.hourly_summary = pq.read_table(summary_path).to_pandas()
        except:
            self.hourly_summary = pd.read_csv(summary_path)
        
        self.hourly_summary['timestamp'] = pd.to_datetime(self.hourly_summary['timestamp'])
        self.hourly_summary = self.hourly_summary.sort_values(['grid_id', 'timestamp'])
        
        # Ensure derived columns
        if 'total_activity' not in self.hourly_summary.columns:
            self.hourly_summary['total_activity'] = (
                self.hourly_summary['sms_in'] + self.hourly_summary['sms_out'] +
                self.hourly_summary['call_in'] + self.hourly_summary['call_out'] +
                self.hourly_summary['internet_activity']
            )
        
        logger.info(f"Loaded {len(self.hourly_summary)} hourly records")
        return self.hourly_summary

    def compute_anomaly_scores(self) -> pd.DataFrame:
        """
        Compute anomaly scores for all grid/timestamp combinations.
        
        For each grid and hour, compute:
          - baseline (hour-of-day median)
          - current activity
          - deviation (absolute and percentage)
          - direction (HIGH if above baseline, LOW if below)
          - anomaly_score (standardized deviation)
          
        Returns:
            DataFrame with anomaly scores
        """
        scores = []
        
        for grid_id in self.hourly_summary['grid_id'].unique():
            grid_data = self.hourly_summary[self.hourly_summary['grid_id'] == grid_id]
            
            for _, row in grid_data.iterrows():
                timestamp = row['timestamp']
                current_activity = row['total_activity']
                
                # Get baseline
                baseline, confidence = self.baseline_function(
                    self.hourly_summary,
                    grid_id,
                    timestamp,
                    bucketing_key='hour_of_day'
                )
                
                # Only compute anomaly if we have baseline observations
                if confidence < 1:
                    continue
                
                # Compute deviation
                if baseline > 0:
                    pct_deviation = (current_activity - baseline) / baseline
                else:
                    pct_deviation = 0.0
                
                abs_deviation = abs(current_activity - baseline)
                
                # Determine direction
                if current_activity > baseline:
                    direction = 'HIGH'
                elif current_activity < baseline * 0.5:  # More than 50% drop
                    direction = 'LOW'
                else:
                    direction = 'NORMAL'
                
                # Standardized score
                # Use percentage deviation as the anomaly score
                anomaly_score = abs(pct_deviation)
                
                scores.append({
                    'grid_id': grid_id,
                    'timestamp': timestamp,
                    'current_activity': current_activity,
                    'baseline_activity': baseline,
                    'absolute_deviation': abs_deviation,
                    'pct_deviation': pct_deviation,
                    'direction': direction,
                    'anomaly_score': anomaly_score,
                    'baseline_confidence': int(confidence),
                    'reason': self._format_reason(baseline, current_activity, pct_deviation)
                })
        
        self.anomaly_scores = pd.DataFrame(scores)
        logger.info(f"Computed anomaly scores for {len(self.anomaly_scores)} grid/timestamp pairs")
        
        return self.anomaly_scores

    def _format_reason(self, baseline: float, current: float, pct_dev: float) -> str:
        """Generate human-readable reason for anomaly."""
        if pct_dev > 0.5:
            return f"Activity {current:.0f} is {abs(pct_dev):.0%} above baseline {baseline:.0f}"
        elif pct_dev < -0.5:
            return f"Activity {current:.0f} is {abs(pct_dev):.0%} below baseline {baseline:.0f}"
        else:
            return f"Activity {current:.0f} within normal range of baseline {baseline:.0f}"

    def compare_with_rules_and_classifier(
        self,
        rule_alerts: pd.DataFrame,
        classifier_predictions: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare anomaly scores with NP3 rule-based alerts and ML3 classifier.
        
        INPUT FILE PLACEHOLDERS:
          rule_alerts: network_alerts.csv or network_alerts.json from NP3
          classifier_predictions: model predictions from ML3
          
        Args:
            rule_alerts: DataFrame from NP3 with columns:
                        grid_id, timestamp, alert_type, current_activity, baseline_activity
            classifier_predictions: DataFrame from ML3 with columns:
                                   grid_id, timestamp, predicted_risk
                                   
        Returns:
            Comparison DataFrame showing agreement/disagreement
        """
        logger.info("Comparing anomaly scores with rules and classifier predictions")
        
        # Merge all three signals
        comparison = self.anomaly_scores[['grid_id', 'timestamp', 'anomaly_score', 'direction']].copy()
        comparison.columns = ['grid_id', 'timestamp', 'anomaly_score', 'anomaly_direction']
        
        # Add rule alerts (high_activity flag)
        rule_flags = rule_alerts.groupby(['grid_id', 'timestamp']).apply(
            lambda x: (x['alert_type'] == 'HIGH_ACTIVITY').any()
        ).reset_index(name='rule_high_activity')
        
        comparison = comparison.merge(rule_flags, on=['grid_id', 'timestamp'], how='left')
        comparison['rule_high_activity'] = comparison['rule_high_activity'].fillna(False)
        
        # Add classifier predictions
        comparison = comparison.merge(
            classifier_predictions[['grid_id', 'timestamp', 'high_activity_risk']],
            on=['grid_id', 'timestamp'],
            how='left'
        )
        comparison['high_activity_risk'] = comparison['high_activity_risk'].fillna(False)
        
        # Compute agreement metrics
        anomaly_flag = comparison['anomaly_score'] > 0.3  # Threshold for anomaly
        
        all_agree = (
            (anomaly_flag == comparison['rule_high_activity']) &
            (anomaly_flag == comparison['high_activity_risk'])
        ).sum()
        
        rule_vs_classifier = (
            comparison['rule_high_activity'] == comparison['high_activity_risk']
        ).sum()
        
        rule_vs_anomaly = (
            comparison['rule_high_activity'] == anomaly_flag
        ).sum()
        
        anomaly_vs_classifier = (
            anomaly_flag == comparison['high_activity_risk']
        ).sum()
        
        logger.info(f"\nAgreement Analysis (out of {len(comparison)} samples):")
        logger.info(f"  All three methods agree: {all_agree} ({100*all_agree/len(comparison):.1f}%)")
        logger.info(f"  Rule & Classifier agree: {rule_vs_classifier} ({100*rule_vs_classifier/len(comparison):.1f}%)")
        logger.info(f"  Rule & Anomaly agree: {rule_vs_anomaly} ({100*rule_vs_anomaly/len(comparison):.1f}%)")
        logger.info(f"  Anomaly & Classifier agree: {anomaly_vs_classifier} ({100*anomaly_vs_classifier/len(comparison):.1f}%)")
        
        # Find interesting disagreements
        disagreements = comparison[
            (anomaly_flag != comparison['rule_high_activity']) |
            (anomaly_flag != comparison['high_activity_risk'])
        ]
        
        if len(disagreements) > 0:
            logger.info(f"\nExample disagreements:")
            for idx, row in disagreements.head(5).iterrows():
                logger.info(f"  Grid {row['grid_id']} at {row['timestamp']}")
                logger.info(f"    Anomaly: {row['anomaly_score']:.3f} ({row['anomaly_direction']})")
                logger.info(f"    Rule:    {row['rule_high_activity']}")
                logger.info(f"    Classifier: {row['high_activity_risk']}")
        
        return comparison

    def save_scores(self, output_path: str = None) -> str:
        """
        Save anomaly scores to disk.
        
        OUTPUT PATH PLACEHOLDER:
          Path: data/ml/network_anomaly_scores.parquet
          
        Args:
            output_path: Path to save scores
            
        Returns:
            Path where scores were saved
        """
        if self.anomaly_scores is None:
            logger.error("No anomaly scores computed yet")
            return None
        
        output_path = output_path or 'data/ml/network_anomaly_scores.parquet'
        
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        self.anomaly_scores.to_parquet(output_path, index=False)
        logger.info(f"Anomaly scores saved to {output_path}")
        
        return output_path


def main():
    """
    Example usage: Compute anomaly scores and compare with other methods.
    """
    logger.basicConfig(level=logging.INFO)
    
    print("\n=== ML4: Add an Anomaly Baseline ===\n")
    
    # INPUT PATHS - PLACEHOLDERS
    SUMMARY_PATH = 'data/analytics/hourly_grid_summary/'
    RULE_ALERTS_PATH = 'data/ml/network_alerts.csv'  # From NP3
    CLASSIFIER_PRED_PATH = 'data/ml/classifier_predictions.csv'  # From ML3
    
    # Initialize
    detector = AnomalyDetector()
    
    # Load data
    detector.load_data(SUMMARY_PATH)
    
    # Compute anomaly scores
    anomaly_scores = detector.compute_anomaly_scores()
    
    print(f"\nAnomaly Score Summary:\n{anomaly_scores['anomaly_score'].describe()}\n")
    
    # Optional: Load rules and classifier for comparison
    try:
        rule_alerts = pd.read_csv(RULE_ALERTS_PATH)
        classifier_pred = pd.read_csv(CLASSIFIER_PRED_PATH)
        
        comparison = detector.compare_with_rules_and_classifier(rule_alerts, classifier_pred)
        print(f"\nComparison saved")
    except FileNotFoundError:
        print(f"Warning: Could not load rules or classifier predictions for comparison")
    
    # Save
    output_path = detector.save_scores()
    print(f"\nAnomaly scores saved to {output_path}\n")
    
    return detector


if __name__ == '__main__':
    main()
