#!/usr/bin/env python3
"""
Run ETL Pipeline for VLA Inference Analytics

Usage:
    python scripts/etl/run_etl_pipeline.py --date 2025-11-06 --pipeline all
    python scripts/etl/run_etl_pipeline.py --date 2025-11-06 --pipeline robot
    python scripts/etl/run_etl_pipeline.py --pipeline all  # Defaults to yesterday

Pipelines:
    - robot: Robot performance metrics aggregation
    - instruction: Instruction analytics aggregation
    - context: Context metadata aggregation
    - billing: Billing summaries computation
    - views: Refresh materialized views
    - all: Run complete pipeline
"""

import sys
import asyncio
import argparse
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.services.data_pipeline.etl_pipeline import ETLPipeline
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/etl_pipeline.log')
    ]
)

logger = logging.getLogger(__name__)


async def run_pipeline(
    pipeline_type: str,
    target_date: date,
    db_session: AsyncSession
) -> dict:
    """
    Run specific ETL pipeline.

    Args:
        pipeline_type: Pipeline to run ('robot', 'instruction', 'context', 'billing', 'views', 'all')
        target_date: Date to process
        db_session: Database session

    Returns:
        Execution results
    """
    etl = ETLPipeline(db_session)

    results = {
        'pipeline': pipeline_type,
        'date': target_date,
        'start_time': datetime.utcnow()
    }

    try:
        if pipeline_type == 'robot':
            results['data'] = await etl.aggregate_robot_performance(target_date)

        elif pipeline_type == 'instruction':
            results['data'] = await etl.aggregate_instruction_analytics(target_date)

        elif pipeline_type == 'context':
            results['data'] = await etl.aggregate_context_metadata(target_date)

        elif pipeline_type == 'billing':
            results['data'] = await etl.compute_billing_summaries(target_date)

        elif pipeline_type == 'views':
            results['data'] = await etl.refresh_materialized_views()

        elif pipeline_type == 'all':
            results['data'] = await etl.run_full_pipeline(target_date)

        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")

        results['status'] = 'success'
        results['end_time'] = datetime.utcnow()
        results['duration_seconds'] = (results['end_time'] - results['start_time']).total_seconds()

        logger.info(
            f"Pipeline '{pipeline_type}' completed successfully in "
            f"{results['duration_seconds']:.2f} seconds"
        )

    except Exception as e:
        results['status'] = 'failed'
        results['error'] = str(e)
        results['end_time'] = datetime.utcnow()

        logger.error(f"Pipeline '{pipeline_type}' failed: {e}", exc_info=True)
        raise

    return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run VLA Inference ETL Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--date',
        type=str,
        help='Target date (YYYY-MM-DD format). Defaults to yesterday.',
        default=None
    )

    parser.add_argument(
        '--pipeline',
        choices=['robot', 'instruction', 'context', 'billing', 'views', 'all'],
        default='all',
        help='Pipeline to run (default: all)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for processing (default: 1000)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate pipeline without committing changes'
    )

    args = parser.parse_args()

    # Parse target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        # Default to yesterday
        target_date = date.today() - timedelta(days=1)

    logger.info(f"Starting ETL pipeline: {args.pipeline} for date {target_date}")

    if args.dry_run:
        logger.warning("DRY RUN MODE: No changes will be committed")

    # Create database engine and session
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    try:
        async with async_session() as session:
            # Run pipeline
            results = await run_pipeline(
                pipeline_type=args.pipeline,
                target_date=target_date,
                db_session=session
            )

            if args.dry_run:
                logger.info("Rolling back changes (dry run)")
                await session.rollback()

            # Print results
            print("\n" + "="*60)
            print("ETL PIPELINE RESULTS")
            print("="*60)
            print(f"Pipeline: {results['pipeline']}")
            print(f"Date: {results['date']}")
            print(f"Status: {results['status']}")
            print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")

            if results['status'] == 'success':
                print("\nData:")
                for key, value in results.get('data', {}).items():
                    print(f"  {key}: {value}")
            else:
                print(f"\nError: {results.get('error', 'Unknown error')}")

            print("="*60 + "\n")

            sys.exit(0 if results['status'] == 'success' else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
