"""
Discounts service for CRUD operations and comprehensive validation
Handles discount code creation, management, and checkout validation
"""

from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, text
from sqlalchemy.exc import IntegrityError

from ..models.api import (
    CreateDiscountRequest,
    UpdateDiscountRequest,
    DiscountResponse,
    ValidateDiscountRequest,
    DiscountValidationResponse,
)
from ..models.sqlalchemy_models import Discount
from ..utils.logger import log


class DiscountError(Exception):
    """Discount related errors"""

    pass


class DiscountsService:
    """Service class for discount operations with comprehensive business validation"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_discounts(
        self,
        merchant_id: UUID,
        status: Optional[str] = None,
        active_only: Optional[bool] = None,
    ) -> List[DiscountResponse]:
        """
        Get list of discounts for a merchant

        Args:
            merchant_id: Merchant UUID
            status: Filter by status ('active', 'paused', 'expired')
            active_only: Filter by active flag if provided

        Returns:
            List of DiscountResponse objects
        """
        try:
            # Build query
            query = select(Discount).where(Discount.merchant_id == merchant_id)

            if status:
                query = query.where(Discount.status == status)

            if active_only is not None:
                if active_only:
                    # Active means status='active' and not expired
                    now = datetime.now(timezone.utc)
                    query = query.where(
                        and_(
                            Discount.status == "active",
                            func.coalesce(
                                Discount.expires_at, now + text("INTERVAL '1 year'")
                            )
                            > now,
                        )
                    )
                else:
                    # Inactive means paused or expired
                    now = datetime.now(timezone.utc)
                    query = query.where(
                        or_(
                            Discount.status.in_(["paused", "expired"]),
                            Discount.expires_at <= now,
                        )
                    )

            query = query.order_by(Discount.created_at.desc())

            # Execute query
            result = await self.db.execute(query)
            discounts = result.scalars().all()

            # Convert to response models
            return [
                DiscountResponse.from_attributes(discount) for discount in discounts
            ]

        except Exception as e:
            log.error(
                "Failed to list discounts",
                extra={
                    "merchant_id": str(merchant_id),
                    "error": str(e),
                    "event_type": "discounts_list_error",
                },
            )
            raise DiscountError(f"Failed to list discounts: {str(e)}")

    async def create_discount(
        self,
        merchant_id: UUID,
        discount_data: CreateDiscountRequest,
        idempotency_key: Optional[str] = None,
    ) -> DiscountResponse:
        """
        Create a new discount with business validation

        Args:
            merchant_id: Merchant UUID
            discount_data: Discount creation request
            idempotency_key: Optional idempotency key

        Returns:
            DiscountResponse object

        Raises:
            DiscountError: If validation fails or creation fails
        """
        try:
            # Validate business rules
            await self._validate_discount_creation(merchant_id, discount_data)

            # Prepare discount data
            discount_dict = {
                "id": uuid4(),
                "merchant_id": merchant_id,
                "code": discount_data.code.upper().strip(),
                "type": discount_data.type,
                "min_subtotal_kobo": discount_data.min_subtotal_kobo,
                "starts_at": discount_data.starts_at,
                "expires_at": discount_data.expires_at,
                "usage_limit_total": discount_data.usage_limit_total,
                "usage_limit_per_customer": discount_data.usage_limit_per_customer,
                "times_redeemed": 0,
                "status": "active",
                "stackable": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            # Set type-specific fields
            if discount_data.type == "percent":
                if not discount_data.value_bp:
                    raise DiscountError("value_bp is required for percent discounts")
                discount_dict["value_bp"] = discount_data.value_bp
                discount_dict["max_discount_kobo"] = discount_data.max_discount_kobo
                discount_dict["amount_kobo"] = None
            else:  # fixed
                if not discount_data.amount_kobo:
                    raise DiscountError("amount_kobo is required for fixed discounts")
                discount_dict["amount_kobo"] = discount_data.amount_kobo
                discount_dict["value_bp"] = None
                discount_dict["max_discount_kobo"] = None

            # Create discount
            discount = Discount(**discount_dict)
            self.db.add(discount)
            await self.db.commit()
            await self.db.refresh(discount)

            log.info(
                "Discount created",
                extra={
                    "merchant_id": str(merchant_id),
                    "discount_id": str(discount.id),
                    "code": discount.code,
                    "type": discount.type,
                    "event_type": "discount_created",
                },
            )

            return DiscountResponse.from_attributes(discount)

        except IntegrityError as e:
            await self.db.rollback()
            if "unique" in str(e).lower():
                raise DiscountError(
                    f"Discount code '{discount_data.code}' already exists"
                )
            raise DiscountError(f"Database constraint error: {str(e)}")

        except Exception as e:
            await self.db.rollback()
            log.error(
                "Failed to create discount",
                extra={
                    "merchant_id": str(merchant_id),
                    "code": discount_data.code,
                    "error": str(e),
                    "event_type": "discount_create_error",
                },
            )
            raise DiscountError(f"Failed to create discount: {str(e)}")

    async def update_discount(
        self, merchant_id: UUID, discount_id: UUID, update_data: UpdateDiscountRequest
    ) -> DiscountResponse:
        """
        Update an existing discount

        Args:
            merchant_id: Merchant UUID
            discount_id: Discount UUID
            update_data: Update request data

        Returns:
            Updated DiscountResponse object

        Raises:
            DiscountError: If discount not found or update fails
        """
        try:
            # Get existing discount
            query = select(Discount).where(
                and_(Discount.id == discount_id, Discount.merchant_id == merchant_id)
            )
            result = await self.db.execute(query)
            discount = result.scalar_one_or_none()

            if not discount:
                raise DiscountError(f"Discount with ID {discount_id} not found")

            # Validate update data
            await self._validate_discount_update(discount, update_data)

            # Apply updates
            update_dict = {"updated_at": datetime.now(timezone.utc)}

            if update_data.status is not None:
                update_dict["status"] = update_data.status

            if update_data.expires_at is not None:
                update_dict["expires_at"] = update_data.expires_at

            if update_data.usage_limit_total is not None:
                update_dict["usage_limit_total"] = update_data.usage_limit_total

            if update_data.usage_limit_per_customer is not None:
                update_dict["usage_limit_per_customer"] = (
                    update_data.usage_limit_per_customer
                )

            # Update discount
            await self.db.execute(
                update(Discount).where(Discount.id == discount_id).values(**update_dict)
            )
            await self.db.commit()

            # Refresh and return
            await self.db.refresh(discount)

            log.info(
                "Discount updated",
                extra={
                    "merchant_id": str(merchant_id),
                    "discount_id": str(discount_id),
                    "changes": update_dict,
                    "event_type": "discount_updated",
                },
            )

            return DiscountResponse.from_attributes(discount)

        except Exception as e:
            await self.db.rollback()
            log.error(
                "Failed to update discount",
                extra={
                    "merchant_id": str(merchant_id),
                    "discount_id": str(discount_id),
                    "error": str(e),
                    "event_type": "discount_update_error",
                },
            )
            raise DiscountError(f"Failed to update discount: {str(e)}")

    async def delete_discount(self, merchant_id: UUID, discount_id: UUID) -> bool:
        """
        Delete a discount

        Args:
            merchant_id: Merchant UUID
            discount_id: Discount UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            # Check if discount exists for merchant
            query = select(func.count(Discount.id)).where(
                and_(Discount.id == discount_id, Discount.merchant_id == merchant_id)
            )
            result = await self.db.execute(query)
            count = result.scalar()

            if count == 0:
                return False

            # Delete discount
            await self.db.execute(
                delete(Discount).where(
                    and_(
                        Discount.id == discount_id, Discount.merchant_id == merchant_id
                    )
                )
            )
            await self.db.commit()

            log.info(
                "Discount deleted",
                extra={
                    "merchant_id": str(merchant_id),
                    "discount_id": str(discount_id),
                    "event_type": "discount_deleted",
                },
            )

            return True

        except Exception as e:
            await self.db.rollback()
            log.error(
                "Failed to delete discount",
                extra={
                    "merchant_id": str(merchant_id),
                    "discount_id": str(discount_id),
                    "error": str(e),
                    "event_type": "discount_delete_error",
                },
            )
            raise DiscountError(f"Failed to delete discount: {str(e)}")

    async def validate_discount(
        self, merchant_id: UUID, validation_request: ValidateDiscountRequest
    ) -> DiscountValidationResponse:
        """
        Validate a discount code for checkout

        Args:
            merchant_id: Merchant UUID
            validation_request: Validation request data

        Returns:
            DiscountValidationResponse with validation result
        """
        try:
            code = validation_request.code.upper().strip()
            subtotal_kobo = validation_request.subtotal_kobo
            customer_id = validation_request.customer_id

            log.info(
                "Discount validation requested",
                extra={
                    "merchant_id": str(merchant_id),
                    "code": code,
                    "subtotal_kobo": subtotal_kobo,
                    "customer_id": str(customer_id) if customer_id else None,
                    "event_type": "discount_validation_requested",
                },
            )

            # Find discount
            query = select(Discount).where(
                and_(Discount.merchant_id == merchant_id, Discount.code == code)
            )
            result = await self.db.execute(query)
            discount = result.scalar_one_or_none()

            if not discount:
                log.info(
                    "Discount validation failed - code not found",
                    extra={
                        "merchant_id": str(merchant_id),
                        "code": code,
                        "event_type": "discount_validation_failed",
                    },
                )
                return DiscountValidationResponse(
                    valid=False, reason="Discount code not found"
                )

            # Check all validation rules
            validation_result = await self._validate_discount_usage(
                discount, subtotal_kobo, customer_id
            )

            log.info(
                "Discount validation completed",
                extra={
                    "merchant_id": str(merchant_id),
                    "discount_id": str(discount.id),
                    "code": code,
                    "valid": validation_result.valid,
                    "discount_kobo": validation_result.discount_kobo,
                    "reason": validation_result.reason,
                    "event_type": "discount_validated",
                },
            )

            return validation_result

        except Exception as e:
            log.error(
                "Discount validation error",
                extra={
                    "merchant_id": str(merchant_id),
                    "code": validation_request.code,
                    "error": str(e),
                    "event_type": "discount_validation_error",
                },
            )
            return DiscountValidationResponse(
                valid=False, reason="Validation error occurred"
            )

    async def _validate_discount_creation(
        self, merchant_id: UUID, discount_data: CreateDiscountRequest
    ) -> None:
        """Validate discount creation business rules"""

        # Validate discount type requirements
        if discount_data.type == "percent":
            if not discount_data.value_bp:
                raise DiscountError("value_bp is required for percent discounts")
            if discount_data.value_bp < 0 or discount_data.value_bp > 10000:
                raise DiscountError("value_bp must be between 0 and 10000 (0-100%)")
        else:  # fixed
            if not discount_data.amount_kobo:
                raise DiscountError("amount_kobo is required for fixed discounts")
            if discount_data.amount_kobo <= 0:
                raise DiscountError("amount_kobo must be greater than 0")

        # Validate date ranges
        if discount_data.starts_at and discount_data.expires_at:
            if discount_data.starts_at >= discount_data.expires_at:
                raise DiscountError("starts_at must be before expires_at")

        # Validate usage limits
        if discount_data.usage_limit_per_customer and discount_data.usage_limit_total:
            if discount_data.usage_limit_per_customer > discount_data.usage_limit_total:
                raise DiscountError(
                    "usage_limit_per_customer cannot exceed usage_limit_total"
                )

        # Validate reasonable discount amounts
        if discount_data.type == "fixed" and discount_data.amount_kobo:
            if discount_data.amount_kobo > 100000000:  # 1M naira
                raise DiscountError("Fixed discount amount too large")

        if (
            discount_data.max_discount_kobo
            and discount_data.max_discount_kobo > 100000000
        ):
            raise DiscountError("Maximum discount amount too large")

    async def _validate_discount_update(
        self, discount: Discount, update_data: UpdateDiscountRequest
    ) -> None:
        """Validate discount update business rules"""

        # Can't reactivate expired discounts
        if update_data.status == "active" and discount.expires_at:
            now = datetime.now(timezone.utc)
            if discount.expires_at <= now:
                raise DiscountError("Cannot reactivate expired discount")

        # Validate date updates
        if update_data.expires_at:
            now = datetime.now(timezone.utc)
            if update_data.expires_at <= now:
                raise DiscountError("expires_at must be in the future")

            if discount.starts_at and update_data.expires_at <= discount.starts_at:
                raise DiscountError("expires_at must be after starts_at")

        # Validate usage limit updates (can't reduce below current usage)
        if update_data.usage_limit_total is not None:
            if update_data.usage_limit_total < discount.times_redeemed:
                raise DiscountError(
                    f"usage_limit_total cannot be less than current redemptions ({discount.times_redeemed})"
                )

    async def _validate_discount_usage(
        self, discount: Discount, subtotal_kobo: int, customer_id: Optional[UUID]
    ) -> DiscountValidationResponse:
        """Validate if discount can be used for a specific order"""

        now = datetime.now(timezone.utc)

        # Check status
        if discount.status != "active":
            return DiscountValidationResponse(
                valid=False, reason=f"Discount is {discount.status}"
            )

        # Check time window
        if discount.starts_at and now < discount.starts_at:
            return DiscountValidationResponse(
                valid=False, reason="Discount not yet active"
            )

        if discount.expires_at and now > discount.expires_at:
            return DiscountValidationResponse(
                valid=False, reason="Discount has expired"
            )

        # Check minimum subtotal
        if subtotal_kobo < discount.min_subtotal_kobo:
            return DiscountValidationResponse(
                valid=False,
                reason=f"Minimum order amount not met (required: ₦{discount.min_subtotal_kobo/100:.2f})",
            )

        # Check total usage limit
        if discount.usage_limit_total is not None:
            if discount.times_redeemed >= discount.usage_limit_total:
                return DiscountValidationResponse(
                    valid=False, reason="Discount usage limit exceeded"
                )

        # Check per-customer usage limit
        if discount.usage_limit_per_customer is not None and customer_id:
            customer_usage = await self._get_customer_usage_count(
                discount.id, customer_id
            )
            if customer_usage >= discount.usage_limit_per_customer:
                return DiscountValidationResponse(
                    valid=False, reason="Customer usage limit exceeded"
                )

        # Calculate discount amount
        discount_kobo = self._calculate_discount_amount(discount, subtotal_kobo)

        return DiscountValidationResponse(valid=True, discount_kobo=discount_kobo)

    async def _get_customer_usage_count(
        self, discount_id: UUID, customer_id: UUID
    ) -> int:
        """Get number of times customer has used this discount"""
        try:
            query = text(
                """
                SELECT COUNT(*)
                FROM coupon_redemptions
                WHERE discount_id = :discount_id AND customer_id = :customer_id
            """
            )
            result = await self.db.execute(
                query,
                {"discount_id": str(discount_id), "customer_id": str(customer_id)},
            )
            return result.scalar() or 0
        except Exception:
            # If we can't check, assume 0 usage (fail open)
            return 0

    def _calculate_discount_amount(self, discount: Discount, subtotal_kobo: int) -> int:
        """Calculate discount amount based on discount type"""

        if discount.type == "fixed":
            # Fixed discount, but can't exceed subtotal
            return min(discount.amount_kobo or 0, subtotal_kobo)

        elif discount.type == "percent":
            # Percentage discount
            discount_kobo = int((subtotal_kobo * (discount.value_bp or 0)) / 10000)

            # Apply maximum discount cap if set
            if discount.max_discount_kobo is not None:
                discount_kobo = min(discount_kobo, discount.max_discount_kobo)

            # Can't exceed subtotal
            return min(discount_kobo, subtotal_kobo)

        return 0
