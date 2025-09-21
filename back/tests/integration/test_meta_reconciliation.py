"""
Integration tests for Meta Catalog reconciliation functionality
Tests complete reconciliation workflow from API endpoints to database state
"""

import pytest
import json
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.sqlalchemy_models import Product, Merchant
from src.models.meta_reconciliation import (
    MetaReconciliationRun,
    MetaDriftLog,
    ReconciliationRunType,
    ReconciliationStatus,
    DriftAction
)
from src.services.meta_reconciliation_service import MetaReconciliationService
from src.workers.reconciliation_worker import trigger_manual_reconciliation_for_merchant

pytestmark = pytest.mark.asyncio


class TestMetaReconciliationService:
    """Test Meta reconciliation service core functionality"""

    async def test_reconciliation_run_lifecycle(self, test_db, sample_merchant, sample_product):
        """Test complete reconciliation run lifecycle"""

        # Set up product as synced
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                status="active",
                meta_sync_status="synced",
                retailer_id="sayar_product_" + str(sample_product.id),
                price_kobo=20000,
                stock=10,
                title="Test Product"
            )
        )
        await test_db.commit()

        service = MetaReconciliationService(test_db)

        # Mock Meta API response with drift
        meta_items = {
            f"sayar_product_{sample_product.id}": {
                "price": "250.00 NGN",  # Different from local (200.00 NGN)
                "availability": "in stock",
                "title": "Test Product",
                "image_link": "https://example.com/image.jpg"
            }
        }

        with patch.object(service, '_fetch_meta_catalog_data', return_value=meta_items):
            with patch.object(service, '_load_meta_credentials', return_value=MagicMock()):
                # Run reconciliation
                run = await service.run_reconciliation(
                    merchant_id=sample_merchant.id,
                    run_type=ReconciliationRunType.MANUAL
                )

                assert run is not None
                assert run.status == ReconciliationStatus.COMPLETED
                assert run.stats.products_checked == 1
                assert run.stats.drift_detected == 1
                assert run.stats.syncs_triggered == 1

                # Verify drift was logged
                drift_query = select(MetaDriftLog).where(
                    MetaDriftLog.reconciliation_run_id == run.id
                )
                drift_result = await test_db.execute(drift_query)
                drift_logs = drift_result.scalars().all()

                assert len(drift_logs) == 1
                assert drift_logs[0].field_name == "price_kobo"
                assert drift_logs[0].action_taken == DriftAction.SYNC_TRIGGERED.value

    async def test_no_drift_detected(self, test_db, sample_merchant, sample_product):
        """Test reconciliation when no drift is detected"""

        # Set up product as synced
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                status="active",
                meta_sync_status="synced",
                retailer_id="sayar_product_" + str(sample_product.id),
                price_kobo=20000,
                stock=10,
                title="Test Product"
            )
        )
        await test_db.commit()

        service = MetaReconciliationService(test_db)

        # Mock Meta API response with no drift
        meta_items = {
            f"sayar_product_{sample_product.id}": {
                "price": "200.00 NGN",  # Same as local
                "availability": "in stock",  # Same as local
                "title": "Test Product",  # Same as local
                "image_link": ""
            }
        }

        with patch.object(service, '_fetch_meta_catalog_data', return_value=meta_items):
            with patch.object(service, '_load_meta_credentials', return_value=MagicMock()):
                run = await service.run_reconciliation(
                    merchant_id=sample_merchant.id,
                    run_type=ReconciliationRunType.MANUAL
                )

                assert run.status == ReconciliationStatus.COMPLETED
                assert run.stats.products_checked == 1
                assert run.stats.drift_detected == 0
                assert run.stats.syncs_triggered == 0

    async def test_missing_remote_product(self, test_db, sample_merchant, sample_product):
        """Test reconciliation when product is missing from Meta catalog"""

        # Set up product as synced
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                status="active",
                meta_sync_status="synced",
                retailer_id="sayar_product_" + str(sample_product.id)
            )
        )
        await test_db.commit()

        service = MetaReconciliationService(test_db)

        # Mock Meta API response with missing product
        meta_items = {}  # Product not found in Meta catalog

        with patch.object(service, '_fetch_meta_catalog_data', return_value=meta_items):
            with patch.object(service, '_load_meta_credentials', return_value=MagicMock()):
                run = await service.run_reconciliation(
                    merchant_id=sample_merchant.id,
                    run_type=ReconciliationRunType.MANUAL
                )

                assert run.status == ReconciliationStatus.COMPLETED
                assert run.stats.drift_detected == 1
                assert run.stats.syncs_triggered == 1

                # Verify missing_remote drift was logged
                drift_query = select(MetaDriftLog).where(
                    MetaDriftLog.reconciliation_run_id == run.id
                )
                drift_result = await test_db.execute(drift_query)
                drift_logs = drift_result.scalars().all()

                assert len(drift_logs) == 1
                assert drift_logs[0].field_name == "missing_remote"

    async def test_meta_api_error_handling(self, test_db, sample_merchant, sample_product):
        """Test reconciliation when Meta API fails"""

        # Set up product as synced
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                status="active",
                meta_sync_status="synced",
                retailer_id="sayar_product_" + str(sample_product.id)
            )
        )
        await test_db.commit()

        service = MetaReconciliationService(test_db)

        # Mock Meta API error
        with patch.object(service, '_fetch_meta_catalog_data', side_effect=Exception("Meta API error")):
            with patch.object(service, '_load_meta_credentials', return_value=MagicMock()):
                run = await service.run_reconciliation(
                    merchant_id=sample_merchant.id,
                    run_type=ReconciliationRunType.MANUAL
                )

                assert run.status == ReconciliationStatus.FAILED
                assert "Meta API error" in run.last_error

    async def test_no_meta_credentials(self, test_db, sample_merchant, sample_product):
        """Test reconciliation when merchant has no Meta credentials"""

        service = MetaReconciliationService(test_db)

        # Mock no credentials
        with patch.object(service, '_load_meta_credentials', return_value=None):
            run = await service.run_reconciliation(
                merchant_id=sample_merchant.id,
                run_type=ReconciliationRunType.MANUAL
            )

            assert run.status == ReconciliationStatus.FAILED
            assert "No verified Meta credentials" in run.last_error

    async def test_recent_run_deduplication(self, test_db, sample_merchant):
        """Test that recent runs prevent duplicate reconciliation"""

        service = MetaReconciliationService(test_db)

        # Create a recent run
        recent_run = MetaReconciliationRun(
            merchant_id=sample_merchant.id,
            run_type=ReconciliationRunType.MANUAL.value,
            status=ReconciliationStatus.COMPLETED.value,
            started_at=datetime.utcnow() - timedelta(minutes=30),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(recent_run)
        await test_db.commit()

        # Try to start another run
        run_id = await service.start_reconciliation_run(
            merchant_id=sample_merchant.id,
            run_type=ReconciliationRunType.MANUAL
        )

        assert run_id is None  # Should be skipped due to recent run


class TestReconciliationAdminAPI:
    """Test reconciliation admin API endpoints"""

    async def test_get_reconciliation_status_success(self, test_client, test_db, sample_admin, sample_merchant):
        """Test successful reconciliation status retrieval"""

        # Create a reconciliation run
        run = MetaReconciliationRun(
            merchant_id=sample_merchant.id,
            run_type=ReconciliationRunType.SCHEDULED.value,
            status=ReconciliationStatus.COMPLETED.value,
            products_total=10,
            products_checked=10,
            drift_detected=2,
            syncs_triggered=2,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_ms=5000,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(run)
        await test_db.commit()

        response = await test_client.get(
            "/api/v1/admin/reconciliation/status",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["status"] == "completed"
        assert data["data"]["stats"]["products_checked"] == 10
        assert data["data"]["stats"]["drift_detected"] == 2

    async def test_get_reconciliation_status_no_runs(self, test_client, sample_admin):
        """Test reconciliation status when no runs exist"""

        response = await test_client.get(
            "/api/v1/admin/reconciliation/status",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["last_run_at"] is None
        assert data["data"]["status"] is None

    async def test_trigger_reconciliation_success(self, test_client, test_db, sample_admin, sample_merchant):
        """Test successful manual reconciliation trigger"""

        with patch('src.api.admin.reconciliation.trigger_manual_reconciliation_for_merchant') as mock_trigger:
            mock_trigger.return_value = uuid4()

            response = await test_client.post(
                f"/api/v1/admin/reconciliation/trigger?merchant_id={sample_merchant.id}",
                headers=create_admin_auth_headers(sample_admin.id)
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "job_id" in data["data"]
            assert "scheduled_at" in data["data"]
            mock_trigger.assert_called_once_with(sample_merchant.id)

    async def test_trigger_reconciliation_rate_limited(self, test_client, test_db, sample_admin, sample_merchant):
        """Test reconciliation trigger rate limiting"""

        # Create a recent manual run
        recent_run = MetaReconciliationRun(
            merchant_id=sample_merchant.id,
            run_type=ReconciliationRunType.MANUAL.value,
            status=ReconciliationStatus.COMPLETED.value,
            started_at=datetime.utcnow() - timedelta(minutes=30),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(recent_run)
        await test_db.commit()

        response = await test_client.post(
            f"/api/v1/admin/reconciliation/trigger?merchant_id={sample_merchant.id}",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 429
        data = response.json()
        assert "rate limited" in data["detail"]["message"].lower()

    async def test_trigger_reconciliation_unauthorized(self, test_client, sample_merchant):
        """Test reconciliation trigger without admin access"""

        response = await test_client.post(
            f"/api/v1/admin/reconciliation/trigger?merchant_id={sample_merchant.id}"
        )

        assert response.status_code == 401

    async def test_get_reconciliation_history(self, test_client, test_db, sample_admin, sample_merchant):
        """Test reconciliation history retrieval"""

        # Create multiple reconciliation runs
        runs = []
        for i in range(3):
            run = MetaReconciliationRun(
                merchant_id=sample_merchant.id,
                run_type=ReconciliationRunType.SCHEDULED.value,
                status=ReconciliationStatus.COMPLETED.value,
                products_checked=10 + i,
                drift_detected=i,
                started_at=datetime.utcnow() - timedelta(days=i),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            runs.append(run)
            test_db.add(run)

        await test_db.commit()

        response = await test_client.get(
            "/api/v1/admin/reconciliation/history?limit=2",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["data"]["runs"]) == 2
        assert data["data"]["total"] == 3
        assert data["data"]["pagination"]["has_more"] is True

    async def test_get_reconciliation_history_filtered(self, test_client, test_db, sample_admin, sample_merchant):
        """Test reconciliation history with merchant filter"""

        # Create reconciliation run for specific merchant
        run = MetaReconciliationRun(
            merchant_id=sample_merchant.id,
            run_type=ReconciliationRunType.MANUAL.value,
            status=ReconciliationStatus.COMPLETED.value,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(run)
        await test_db.commit()

        response = await test_client.get(
            f"/api/v1/admin/reconciliation/history?merchant_id={sample_merchant.id}",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["data"]["runs"]) == 1
        assert data["data"]["runs"][0]["merchant_id"] == str(sample_merchant.id)


class TestMerchantReconciliationAPI:
    """Test merchant-scoped reconciliation API endpoints"""

    async def test_get_merchant_reconciliation_status(self, test_client, test_db, sample_merchant):
        """Test merchant reconciliation status retrieval"""

        # Create reconciliation run for merchant
        run = MetaReconciliationRun(
            merchant_id=sample_merchant.id,
            run_type=ReconciliationRunType.SCHEDULED.value,
            status=ReconciliationStatus.COMPLETED.value,
            products_checked=15,
            drift_detected=3,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(run)
        await test_db.commit()

        response = await test_client.get(
            "/api/v1/reconciliation/status",
            headers=create_auth_headers(sample_merchant.id)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["products_checked"] == 15
        assert data["data"]["drift_detected"] == 3
        assert data["data"]["sync_pending"] == 0

    async def test_get_merchant_reconciliation_status_no_runs(self, test_client, sample_merchant):
        """Test merchant reconciliation status when no runs exist"""

        response = await test_client.get(
            "/api/v1/reconciliation/status",
            headers=create_auth_headers(sample_merchant.id)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["last_run_at"] is None
        assert data["data"]["products_checked"] == 0
        assert data["data"]["drift_detected"] == 0


class TestReconciliationWorker:
    """Test reconciliation worker functionality"""

    async def test_manual_reconciliation_trigger(self, test_db, sample_merchant, sample_product):
        """Test manual reconciliation trigger function"""

        # Set up product as synced
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                status="active",
                meta_sync_status="synced",
                retailer_id="sayar_product_" + str(sample_product.id)
            )
        )
        await test_db.commit()

        # Mock Meta credentials and API
        with patch('src.workers.reconciliation_worker.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = test_db

            with patch('src.services.meta_reconciliation_service.MetaReconciliationService.run_reconciliation') as mock_run:
                mock_run.return_value = MagicMock(id=uuid4(), status=MagicMock(value="completed"))

                run_id = await trigger_manual_reconciliation_for_merchant(sample_merchant.id)

                assert run_id is not None
                mock_run.assert_called_once()


# Helper functions
def create_auth_headers(merchant_id):
    """Create authentication headers for merchant"""
    # This would be implemented based on your auth system
    return {"Authorization": f"Bearer merchant_{merchant_id}"}


def create_admin_auth_headers(admin_id):
    """Create authentication headers for admin"""
    # This would be implemented based on your auth system
    return {"Authorization": f"Bearer admin_{admin_id}"}