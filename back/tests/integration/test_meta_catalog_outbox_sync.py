"""
Integration tests for Meta Catalog outbox sync functionality
Tests the complete flow from image changes to Meta Catalog API calls
"""

import uuid
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import UUID

from src.services.meta_catalog_service import MetaCatalogService
from src.integrations.meta_catalog import MetaCatalogClient
from src.services.cloudinary_service import CloudinaryService
from src.workers.job_handlers import handle_catalog_sync
from src.models.meta_catalog import (
    MetaCatalogSyncPayload,
    CatalogSyncAction,
    CatalogSyncStatus,
    CatalogSyncTrigger,
    MetaCatalogImageUpdate,
    MetaCatalogSyncResult,
    IdempotencyCheck,
)
from src.models.sqlalchemy_models import (
    Product,
    ProductImage,
    Merchant,
    MetaCatalogSyncLog,
    OutboxEvent,
)
from src.models.outbox import JobType
from src.utils.outbox import OutboxUtils


class TestMetaCatalogOutboxSync:
    """Test suite for Meta Catalog outbox synchronization"""

    @pytest.fixture
    def catalog_service(self, db_session):
        """Create MetaCatalogService instance"""
        return MetaCatalogService(db_session)

    @pytest.fixture
    def cloudinary_service(self, db_session):
        """Create CloudinaryService instance"""
        return CloudinaryService(db_session)

    @pytest.fixture
    def outbox_utils(self, db_session):
        """Create OutboxUtils instance"""
        return OutboxUtils(db_session)

    @pytest.fixture
    def merchant(self, db_session):
        """Create test merchant"""
        merchant = Merchant(
            id=uuid.uuid4(),
            name="Test Beauty Store",
            email="test@beauty.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(merchant)
        db_session.commit()
        return merchant

    @pytest.fixture
    def product(self, db_session, merchant):
        """Create test product"""
        product = Product(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            title="Test Lipstick",
            description="Premium matte lipstick",
            price_kobo=2500,  # 25.00 NGN
            stock=100,
            reserved_qty=0,
            sku="LIP001",
            status="active",
            retailer_id=f"sayar_{merchant.id}_{uuid.uuid4()}",
            meta_image_sync_version=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(product)
        db_session.commit()
        return product

    @pytest.fixture
    def product_image(self, db_session, product, merchant):
        """Create test product image"""
        image = ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            merchant_id=merchant.id,
            cloudinary_public_id="test_image_123",
            secure_url="https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v1/test_image_123.jpg",
            thumbnail_url="https://res.cloudinary.com/test/image/upload/c_fill,w_600,h_600/v1/test_image_123.jpg",
            width=1600,
            height=1600,
            format="jpg",
            bytes=245760,
            is_primary=True,
            upload_status="completed",
            cloudinary_version="1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(image)

        # Update product with primary image
        product.primary_image_id = image.id
        db_session.commit()
        return image

    def test_detect_image_changes_primary_changed(
        self, catalog_service, product, merchant
    ):
        """Test detection of primary image changes"""
        new_url = "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v2/new_image.jpg"

        changes = catalog_service.detect_image_changes(
            product_id=product.id, merchant_id=merchant.id, primary_image_url=new_url
        )

        assert changes is not None
        assert changes["primary_image_url"] == new_url

    def test_detect_image_changes_no_change(
        self, catalog_service, product, merchant, product_image
    ):
        """Test no changes detected when URLs are same"""
        changes = catalog_service.detect_image_changes(
            product_id=product.id,
            merchant_id=merchant.id,
            primary_image_url=product_image.secure_url,
        )

        assert changes is None

    def test_enqueue_catalog_sync_success(
        self, catalog_service, product, merchant, db_session
    ):
        """Test successful catalog sync job enqueuing"""
        changes = {
            "primary_image_url": "https://res.cloudinary.com/test/image/upload/new.jpg"
        }

        job_id = catalog_service.enqueue_catalog_sync(
            product_id=product.id,
            merchant_id=merchant.id,
            action=CatalogSyncAction.UPDATE_IMAGE,
            changes=changes,
            triggered_by=CatalogSyncTrigger.IMAGE_UPLOAD,
        )

        assert job_id is not None

        # Verify sync log created
        sync_log = (
            db_session.query(MetaCatalogSyncLog)
            .filter(
                MetaCatalogSyncLog.product_id == product.id,
                MetaCatalogSyncLog.merchant_id == merchant.id,
            )
            .first()
        )

        assert sync_log is not None
        assert sync_log.action == CatalogSyncAction.UPDATE_IMAGE.value
        assert sync_log.status == CatalogSyncStatus.PENDING.value
        assert sync_log.outbox_job_id == job_id

    def test_enqueue_catalog_sync_idempotency(
        self, catalog_service, product, merchant, db_session
    ):
        """Test idempotency prevents duplicate jobs"""
        changes = {
            "primary_image_url": "https://res.cloudinary.com/test/image/upload/same.jpg"
        }

        # First enqueue
        job_id1 = catalog_service.enqueue_catalog_sync(
            product_id=product.id,
            merchant_id=merchant.id,
            action=CatalogSyncAction.UPDATE_IMAGE,
            changes=changes,
            triggered_by=CatalogSyncTrigger.IMAGE_UPLOAD,
        )

        # Second enqueue with same changes should be skipped
        job_id2 = catalog_service.enqueue_catalog_sync(
            product_id=product.id,
            merchant_id=merchant.id,
            action=CatalogSyncAction.UPDATE_IMAGE,
            changes=changes,
            triggered_by=CatalogSyncTrigger.IMAGE_UPLOAD,
        )

        assert job_id1 is not None
        assert job_id2 is None  # Skipped due to idempotency

    def test_handle_primary_image_change(
        self, catalog_service, product, merchant, db_session
    ):
        """Test handling primary image change events"""
        new_url = "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/new_primary.jpg"

        job_id = catalog_service.handle_primary_image_change(
            product_id=product.id, merchant_id=merchant.id, new_primary_url=new_url
        )

        assert job_id is not None

        # Verify outbox job created
        outbox_job = (
            db_session.query(OutboxEvent).filter(OutboxEvent.id == job_id).first()
        )

        assert outbox_job is not None
        assert outbox_job.job_type == JobType.CATALOG_SYNC.value
        assert "primary_image_url" in str(outbox_job.payload)

    def test_handle_image_upload_primary(self, catalog_service, product, merchant):
        """Test handling primary image upload"""
        uploaded_url = "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/uploaded.jpg"

        job_id = catalog_service.handle_image_upload(
            product_id=product.id,
            merchant_id=merchant.id,
            uploaded_image_url=uploaded_url,
            is_primary=True,
        )

        assert job_id is not None

    def test_handle_image_upload_non_primary(self, catalog_service, product, merchant):
        """Test handling non-primary image upload (should not trigger sync)"""
        uploaded_url = "https://res.cloudinary.com/test/image/upload/additional.jpg"

        job_id = catalog_service.handle_image_upload(
            product_id=product.id,
            merchant_id=merchant.id,
            uploaded_image_url=uploaded_url,
            is_primary=False,
        )

        assert job_id is None

    def test_handle_webhook_update(self, catalog_service, product, merchant):
        """Test handling webhook update events"""
        webhook_metadata = {
            "secure_url": "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/webhook.jpg",
            "width": 1600,
            "height": 1600,
            "format": "jpg",
        }

        job_id = catalog_service.handle_webhook_update(
            product_id=product.id,
            merchant_id=merchant.id,
            image_metadata=webhook_metadata,
        )

        assert job_id is not None

    def test_update_sync_status_success(
        self, catalog_service, product, merchant, db_session
    ):
        """Test updating sync status to success"""
        # Create sync log
        sync_log = MetaCatalogSyncLog(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            product_id=product.id,
            action=CatalogSyncAction.UPDATE_IMAGE.value,
            retailer_id=product.retailer_id,
            catalog_id="test_catalog",
            status=CatalogSyncStatus.PENDING.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(sync_log)
        db_session.commit()

        # Update to success
        catalog_service.update_sync_status(
            sync_log_id=sync_log.id,
            status=CatalogSyncStatus.SUCCESS,
            response_data={"meta_product_id": "meta_123"},
        )

        # Verify update
        updated_log = (
            db_session.query(MetaCatalogSyncLog)
            .filter(MetaCatalogSyncLog.id == sync_log.id)
            .first()
        )

        assert updated_log.status == CatalogSyncStatus.SUCCESS.value
        assert updated_log.response_data["meta_product_id"] == "meta_123"

        # Verify product sync version incremented
        updated_product = (
            db_session.query(Product).filter(Product.id == product.id).first()
        )

        assert updated_product.meta_image_sync_version == 1
        assert updated_product.meta_last_image_sync_at is not None

    def test_legacy_payload_normalization(self, catalog_service, merchant):
        """Test normalization of legacy payload formats"""
        legacy_payload = {
            "action": "update_image",
            "product_id": str(uuid.uuid4()),
            "retailer_id": "test_retailer",
            "meta_catalog_id": "test_catalog",
            "changes": {
                "image_url": "https://res.cloudinary.com/test/legacy.jpg",  # Legacy field name
                "image_urls": [
                    "https://res.cloudinary.com/test/additional.jpg"
                ],  # Legacy field name
            },
            "idempotency_key": "test_key",
            "triggered_by": "image_upload",
        }

        normalized = catalog_service.normalize_legacy_payload(
            legacy_payload, merchant.id
        )

        # Verify normalization
        changes = normalized["changes"]
        assert "primary_image_url" in changes
        assert "additional_image_urls" in changes
        assert "image_url" not in changes  # Legacy field removed
        assert "image_urls" not in changes  # Legacy field removed

    @pytest.mark.asyncio
    async def test_meta_catalog_client_update_images(self):
        """Test Meta Catalog client image update functionality"""
        client = MetaCatalogClient()

        image_data = MetaCatalogImageUpdate(
            image_url="https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/main.jpg",
            additional_image_urls=["https://res.cloudinary.com/test/additional.jpg"],
        )

        from src.models.meta_catalog import MetaCatalogConfig

        config = MetaCatalogConfig(
            catalog_id="test_catalog",
            access_token="test_token",
            app_id="test_app",
            app_secret="test_secret",
        )

        # Mock the API call
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"data": [{"id": "meta_product_123"}]}

            result = await client.update_product_images(
                catalog_id=config.catalog_id,
                retailer_id="test_retailer",
                image_data=image_data,
                config=config,
            )

            assert result.success
            assert result.meta_product_id == "meta_product_123"
            assert result.retailer_id == "test_retailer"

    @pytest.mark.asyncio
    async def test_meta_catalog_client_rate_limiting(self):
        """Test Meta Catalog client rate limiting handling"""
        client = MetaCatalogClient()

        image_data = MetaCatalogImageUpdate(
            image_url="https://res.cloudinary.com/test/image/upload/main.jpg"
        )

        from src.models.meta_catalog import MetaCatalogConfig

        config = MetaCatalogConfig(
            catalog_id="test_catalog",
            access_token="test_token",
            app_id="test_app",
            app_secret="test_secret",
        )

        # Mock rate limit response
        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            from src.integrations.meta_catalog import MetaCatalogRateLimitError

            retry_after = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_request.side_effect = MetaCatalogRateLimitError(
                "Rate limit exceeded", retry_after=retry_after
            )

            result = await client.update_product_images(
                catalog_id=config.catalog_id,
                retailer_id="test_retailer",
                image_data=image_data,
                config=config,
            )

            assert not result.success
            assert result.rate_limited
            assert result.retry_after == retry_after

    @pytest.mark.asyncio
    async def test_handle_catalog_sync_job_update_image(
        self, db_session, merchant, product
    ):
        """Test complete catalog sync job handling for image updates"""
        # Create sync payload
        payload = {
            "action": "update_image",
            "product_id": str(product.id),
            "retailer_id": product.retailer_id,
            "meta_catalog_id": "test_catalog",
            "changes": {
                "primary_image_url": "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/new.jpg"
            },
            "idempotency_key": "test_key",
            "triggered_by": "image_upload",
        }

        # Mock Meta API success
        with patch("src.workers.job_handlers.MetaCatalogClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock successful image update
            mock_result = MetaCatalogSyncResult(
                success=True,
                retailer_id=product.retailer_id,
                meta_product_id="meta_123",
                duration_ms=1200,
                idempotency_key="test_key",
                rate_limited=False,
            )
            mock_client.update_product_images = AsyncMock(return_value=mock_result)

            # Mock database session
            with patch("src.workers.job_handlers.get_db_session") as mock_db:
                mock_db.return_value = [db_session]

                # Execute job handler
                await handle_catalog_sync(str(merchant.id), payload)

                # Verify API was called
                mock_client.update_product_images.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_catalog_sync_job_retry_on_rate_limit(
        self, db_session, merchant, product
    ):
        """Test catalog sync job retry behavior on rate limiting"""
        payload = {
            "action": "update_image",
            "product_id": str(product.id),
            "retailer_id": product.retailer_id,
            "meta_catalog_id": "test_catalog",
            "changes": {
                "primary_image_url": "https://res.cloudinary.com/test/image/upload/new.jpg"
            },
            "idempotency_key": "test_key",
            "triggered_by": "image_upload",
        }

        with patch("src.workers.job_handlers.MetaCatalogClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock rate limited response
            retry_after = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_result = MetaCatalogSyncResult(
                success=False,
                retailer_id=product.retailer_id,
                errors=["Rate limit exceeded"],
                retry_after=retry_after,
                rate_limited=True,
                idempotency_key="test_key",
            )
            mock_client.update_product_images = AsyncMock(return_value=mock_result)

            with patch("src.workers.job_handlers.get_db_session") as mock_db:
                mock_db.return_value = [db_session]

                # Should raise RetryableError
                from src.workers.job_handlers import RetryableError

                with pytest.raises(RetryableError) as exc_info:
                    await handle_catalog_sync(str(merchant.id), payload)

                assert "rate limited" in str(exc_info.value).lower()

    def test_cloudinary_service_integration(
        self, cloudinary_service, product, merchant, db_session
    ):
        """Test Cloudinary service integration with catalog sync"""
        # Mock Cloudinary client
        with patch.object(
            cloudinary_service.cloudinary_client, "upload_image"
        ) as mock_upload:
            mock_upload.return_value = {
                "public_id": "test_upload_123",
                "secure_url": "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/upload.jpg",
                "width": 1600,
                "height": 1600,
                "format": "jpg",
                "bytes": 245760,
                "version": "1",
            }

            # Upload primary image
            result = cloudinary_service.upload_product_image(
                product_id=product.id,
                merchant_id=merchant.id,
                file_content=b"fake_image_data",
                filename="test.jpg",
                is_primary=True,
            )

            assert result.is_primary

            # Verify outbox job was created
            outbox_jobs = (
                db_session.query(OutboxEvent)
                .filter(
                    OutboxEvent.merchant_id == merchant.id,
                    OutboxEvent.job_type == JobType.CATALOG_SYNC.value,
                )
                .all()
            )

            assert len(outbox_jobs) > 0

    def test_error_classification(self):
        """Test error classification for retry logic"""
        client = MetaCatalogClient()

        # Retryable errors
        assert client.classify_error("Network timeout") == True
        assert client.classify_error("Internal server error") == True
        assert client.classify_error("Rate limit exceeded") == True
        assert client.classify_error("Connection failed") == True

        # Non-retryable errors
        assert client.classify_error("Invalid retailer id") == False
        assert client.classify_error("Product not found") == False
        assert client.classify_error("Permission denied") == False
        assert client.classify_error("Invalid access token") == False

    def test_sync_metrics_tracking(
        self, catalog_service, product, merchant, db_session
    ):
        """Test sync metrics are properly tracked"""
        # Create multiple sync logs with different statuses
        statuses = [
            CatalogSyncStatus.SUCCESS,
            CatalogSyncStatus.FAILED,
            CatalogSyncStatus.RATE_LIMITED,
            CatalogSyncStatus.PENDING,
        ]

        for i, status in enumerate(statuses):
            sync_log = MetaCatalogSyncLog(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                product_id=product.id,
                action=CatalogSyncAction.UPDATE_IMAGE.value,
                retailer_id=f"retailer_{i}",
                catalog_id="test_catalog",
                status=status.value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db_session.add(sync_log)

        db_session.commit()

        # Query metrics
        logs = catalog_service.get_sync_logs(merchant_id=merchant.id)
        assert len(logs) == 4

        success_logs = catalog_service.get_sync_logs(
            merchant_id=merchant.id, status=CatalogSyncStatus.SUCCESS
        )
        assert len(success_logs) == 1

    def test_image_url_validation(self):
        """Test image URL validation in MetaCatalogImageUpdate"""
        # Valid Cloudinary main preset URL
        valid_image = MetaCatalogImageUpdate(
            image_url="https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v1/image.jpg"
        )
        assert valid_image.image_url is not None

        # Invalid URL format should raise validation error
        with pytest.raises(ValueError):
            MetaCatalogImageUpdate(image_url="https://example.com/invalid.jpg")

    def test_idempotency_key_generation(self):
        """Test idempotency key generation consistency"""
        product_id = uuid.uuid4()
        action = CatalogSyncAction.UPDATE_IMAGE
        content = {"primary_image_url": "https://example.com/image.jpg"}

        key1 = MetaCatalogSyncPayload.generate_idempotency_key(
            product_id, action, content
        )
        key2 = MetaCatalogSyncPayload.generate_idempotency_key(
            product_id, action, content
        )

        # Same inputs should generate same key
        assert key1 == key2

        # Different content should generate different key
        different_content = {"primary_image_url": "https://example.com/different.jpg"}
        key3 = MetaCatalogSyncPayload.generate_idempotency_key(
            product_id, action, different_content
        )

        assert key1 != key3

    def test_legacy_event_normalization_logging(
        self, catalog_service, merchant, caplog
    ):
        """Test that legacy event normalization is logged"""
        legacy_payload = {
            "action": "update_image",
            "product_id": str(uuid.uuid4()),
            "retailer_id": "test_retailer",
            "meta_catalog_id": "test_catalog",
            "changes": {
                "image_url": "https://res.cloudinary.com/test/legacy.jpg"  # Legacy field
            },
            "idempotency_key": "test_key",
            "triggered_by": "image_upload",
        }

        with caplog.at_level("INFO"):
            catalog_service.normalize_legacy_payload(legacy_payload, merchant.id)

        # Verify normalization was logged
        assert "catalog_sync_legacy_normalized" in caplog.text
        assert "image_url" in caplog.text

    @pytest.mark.asyncio
    async def test_complete_image_change_to_sync_flow(
        self, db_session, cloudinary_service, catalog_service, merchant, product
    ):
        """Test complete end-to-end flow from image change to sync completion"""
        # 1. Simulate Cloudinary webhook for image update
        from src.models.api import CloudinaryWebhookPayload

        webhook_payload = CloudinaryWebhookPayload(
            notification_type="upload",
            public_id="test_image_123",
            version="2",
            width=1600,
            height=1600,
            format="jpg",
            bytes=245760,
            secure_url="https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v2/updated.jpg",
            eager=[
                {
                    "transformation": "c_limit,w_1600,h_1600,f_auto,q_auto:good",
                    "secure_url": "https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v2/updated.jpg",
                }
            ],
        )

        # Create existing image
        existing_image = ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            merchant_id=merchant.id,
            cloudinary_public_id="test_image_123",
            secure_url="https://res.cloudinary.com/test/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v1/original.jpg",
            is_primary=True,
            upload_status="uploading",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(existing_image)
        product.primary_image_id = existing_image.id
        db_session.commit()

        # 2. Process webhook
        with patch.object(
            cloudinary_service.cloudinary_client,
            "verify_webhook_signature",
            return_value=True,
        ):
            result = cloudinary_service.process_webhook(
                payload=webhook_payload,
                signature="test_signature",
                timestamp="1234567890",
                raw_body=b"test_body",
            )

        assert result["success"]

        # 3. Verify outbox job was created
        outbox_jobs = (
            db_session.query(OutboxEvent)
            .filter(
                OutboxEvent.merchant_id == merchant.id,
                OutboxEvent.job_type == JobType.CATALOG_SYNC.value,
            )
            .all()
        )

        assert len(outbox_jobs) > 0

        # 4. Verify sync log was created
        sync_logs = (
            db_session.query(MetaCatalogSyncLog)
            .filter(
                MetaCatalogSyncLog.merchant_id == merchant.id,
                MetaCatalogSyncLog.product_id == product.id,
            )
            .all()
        )

        assert len(sync_logs) > 0

        latest_sync = sync_logs[-1]
        assert latest_sync.action == CatalogSyncAction.UPDATE_IMAGE.value
        assert latest_sync.status == CatalogSyncStatus.PENDING.value

        # 5. Simulate successful job processing
        catalog_service.update_sync_status(
            sync_log_id=latest_sync.id,
            status=CatalogSyncStatus.SUCCESS,
            response_data={"meta_product_id": "meta_12345"},
        )

        # 6. Verify final state
        updated_sync = (
            db_session.query(MetaCatalogSyncLog)
            .filter(MetaCatalogSyncLog.id == latest_sync.id)
            .first()
        )

        assert updated_sync.status == CatalogSyncStatus.SUCCESS.value
        assert updated_sync.response_data["meta_product_id"] == "meta_12345"

        # Verify product sync version incremented
        updated_product = (
            db_session.query(Product).filter(Product.id == product.id).first()
        )

        assert updated_product.meta_image_sync_version > 0
        assert updated_product.meta_last_image_sync_at is not None
