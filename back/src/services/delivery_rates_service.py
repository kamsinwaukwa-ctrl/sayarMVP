"""
Delivery Rates service for CRUD operations and business validation
Enforces "at least one active rule" constraint for merchant delivery rates
"""

from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, text
from sqlalchemy.exc import IntegrityError

from ..models.api import (
    CreateDeliveryRateRequest,
    UpdateDeliveryRateRequest,
    DeliveryRateResponse,
)
from ..models.sqlalchemy_models import DeliveryRate


class DeliveryRateError(Exception):
    """Delivery rate related errors"""

    pass


class DeliveryRatesService:
    """Service class for delivery rate operations with business validation"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rates(
        self, merchant_id: UUID, active_only: Optional[bool] = None
    ) -> List[DeliveryRateResponse]:
        """
        Get list of delivery rates for a merchant

        Args:
            merchant_id: Merchant UUID
            active_only: Filter by active status if provided

        Returns:
            List of DeliveryRateResponse objects
        """
        try:
            # Build query
            query = select(DeliveryRate).where(DeliveryRate.merchant_id == merchant_id)

            if active_only is not None:
                query = query.where(DeliveryRate.active == active_only)

            query = query.order_by(DeliveryRate.created_at.desc())

            # Execute query
            result = await self.db.execute(query)
            delivery_rates = result.scalars().all()

            # Convert to response models
            return [
                DeliveryRateResponse(
                    id=rate.id,
                    merchant_id=rate.merchant_id,
                    name=rate.name,
                    areas_text=rate.areas_text,
                    price_kobo=rate.price_kobo,
                    description=rate.description,
                    active=rate.active,
                    created_at=rate.created_at,
                    updated_at=rate.updated_at,
                )
                for rate in delivery_rates
            ]

        except Exception as e:
            raise DeliveryRateError(f"Failed to list delivery rates: {str(e)}")

    async def create_rate(
        self, merchant_id: UUID, request: CreateDeliveryRateRequest
    ) -> DeliveryRateResponse:
        """
        Create a new delivery rate

        Args:
            merchant_id: Merchant UUID
            request: Rate creation request

        Returns:
            DeliveryRateResponse

        Raises:
            DeliveryRateError: If creation fails
        """
        try:
            # Create new delivery rate
            rate_id = uuid4()
            now = datetime.utcnow()

            new_rate = DeliveryRate(
                id=rate_id,
                merchant_id=merchant_id,
                name=request.name,
                areas_text=request.areas_text,
                price_kobo=request.price_kobo,
                description=request.description,
                active=True,  # New rates are active by default
                created_at=now,
                updated_at=now,
            )

            # Add to session and commit
            self.db.add(new_rate)
            await self.db.commit()
            await self.db.refresh(new_rate)

            return DeliveryRateResponse(
                id=new_rate.id,
                merchant_id=new_rate.merchant_id,
                name=new_rate.name,
                areas_text=new_rate.areas_text,
                price_kobo=new_rate.price_kobo,
                description=new_rate.description,
                active=new_rate.active,
                created_at=new_rate.created_at,
                updated_at=new_rate.updated_at,
            )

        except IntegrityError as e:
            await self.db.rollback()
            raise DeliveryRateError(f"Database constraint violation: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            raise DeliveryRateError(f"Failed to create delivery rate: {str(e)}")

    async def update_rate(
        self, merchant_id: UUID, rate_id: UUID, request: UpdateDeliveryRateRequest
    ) -> DeliveryRateResponse:
        """
        Update an existing delivery rate with business validation

        Args:
            merchant_id: Merchant UUID
            rate_id: Rate UUID
            request: Update request with partial fields

        Returns:
            DeliveryRateResponse

        Raises:
            DeliveryRateError: If update fails or violates business rules
        """
        try:
            # Get existing rate
            query = select(DeliveryRate).where(
                and_(
                    DeliveryRate.id == rate_id, DeliveryRate.merchant_id == merchant_id
                )
            )
            result = await self.db.execute(query)
            existing_rate = result.scalar_one_or_none()

            if not existing_rate:
                raise DeliveryRateError(f"Delivery rate {rate_id} not found")

            # Validate "at least one active rule" constraint
            if request.active is False and existing_rate.active:
                await self._validate_can_deactivate_rate(merchant_id, rate_id)

            # Build update data
            update_data = {"updated_at": datetime.utcnow()}

            if request.name is not None:
                update_data["name"] = request.name
            if request.areas_text is not None:
                update_data["areas_text"] = request.areas_text
            if request.price_kobo is not None:
                update_data["price_kobo"] = request.price_kobo
            if request.description is not None:
                update_data["description"] = request.description
            if request.active is not None:
                update_data["active"] = request.active

            # Update the rate
            stmt = (
                update(DeliveryRate)
                .where(
                    and_(
                        DeliveryRate.id == rate_id,
                        DeliveryRate.merchant_id == merchant_id,
                    )
                )
                .values(**update_data)
            )

            await self.db.execute(stmt)
            await self.db.commit()

            # Refresh and return updated rate
            await self.db.refresh(existing_rate)

            return DeliveryRateResponse(
                id=existing_rate.id,
                merchant_id=existing_rate.merchant_id,
                name=existing_rate.name,
                areas_text=existing_rate.areas_text,
                price_kobo=existing_rate.price_kobo,
                description=existing_rate.description,
                active=existing_rate.active,
                created_at=existing_rate.created_at,
                updated_at=existing_rate.updated_at,
            )

        except DeliveryRateError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise DeliveryRateError(f"Failed to update delivery rate: {str(e)}")

    async def delete_rate(self, merchant_id: UUID, rate_id: UUID) -> bool:
        """
        Delete a delivery rate with business validation

        Args:
            merchant_id: Merchant UUID
            rate_id: Rate UUID

        Returns:
            True if deleted successfully

        Raises:
            DeliveryRateError: If deletion fails or violates business rules
        """
        try:
            # Get existing rate
            query = select(DeliveryRate).where(
                and_(
                    DeliveryRate.id == rate_id, DeliveryRate.merchant_id == merchant_id
                )
            )
            result = await self.db.execute(query)
            existing_rate = result.scalar_one_or_none()

            if not existing_rate:
                raise DeliveryRateError(f"Delivery rate {rate_id} not found")

            # Validate "at least one active rule" constraint if rate is active
            if existing_rate.active:
                await self._validate_can_deactivate_rate(merchant_id, rate_id)

            # Delete the rate
            stmt = delete(DeliveryRate).where(
                and_(
                    DeliveryRate.id == rate_id, DeliveryRate.merchant_id == merchant_id
                )
            )

            await self.db.execute(stmt)
            await self.db.commit()

            return True

        except DeliveryRateError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise DeliveryRateError(f"Failed to delete delivery rate: {str(e)}")

    async def get_rate_by_id(
        self, merchant_id: UUID, rate_id: UUID
    ) -> Optional[DeliveryRateResponse]:
        """
        Get a specific delivery rate by ID

        Args:
            merchant_id: Merchant UUID
            rate_id: Rate UUID

        Returns:
            DeliveryRateResponse or None if not found
        """
        try:
            query = select(DeliveryRate).where(
                and_(
                    DeliveryRate.id == rate_id, DeliveryRate.merchant_id == merchant_id
                )
            )
            result = await self.db.execute(query)
            rate = result.scalar_one_or_none()

            if not rate:
                return None

            return DeliveryRateResponse(
                id=rate.id,
                merchant_id=rate.merchant_id,
                name=rate.name,
                areas_text=rate.areas_text,
                price_kobo=rate.price_kobo,
                description=rate.description,
                active=rate.active,
                created_at=rate.created_at,
                updated_at=rate.updated_at,
            )

        except Exception as e:
            raise DeliveryRateError(f"Failed to get delivery rate: {str(e)}")

    async def _validate_can_deactivate_rate(
        self, merchant_id: UUID, rate_id: UUID
    ) -> None:
        """
        Validate that deactivating/deleting this rate won't leave merchant with zero active rates

        Args:
            merchant_id: Merchant UUID
            rate_id: Rate UUID that will be deactivated/deleted

        Raises:
            DeliveryRateError: If this would violate the "at least one active rule" constraint
        """
        # Count other active rates (excluding the one being deactivated)
        query = select(func.count(DeliveryRate.id)).where(
            and_(
                DeliveryRate.merchant_id == merchant_id,
                DeliveryRate.active == True,
                DeliveryRate.id != rate_id,
            )
        )

        result = await self.db.execute(query)
        other_active_count = result.scalar() or 0

        if other_active_count == 0:
            raise DeliveryRateError(
                "Cannot deactivate or delete the last active delivery rate. "
                "Merchant must have at least one active delivery rate."
            )
