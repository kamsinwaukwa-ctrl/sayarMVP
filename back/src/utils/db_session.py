"""
Database session utilities for managing GUCs and encryption
"""

import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseSessionHelper:
    """Helper class for managing database session GUCs"""

    @staticmethod
    async def set_encryption_key(db: AsyncSession) -> None:
        """
        Set encryption key for PGP operations in the current database session

        Args:
            db: The database session

        Raises:
            ValueError: If DATABASE_ENCRYPTION_KEY is not configured
        """
        key = os.getenv("DATABASE_ENCRYPTION_KEY")
        if not key:
            raise ValueError("DATABASE_ENCRYPTION_KEY environment variable not configured")

        # Use set_config() with bind parameters - SET LOCAL doesn't support $1 syntax
        # The third parameter 'true' makes it local to the current transaction
        await db.execute(
            text("SELECT set_config('app.encryption_key', :key, true)"),
            {"key": key}
        )

        logger.debug("Encryption key set for database session")

    @staticmethod
    async def set_base_url(db: AsyncSession, base_url: Optional[str] = None) -> None:
        """
        Set base URL for URL generation in SQL functions

        Args:
            db: The database session
            base_url: Optional base URL override
        """
        if not base_url:
            base_url = os.getenv("RAILWAY_STATIC_URL", "http://localhost:8000")
            if not base_url.startswith("http"):
                base_url = f"https://{base_url}"

        # Use set_config() with bind parameters - SET LOCAL doesn't support $1 syntax
        await db.execute(
            text("SELECT set_config('app.base_url', :url, true)"),
            {"url": base_url}
        )

        logger.debug(f"Base URL set for database session: {base_url}")

    @staticmethod
    async def set_service_role(db: AsyncSession) -> None:
        """
        Set service role for admin operations (for testing/admin endpoints)
        Note: In production, this should come from JWT claims

        Args:
            db: The database session
        """
        # This is primarily for admin operations that need service role
        # In production, the JWT should already contain the proper role
        await db.execute(
            text("SET LOCAL role = 'service_role'")
        )

        logger.debug("Service role set for database session")


# Convenience function for setting up admin session
async def setup_admin_session(db: AsyncSession, base_url: Optional[str] = None) -> None:
    """
    Setup database session for admin operations

    Args:
        db: The database session
        base_url: Optional base URL override
    """
    await DatabaseSessionHelper.set_encryption_key(db)
    await DatabaseSessionHelper.set_base_url(db, base_url)
    # Note: service role should come from JWT in production