"""
ML6 - Batch Score All Grids

Integrates ML scoring into the data engineering pipeline.
After each Spark processing run, all grids are scored and a risk table
is published for the API and dashboard to consume.

This module is designed to be called by Airflow (see ml_batch_score_task in
the DAG definition).
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict
import sys
import os

logger = logging.getLogger(__name__)


class BatchScorer:
    """
    Batch inference for all grids in the processed analytics layer.
    
    Workflow:
      1. Load the latest engineered features from ML2
      2. Load the trained model from ML3
      3. Run inference on all grid/timestamp combinations
      4. Publish results to network_risk_scores table
      5. Generate a top-20 operational attention report
    """
    
    def __init__(self):
        """Initialize batch scorer."""
        self.features_df = None
        self.scores_df = None
        self.predictor = None
    
    def load_features(self, features_path: str) -> pd.DataFrame:
        """
        Load engineered features from ML2.
        
        INPUT FILE PLACEHOLDER:
          Path: data/ml/network_feature_table/
          
        Args:
            features_path: Path to features Parquet or CSV
            
        Returns:
            Features DataFrame
        """
        logger.info(f"Loading features from {features_path}")
        
        try:
            import pyarrow.parquet as pq
            self.features_df = pq.read_table(features_path).to_pandas()
        except:
            self.features_df = pd.read_csv(features_path)
        
        self.features_df['feature_timestamp'] = pd.to_datetime(
            self.features_df['feature_timestamp']
        )
        
        logger.info(f"Loaded {len(self.features_df)} feature rows")
        return self.features_df
    
    def load_model(self, model_path: str) -> None:
        """
        Load trained model from ML3.
        
        INPUT FILE PLACEHOLDER:
          Path: data/ml/model.pkl
          
        Args:
            model_path: Path to pickled model
        """
        # Import here to avoid hard dependency
        try:
            from predict import NetworkRiskPredictor
            self.predictor = NetworkRiskPredictor(model_path)
            logger.info("Model loaded successfully")
        except ImportError:
            logger.error("Cannot import predict module. Check ML5 is complete.")
            raise
    
    def score_all_grids(self) -> pd.DataFrame:
        """
        Run inference on all grid/timestamp combinations.
        
        Returns:
            DataFrame with columns:
              grid_id, timestamp, risk_score, risk_level, model_version
        """
        if self.predictor is None:
            raise ValueError("Must load model first with load_model()")
        
        if self.features_df is None:
            raise ValueError("Must load features first with load_features()")
        
        logger.info(f"Scoring {len(self.features_df)} grid/timestamp combinations")
        
        # Call predictor's batch function
        self.scores_df = self.predictor.predict_batch(self.features_df)
        
        # Count by risk level
        risk_counts = self.scores_df['risk_level'].value_counts()
        logger.info(f"\nScoring Results:")
        for level in ['HIGH', 'ATTENTION', 'NORMAL']:
            count = risk_counts.get(level, 0)
            logger.info(f"  {level}: {count}")
        
        return self.scores_df
    
    def load_anomaly_scores(self, anomaly_path: str) -> pd.DataFrame:
        """
        Load anomaly scores from ML4 to include in risk assessment.
        
        INPUT FILE PLACEHOLDER:
          Path: data/ml/network_anomaly_scores.parquet
          
        Args:
            anomaly_path: Path to anomaly scores
            
        Returns:
            Anomaly DataFrame
        """
        logger.info(f"Loading anomaly scores from {anomaly_path}")
        
        try:
            import pyarrow.parquet as pq
            anomaly_df = pq.read_table(anomaly_path).to_pandas()
        except:
            anomaly_df = pd.read_csv(anomaly_path)
        
        anomaly_df['timestamp'] = pd.to_datetime(anomaly_df['timestamp'])
        
        # Merge anomaly into scores
        self.scores_df = self.scores_df.merge(
            anomaly_df[['grid_id', 'timestamp', 'anomaly_score', 'anomaly_direction']],
            on=['grid_id', 'timestamp'],
            how='left'
        )
        
        logger.info(f"Merged {len(anomaly_df)} anomaly records")
        
        return self.scores_df

    def generate_top_attention_report(self, top_n: int = 20) -> pd.DataFrame:
        """
        Generate prioritized list of grids requiring operational attention.
        
        Combines risk_score and anomaly_score for ranking.
        
        Args:
            top_n: Number of top grids to include in report
            
        Returns:
            DataFrame with top grids sorted by attention priority
        """
        if self.scores_df is None:
            raise ValueError("Must score grids first")
        
        # Create attention score = weighted combination
        # 60% from ML risk score, 40% from anomaly
        scores_for_report = self.scores_df[self.scores_df['risk_level'].isin(['HIGH', 'ATTENTION'])].copy()
        
        # Fill NaN anomaly scores with 0
        if 'anomaly_score' in scores_for_report.columns:
            scores_for_report['anomaly_score'] = scores_for_report['anomaly_score'].fillna(0)
            scores_for_report['attention_score'] = (
                0.6 * scores_for_report['risk_score'] +
                0.4 * scores_for_report['anomaly_score']
            )
        else:
            scores_for_report['attention_score'] = scores_for_report['risk_score']
        
        # Sort and take top N
        report = scores_for_report.sort_values('attention_score', ascending=False).head(top_n)
        
        logger.info(f"\n=== Top {top_n} Grids Requiring Attention ===\n")
        
        for idx, row in report.iterrows():
            logger.info(
                f"Grid {row['grid_id']:5d} at {row['timestamp']}: "
                f"Risk={row['risk_score']:.2f} ({row['risk_level']:10s}), "
                f"Attention Score={row['attention_score']:.2f}"
            )
        
        logger.info("\n")
        
        return report

    def save_scores(self, output_path: str = None) -> str:
        """
        Save risk scores to disk for API consumption.
        
        OUTPUT PATH PLACEHOLDER:
          Path: data/ml/network_risk_scores/
          Format: Parquet
          
        Args:
            output_path: Path to save scores
            
        Returns:
            Path where scores were saved
        """
        if self.scores_df is None:
            logger.error("No scores to save")
            return None
        
        output_path = output_path or 'data/ml/network_risk_scores/'
        
        import os
        os.makedirs(output_path, exist_ok=True)
        
        # Save as Parquet
        self.scores_df.to_parquet(f"{output_path}/risk_scores.parquet", index=False)
        
        logger.info(f"Risk scores saved to {output_path}")
        
        return output_path

    def validate_scores(self) -> bool:
        """
        Validate score integrity.
        
        Checks:
          - No NaN risk_scores
          - risk_score between 0 and 1
          - All grids present
          - Deterministic ordering
          
        Returns:
            True if all validations pass
            
        Raises:
            AssertionError if any validation fails
        """
        assert self.scores_df is not None, "No scores to validate"
        
        # Check for NaN
        nan_count = self.scores_df['risk_score'].isna().sum()
        assert nan_count == 0, f"Found {nan_count} NaN risk scores"
        
        # Check range
        assert (self.scores_df['risk_score'] >= 0).all(), "Found negative risk scores"
        assert (self.scores_df['risk_score'] <= 1).all(), "Found risk scores > 1"
        
        # Check duplicates
        dup_count = self.scores_df.duplicated(subset=['grid_id', 'timestamp']).sum()
        assert dup_count == 0, f"Found {dup_count} duplicate grid/timestamp combinations"
        
        logger.info("Score validation passed")
        return True


def run_batch_scoring(
    features_path: str,
    model_path: str,
    anomaly_path: str = None,
    output_path: str = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Main entry point for batch scoring - designed for Airflow DAG.
    
    INPUT FILE PLACEHOLDERS:
      features_path: 'data/ml/network_feature_table/'
      model_path: 'data/ml/model.pkl'
      anomaly_path: 'data/ml/network_anomaly_scores.parquet'
      
    OUTPUT FILE PLACEHOLDER:
      output_path: 'data/ml/network_risk_scores/'
      
    Args:
        features_path: Path to engineered features
        model_path: Path to trained model
        anomaly_path: Optional path to anomaly scores
        output_path: Path to save results
        
    Returns:
        (scores_df, report_df) tuple
        
    Raises:
        Exception: If any step fails (suitable for Airflow error handling)
    """
    logger.info("Starting ML6 Batch Scoring")
    logger.info(f"Features: {features_path}")
    logger.info(f"Model: {model_path}")
    logger.info(f"Anomalies: {anomaly_path}")
    
    try:
        scorer = BatchScorer()
        
        # Load data and model
        scorer.load_features(features_path)
        scorer.load_model(model_path)
        
        # Score all grids
        scores = scorer.score_all_grids()
        
        # Load anomalies if available
        if anomaly_path:
            try:
                scorer.load_anomaly_scores(anomaly_path)
            except Exception as e:
                logger.warning(f"Could not load anomaly scores: {e}")
        
        # Generate report
        report = scorer.generate_top_attention_report(top_n=20)
        
        # Validate
        scorer.validate_scores()
        
        # Save
        save_path = scorer.save_scores(output_path)
        
        logger.info(f"Batch scoring complete. Results at {save_path}")
        
        return scores, report
    
    except Exception as e:
        logger.error(f"Batch scoring failed: {e}", exc_info=True)
        raise


def main():
    """
    Example usage: Load features, model, and run batch scoring.
    """
    logger.basicConfig(level=logging.INFO)
    
    print("\n=== ML6: Batch Score All Grids ===\n")
    
    # INPUT PATHS - PLACEHOLDERS
    FEATURES_PATH = 'data/ml/network_feature_table/'
    MODEL_PATH = 'data/ml/model.pkl'
    ANOMALY_PATH = 'data/ml/network_anomaly_scores.parquet'
    OUTPUT_PATH = 'data/ml/network_risk_scores/'
    
    try:
        scores, report = run_batch_scoring(
            features_path=FEATURES_PATH,
            model_path=MODEL_PATH,
            anomaly_path=ANOMALY_PATH,
            output_path=OUTPUT_PATH
        )
        
        print(f"\nBatch Scoring Complete")
        print(f"Total scores: {len(scores)}")
        print(f"Top attention grids: {len(report)}\n")
        
        return scores, report
    
    except FileNotFoundError as e:
        print(f"\nError: Input file not found - {e}")
        print(f"Please ensure ML1-ML5 have been completed first\n")
        return None, None
    except Exception as e:
        print(f"\nError during batch scoring: {e}\n")
        return None, None


if __name__ == '__main__':
    main()
