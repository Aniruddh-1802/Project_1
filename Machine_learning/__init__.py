"""
Network Operations Predictive Intelligence - ML Phase

Modules for machine learning workflow:
  - features: Feature engineering (ML2)
  - train: Model training (ML3)
  - anomaly: Anomaly detection (ML4)
  - predict: Model inference (ML5)
  - batch_score: Batch scoring (ML6)
"""

__version__ = "1.0"
__author__ = "Network Operations Team"

try:
    from .features import NetworkActivityFeatures
    from .train import NetworkActivityClassifier
    from .anomaly import AnomalyDetector
    from .predict import NetworkRiskPredictor, PredictionRequest, PredictionResponse
    from .batch_score import BatchScorer, run_batch_scoring
    
    __all__ = [
        'NetworkActivityFeatures',
        'NetworkActivityClassifier',
        'AnomalyDetector',
        'NetworkRiskPredictor',
        'PredictionRequest',
        'PredictionResponse',
        'BatchScorer',
        'run_batch_scoring'
    ]
except ImportError as e:
    print(f"Warning: Could not import all ML modules: {e}")
    print("Ensure all required packages are installed: pip install -r requirements.txt")
