#!/usr/bin/env python
"""
Run All ML Phases in Sequence

Executes the complete ML pipeline:
  ML2: Feature Engineering
  ML3: Train Classifier
  ML4: Anomaly Detection
  ML5: Model Inference (validation)
  ML6: Batch Scoring

Usage:
  python run_all.py
  python run_all.py --skip-feature-engineering  # If features already exist
  python run_all.py --phase ml3  # Run only ML3 (requires ML2 output)
"""

import logging
import sys
import argparse
from datetime import datetime
from pathlib import Path

import config
from features import NetworkActivityFeatures
from train import NetworkActivityClassifier
from anomaly import AnomalyDetector
from predict import NetworkRiskPredictor
from batch_score import run_batch_scoring

# Setup logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE_PATH)
    ]
)
logger = logging.getLogger(__name__)


def print_banner(phase_name: str):
    """Print a formatted banner for each phase."""
    banner = f"""
╔════════════════════════════════════════════════════════════╗
║  {phase_name:58}║
╚════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_ml2_feature_engineering():
    """Execute ML2: Feature Engineering."""
    print_banner("ML2: Feature Engineering")
    
    try:
        fe = NetworkActivityFeatures(hourly_summary_path=config.HOURLY_SUMMARY_PATH)
        
        logger.info(f"Loading data from {config.HOURLY_SUMMARY_PATH}")
        fe.load_data()
        
        logger.info("Computing derived activity measures")
        fe.compute_derived_activity()
        
        logger.info("Engineering features")
        features_df = fe.engineer_features()
        
        logger.info("Validating features for leakage")
        fe.validate_no_leakage(features_df)
        
        logger.info(f"Saving features to {config.FEATURES_OUTPUT_PATH}")
        fe.save_features(config.FEATURES_OUTPUT_PATH)
        
        print(f"✓ ML2 Complete: {len(features_df)} feature rows\n")
        return True
    
    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        logger.error(f"Expected hourly summary at: {config.HOURLY_SUMMARY_PATH}")
        print(f"✗ ML2 Failed: {e}\n")
        return False
    except Exception as e:
        logger.error(f"ML2 failed: {e}", exc_info=True)
        print(f"✗ ML2 Failed: {e}\n")
        return False


def run_ml3_train_classifier():
    """Execute ML3: Train Simple Classifier."""
    print_banner("ML3: Train Simple Classifier")
    
    try:
        clf = NetworkActivityClassifier(model_type=config.MODEL_TYPE)
        
        logger.info(f"Loading features from {config.FEATURES_OUTPUT_PATH}")
        clf.load_features(f"{config.FEATURES_OUTPUT_PATH}/features.parquet")
        
        logger.info(f"Loading raw summary from {config.HOURLY_SUMMARY_PATH}")
        summary_df = clf.load_raw_summary(config.HOURLY_SUMMARY_PATH)
        
        logger.info("Creating labels")
        label_df = clf.create_labels(summary_df)
        
        logger.info("Merging features and labels")
        labeled_data = clf.merge_features_and_labels(label_df)
        
        logger.info("Performing chronological train/test split")
        train_df, test_df = clf.chronological_train_test_split()
        
        logger.info(f"Training {config.MODEL_TYPE} model")
        clf.train()
        
        logger.info("Evaluating model")
        metrics = clf.evaluate()
        
        logger.info(f"Saving model to {config.MODEL_OUTPUT_PATH}")
        clf.save_model(config.MODEL_OUTPUT_PATH)
        
        # Check for suspicious accuracy
        if metrics['accuracy'] > 0.95:
            logger.warning("⚠️  SUSPICIOUS ACCURACY - Check for data leakage!")
        
        print(f"✓ ML3 Complete: Model trained with {metrics['accuracy']:.2%} accuracy\n")
        return True
    
    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        logger.error(f"Did you run ML2 first?")
        print(f"✗ ML3 Failed: {e}\n")
        return False
    except Exception as e:
        logger.error(f"ML3 failed: {e}", exc_info=True)
        print(f"✗ ML3 Failed: {e}\n")
        return False


def run_ml4_anomaly_baseline():
    """Execute ML4: Add Anomaly Baseline."""
    print_banner("ML4: Add Anomaly Baseline")
    
    try:
        detector = AnomalyDetector()
        
        logger.info(f"Loading hourly summary from {config.HOURLY_SUMMARY_PATH}")
        detector.load_data(config.HOURLY_SUMMARY_PATH)
        
        logger.info("Computing anomaly scores")
        anomaly_scores = detector.compute_anomaly_scores()
        
        logger.info(f"Saving anomaly scores to {config.ANOMALY_SCORES_PATH}")
        detector.save_scores(config.ANOMALY_SCORES_PATH)
        
        print(f"✓ ML4 Complete: {len(anomaly_scores)} anomaly scores computed\n")
        return True
    
    except Exception as e:
        logger.error(f"ML4 failed: {e}", exc_info=True)
        print(f"✗ ML4 Failed: {e}\n")
        return False


def run_ml5_model_inference():
    """Execute ML5: Model Inference Validation."""
    print_banner("ML5: Model Inference (Validation)")
    
    try:
        logger.info(f"Loading model from {config.MODEL_OUTPUT_PATH}")
        predictor = NetworkRiskPredictor(model_path=config.MODEL_OUTPUT_PATH)
        
        logger.info("Model information:")
        info = predictor.get_model_info()
        logger.info(f"  Type: {info.get('model_type', 'unknown')}")
        logger.info(f"  Version: {info.get('model_version', 'unknown')}")
        
        # Test with example
        from predict import PredictionRequest
        
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
        logger.info(f"Example prediction: Grid {response.grid_id} -> {response.risk_level} ({response.risk_score:.3f})")
        
        print(f"✓ ML5 Complete: Model inference working\n")
        return True
    
    except FileNotFoundError as e:
        logger.error(f"Model not found: {e}")
        logger.error(f"Did you run ML3 first?")
        print(f"✗ ML5 Failed: {e}\n")
        return False
    except Exception as e:
        logger.error(f"ML5 failed: {e}", exc_info=True)
        print(f"✗ ML5 Failed: {e}\n")
        return False


def run_ml6_batch_scoring():
    """Execute ML6: Batch Scoring."""
    print_banner("ML6: Batch Score All Grids")
    
    try:
        logger.info("Running batch scoring")
        scores, report = run_batch_scoring(
            features_path=config.FEATURES_OUTPUT_PATH,
            model_path=config.MODEL_OUTPUT_PATH,
            anomaly_path=config.ANOMALY_SCORES_PATH,
            output_path=config.RISK_SCORES_OUTPUT_PATH
        )
        
        if scores is not None:
            print(f"✓ ML6 Complete: {len(scores)} grids scored\n")
            return True
        else:
            print(f"✗ ML6 Failed: Batch scoring returned None\n")
            return False
    
    except Exception as e:
        logger.error(f"ML6 failed: {e}", exc_info=True)
        print(f"✗ ML6 Failed: {e}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run Network Operations ML Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all.py                    # Run all phases
  python run_all.py --phase ml3        # Run only ML3
  python run_all.py --skip-anomaly     # Skip ML4
  python run_all.py --verbose          # Debug logging
        """
    )
    
    parser.add_argument(
        '--phase',
        choices=['ml2', 'ml3', 'ml4', 'ml5', 'ml6'],
        help='Run only a specific phase (default: all)'
    )
    
    parser.add_argument(
        '--skip-feature-engineering',
        action='store_true',
        help='Skip ML2 if features already exist'
    )
    
    parser.add_argument(
        '--skip-anomaly',
        action='store_true',
        help='Skip ML4'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable DEBUG logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure output directories exist
    config.ensure_output_directories()
    
    # Print configuration
    print(config.get_config_summary())
    
    start_time = datetime.now()
    logger.info(f"Starting ML pipeline at {start_time}")
    
    # Determine which phases to run
    phases_to_run = []
    
    if args.phase:
        # Run only the specified phase
        phases_to_run = [args.phase]
    else:
        # Run all phases (with skips)
        phases_to_run = ['ml2', 'ml3', 'ml4', 'ml5', 'ml6']
        if args.skip_feature_engineering:
            phases_to_run.remove('ml2')
        if args.skip_anomaly:
            phases_to_run.remove('ml4')
    
    # Execute phases
    results = {}
    
    if 'ml2' in phases_to_run:
        results['ml2'] = run_ml2_feature_engineering()
        if not results['ml2'] and args.phase != 'ml2':
            logger.error("ML2 failed. Cannot proceed to later phases.")
            return 1
    
    if 'ml3' in phases_to_run:
        results['ml3'] = run_ml3_train_classifier()
        if not results['ml3'] and args.phase != 'ml3':
            logger.error("ML3 failed. Cannot proceed to later phases.")
            return 1
    
    if 'ml4' in phases_to_run:
        results['ml4'] = run_ml4_anomaly_baseline()
    
    if 'ml5' in phases_to_run:
        results['ml5'] = run_ml5_model_inference()
    
    if 'ml6' in phases_to_run:
        results['ml6'] = run_ml6_batch_scoring()
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("ML PIPELINE SUMMARY")
    print("=" * 60)
    
    for phase, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{phase.upper():5} {status}")
    
    total_success = all(results.values())
    
    print("=" * 60)
    print(f"Total time: {duration}")
    
    if total_success:
        print("\n🎉 All phases completed successfully!")
        logger.info(f"Pipeline complete at {end_time}")
        return 0
    else:
        print("\n❌ Some phases failed. Check logs for details.")
        logger.error(f"Pipeline failed at {end_time}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
