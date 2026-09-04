"""
ML3 - Train Simple Risk Classifier

Trains a Logistic Regression or Decision Tree classifier on engineered features
using a CHRONOLOGICAL train/test split (mandatory for time-series data).

Key Principle:
  - Earlier time periods -> TRAIN
  - Later time periods -> TEST
  - NO random mixing of neighboring time observations
  - Features from window ending at t; label describes t+1
  - Report BASE RATE alongside all accuracy metrics
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import pickle

logger = logging.getLogger(__name__)

# LABEL CONFIGURATION
# Threshold for HIGH_ACTIVITY - set empirically from data distribution
ACTIVITY_PERCENTILE = 75  # Top 25% of activities


class NetworkActivityClassifier:
    """
    Simple baseline classifier for network grid high-activity risk.
    
    Uses chronological train/test split enforced at the timestamp level.
    Models: Logistic Regression (default) or Decision Tree
    """
    
    def __init__(self, model_type: str = 'logistic'):
        """
        Initialize classifier.
        
        Args:
            model_type: 'logistic' or 'tree'
        """
        self.model_type = model_type
        self.model = None
        self.features_df = None
        self.labeled_df = None
        self.train_df = None
        self.test_df = None
        self.train_start = None
        self.train_end = None
        self.test_start = None
        self.test_end = None
        self.base_rate = None
        
    def load_features(self, features_path: str) -> pd.DataFrame:
        """
        Load engineered features from ML2.
        
        INPUT FILE PLACEHOLDER:
          Path: data/ml/network_feature_table/features.parquet
          
        Args:
            features_path: Path to features Parquet or CSV
            
        Returns:
            Features DataFrame
        """
        logger.info(f"Loading features from {features_path}")
        
        try:
            self.features_df = pd.read_parquet(features_path)
        except:
            self.features_df = pd.read_csv(features_path)
        
        # Ensure timestamp is datetime
        self.features_df['feature_timestamp'] = pd.to_datetime(
            self.features_df['feature_timestamp']
        )
        
        logger.info(f"Loaded {len(self.features_df)} feature rows")
        return self.features_df
    
    def load_raw_summary(self, summary_path: str) -> pd.DataFrame:
        """
        Load raw hourly_grid_summary to create labels.
        
        INPUT FILE PLACEHOLDER:
          Path: data/analytics/hourly_grid_summary/
          
        Args:
            summary_path: Path to hourly summary Parquet or CSV
            
        Returns:
            Summary DataFrame
        """
        logger.info(f"Loading raw summary from {summary_path}")
        
        try:
            import pyarrow.parquet as pq
            summary_df = pq.read_table(summary_path).to_pandas()
        except:
            summary_df = pd.read_csv(summary_path)
        
        summary_df['timestamp'] = pd.to_datetime(summary_df['timestamp'])
        return summary_df

    def create_labels(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create binary HIGH_ACTIVITY labels from the raw summary.
        
        Label definition:
          - For each grid at t+1: is total_activity >= percentile threshold?
          - Threshold is set empirically (75th percentile = top 25%)
          
        Returns:
            DataFrame with grid_id, timestamp (the LABEL timestamp, which is t+1),
            and high_activity (binary: 1 if activity >= threshold, 0 otherwise)
        """
        # Compute threshold from all data
        threshold = summary_df['total_activity'].quantile(ACTIVITY_PERCENTILE / 100.0)
        logger.info(f"Activity threshold (75th percentile): {threshold:.2f}")
        
        # Create label: 1 if activity >= threshold
        summary_df['high_activity'] = (summary_df['total_activity'] >= threshold).astype(int)
        
        # The label_timestamp is the PREDICTION TARGET time (t+1)
        label_df = summary_df[['grid_id', 'timestamp', 'high_activity', 'total_activity']].copy()
        label_df.columns = ['grid_id', 'label_timestamp', 'high_activity', 'activity_value']
        
        logger.info(f"Created {label_df['high_activity'].sum()} positive labels out of {len(label_df)}")
        self.base_rate = label_df['high_activity'].mean()
        logger.info(f"Base rate (positive class): {self.base_rate:.4f}")
        
        return label_df

    def merge_features_and_labels(self, label_df: pd.DataFrame) -> pd.DataFrame:
        """
        Join features (at time t) with labels (at time t+1).
        
        Ensures that:
          - feature_timestamp (t) is one hour before label_timestamp (t+1)
          - This maintains the strict t/t+1 boundary
          
        Returns:
            Merged DataFrame with features and label
        """
        # Create a t+1 version of feature_timestamp to match with label_timestamp
        self.features_df['label_timestamp'] = (
            self.features_df['feature_timestamp'] + timedelta(hours=1)
        )
        
        # Merge on grid_id and label_timestamp
        merged = self.features_df.merge(
            label_df[['grid_id', 'label_timestamp', 'high_activity']],
            on=['grid_id', 'label_timestamp'],
            how='inner'
        )
        
        logger.info(f"After merge: {len(merged)} rows with both features and labels")
        
        # Validate: feature_timestamp should be exactly 1 hour before label_timestamp
        time_diff = (merged['label_timestamp'] - merged['feature_timestamp']).dt.total_seconds() / 3600
        assert (time_diff == 1.0).all(), "Feature/label time mismatch - should be 1 hour apart"
        
        self.labeled_df = merged
        return merged

    def chronological_train_test_split(self, split_date: str = None) -> Tuple:
        """
        Split data chronologically: earlier -> train, later -> test.
        
        MANDATORY: Do NOT use random split on time-series data.
        
        Args:
            split_date: Date string (YYYY-MM-DD) to split on.
                       If None, splits at 70% of the time range.
                       
        Returns:
            (train_df, test_df) tuple
        """
        if self.labeled_df is None:
            raise ValueError("Must call merge_features_and_labels() first")
        
        # Determine split point
        if split_date is None:
            # 70/30 split
            time_range = self.labeled_df['label_timestamp'].max() - self.labeled_df['label_timestamp'].min()
            split_point = self.labeled_df['label_timestamp'].min() + (0.7 * time_range)
            split_date = split_point.strftime('%Y-%m-%d')
        
        split_datetime = pd.to_datetime(split_date)
        
        # Train: before split date
        self.train_df = self.labeled_df[self.labeled_df['label_timestamp'] < split_datetime].copy()
        # Test: from split date onward
        self.test_df = self.labeled_df[self.labeled_df['label_timestamp'] >= split_datetime].copy()
        
        self.train_start = self.train_df['label_timestamp'].min()
        self.train_end = self.train_df['label_timestamp'].max()
        self.test_start = self.test_df['label_timestamp'].min()
        self.test_end = self.test_df['label_timestamp'].max()
        
        logger.info(f"\nChronological Train/Test Split:")
        logger.info(f"  TRAIN: {self.train_start} to {self.train_end} ({len(self.train_df)} rows)")
        logger.info(f"  TEST:  {self.test_start} to {self.test_end} ({len(self.test_df)} rows)")
        logger.info(f"  Split point: {split_date}\n")
        
        return self.train_df, self.test_df

    def train(self) -> None:
        """
        Train the classifier on training set.
        """
        if self.train_df is None:
            raise ValueError("Must call chronological_train_test_split() first")
        
        # Prepare feature matrix and labels
        feature_cols = [
            'avg_activity', 'activity_growth', 'active_hours',
            'peak_ratio', 'variability', 'internet_share'
        ]
        X_train = self.train_df[feature_cols].values
        y_train = self.train_df['high_activity'].values
        
        logger.info(f"Training {self.model_type} on {len(X_train)} samples")
        
        # Create and train model
        if self.model_type == 'logistic':
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced'  # Handle class imbalance
            )
        elif self.model_type == 'tree':
            self.model = DecisionTreeClassifier(
                max_depth=5,
                min_samples_leaf=10,
                random_state=42,
                class_weight='balanced'
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        self.model.fit(X_train, y_train)
        logger.info(f"Model trained successfully")
        
        # Log feature importances
        if self.model_type == 'logistic':
            feature_importance = self.model.coef_[0]
            importance_df = pd.DataFrame({
                'feature': feature_cols,
                'coefficient': feature_importance
            }).sort_values('coefficient', key=abs, ascending=False)
            logger.info(f"\nLogistic Regression Coefficients:\n{importance_df}\n")
        elif self.model_type == 'tree':
            feature_importance = self.model.feature_importances_
            importance_df = pd.DataFrame({
                'feature': feature_cols,
                'importance': feature_importance
            }).sort_values('importance', ascending=False)
            logger.info(f"\nDecision Tree Feature Importance:\n{importance_df}\n")

    def evaluate(self) -> Dict:
        """
        Evaluate model on test set.
        
        Returns:
            Dictionary with accuracy, precision, recall, base_rate
        """
        if self.model is None or self.test_df is None:
            raise ValueError("Must train() the model first")
        
        # Prepare feature matrix and labels
        feature_cols = [
            'avg_activity', 'activity_growth', 'active_hours',
            'peak_ratio', 'variability', 'internet_share'
        ]
        X_test = self.test_df[feature_cols].values
        y_test = self.test_df['high_activity'].values
        
        # Predict
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Compute metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'base_rate': (y_test.sum() / len(y_test)),
            'tp': int(tp),
            'tn': int(tn),
            'fp': int(fp),
            'fn': int(fn),
            'threshold': ACTIVITY_PERCENTILE
        }
        
        logger.info(f"\n=== Evaluation Results ===")
        logger.info(f"Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info(f"Recall:    {metrics['recall']:.4f}")
        logger.info(f"Base Rate: {metrics['base_rate']:.4f}")
        logger.info(f"\nConfusion Matrix:")
        logger.info(f"  TP: {tp:5d}  FP: {fp:5d}")
        logger.info(f"  FN: {fn:5d}  TN: {tn:5d}")
        logger.info(f"\nInterpretation:")
        logger.info(f"  This classifier predicts HIGH_ACTIVITY with {metrics['precision']:.1%} precision")
        logger.info(f"  and catches {metrics['recall']:.1%} of actual high-activity periods.")
        if metrics['accuracy'] > 0.95:
            logger.warning(f"  WARNING: Accuracy is suspiciously high ({metrics['accuracy']:.1%})")
            logger.warning(f"  Check for data leakage (features including label data)")
        
        return metrics

    def save_model(self, output_path: str = None) -> str:
        """
        Save trained model to disk.
        
        OUTPUT PATH PLACEHOLDER:
          Path: data/ml/model.pkl
          
        Args:
            output_path: Path to save model
            
        Returns:
            Path where model was saved
        """
        if self.model is None:
            logger.error("No model trained yet")
            return None
        
        output_path = output_path or 'data/ml/model.pkl'
        
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        logger.info(f"Model saved to {output_path}")
        return output_path


def main():
    """
    Example usage: Load features, create labels, split, train, evaluate.
    """
    from timedelta import timedelta
    
    logger.basicConfig(level=logging.INFO)
    
    print("\n=== ML3: Train Simple Risk Classifier ===\n")
    
    # INPUT PATHS - PLACEHOLDERS
    FEATURES_PATH = 'data/ml/network_feature_table/features.parquet'
    SUMMARY_PATH = 'data/analytics/hourly_grid_summary/'
    
    # Initialize
    clf = NetworkActivityClassifier(model_type='logistic')
    
    # Load data
    clf.load_features(FEATURES_PATH)
    summary_df = clf.load_raw_summary(SUMMARY_PATH)
    
    # Create labels
    label_df = clf.create_labels(summary_df)
    
    # Merge
    labeled_data = clf.merge_features_and_labels(label_df)
    
    # Split chronologically
    train_df, test_df = clf.chronological_train_test_split()
    
    # Train
    clf.train()
    
    # Evaluate
    metrics = clf.evaluate()
    
    # Save
    model_path = clf.save_model()
    
    print(f"\nModel saved to {model_path}")
    print(f"Ready for ML5: Operationalization through FastAPI\n")
    
    return clf, metrics


if __name__ == '__main__':
    main()
