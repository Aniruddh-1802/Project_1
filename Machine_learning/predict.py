"""
ML5 - Operationalize Model through Inference

Provides a clean interface for model inference that FastAPI can call.
Loads the trained model and feature engineering pipeline, validates inputs,
and returns structured risk predictions.

This module is the bridge between the ML pipeline (train.py, features.py)
and the API layer (api/routers/prediction.py).
"""

import logging
import pickle
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Feature column names - MUST match ML2/ML3 exactly
FEATURE_COLUMNS = [
    'avg_activity',
    'activity_growth',
    'active_hours',
    'peak_ratio',
    'variability',
    'internet_share'
]


@dataclass
class PredictionRequest:
    """Input to prediction endpoint."""
    grid_id: int
    feature_timestamp: str  # ISO format datetime
    avg_activity: float
    activity_growth: float
    active_hours: int
    peak_ratio: float
    variability: float
    internet_share: float


@dataclass
class PredictionResponse:
    """Output from prediction endpoint."""
    grid_id: int
    feature_timestamp: str
    risk_score: float  # 0.0 to 1.0
    risk_level: str  # NORMAL, ATTENTION, HIGH
    model_version: str
    explanation_note: str


class NetworkRiskPredictor:
    """
    Inference engine for network grid high-activity risk prediction.
    
    Loads trained model and performs batch or single-sample predictions.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize predictor by loading trained model.
        
        Args:
            model_path: Path to pickled model from ML3 training
                       Placeholder: 'data/ml/model.pkl'
        """
        self.model = None
        self.model_path = model_path
        self.model_version = "1.0"
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> None:
        """
        Load trained model from disk.
        
        INPUT FILE PLACEHOLDER:
          Path: data/ml/model.pkl
          
        Args:
            model_path: Path to model pickle file
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If model fails to load
        """
        logger.info(f"Loading model from {model_path}")
        
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info("Model loaded successfully")
        except FileNotFoundError:
            raise FileNotFoundError(f"Model not found at {model_path}")
        except Exception as e:
            raise ValueError(f"Failed to load model: {e}")
    
    def validate_features(self, features: Dict) -> bool:
        """
        Validate that input features have correct columns and types.
        
        Args:
            features: Dictionary with feature keys/values
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        missing_cols = set(FEATURE_COLUMNS) - set(features.keys())
        if missing_cols:
            raise ValueError(f"Missing features: {missing_cols}")
        
        for col in FEATURE_COLUMNS:
            val = features[col]
            if val is None:
                raise ValueError(f"Feature {col} is None")
            try:
                float(val)
            except (TypeError, ValueError):
                raise ValueError(f"Feature {col} = {val} is not numeric")
        
        # Additional checks
        if not 0 <= features['internet_share'] <= 1:
            logger.warning(f"internet_share = {features['internet_share']} outside [0,1]")
        
        if features['active_hours'] < 0 or features['active_hours'] > 24:
            raise ValueError(f"active_hours must be 0-24, got {features['active_hours']}")
        
        return True

    def predict_single(self, request: PredictionRequest) -> PredictionResponse:
        """
        Predict risk for a single grid/timestamp.
        
        Args:
            request: PredictionRequest with features
            
        Returns:
            PredictionResponse with risk score and level
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        # Validate
        features_dict = {
            'avg_activity': request.avg_activity,
            'activity_growth': request.activity_growth,
            'active_hours': request.active_hours,
            'peak_ratio': request.peak_ratio,
            'variability': request.variability,
            'internet_share': request.internet_share
        }
        
        self.validate_features(features_dict)
        
        # Prepare feature vector
        X = np.array([[
            features_dict['avg_activity'],
            features_dict['activity_growth'],
            features_dict['active_hours'],
            features_dict['peak_ratio'],
            features_dict['variability'],
            features_dict['internet_share']
        ]])
        
        # Predict
        risk_score = self.model.predict_proba(X)[0, 1]  # Probability of class 1 (HIGH)
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = 'HIGH'
        elif risk_score >= 0.4:
            risk_level = 'ATTENTION'
        else:
            risk_level = 'NORMAL'
        
        response = PredictionResponse(
            grid_id=request.grid_id,
            feature_timestamp=request.feature_timestamp,
            risk_score=round(float(risk_score), 4),
            risk_level=risk_level,
            model_version=self.model_version,
            explanation_note=(
                "Risk score is a probability (0.0-1.0) from the trained classifier. "
                "It represents the likelihood of high activity in the next hourly interval. "
                "This is an operational attention signal, not a confirmed network fault."
            )
        )
        
        logger.info(
            f"Predicted risk for grid {request.grid_id}: {risk_level} "
            f"(score {risk_score:.3f})"
        )
        
        return response

    def predict_batch(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict risk for multiple grids/timestamps.
        
        Args:
            features_df: DataFrame with columns matching FEATURE_COLUMNS
                        plus grid_id and timestamp
                        
        Returns:
            DataFrame with risk_score, risk_level, model_version
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")
        
        logger.info(f"Predicting risk for {len(features_df)} records")
        
        # Extract feature matrix
        X = features_df[FEATURE_COLUMNS].values
        
        # Predict
        risk_scores = self.model.predict_proba(X)[:, 1]
        
        # Determine risk levels
        risk_levels = pd.cut(
            risk_scores,
            bins=[0, 0.4, 0.7, 1.0],
            labels=['NORMAL', 'ATTENTION', 'HIGH'],
            include_lowest=True
        )
        
        # Build output DataFrame
        predictions_df = pd.DataFrame({
            'grid_id': features_df['grid_id'],
            'timestamp': features_df['timestamp'],
            'risk_score': risk_scores,
            'risk_level': risk_levels.astype(str),
            'model_version': self.model_version
        })
        
        logger.info(
            f"Predictions: {(risk_levels == 'HIGH').sum()} HIGH, "
            f"{(risk_levels == 'ATTENTION').sum()} ATTENTION, "
            f"{(risk_levels == 'NORMAL').sum()} NORMAL"
        )
        
        return predictions_df

    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model metadata
        """
        if self.model is None:
            return {
                'status': 'not_loaded',
                'model_version': self.model_version
            }
        
        info = {
            'status': 'loaded',
            'model_version': self.model_version,
            'model_type': type(self.model).__name__,
            'feature_columns': FEATURE_COLUMNS,
            'expected_input_shape': (1, len(FEATURE_COLUMNS))
        }
        
        # Add model-specific info
        if hasattr(self.model, 'coef_'):
            info['coefficients'] = self.model.coef_[0].tolist()
        
        if hasattr(self.model, 'feature_importances_'):
            info['feature_importances'] = self.model.feature_importances_.tolist()
        
        return info


def stub_prediction() -> PredictionResponse:
    """
    Stub prediction for API5 - before model is trained.
    
    Returns:
        Stub response with note about implementation status
    """
    return PredictionResponse(
        grid_id=0,
        feature_timestamp=datetime.utcnow().isoformat(),
        risk_score=0.0,
        risk_level='NORMAL',
        model_version='stub',
        explanation_note='This prediction is from a stub implementation (ML5 not yet complete)'
    )


def main():
    """
    Example usage: Load model and make predictions.
    """
    logger.basicConfig(level=logging.INFO)
    
    print("\n=== ML5: Operationalize Model ===\n")
    
    # MODEL PATH - PLACEHOLDER
    MODEL_PATH = 'data/ml/model.pkl'
    
    # Initialize predictor
    predictor = NetworkRiskPredictor(model_path=MODEL_PATH)
    
    # Get model info
    info = predictor.get_model_info()
    print(f"Model Info:\n{info}\n")
    
    # Example prediction
    request = PredictionRequest(
        grid_id=4821,
        feature_timestamp='2013-11-05T14:00:00',
        avg_activity=150.0,
        activity_growth=0.2,
        active_hours=18,
        peak_ratio=2.5,
        variability=45.0,
        internet_share=0.65
    )
    
    response = predictor.predict_single(request)
    print(f"Single Prediction:\n{response}\n")
    
    print("Ready for ML6: Batch Scoring and Airflow Integration\n")


if __name__ == '__main__':
    main()
