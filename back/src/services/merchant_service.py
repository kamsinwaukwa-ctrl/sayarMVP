"""
Merchant service for business logic operations
"""

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound

from ..models.sqlalchemy_models import Merchant


class MerchantService:
    """Service class for merchant operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, merchant_id: UUID) -> Optional[Merchant]:
        """
        Get merchant by ID

        Args:
            merchant_id: The merchant UUID

        Returns:
            Merchant model or None if not found
        """
        try:
            result = await self.session.execute(
                select(Merchant).where(Merchant.id == merchant_id)
            )
            return result.scalar_one_or_none()  # Returns None instead of throwing
        except Exception as e:
            print(f"❌ MerchantService.get_by_id error: {type(e).__name__}: {str(e)}")
            import traceback

            print(f"❌ Traceback: {traceback.format_exc()}")
            return None

    async def update_brand_basics(
        self,
        merchant_id: UUID,
        *,
        description: Optional[str] = None,
        primary_currency: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> Merchant:
        """
        Update merchant brand basics (description, currency, logo)

        Args:
            merchant_id: The merchant UUID
            description: Business description
            primary_currency: Primary currency code (NGN, USD, etc.)
            logo_url: URL to uploaded logo image

        Returns:
            Updated merchant model

        Raises:
            ValueError: If merchant not found
        """
        fields: Dict[str, Any] = {}

        if description is not None:
            fields["description"] = description.strip() if description else None
        if primary_currency is not None:
            fields["currency"] = primary_currency  # Using 'currency' field from model
        if logo_url is not None:
            fields["logo_url"] = logo_url

        if not fields:
            # Nothing to update, just return current merchant
            merchant = await self.get_by_id(merchant_id)
            if not merchant:
                raise ValueError("Merchant not found")
            return merchant

        try:
            stmt = (
                update(Merchant)
                .where(Merchant.id == merchant_id)
                .values(**fields)
                .returning(Merchant)
            )

            result = await self.session.execute(stmt)
            merchant = result.scalar_one_or_none()

            if not merchant:
                raise ValueError("Merchant not found")

            # Commit the transaction
            await self.session.commit()

            return merchant

        except Exception as e:
            # Rollback on error
            await self.session.rollback()
            raise ValueError(f"Failed to update merchant: {str(e)}")
