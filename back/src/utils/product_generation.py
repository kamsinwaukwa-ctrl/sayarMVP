"""
Product field generation utilities for BE-010.2
Auto-generation of brand, SKU, and MPN fields
"""

import re
import secrets
import string
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.sqlalchemy_models import Product, Merchant
from ..models.errors import APIError, ErrorCode
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ProductFieldGenerator:
    """Utility class for auto-generating product fields"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def validate_brand(brand: str) -> str:
        """Validate and sanitize brand field."""
        if not brand or not brand.strip():
            raise ValueError("Brand cannot be empty")

        # Remove control characters and normalize spaces
        cleaned = "".join(char for char in brand if ord(char) >= 32)
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        if len(cleaned) < 1 or len(cleaned) > 70:
            raise ValueError("Brand must be 1-70 characters after trimming")

        return cleaned

    @staticmethod
    def validate_sku(sku: str) -> str:
        """Validate SKU format."""
        if not re.match(r"^[A-Za-z0-9-_]{1,64}$", sku):
            raise ValueError(
                "SKU must contain only alphanumeric characters, hyphens, and underscores (1-64 chars)"
            )
        return sku

    @staticmethod
    def validate_mpn(mpn: str) -> str:
        """Validate MPN format."""
        if not re.match(r"^[A-Za-z0-9-._]{1,70}$", mpn):
            raise ValueError(
                "MPN must contain only alphanumeric characters, hyphens, dots, and underscores (1-70 chars)"
            )
        return mpn

    @staticmethod
    def default_brand_from_merchant(
        merchant_name: str, request_brand: Optional[str]
    ) -> str:
        """Default brand from merchant business name if not provided."""
        if request_brand and request_brand.strip():
            return ProductFieldGenerator.validate_brand(request_brand.strip())

        # Collapse spaces and trim
        default_brand = re.sub(r"\s+", " ", merchant_name.strip())

        # Ensure max 70 chars for Meta compliance
        if len(default_brand) > 70:
            default_brand = default_brand[:70].rstrip()

        return ProductFieldGenerator.validate_brand(default_brand)

    async def generate_unique_sku(
        self, merchant_id: UUID, merchant_slug: str, max_attempts: int = 5
    ) -> str:
        """Generate unique SKU with collision retry."""
        # Define base36 alphabet (lowercase + digits)
        ALPH = string.ascii_lowercase + string.digits

        def shortid(n=7) -> str:
            """Generate n-character base36 ID."""
            return "".join(secrets.choice(ALPH) for _ in range(n))

        for attempt in range(max_attempts):
            # Generate 7-character base36 short ID
            sku = f"{merchant_slug}-{shortid()}"

            try:
                # Check uniqueness
                if not await self._sku_exists(merchant_id, sku):
                    logger.info(
                        "sku_generated",
                        extra={
                            "event_type": "sku_generated",
                            "merchant_id": str(merchant_id),
                            "sku": sku,
                            "attempt": attempt + 1,
                        },
                    )
                    return sku
            except Exception as e:
                # Handle potential race condition, retry
                logger.warning(
                    "sku_generation_collision",
                    extra={
                        "event_type": "sku_generation_collision",
                        "merchant_id": str(merchant_id),
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                )
                continue

        raise APIError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Failed to generate unique SKU after maximum attempts",
        )

    @staticmethod
    def generate_mpn(merchant_slug: str, sku: str) -> str:
        """Generate MPN from merchant slug and SKU."""
        mpn = f"{merchant_slug}-{sku}"

        # Validate length (max 70 chars for Meta)
        if len(mpn) > 70:
            # Truncate SKU portion if needed
            max_sku_length = 70 - len(merchant_slug) - 1
            sku_truncated = sku[:max_sku_length]
            mpn = f"{merchant_slug}-{sku_truncated}"

        return ProductFieldGenerator.validate_mpn(mpn)

    async def _sku_exists(self, merchant_id: UUID, sku: str) -> bool:
        """Check if SKU already exists for the merchant."""
        stmt = select(Product).where(
            Product.merchant_id == merchant_id, Product.sku == sku
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_merchant(self, merchant_id: UUID) -> Merchant:
        """Get merchant by ID."""
        stmt = select(Merchant).where(Merchant.id == merchant_id)
        result = await self.db.execute(stmt)
        merchant = result.scalar_one_or_none()
        if not merchant:
            raise APIError(
                code=ErrorCode.MERCHANT_NOT_FOUND,
                message=f"Merchant not found: {merchant_id}",
            )
        return merchant
