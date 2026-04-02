#!/usr/bin/env python3
"""
NFLStatsAnalyzer Master Pipeline Orchestrator
=============================================

This script acts as the centralized entry point to execute the
production data pipelines for offensive constraints and defensive rankings.

Usage:
  python run_pipelines.py --all
  python run_pipelines.py --offensive
  python run_pipelines.py --defensive
"""

import sys
import argparse
import traceback
from pathlib import Path

# Ensure 'src' is in sys.path for absolute imports like 'from pipelines...'
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipelines.logger import get_pipeline_logger, PipelineTimer
from pipelines.rankings.offensive import main as fetch_offensive
from pipelines.rankings.defensive import main as fetch_defensive
from pipelines.get_weekly_rankings import main as fetch_weekly

# Initialize the global master logger
logger = get_pipeline_logger("master_orchestrator")


def run_all() -> None:
    """Execute all pipelines sequentially within a timer context."""
    logger.info("Starting Full NFLStatsAnalyzer Pipeline Deployment")
    
    with PipelineTimer("full_pipeline_run", logger):
        logger.info("-" * 40)
        logger.info("PHASE 1: Extracting Offensive Rankings (Seasonal)")
        logger.info("-" * 40)
        try:
            fetch_offensive()
        except Exception as e:
            logger.error("Offensive Pipeline suffered a fatal error.", exc_info=True)
            raise

        logger.info("-" * 40)
        logger.info("PHASE 2: Extracting Defensive Rankings (Seasonal)")
        logger.info("-" * 40)
        try:
            fetch_defensive()
        except Exception as e:
            logger.error("Defensive Pipeline suffered a fatal error.", exc_info=True)
            raise
            
        logger.info("-" * 40)
        logger.info("PHASE 3: Extracting Weekly Rankings (Enriched)")
        logger.info("-" * 40)
        try:
            fetch_weekly()
        except Exception as e:
            logger.error("Weekly Pipeline suffered a fatal error.", exc_info=True)
            raise
            
        logger.info("All pipeline phases completed successfully.")


def run_offensive() -> None:
    logger.info("Starting Offensive Pipeline (Standalone)")
    try:
        fetch_offensive()
    except Exception as e:
        logger.error("Failed to run offensive pipeline.", exc_info=True)
        sys.exit(1)


def run_defensive() -> None:
    logger.info("Starting Defensive Pipeline (Standalone)")
    try:
        fetch_defensive()
    except Exception as e:
        logger.error("Failed to run defensive pipeline.", exc_info=True)
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="NFL Rankings Pipeline Orchestrator")
    parser.add_argument("--all", action="store_true", help="Run all ranking pipelines (Offense + Defense)")
    parser.add_argument("--offensive", action="store_true", help="Run only the offensive rankings pipeline")
    parser.add_argument("--defensive", action="store_true", help="Run only the defensive rankings pipeline")
    
    args = parser.parse_args()
    
    # Default to running all if no specific flag is provided
    if not (args.all or args.offensive or args.defensive):
        return argparse.Namespace(all=True, offensive=False, defensive=False)
        
    return args


if __name__ == "__main__":
    args = parse_args()
    
    exit_code = 0
    try:
        if args.offensive:
            run_offensive()
        elif args.defensive:
            run_defensive()
        else:
            run_all()
    except Exception as e:
        logger.critical("Master Pipeline Terminated unexpectedly.")
        exit_code = 1
    finally:
        sys.exit(exit_code)
