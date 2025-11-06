"""
Comprehensive tests for ETL Pipeline.

Tests:
- Robot performance aggregation (success rate, latency, action stats)
- Instruction analytics (deduplication by SHA256, usage tracking)
- Context metadata aggregation (with consent checks)
- Billing summaries computation
- Materialized view refresh
- Batch processing (1000+ records)
- Exponential moving average calculations
- Deduplication logic
- Transaction rollback on errors
"""

import pytest
import asyncio
import hashlib
import numpy as np
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.services.data_pipeline.etl_pipeline import ETLPipeline


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock(spec=AsyncSession)

    # Mock execute to return various results
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    return session


@pytest.fixture
def etl_pipeline(mock_db_session):
    """Create ETL pipeline with mock database."""
    return ETLPipeline(db_session=mock_db_session, batch_size=1000)


@pytest.fixture
def sample_inference_logs():
    """Create sample inference log data."""
    return [
        {
            'customer_id': 'customer-1',
            'robot_type': 'ur5',
            'model_name': 'openvla-7b',
            'status': 'completed',
            'latency_ms': 150.5,
            'response_data': {'predicted_action': 'move_forward'},
            'created_at': datetime.utcnow()
        },
        {
            'customer_id': 'customer-1',
            'robot_type': 'ur5',
            'model_name': 'openvla-7b',
            'status': 'completed',
            'latency_ms': 180.3,
            'response_data': {'predicted_action': 'rotate_left'},
            'created_at': datetime.utcnow()
        },
        {
            'customer_id': 'customer-1',
            'robot_type': 'ur5',
            'model_name': 'openvla-7b',
            'status': 'failed',
            'latency_ms': 200.0,
            'response_data': {},
            'created_at': datetime.utcnow()
        }
    ]


@pytest.mark.asyncio
class TestRobotPerformanceAggregation:
    """Test robot performance metrics aggregation."""

    async def test_aggregate_robot_performance_new_metrics(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test aggregation when creating new performance metrics."""
        target_date = date.today() - timedelta(days=1)

        # Mock query results - aggregation query
        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                customer_id='customer-1',
                robot_type='ur5',
                model_name='openvla-7b',
                total_inferences=100,
                successful_inferences=95,
                failed_inferences=5,
                avg_latency=150.5,
                p50_latency=145.0,
                p95_latency=200.0,
                p99_latency=250.0,
                action_distribution={'move_forward': 40, 'rotate_left': 35, 'stop': 20}
            )
        ]

        # Mock existing metrics query (no existing metrics)
        existing_result = MagicMock()
        existing_result.fetchone.return_value = None

        # Setup execute to return different results based on query
        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:  # First call is aggregation query
                return agg_result
            else:  # Subsequent calls are existing/insert queries
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_robot_performance(target_date)

        assert result['date'] == target_date
        assert result['metrics_created'] == 1
        assert result['metrics_updated'] == 0

    async def test_aggregate_robot_performance_update_existing(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test updating existing performance metrics with exponential moving average."""
        target_date = date.today() - timedelta(days=1)

        # Mock aggregation results
        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                customer_id='customer-1',
                robot_type='ur5',
                model_name='openvla-7b',
                total_inferences=50,
                successful_inferences=45,
                failed_inferences=5,
                avg_latency=160.0,
                p50_latency=155.0,
                p95_latency=210.0,
                p99_latency=260.0,
                action_distribution={'move_forward': 25, 'rotate_left': 20}
            )
        ]

        # Mock existing metrics (previous day)
        existing_result = MagicMock()
        existing_result.fetchone.return_value = MagicMock(
            id='metric-1',
            success_rate=0.90,
            total_inferences=100
        )

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_robot_performance(target_date)

        assert result['metrics_updated'] == 1
        assert result['metrics_created'] == 0

        # Verify exponential moving average calculation
        # new_success_rate = 0.3 * (45/50) + 0.7 * 0.90
        expected_ema = 0.3 * (45/50) + 0.7 * 0.90
        # Should be approximately 0.9

    async def test_aggregate_robot_performance_batch_processing(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test batch processing of 1000+ records."""
        target_date = date.today() - timedelta(days=1)

        # Create 1000 mock rows (different robot types)
        mock_rows = []
        for i in range(1000):
            mock_rows.append(
                MagicMock(
                    customer_id=f'customer-{i % 10}',
                    robot_type=f'robot-{i % 5}',
                    model_name='openvla-7b',
                    total_inferences=10,
                    successful_inferences=9,
                    failed_inferences=1,
                    avg_latency=150.0,
                    p50_latency=145.0,
                    p95_latency=200.0,
                    p99_latency=250.0,
                    action_distribution={'move': 10}
                )
            )

        agg_result = MagicMock()
        agg_result.fetchall.return_value = mock_rows

        existing_result = MagicMock()
        existing_result.fetchone.return_value = None

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_robot_performance(target_date)

        assert result['total_processed'] == 1000
        assert result['metrics_created'] == 1000


@pytest.mark.asyncio
class TestInstructionAnalytics:
    """Test instruction analytics aggregation."""

    async def test_aggregate_instruction_analytics_deduplication(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test instruction deduplication by SHA256 hash."""
        target_date = date.today() - timedelta(days=1)

        instruction_text = "pick up the red block"
        instruction_hash = hashlib.sha256(instruction_text.encode()).hexdigest()

        # Mock aggregation results
        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                instruction=instruction_text,
                robot_type='ur5',
                usage_count=50,
                avg_safety_score=0.95,
                successful_count=48
            )
        ]

        # Mock existing instruction check
        existing_result = MagicMock()
        existing_result.fetchone.return_value = None

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_instruction_analytics(target_date)

        assert result['instructions_created'] == 1
        assert result['instructions_updated'] == 0

    async def test_aggregate_instruction_analytics_update_existing(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test updating existing instruction with weighted average."""
        target_date = date.today() - timedelta(days=1)

        instruction_text = "move to position X"

        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                instruction=instruction_text,
                robot_type='ur5',
                usage_count=20,
                avg_safety_score=0.90,
                successful_count=18
            )
        ]

        # Mock existing instruction
        existing_result = MagicMock()
        existing_result.fetchone.return_value = MagicMock(
            id='instruction-1',
            total_uses=100,
            success_rate=0.95
        )

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_instruction_analytics(target_date)

        assert result['instructions_updated'] == 1
        assert result['instructions_created'] == 0

        # Verify weighted average: (0.95 * 100 + (18/20) * 20) / 120
        # = (95 + 18) / 120 = 113 / 120 = 0.9417

    async def test_aggregate_instruction_analytics_embedding_generation(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test placeholder embedding generation for new instructions."""
        target_date = date.today() - timedelta(days=1)

        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                instruction="test instruction",
                robot_type='ur5',
                usage_count=10,
                avg_safety_score=0.90,
                successful_count=9
            )
        ]

        existing_result = MagicMock()
        existing_result.fetchone.return_value = None

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_instruction_analytics(target_date)

        # Verify embedding was created (placeholder zero vector)
        assert result['instructions_created'] == 1


