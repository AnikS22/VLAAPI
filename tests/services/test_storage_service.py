"""
Comprehensive tests for StorageService (S3/MinIO integration).

Tests:
- S3/MinIO connection and bucket operations
- Training image upload with metadata
- Embedding upload (numpy arrays)
- Presigned URL generation
- Batch operations (upload/delete)
- Consent checks before storage
- Error handling (network failures, missing objects)
"""

import pytest
import io
import numpy as np
from PIL import Image
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError

from src.services.storage.storage_service import StorageService


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 S3 client."""
    client = MagicMock()

    # Mock successful operations
    client.head_bucket.return_value = {}
    client.create_bucket.return_value = {}
    client.put_object.return_value = {
        'ETag': '"mock-etag"',
        'VersionId': 'mock-version'
    }
    client.get_object.return_value = {
        'Body': MagicMock(),
        'Metadata': {}
    }
    client.list_objects_v2.return_value = {
        'Contents': []
    }
    client.delete_object.return_value = {}
    client.delete_objects.return_value = {
        'Deleted': []
    }
    client.generate_presigned_url.return_value = 'https://mock-url.com/object?signature=xyz'

    return client


@pytest.fixture
def storage_service(mock_boto3_client):
    """Create StorageService with mocked boto3 client."""
    with patch('src.services.storage.storage_service.boto3.client', return_value=mock_boto3_client):
        service = StorageService(
            endpoint='http://localhost:9000',
            access_key='test-key',
            secret_key='test-secret',
            bucket='test-bucket'
        )
        service.client = mock_boto3_client
        return service


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    return Image.new("RGB", (224, 224), color=(255, 0, 0))


@pytest.fixture
def sample_embedding():
    """Create a sample embedding vector."""
    return np.random.randn(768).astype(np.float32)


@pytest.mark.asyncio
class TestStorageServiceConnection:
    """Test S3/MinIO connection and bucket operations."""

    async def test_bucket_exists(self, storage_service, mock_boto3_client):
        """Test bucket existence check."""
        mock_boto3_client.head_bucket.return_value = {}

        # Bucket should exist (called during initialization)
        mock_boto3_client.head_bucket.assert_called()

    async def test_bucket_creation(self, mock_boto3_client):
        """Test bucket creation when it doesn't exist."""
        # Simulate bucket not found
        mock_boto3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}},
            'HeadBucket'
        )
        mock_boto3_client.create_bucket.return_value = {}

        with patch('src.services.storage.storage_service.boto3.client', return_value=mock_boto3_client):
            service = StorageService(
                endpoint='http://localhost:9000',
                access_key='test-key',
                secret_key='test-secret',
                bucket='new-bucket'
            )

            mock_boto3_client.create_bucket.assert_called_once()

    async def test_connection_error_handling(self, mock_boto3_client):
        """Test handling of connection errors."""
        mock_boto3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '403', 'Message': 'Forbidden'}},
            'HeadBucket'
        )

        with patch('src.services.storage.storage_service.boto3.client', return_value=mock_boto3_client):
            with pytest.raises(ClientError):
                StorageService(
                    endpoint='http://localhost:9000',
                    access_key='invalid-key',
                    secret_key='invalid-secret',
                    bucket='test-bucket'
                )


@pytest.mark.asyncio
class TestTrainingImageUpload:
    """Test training image upload functionality."""

    async def test_upload_training_image_success(
        self,
        storage_service,
        mock_boto3_client,
        sample_image
    ):
        """Test successful training image upload."""
        customer_id = "customer-123"
        inference_id = "inference-456"
        metadata = {
            "robot_type": "ur5",
            "model_name": "openvla-7b",
            "timestamp": datetime.utcnow().isoformat()
        }

        object_key = await storage_service.upload_training_image(
            customer_id=customer_id,
            inference_id=inference_id,
            image=sample_image,
            metadata=metadata,
            consent_given=True
        )

        assert object_key == f"training-data/{customer_id}/{inference_id}.jpg"
        assert mock_boto3_client.put_object.call_count == 2  # Image + metadata

    async def test_upload_without_consent(
        self,
        storage_service,
        mock_boto3_client,
        sample_image
    ):
        """Test that upload is skipped when consent is not given."""
        object_key = await storage_service.upload_training_image(
            customer_id="customer-123",
            inference_id="inference-456",
            image=sample_image,
            metadata={},
            consent_given=False
        )

        assert object_key is None
        mock_boto3_client.put_object.assert_not_called()

    async def test_upload_training_image_network_failure(
        self,
        storage_service,
        mock_boto3_client,
        sample_image
    ):
        """Test handling of network failures during upload."""
        mock_boto3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'NetworkError', 'Message': 'Connection timeout'}},
            'PutObject'
        )

        with pytest.raises(ClientError):
            await storage_service.upload_training_image(
                customer_id="customer-123",
                inference_id="inference-456",
                image=sample_image,
                metadata={},
                consent_given=True
            )


