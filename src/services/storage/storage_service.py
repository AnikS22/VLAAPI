"""
Storage Service for S3/MinIO Integration

Handles:
- Training image uploads with metadata
- Embedding storage (numpy arrays)
- Presigned URL generation
- Batch operations for ETL
"""

import io
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class StorageService:
    """S3/MinIO storage service for VLA training data and embeddings."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        secure: bool = True
    ):
        """
        Initialize storage service.

        Args:
            endpoint: S3/MinIO endpoint URL
            access_key: Access key ID
            secret_key: Secret access key
            bucket: Bucket name
            region: AWS region
            secure: Use HTTPS
        """
        self.endpoint = endpoint
        self.bucket = bucket

        # Configure boto3 client with retry logic
        config = Config(
            region_name=region,
            signature_version='s3v4',
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )

        self.client = boto3.client(
            's3',
            endpoint_url=endpoint if endpoint else None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
            use_ssl=secure
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"Bucket '{self.bucket}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Created bucket '{self.bucket}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise

    async def upload_training_image(
        self,
        customer_id: str,
        inference_id: str,
        image: Image.Image,
        metadata: Dict,
        consent_given: bool = True
    ) -> str:
        """
        Upload training image with metadata to S3.

        Args:
            customer_id: Customer UUID
            inference_id: Inference UUID
            image: PIL Image object
            metadata: Image metadata (robot_type, model, timestamp, etc.)
            consent_given: Whether customer gave consent for training data

        Returns:
            S3 object key
        """
        if not consent_given:
            logger.warning(f"No consent for {customer_id}/{inference_id}, skipping upload")
            return None

        # Generate S3 key: training-data/{customer_id}/{inference_id}.jpg
        object_key = f"training-data/{customer_id}/{inference_id}.jpg"
        metadata_key = f"training-data/{customer_id}/{inference_id}_metadata.json"

        try:
            # Convert image to bytes
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG', quality=95)
            img_buffer.seek(0)

            # Upload image
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=img_buffer,
                ContentType='image/jpeg',
                Metadata={
                    'customer_id': customer_id,
                    'inference_id': inference_id,
                    'upload_time': datetime.utcnow().isoformat()
                }
            )

            # Upload metadata as JSON sidecar
            metadata_json = json.dumps(metadata, default=str, indent=2)
            self.client.put_object(
                Bucket=self.bucket,
                Key=metadata_key,
                Body=metadata_json.encode('utf-8'),
                ContentType='application/json'
            )

            logger.info(f"Uploaded training image: {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Failed to upload training image: {e}")
            raise

    async def upload_embedding(
        self,
        customer_id: str,
        inference_id: str,
        embedding: np.ndarray,
        embedding_type: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Upload embedding as numpy array to S3.

        Args:
            customer_id: Customer UUID
            inference_id: Inference UUID
            embedding: Numpy array (768-dim for CLIP)
            embedding_type: Type (e.g., 'clip', 'instruction', 'context')
            metadata: Optional metadata

        Returns:
            S3 object key
        """
        # Generate S3 key: embeddings/{customer_id}/{inference_id}_{type}.npy
        object_key = f"embeddings/{customer_id}/{inference_id}_{embedding_type}.npy"

        try:
            # Convert numpy array to bytes
            buffer = io.BytesIO()
            np.save(buffer, embedding)
            buffer.seek(0)

            # Prepare metadata
            s3_metadata = {
                'customer_id': customer_id,
                'inference_id': inference_id,
                'embedding_type': embedding_type,
                'shape': str(embedding.shape),
                'dtype': str(embedding.dtype),
                'upload_time': datetime.utcnow().isoformat()
            }

            if metadata:
                s3_metadata.update({
                    k: str(v) for k, v in metadata.items()
                })

            # Upload embedding
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=buffer,
                ContentType='application/octet-stream',
                Metadata=s3_metadata
            )

            logger.info(f"Uploaded embedding: {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Failed to upload embedding: {e}")
            raise

    async def get_presigned_url(
        self,
        customer_id: str,
        inference_id: str,
        resource_type: str = 'image',
        expires_in: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access to S3 object.

        Args:
            customer_id: Customer UUID
            inference_id: Inference UUID
            resource_type: 'image', 'metadata', or 'embedding'
            expires_in: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL
        """
        # Determine object key based on resource type
        if resource_type == 'image':
            object_key = f"training-data/{customer_id}/{inference_id}.jpg"
        elif resource_type == 'metadata':
            object_key = f"training-data/{customer_id}/{inference_id}_metadata.json"
        elif resource_type.startswith('embedding_'):
            embedding_type = resource_type.replace('embedding_', '')
            object_key = f"embeddings/{customer_id}/{inference_id}_{embedding_type}.npy"
        else:
            raise ValueError(f"Invalid resource_type: {resource_type}")

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated presigned URL for {object_key} (expires in {expires_in}s)")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def batch_upload_embeddings(
        self,
        embeddings: List[Dict]
    ) -> List[str]:
        """
        Batch upload multiple embeddings efficiently.

        Args:
            embeddings: List of dicts with keys:
                - customer_id
                - inference_id
                - embedding (np.ndarray)
                - embedding_type
                - metadata (optional)

        Returns:
            List of S3 object keys
        """
        uploaded_keys = []

        for item in embeddings:
            try:
                key = await self.upload_embedding(
                    customer_id=item['customer_id'],
                    inference_id=item['inference_id'],
                    embedding=item['embedding'],
                    embedding_type=item['embedding_type'],
                    metadata=item.get('metadata')
                )
                uploaded_keys.append(key)
            except Exception as e:
                logger.error(f"Failed to upload embedding for {item['inference_id']}: {e}")
                continue

        logger.info(f"Batch uploaded {len(uploaded_keys)}/{len(embeddings)} embeddings")
        return uploaded_keys

    async def download_embedding(
        self,
        customer_id: str,
        inference_id: str,
        embedding_type: str
    ) -> Optional[np.ndarray]:
        """
        Download and load embedding from S3.

        Args:
            customer_id: Customer UUID
            inference_id: Inference UUID
            embedding_type: Embedding type

        Returns:
            Numpy array or None if not found
        """
        object_key = f"embeddings/{customer_id}/{inference_id}_{embedding_type}.npy"

        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=object_key
            )

            buffer = io.BytesIO(response['Body'].read())
            embedding = np.load(buffer)

            logger.debug(f"Downloaded embedding: {object_key}")
            return embedding

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Embedding not found: {object_key}")
                return None
            else:
                logger.error(f"Failed to download embedding: {e}")
                raise

    async def list_customer_objects(
        self,
        customer_id: str,
        prefix: str = 'training-data',
        max_keys: int = 1000
    ) -> List[Dict]:
        """
        List all objects for a customer.

        Args:
            customer_id: Customer UUID
            prefix: S3 prefix ('training-data' or 'embeddings')
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata
        """
        prefix_path = f"{prefix}/{customer_id}/"

        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix_path,
                MaxKeys=max_keys
            )

            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })

            logger.info(f"Listed {len(objects)} objects for customer {customer_id}")
            return objects

        except ClientError as e:
            logger.error(f"Failed to list objects: {e}")
            raise

    async def delete_object(self, object_key: str) -> bool:
        """
        Delete an object from S3.

        Args:
            object_key: S3 object key

        Returns:
            True if successful
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=object_key
            )

            logger.info(f"Deleted object: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete object: {e}")
            return False

    async def batch_delete_objects(self, object_keys: List[str]) -> int:
        """
        Batch delete multiple objects.

        Args:
            object_keys: List of S3 object keys

        Returns:
            Number of successfully deleted objects
        """
        if not object_keys:
            return 0

        # S3 batch delete supports max 1000 objects
        deleted_count = 0
        batch_size = 1000

        for i in range(0, len(object_keys), batch_size):
            batch = object_keys[i:i + batch_size]

            try:
                response = self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={
                        'Objects': [{'Key': key} for key in batch],
                        'Quiet': True
                    }
                )

                deleted_count += len(batch)
                logger.info(f"Batch deleted {len(batch)} objects")

            except ClientError as e:
                logger.error(f"Failed to batch delete objects: {e}")

        return deleted_count
