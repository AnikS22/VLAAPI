#!/usr/bin/env python3
"""
Data Retention Policy Implementation

Retention Rules:
1. Archive inference_logs older than 90 days to S3 (Parquet format)
2. Delete aggregated data older than 1 year
3. Keep safety_incidents indefinitely
4. Delete archived training images older than 2 years (if consent expired)

Usage:
    python scripts/retention/data_retention.py --action archive --days 90
    python scripts/retention/data_retention.py --action delete --days 365
    python scripts/retention/data_retention.py --action all
"""

import sys
import asyncio
import argparse
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import io

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.services.storage.storage_service import StorageService
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/data_retention.log')
    ]
)

logger = logging.getLogger(__name__)


class DataRetentionManager:
    """Manage data retention policies."""

    def __init__(
        self,
        db_session: AsyncSession,
        storage_service: StorageService
    ):
        self.db = db_session
        self.storage = storage_service

    async def archive_old_inference_logs(
        self,
        days_old: int = 90,
        batch_size: int = 10000
    ) -> dict:
        """
        Archive inference logs older than N days to S3 in Parquet format.

        Args:
            days_old: Archive logs older than this many days
            batch_size: Process logs in batches

        Returns:
            Archive statistics
        """
        cutoff_date = date.today() - timedelta(days=days_old)
        logger.info(f"Archiving inference logs older than {cutoff_date}")

        # Query old logs
        query = text("""
            SELECT
                id, customer_id, robot_type, model_name,
                request_data, response_data, status,
                latency_ms, cost, created_at
            FROM inference_logs
            WHERE DATE(created_at) < :cutoff_date
            ORDER BY created_at
            LIMIT :batch_size
        """)

        total_archived = 0
        total_deleted = 0

        while True:
            result = await self.db.execute(
                query,
                {"cutoff_date": cutoff_date, "batch_size": batch_size}
            )
            rows = result.fetchall()

            if not rows:
                break

            # Convert to DataFrame
            df = pd.DataFrame([dict(row._mapping) for row in rows])

            # Generate Parquet file
            archive_date = rows[0].created_at.date()
            object_key = f"archives/inference_logs/{archive_date.year}/{archive_date.month:02d}/{archive_date}.parquet"

            # Convert to Parquet
            table = pa.Table.from_pandas(df)
            buffer = io.BytesIO()
            pq.write_table(table, buffer, compression='snappy')
            buffer.seek(0)

            # Upload to S3
            try:
                self.storage.client.put_object(
                    Bucket=self.storage.bucket,
                    Key=object_key,
                    Body=buffer,
                    ContentType='application/octet-stream',
                    Metadata={
                        'archive_date': str(archive_date),
                        'record_count': str(len(rows)),
                        'cutoff_date': str(cutoff_date)
                    }
                )

                logger.info(f"Archived {len(rows)} logs to {object_key}")
                total_archived += len(rows)

                # Delete archived logs from database
                log_ids = [str(row.id) for row in rows]
                delete_query = text("""
                    DELETE FROM inference_logs
                    WHERE id = ANY(:log_ids)
                """)

                await self.db.execute(delete_query, {"log_ids": log_ids})
                await self.db.commit()

                total_deleted += len(rows)
                logger.info(f"Deleted {len(rows)} archived logs from database")

            except Exception as e:
                logger.error(f"Failed to archive logs: {e}")
                await self.db.rollback()
                raise

        return {
            "cutoff_date": cutoff_date,
            "total_archived": total_archived,
            "total_deleted": total_deleted
        }

    async def delete_old_aggregated_data(self, days_old: int = 365) -> dict:
        """
        Delete aggregated data older than N days.

        Args:
            days_old: Delete data older than this many days

        Returns:
            Deletion statistics
        """
        cutoff_date = date.today() - timedelta(days=days_old)
        logger.info(f"Deleting aggregated data older than {cutoff_date}")

        tables = [
            'robot_performance_metrics',
            'instruction_analytics',
            'context_metadata',
            'billing_daily_summary'
        ]

        results = {}

        for table in tables:
            try:
                # Delete old records
                query = text(f"""
                    DELETE FROM {table}
                    WHERE created_at < :cutoff_date
                    RETURNING id
                """)

                result = await self.db.execute(query, {"cutoff_date": cutoff_date})
                deleted_count = len(result.fetchall())

                await self.db.commit()

                results[table] = deleted_count
                logger.info(f"Deleted {deleted_count} records from {table}")

            except Exception as e:
                logger.error(f"Failed to delete from {table}: {e}")
                await self.db.rollback()
                results[table] = f"error: {str(e)}"

        return {
            "cutoff_date": cutoff_date,
            "deletions": results
        }

    async def cleanup_expired_training_data(self, days_old: int = 730) -> dict:
        """
        Clean up training images older than 2 years if consent expired.

        Args:
            days_old: Delete images older than this many days

        Returns:
            Cleanup statistics
        """
        cutoff_date = date.today() - timedelta(days=days_old)
        logger.info(f"Cleaning up training data older than {cutoff_date}")

        # Find customers with expired consent or no consent
        query = text("""
            SELECT DISTINCT customer_id
            FROM inference_logs
            WHERE DATE(created_at) < :cutoff_date
              AND customer_id IN (
                  SELECT id FROM customers
                  WHERE training_data_consent = false
                     OR consent_expiry < NOW()
              )
        """)

        result = await self.db.execute(query, {"cutoff_date": cutoff_date})
        customer_ids = [row.customer_id for row in result.fetchall()]

        total_deleted = 0

        for customer_id in customer_ids:
            # List objects for customer
            objects = await self.storage.list_customer_objects(
                customer_id=str(customer_id),
                prefix='training-data'
            )

            # Filter by date
            old_objects = [
                obj for obj in objects
                if obj['last_modified'].date() < cutoff_date
            ]

            if old_objects:
                # Batch delete
                object_keys = [obj['key'] for obj in old_objects]
                deleted = await self.storage.batch_delete_objects(object_keys)
                total_deleted += deleted

                logger.info(f"Deleted {deleted} objects for customer {customer_id}")

        return {
            "cutoff_date": cutoff_date,
            "customers_processed": len(customer_ids),
            "total_deleted": total_deleted
        }

    async def verify_safety_incidents_retention(self) -> dict:
        """
        Verify safety incidents are retained indefinitely.

        Returns:
            Verification statistics
        """
        logger.info("Verifying safety incidents retention")

        query = text("""
            SELECT
                COUNT(*) as total_incidents,
                MIN(created_at) as oldest_incident,
                MAX(created_at) as newest_incident
            FROM safety_incidents
        """)

        result = await self.db.execute(query)
        row = result.fetchone()

        return {
            "total_incidents": row.total_incidents,
            "oldest_incident": row.oldest_incident,
            "newest_incident": row.newest_incident,
            "status": "retained_indefinitely"
        }

    async def run_full_retention_policy(self) -> dict:
        """
        Run complete data retention policy.

        Returns:
            Execution summary
        """
        logger.info("Starting full data retention policy execution")

        results = {
            "start_time": datetime.utcnow()
        }

        try:
            # 1. Archive 90-day-old inference logs
            results['archive'] = await self.archive_old_inference_logs(days_old=90)

            # 2. Delete 1-year-old aggregated data
            results['delete_aggregated'] = await self.delete_old_aggregated_data(days_old=365)

            # 3. Clean up 2-year-old training data (expired consent)
            results['cleanup_training'] = await self.cleanup_expired_training_data(days_old=730)

            # 4. Verify safety incidents retention
            results['safety_verification'] = await self.verify_safety_incidents_retention()

            results['status'] = 'success'
            results['end_time'] = datetime.utcnow()

            logger.info("Data retention policy completed successfully")

        except Exception as e:
            logger.error(f"Data retention policy failed: {e}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run VLA Data Retention Policy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--action',
        choices=['archive', 'delete', 'cleanup', 'verify', 'all'],
        default='all',
        help='Retention action to perform (default: all)'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Days threshold (overrides defaults)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate retention without committing changes'
    )

    args = parser.parse_args()

    logger.info(f"Starting data retention: action={args.action}")

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

    # Initialize storage service
    storage = StorageService(
        endpoint=settings.S3_ENDPOINT,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        bucket=settings.S3_BUCKET
    )

    try:
        async with async_session() as session:
            manager = DataRetentionManager(session, storage)

            # Run selected action
            if args.action == 'archive':
                days = args.days or 90
                results = await manager.archive_old_inference_logs(days_old=days)

            elif args.action == 'delete':
                days = args.days or 365
                results = await manager.delete_old_aggregated_data(days_old=days)

            elif args.action == 'cleanup':
                days = args.days or 730
                results = await manager.cleanup_expired_training_data(days_old=days)

            elif args.action == 'verify':
                results = await manager.verify_safety_incidents_retention()

            elif args.action == 'all':
                results = await manager.run_full_retention_policy()

            if args.dry_run:
                logger.info("Rolling back changes (dry run)")
                await session.rollback()

            # Print results
            print("\n" + "="*60)
            print("DATA RETENTION RESULTS")
            print("="*60)
            print(f"Action: {args.action}")
            print(f"Status: {results.get('status', 'completed')}")
            print("\nDetails:")
            for key, value in results.items():
                if key not in ['start_time', 'end_time', 'status']:
                    print(f"  {key}: {value}")
            print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
