"""
ETL Pipeline for VLA Inference Analytics

Aggregates raw inference logs into:
- robot_performance_metrics
- instruction_analytics
- context_metadata
- Materialized views (daily_usage_summary, monthly_billing_summary, safety_trend_summary)

Runs daily via cron/scheduler.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import hashlib

import asyncpg
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import (
    RobotPerformanceMetrics,
    InstructionAnalytics,
    ContextMetadata,
    InferenceLog,
    SafetyIncident
)

logger = logging.getLogger(__name__)


class ETLPipeline:
    """ETL pipeline for aggregating VLA inference data."""

    def __init__(self, db_session: AsyncSession, batch_size: int = 1000):
        """
        Initialize ETL pipeline.

        Args:
            db_session: SQLAlchemy async session
            batch_size: Batch size for processing
        """
        self.db = db_session
        self.batch_size = batch_size

    async def aggregate_robot_performance(self, target_date: date) -> Dict:
        """
        Aggregate robot performance metrics from inference logs.

        Groups by: customer_id, robot_type, model_name, date
        Computes:
            - success_rate (exponential moving average)
            - avg_latency_ms
            - p50, p95, p99 latency
            - action_stats (JSON with action distribution)
            - error_rate
            - total_inferences

        Args:
            target_date: Date to aggregate

        Returns:
            Aggregation statistics
        """
        logger.info(f"Aggregating robot performance for {target_date}")

        # Query to aggregate inference logs by robot/model
        query = text("""
            WITH daily_stats AS (
                SELECT
                    customer_id,
                    robot_type,
                    model_name,
                    :target_date::date as metric_date,
                    COUNT(*) as total_inferences,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful_inferences,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_inferences,
                    AVG(latency_ms) as avg_latency,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency,
                    jsonb_object_agg(
                        COALESCE((response_data->>'predicted_action')::text, 'unknown'),
                        COUNT(*)
                    ) as action_distribution
                FROM inference_logs
                WHERE DATE(created_at) = :target_date
                GROUP BY customer_id, robot_type, model_name
            )
            SELECT * FROM daily_stats
        """)

        result = await self.db.execute(query, {"target_date": target_date})
        rows = result.fetchall()

        metrics_created = 0
        metrics_updated = 0

        for row in rows:
            customer_id = row.customer_id
            robot_type = row.robot_type
            model_name = row.model_name

            # Calculate metrics
            success_rate = row.successful_inferences / row.total_inferences if row.total_inferences > 0 else 0.0
            error_rate = row.failed_inferences / row.total_inferences if row.total_inferences > 0 else 0.0

            # Check if metric already exists
            existing_query = text("""
                SELECT id, success_rate, total_inferences
                FROM robot_performance_metrics
                WHERE customer_id = :customer_id
                  AND robot_type = :robot_type
                  AND model_name = :model_name
                  AND metric_date = :metric_date
            """)

            existing = await self.db.execute(
                existing_query,
                {
                    "customer_id": customer_id,
                    "robot_type": robot_type,
                    "model_name": model_name,
                    "metric_date": target_date
                }
            )
            existing_row = existing.fetchone()

            if existing_row:
                # Update with exponential moving average (alpha = 0.3)
                alpha = 0.3
                new_success_rate = alpha * success_rate + (1 - alpha) * existing_row.success_rate
                new_total = existing_row.total_inferences + row.total_inferences

                update_query = text("""
                    UPDATE robot_performance_metrics
                    SET success_rate = :success_rate,
                        error_rate = :error_rate,
                        avg_latency_ms = :avg_latency,
                        p50_latency_ms = :p50_latency,
                        p95_latency_ms = :p95_latency,
                        p99_latency_ms = :p99_latency,
                        action_stats = :action_stats,
                        total_inferences = :total_inferences,
                        updated_at = NOW()
                    WHERE id = :id
                """)

                await self.db.execute(
                    update_query,
                    {
                        "id": existing_row.id,
                        "success_rate": new_success_rate,
                        "error_rate": error_rate,
                        "avg_latency": row.avg_latency,
                        "p50_latency": row.p50_latency,
                        "p95_latency": row.p95_latency,
                        "p99_latency": row.p99_latency,
                        "action_stats": row.action_distribution,
                        "total_inferences": new_total
                    }
                )

                metrics_updated += 1
            else:
                # Insert new metric
                insert_query = text("""
                    INSERT INTO robot_performance_metrics (
                        customer_id, robot_type, model_name, metric_date,
                        success_rate, error_rate, avg_latency_ms,
                        p50_latency_ms, p95_latency_ms, p99_latency_ms,
                        action_stats, total_inferences
                    ) VALUES (
                        :customer_id, :robot_type, :model_name, :metric_date,
                        :success_rate, :error_rate, :avg_latency,
                        :p50_latency, :p95_latency, :p99_latency,
                        :action_stats, :total_inferences
                    )
                """)

                await self.db.execute(
                    insert_query,
                    {
                        "customer_id": customer_id,
                        "robot_type": robot_type,
                        "model_name": model_name,
                        "metric_date": target_date,
                        "success_rate": success_rate,
                        "error_rate": error_rate,
                        "avg_latency": row.avg_latency,
                        "p50_latency": row.p50_latency,
                        "p95_latency": row.p95_latency,
                        "p99_latency": row.p99_latency,
                        "action_stats": row.action_distribution,
                        "total_inferences": row.total_inferences
                    }
                )

                metrics_created += 1

        await self.db.commit()

        logger.info(
            f"Robot performance aggregation complete: "
            f"{metrics_created} created, {metrics_updated} updated"
        )

        return {
            "date": target_date,
            "metrics_created": metrics_created,
            "metrics_updated": metrics_updated,
            "total_processed": len(rows)
        }

    async def aggregate_instruction_analytics(self, target_date: date) -> Dict:
        """
        Aggregate instruction analytics from inference logs.

        - Deduplicates instructions by SHA256 hash
        - Increments total_uses for existing instructions
        - Generates embeddings for new instructions (placeholder)
        - Updates success_rate, avg_safety_score

        Args:
            target_date: Date to aggregate

        Returns:
            Aggregation statistics
        """
        logger.info(f"Aggregating instruction analytics for {target_date}")

        # Query to get unique instructions for the date
        query = text("""
            SELECT
                (request_data->>'instruction')::text as instruction,
                robot_type,
                COUNT(*) as usage_count,
                AVG((response_data->>'safety_score')::float) as avg_safety_score,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_count
            FROM inference_logs
            WHERE DATE(created_at) = :target_date
              AND request_data->>'instruction' IS NOT NULL
            GROUP BY instruction, robot_type
        """)

        result = await self.db.execute(query, {"target_date": target_date})
        rows = result.fetchall()

        instructions_created = 0
        instructions_updated = 0

        for row in rows:
            instruction_text = row.instruction
            robot_type = row.robot_type

            # Generate SHA256 hash for deduplication
            instruction_hash = hashlib.sha256(instruction_text.encode()).hexdigest()

            # Calculate metrics
            success_rate = row.successful_count / row.usage_count if row.usage_count > 0 else 0.0

            # Check if instruction already exists
            existing_query = text("""
                SELECT id, total_uses, success_rate
                FROM instruction_analytics
                WHERE instruction_hash = :instruction_hash
                  AND robot_type = :robot_type
            """)

            existing = await self.db.execute(
                existing_query,
                {
                    "instruction_hash": instruction_hash,
                    "robot_type": robot_type
                }
            )
            existing_row = existing.fetchone()

            if existing_row:
                # Update existing instruction
                new_total_uses = existing_row.total_uses + row.usage_count

                # Update success rate with weighted average
                new_success_rate = (
                    (existing_row.success_rate * existing_row.total_uses +
                     success_rate * row.usage_count) / new_total_uses
                )

                update_query = text("""
                    UPDATE instruction_analytics
                    SET total_uses = :total_uses,
                        success_rate = :success_rate,
                        avg_safety_score = :avg_safety_score,
                        last_used_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :id
                """)

                await self.db.execute(
                    update_query,
                    {
                        "id": existing_row.id,
                        "total_uses": new_total_uses,
                        "success_rate": new_success_rate,
                        "avg_safety_score": row.avg_safety_score
                    }
                )

                instructions_updated += 1
            else:
                # Insert new instruction
                # TODO: Generate embedding using CLIP/sentence-transformers
                # For now, use placeholder zero vector
                embedding_dim = 768
                embedding = np.zeros(embedding_dim)

                insert_query = text("""
                    INSERT INTO instruction_analytics (
                        instruction_text, instruction_hash, robot_type,
                        total_uses, success_rate, avg_safety_score,
                        embedding, first_seen_at, last_used_at
                    ) VALUES (
                        :instruction_text, :instruction_hash, :robot_type,
                        :total_uses, :success_rate, :avg_safety_score,
                        :embedding, :first_seen_at, :last_used_at
                    )
                """)

                await self.db.execute(
                    insert_query,
                    {
                        "instruction_text": instruction_text,
                        "instruction_hash": instruction_hash,
                        "robot_type": robot_type,
                        "total_uses": row.usage_count,
                        "success_rate": success_rate,
                        "avg_safety_score": row.avg_safety_score,
                        "embedding": embedding.tolist(),
                        "first_seen_at": datetime.utcnow(),
                        "last_used_at": datetime.utcnow()
                    }
                )

                instructions_created += 1

        await self.db.commit()

        logger.info(
            f"Instruction analytics aggregation complete: "
            f"{instructions_created} created, {instructions_updated} updated"
        )

        return {
            "date": target_date,
            "instructions_created": instructions_created,
            "instructions_updated": instructions_updated,
            "total_processed": len(rows)
        }

    async def aggregate_context_metadata(self, target_date: date) -> Dict:
        """
        Aggregate context metadata from inference logs.

        Extracts environmental patterns and stores with embeddings
        (only if customer consent is given).

        Args:
            target_date: Date to aggregate

        Returns:
            Aggregation statistics
        """
        logger.info(f"Aggregating context metadata for {target_date}")

        # Query to get context data with consent
        query = text("""
            SELECT
                il.customer_id,
                il.robot_type,
                il.request_data->>'context_description' as context_description,
                il.request_data->'environmental_context' as env_context,
                COUNT(*) as usage_count
            FROM inference_logs il
            INNER JOIN customers c ON il.customer_id = c.id
            WHERE DATE(il.created_at) = :target_date
              AND c.training_data_consent = true
              AND il.request_data->>'context_description' IS NOT NULL
            GROUP BY
                il.customer_id,
                il.robot_type,
                il.request_data->>'context_description',
                il.request_data->'environmental_context'
        """)

        result = await self.db.execute(query, {"target_date": target_date})
        rows = result.fetchall()

        contexts_created = 0

        for row in rows:
            # Generate context hash for deduplication
            context_str = f"{row.context_description}_{row.env_context}"
            context_hash = hashlib.sha256(context_str.encode()).hexdigest()

            # Check if context already exists
            existing_query = text("""
                SELECT id FROM context_metadata
                WHERE context_hash = :context_hash
                  AND customer_id = :customer_id
            """)

            existing = await self.db.execute(
                existing_query,
                {
                    "context_hash": context_hash,
                    "customer_id": row.customer_id
                }
            )

            if not existing.fetchone():
                # Generate embedding (placeholder)
                embedding = np.zeros(768)

                insert_query = text("""
                    INSERT INTO context_metadata (
                        customer_id, robot_type, context_description,
                        environmental_context, context_hash, embedding,
                        usage_count, first_seen_at
                    ) VALUES (
                        :customer_id, :robot_type, :context_description,
                        :env_context, :context_hash, :embedding,
                        :usage_count, :first_seen_at
                    )
                """)

                await self.db.execute(
                    insert_query,
                    {
                        "customer_id": row.customer_id,
                        "robot_type": row.robot_type,
                        "context_description": row.context_description,
                        "env_context": row.env_context,
                        "context_hash": context_hash,
                        "embedding": embedding.tolist(),
                        "usage_count": row.usage_count,
                        "first_seen_at": datetime.utcnow()
                    }
                )

                contexts_created += 1

        await self.db.commit()

        logger.info(f"Context metadata aggregation complete: {contexts_created} created")

        return {
            "date": target_date,
            "contexts_created": contexts_created,
            "total_processed": len(rows)
        }

    async def refresh_materialized_views(self) -> Dict:
        """
        Refresh all materialized views concurrently.

        Views:
            - daily_usage_summary
            - monthly_billing_summary
            - safety_trend_summary

        Returns:
            Refresh status for each view
        """
        logger.info("Refreshing materialized views")

        views = [
            "daily_usage_summary",
            "monthly_billing_summary",
            "safety_trend_summary"
        ]

        results = {}

        for view in views:
            try:
                query = text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
                await self.db.execute(query)
                results[view] = "success"
                logger.info(f"Refreshed materialized view: {view}")
            except Exception as e:
                logger.error(f"Failed to refresh {view}: {e}")
                results[view] = f"error: {str(e)}"

        await self.db.commit()

        return results

    async def compute_billing_summaries(self, target_date: date) -> Dict:
        """
        Compute billing summaries for daily/monthly costs.

        Args:
            target_date: Date to compute billing for

        Returns:
            Billing summary statistics
        """
        logger.info(f"Computing billing summaries for {target_date}")

        # Daily billing aggregation
        query = text("""
            INSERT INTO billing_daily_summary (
                customer_id, date, total_inferences,
                total_cost_usd, model_breakdown
            )
            SELECT
                customer_id,
                :target_date::date as date,
                COUNT(*) as total_inferences,
                SUM(cost) as total_cost_usd,
                jsonb_object_agg(model_name, COUNT(*)) as model_breakdown
            FROM inference_logs
            WHERE DATE(created_at) = :target_date
            GROUP BY customer_id
            ON CONFLICT (customer_id, date)
            DO UPDATE SET
                total_inferences = EXCLUDED.total_inferences,
                total_cost_usd = EXCLUDED.total_cost_usd,
                model_breakdown = EXCLUDED.model_breakdown,
                updated_at = NOW()
        """)

        await self.db.execute(query, {"target_date": target_date})
        await self.db.commit()

        logger.info("Billing summaries computed")

        return {"date": target_date, "status": "success"}

    async def run_full_pipeline(self, target_date: Optional[date] = None) -> Dict:
        """
        Run complete ETL pipeline for a specific date.

        Args:
            target_date: Date to process (defaults to yesterday)

        Returns:
            Pipeline execution summary
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        logger.info(f"Starting full ETL pipeline for {target_date}")

        results = {}

        try:
            # 1. Aggregate robot performance
            results['robot_performance'] = await self.aggregate_robot_performance(target_date)

            # 2. Aggregate instruction analytics
            results['instruction_analytics'] = await self.aggregate_instruction_analytics(target_date)

            # 3. Aggregate context metadata
            results['context_metadata'] = await self.aggregate_context_metadata(target_date)

            # 4. Compute billing summaries
            results['billing'] = await self.compute_billing_summaries(target_date)

            # 5. Refresh materialized views
            results['materialized_views'] = await self.refresh_materialized_views()

            logger.info(f"ETL pipeline completed successfully for {target_date}")
            results['status'] = 'success'

        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results