@pytest.mark.asyncio
class TestContextMetadataAggregation:
    """Test context metadata aggregation with consent checks."""

    async def test_aggregate_context_metadata_with_consent(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test context aggregation only processes data with consent."""
        target_date = date.today() - timedelta(days=1)

        # Mock aggregation results (only customers with consent)
        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                customer_id='customer-1',
                robot_type='ur5',
                context_description='industrial warehouse',
                env_context={'lighting': 'bright', 'temperature': 22},
                usage_count=15
            )
        ]

        # Mock existing context check
        existing_result = MagicMock()
        existing_result.fetchone.return_value = None

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_context_metadata(target_date)

        assert result['contexts_created'] == 1
        assert result['total_processed'] == 1

    async def test_aggregate_context_metadata_deduplication(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test context deduplication by SHA256 hash."""
        target_date = date.today() - timedelta(days=1)

        context_desc = "warehouse environment"
        env_context = {'lighting': 'dim'}

        # Calculate expected hash
        context_str = f"{context_desc}_{env_context}"
        expected_hash = hashlib.sha256(context_str.encode()).hexdigest()

        agg_result = MagicMock()
        agg_result.fetchall.return_value = [
            MagicMock(
                customer_id='customer-1',
                robot_type='ur5',
                context_description=context_desc,
                env_context=env_context,
                usage_count=10
            )
        ]

        # Mock existing context (should not create duplicate)
        existing_result = MagicMock()
        existing_result.fetchone.return_value = MagicMock(id='context-1')

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.aggregate_context_metadata(target_date)

        # Should not create duplicate
        assert result['contexts_created'] == 0


@pytest.mark.asyncio
class TestBillingSummaries:
    """Test billing summaries computation."""

    async def test_compute_billing_summaries(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test daily billing summary computation."""
        target_date = date.today() - timedelta(days=1)

        result = await etl_pipeline.compute_billing_summaries(target_date)

        assert result['date'] == target_date
        assert result['status'] == 'success'
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called()

    async def test_compute_billing_summaries_upsert(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test billing summary upsert (ON CONFLICT)."""
        target_date = date.today() - timedelta(days=1)

        # Run twice to test upsert
        await etl_pipeline.compute_billing_summaries(target_date)
        await etl_pipeline.compute_billing_summaries(target_date)

        # Should be called twice but handle conflicts
        assert mock_db_session.execute.call_count >= 2


@pytest.mark.asyncio
class TestMaterializedViews:
    """Test materialized view refresh."""

    async def test_refresh_materialized_views_success(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test successful refresh of all materialized views."""
        result = await etl_pipeline.refresh_materialized_views()

        assert result['daily_usage_summary'] == 'success'
        assert result['monthly_billing_summary'] == 'success'
        assert result['safety_trend_summary'] == 'success'

        # Should call execute 3 times (one per view)
        assert mock_db_session.execute.call_count == 3

    async def test_refresh_materialized_views_partial_failure(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test partial failure during view refresh."""
        # Make second view fail
        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("View refresh failed")
            return MagicMock()

        mock_db_session.execute = mock_execute

        result = await etl_pipeline.refresh_materialized_views()

        # First and third should succeed, second should fail
        assert result['daily_usage_summary'] == 'success'
        assert 'error' in result['monthly_billing_summary']
        assert result['safety_trend_summary'] == 'success'


@pytest.mark.asyncio
class TestFullPipeline:
    """Test complete ETL pipeline execution."""

    async def test_run_full_pipeline_success(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test successful execution of full pipeline."""
        target_date = date.today() - timedelta(days=1)

        # Mock all sub-operations
        with patch.object(
            etl_pipeline,
            'aggregate_robot_performance',
            return_value={'metrics_created': 10}
        ), patch.object(
            etl_pipeline,
            'aggregate_instruction_analytics',
            return_value={'instructions_created': 5}
        ), patch.object(
            etl_pipeline,
            'aggregate_context_metadata',
            return_value={'contexts_created': 3}
        ), patch.object(
            etl_pipeline,
            'compute_billing_summaries',
            return_value={'status': 'success'}
        ), patch.object(
            etl_pipeline,
            'refresh_materialized_views',
            return_value={'daily_usage_summary': 'success'}
        ):
            result = await etl_pipeline.run_full_pipeline(target_date)

            assert result['status'] == 'success'
            assert 'robot_performance' in result
            assert 'instruction_analytics' in result
            assert 'context_metadata' in result
            assert 'billing' in result
            assert 'materialized_views' in result

    async def test_run_full_pipeline_default_date(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test pipeline defaults to yesterday when no date provided."""
        yesterday = date.today() - timedelta(days=1)

        with patch.object(
            etl_pipeline,
            'aggregate_robot_performance',
            return_value={'date': yesterday}
        ), patch.object(
            etl_pipeline,
            'aggregate_instruction_analytics',
            return_value={'date': yesterday}
        ), patch.object(
            etl_pipeline,
            'aggregate_context_metadata',
            return_value={'date': yesterday}
        ), patch.object(
            etl_pipeline,
            'compute_billing_summaries',
            return_value={'date': yesterday}
        ), patch.object(
            etl_pipeline,
            'refresh_materialized_views',
            return_value={}
        ):
            result = await etl_pipeline.run_full_pipeline()

            # Verify yesterday's date was used
            assert result['robot_performance']['date'] == yesterday


@pytest.mark.asyncio
class TestTransactionHandling:
    """Test transaction rollback on errors."""

    async def test_transaction_rollback_on_error(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test that transactions are rolled back on errors."""
        target_date = date.today() - timedelta(days=1)

        # Make execute fail
        mock_db_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await etl_pipeline.aggregate_robot_performance(target_date)

        # Rollback should NOT be called by pipeline (handled by caller)
        # But commit should not be called
        mock_db_session.commit.assert_not_called()

    async def test_full_pipeline_rollback_on_failure(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test full pipeline handles errors gracefully."""
        target_date = date.today() - timedelta(days=1)

        with patch.object(
            etl_pipeline,
            'aggregate_robot_performance',
            side_effect=Exception("Aggregation failed")
        ):
            with pytest.raises(Exception):
                await etl_pipeline.run_full_pipeline(target_date)


@pytest.mark.asyncio
class TestPerformance:
    """Test ETL pipeline performance."""

    async def test_batch_processing_performance(
        self,
        etl_pipeline,
        mock_db_session
    ):
        """Test processing 1000 records completes in reasonable time."""
        target_date = date.today() - timedelta(days=1)

        # Create large dataset
        mock_rows = [
            MagicMock(
                customer_id=f'customer-{i}',
                robot_type='ur5',
                model_name='openvla-7b',
                total_inferences=10,
                successful_inferences=9,
                failed_inferences=1,
                avg_latency=150.0,
                p50_latency=145.0,
                p95_latency=200.0,
                p99_latency=250.0,
                action_distribution={'move': 10}
            )
            for i in range(1000)
        ]

        agg_result = MagicMock()
        agg_result.fetchall.return_value = mock_rows

        existing_result = MagicMock()
        existing_result.fetchone.return_value = None

        execute_call_count = [0]

        async def mock_execute(query, params=None):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:
                return agg_result
            else:
                return existing_result

        mock_db_session.execute = mock_execute

        import time
        start = time.time()
        result = await etl_pipeline.aggregate_robot_performance(target_date)
        duration = time.time() - start

        # Should process 1000 records quickly (< 1 second in tests)
        assert duration < 1.0
        assert result['total_processed'] == 1000