@pytest.mark.asyncio
class TestEmbeddingUpload:
    """Test embedding upload functionality."""

    async def test_upload_embedding_success(
        self,
        storage_service,
        mock_boto3_client,
        sample_embedding
    ):
        """Test successful embedding upload."""
        customer_id = "customer-123"
        inference_id = "inference-456"
        embedding_type = "clip"

        object_key = await storage_service.upload_embedding(
            customer_id=customer_id,
            inference_id=inference_id,
            embedding=sample_embedding,
            embedding_type=embedding_type
        )

        expected_key = f"embeddings/{customer_id}/{inference_id}_{embedding_type}.npy"
        assert object_key == expected_key
        mock_boto3_client.put_object.assert_called_once()

        # Verify metadata
        call_args = mock_boto3_client.put_object.call_args
        assert call_args[1]['Metadata']['embedding_type'] == embedding_type
        assert call_args[1]['Metadata']['shape'] == str(sample_embedding.shape)

    async def test_upload_embedding_with_metadata(
        self,
        storage_service,
        mock_boto3_client,
        sample_embedding
    ):
        """Test embedding upload with additional metadata."""
        metadata = {
            "model": "openai/clip-vit-base-patch32",
            "version": "1.0"
        }

        object_key = await storage_service.upload_embedding(
            customer_id="customer-123",
            inference_id="inference-456",
            embedding=sample_embedding,
            embedding_type="instruction",
            metadata=metadata
        )

        assert object_key is not None
        call_args = mock_boto3_client.put_object.call_args
        assert call_args[1]['Metadata']['model'] == metadata['model']

    async def test_download_embedding_success(
        self,
        storage_service,
        mock_boto3_client,
        sample_embedding
    ):
        """Test successful embedding download."""
        # Mock the response with numpy array
        buffer = io.BytesIO()
        np.save(buffer, sample_embedding)
        buffer.seek(0)

        mock_response = MagicMock()
        mock_response.read.return_value = buffer.getvalue()
        mock_boto3_client.get_object.return_value = {
            'Body': mock_response
        }

        downloaded = await storage_service.download_embedding(
            customer_id="customer-123",
            inference_id="inference-456",
            embedding_type="clip"
        )

        assert downloaded is not None
        assert np.array_equal(downloaded, sample_embedding)

    async def test_download_embedding_not_found(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test handling of missing embedding."""
        mock_boto3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
            'GetObject'
        )

        result = await storage_service.download_embedding(
            customer_id="customer-123",
            inference_id="inference-456",
            embedding_type="clip"
        )

        assert result is None


@pytest.mark.asyncio
class TestPresignedUrls:
    """Test presigned URL generation."""

    async def test_generate_presigned_url_image(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test presigned URL generation for training image."""
        url = await storage_service.get_presigned_url(
            customer_id="customer-123",
            inference_id="inference-456",
            resource_type="image",
            expires_in=3600
        )

        assert url is not None
        assert url.startswith("https://")
        mock_boto3_client.generate_presigned_url.assert_called_once()

    async def test_generate_presigned_url_metadata(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test presigned URL generation for metadata."""
        url = await storage_service.get_presigned_url(
            customer_id="customer-123",
            inference_id="inference-456",
            resource_type="metadata"
        )

        assert url is not None
        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert "metadata.json" in call_args[1]['Params']['Key']

    async def test_generate_presigned_url_embedding(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test presigned URL generation for embedding."""
        url = await storage_service.get_presigned_url(
            customer_id="customer-123",
            inference_id="inference-456",
            resource_type="embedding_clip"
        )

        assert url is not None
        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert "clip.npy" in call_args[1]['Params']['Key']

    async def test_invalid_resource_type(self, storage_service):
        """Test error handling for invalid resource type."""
        with pytest.raises(ValueError):
            await storage_service.get_presigned_url(
                customer_id="customer-123",
                inference_id="inference-456",
                resource_type="invalid"
            )


@pytest.mark.asyncio
class TestBatchOperations:
    """Test batch upload and delete operations."""

    async def test_batch_upload_embeddings(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test batch embedding upload."""
        embeddings = [
            {
                'customer_id': f'customer-{i}',
                'inference_id': f'inference-{i}',
                'embedding': np.random.randn(768).astype(np.float32),
                'embedding_type': 'clip',
                'metadata': {'index': i}
            }
            for i in range(10)
        ]

        uploaded_keys = await storage_service.batch_upload_embeddings(embeddings)

        assert len(uploaded_keys) == 10
        assert mock_boto3_client.put_object.call_count == 10

    async def test_batch_upload_with_failures(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test batch upload with some failures."""
        # Make some uploads fail
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:  # Fail every 3rd upload
                raise ClientError(
                    {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Retry'}},
                    'PutObject'
                )
            return {'ETag': 'mock-etag'}

        mock_boto3_client.put_object.side_effect = side_effect

        embeddings = [
            {
                'customer_id': f'customer-{i}',
                'inference_id': f'inference-{i}',
                'embedding': np.random.randn(768).astype(np.float32),
                'embedding_type': 'clip'
            }
            for i in range(10)
        ]

        uploaded_keys = await storage_service.batch_upload_embeddings(embeddings)

        # Should have 7 successful uploads (10 - 3 failures)
        assert len(uploaded_keys) == 7

    async def test_batch_delete_objects(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test batch object deletion."""
        object_keys = [f"training-data/customer-123/inference-{i}.jpg" for i in range(100)]

        mock_boto3_client.delete_objects.return_value = {
            'Deleted': [{'Key': key} for key in object_keys]
        }

        deleted_count = await storage_service.batch_delete_objects(object_keys)

        assert deleted_count == 100
        mock_boto3_client.delete_objects.assert_called_once()

    async def test_batch_delete_large_dataset(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test batch delete with more than 1000 objects (S3 limit)."""
        object_keys = [f"training-data/customer-123/inference-{i}.jpg" for i in range(2500)]

        mock_boto3_client.delete_objects.return_value = {
            'Deleted': []
        }

        deleted_count = await storage_service.batch_delete_objects(object_keys)

        # Should be called 3 times (1000 + 1000 + 500)
        assert mock_boto3_client.delete_objects.call_count == 3
        assert deleted_count == 2500


@pytest.mark.asyncio
class TestObjectListing:
    """Test object listing operations."""

    async def test_list_customer_objects(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test listing objects for a customer."""
        mock_boto3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'training-data/customer-123/inference-1.jpg',
                    'Size': 1024,
                    'LastModified': datetime.utcnow(),
                    'ETag': '"etag1"'
                },
                {
                    'Key': 'training-data/customer-123/inference-2.jpg',
                    'Size': 2048,
                    'LastModified': datetime.utcnow(),
                    'ETag': '"etag2"'
                }
            ]
        }

        objects = await storage_service.list_customer_objects(
            customer_id="customer-123",
            prefix="training-data"
        )

        assert len(objects) == 2
        assert objects[0]['key'] == 'training-data/customer-123/inference-1.jpg'
        assert objects[0]['size'] == 1024

    async def test_list_customer_objects_empty(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test listing when no objects exist."""
        mock_boto3_client.list_objects_v2.return_value = {}

        objects = await storage_service.list_customer_objects(
            customer_id="customer-999"
        )

        assert len(objects) == 0


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_delete_object_error(
        self,
        storage_service,
        mock_boto3_client
    ):
        """Test error handling during object deletion."""
        mock_boto3_client.delete_object.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Server error'}},
            'DeleteObject'
        )

        result = await storage_service.delete_object("some-key")

        assert result is False

    async def test_network_timeout(
        self,
        storage_service,
        mock_boto3_client,
        sample_image
    ):
        """Test handling of network timeouts."""
        mock_boto3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'RequestTimeout', 'Message': 'Timeout'}},
            'PutObject'
        )

        with pytest.raises(ClientError) as exc_info:
            await storage_service.upload_training_image(
                customer_id="customer-123",
                inference_id="inference-456",
                image=sample_image,
                metadata={},
                consent_given=True
            )

        assert exc_info.value.response['Error']['Code'] == 'RequestTimeout'
