"""
Meta Commerce Catalog integration for WhatsApp Business
Handles product catalog synchronization with Meta Graph API
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

from ..models.meta_catalog import (
    MetaCatalogProduct,
    MetaCatalogSyncResult,
    MetaCatalogConfig,
    MetaCatalogBatchRequest,
    MetaCatalogBatchResult,
    MetaCatalogImageUpdate,
    MetaCatalogBatchImageRequest,
    MetaCatalogBatchImageResponse,
)
from ..utils.logger import get_logger
from ..utils.retry import retryable, RetryConfig
from ..utils.error_handling import map_exception_to_response, create_error_response
from ..utils.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


class MetaCatalogError(Exception):
    """Meta catalog API error"""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        retry_after: Optional[datetime] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.retry_after = retry_after
        super().__init__(message)


class MetaCatalogRateLimitError(MetaCatalogError):
    """Meta catalog API rate limit error"""

    pass


class MetaCatalogClient:
    """Meta Commerce Catalog API client with rate limiting and error handling"""

    def __init__(
        self, graph_api_version: str = "v21.0", timeout: int = 30, max_retries: int = 3
    ):
        self.base_url = f"https://graph.facebook.com/{graph_api_version}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=MetaCatalogError,
        )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        config: MetaCatalogConfig,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Meta Graph API"""
        url = f"{self.base_url}/{endpoint}"

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        request_params = {"access_token": config.access_token, **(params or {})}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=request_params,
                    json=data,
                    headers=headers,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "3600")
                    retry_datetime = datetime.now() + timedelta(
                        seconds=int(retry_after)
                    )
                    logger.warning(
                        f"Meta API rate limit hit, retry after: {retry_datetime}"
                    )
                    raise MetaCatalogRateLimitError(
                        f"Rate limit exceeded, retry after {retry_after} seconds",
                        retry_after=retry_datetime,
                    )

                # Parse response
                response_data = response.json() if response.content else {}

                # Handle API errors
                if response.status_code >= 400:
                    error = response_data.get("error", {})
                    error_message = error.get("message", f"HTTP {response.status_code}")
                    error_code = error.get("code", str(response.status_code))

                    logger.error(
                        f"Meta API error: {error_message} (code: {error_code})"
                    )
                    raise MetaCatalogError(error_message, error_code)

                return response_data

            except httpx.RequestError as e:
                logger.error(f"Meta API request failed: {str(e)}")
                raise MetaCatalogError(f"Request failed: {str(e)}")

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def create_product(
        self, catalog_id: str, product: MetaCatalogProduct, config: MetaCatalogConfig
    ) -> MetaCatalogSyncResult:
        """Create product in Meta Commerce Catalog"""
        start_time = datetime.now()

        try:
            logger.info(f"Creating product in Meta catalog: {product.retailer_id}")

            # Prepare product data for Meta API
            product_data = {
                "retailer_id": product.retailer_id,
                "name": product.name,
                "description": product.description,
                "url": product.url,
                "image_url": product.image_url,
                "availability": product.availability,
                "condition": product.condition,
                "price": product.price,
                "brand": product.brand,
                "category": product.category,
                "inventory": product.inventory,
            }

            # Remove None values
            product_data = {k: v for k, v in product_data.items() if v is not None}

            async with self.circuit_breaker:
                response = await self._make_request(
                    method="POST",
                    endpoint=f"{catalog_id}/products",
                    config=config,
                    data=product_data,
                )

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            meta_product_id = response.get("id")

            logger.info(
                f"Product created successfully: {product.retailer_id} -> {meta_product_id}"
            )

            return MetaCatalogSyncResult(
                success=True,
                retailer_id=product.retailer_id,
                meta_product_id=meta_product_id,
                sync_duration_ms=duration_ms,
            )

        except MetaCatalogRateLimitError as e:
            logger.warning(
                f"Rate limit hit for product creation: {product.retailer_id}"
            )
            return MetaCatalogSyncResult(
                success=False,
                retailer_id=product.retailer_id,
                errors=[e.message],
                retry_after=e.retry_after,
            )

        except MetaCatalogError as e:
            logger.error(f"Failed to create product {product.retailer_id}: {e.message}")
            return MetaCatalogSyncResult(
                success=False, retailer_id=product.retailer_id, errors=[e.message]
            )

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def update_product(
        self,
        catalog_id: str,
        retailer_id: str,
        product: MetaCatalogProduct,
        config: MetaCatalogConfig,
    ) -> MetaCatalogSyncResult:
        """Update product in Meta Commerce Catalog"""
        start_time = datetime.now()

        try:
            logger.info(f"Updating product in Meta catalog: {retailer_id}")

            # Prepare update data
            update_data = {
                "name": product.name,
                "description": product.description,
                "url": product.url,
                "image_url": product.image_url,
                "availability": product.availability,
                "condition": product.condition,
                "price": product.price,
                "brand": product.brand,
                "category": product.category,
                "inventory": product.inventory,
            }

            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}

            async with self.circuit_breaker:
                response = await self._make_request(
                    method="POST",
                    endpoint=f"{catalog_id}/products",
                    config=config,
                    data={"retailer_id": retailer_id, **update_data},
                )

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            meta_product_id = response.get("id")

            logger.info(
                f"Product updated successfully: {retailer_id} -> {meta_product_id}"
            )

            return MetaCatalogSyncResult(
                success=True,
                retailer_id=retailer_id,
                meta_product_id=meta_product_id,
                sync_duration_ms=duration_ms,
            )

        except MetaCatalogRateLimitError as e:
            logger.warning(f"Rate limit hit for product update: {retailer_id}")
            return MetaCatalogSyncResult(
                success=False,
                retailer_id=retailer_id,
                errors=[e.message],
                retry_after=e.retry_after,
            )

        except MetaCatalogError as e:
            logger.error(f"Failed to update product {retailer_id}: {e.message}")
            return MetaCatalogSyncResult(
                success=False, retailer_id=retailer_id, errors=[e.message]
            )

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def delete_product(
        self, catalog_id: str, retailer_id: str, config: MetaCatalogConfig
    ) -> MetaCatalogSyncResult:
        """Delete product from Meta Commerce Catalog"""
        start_time = datetime.now()

        try:
            logger.info(f"Deleting product from Meta catalog: {retailer_id}")

            async with self.circuit_breaker:
                await self._make_request(
                    method="DELETE",
                    endpoint=f"{catalog_id}/products",
                    config=config,
                    params={"retailer_id": retailer_id},
                )

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.info(f"Product deleted successfully: {retailer_id}")

            return MetaCatalogSyncResult(
                success=True, retailer_id=retailer_id, sync_duration_ms=duration_ms
            )

        except MetaCatalogRateLimitError as e:
            logger.warning(f"Rate limit hit for product deletion: {retailer_id}")
            return MetaCatalogSyncResult(
                success=False,
                retailer_id=retailer_id,
                errors=[e.message],
                retry_after=e.retry_after,
            )

        except MetaCatalogError as e:
            logger.error(f"Failed to delete product {retailer_id}: {e.message}")
            return MetaCatalogSyncResult(
                success=False, retailer_id=retailer_id, errors=[e.message]
            )

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def unpublish_product(
        self, catalog_id: str, retailer_id: str, config: MetaCatalogConfig
    ) -> MetaCatalogSyncResult:
        """Unpublish product from Meta Commerce Catalog by setting availability to out of stock"""
        start_time = datetime.now()

        try:
            logger.info(f"Unpublishing product from Meta catalog: {retailer_id}")

            # Try preferred approach: set availability to out of stock and visibility to hidden
            unpublish_data = {
                "retailer_id": retailer_id,
                "availability": "out of stock",
                "visibility": "hidden",  # Hide from buyer surfaces
            }

            async with self.circuit_breaker:
                response = await self._make_request(
                    method="POST",
                    endpoint=f"{catalog_id}/products",
                    config=config,
                    data=unpublish_data,
                )

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            meta_product_id = response.get("id")

            logger.info(
                f"Product unpublished successfully: {retailer_id} -> {meta_product_id}"
            )

            return MetaCatalogSyncResult(
                success=True,
                retailer_id=retailer_id,
                meta_product_id=meta_product_id,
                sync_duration_ms=duration_ms,
            )

        except MetaCatalogRateLimitError as e:
            logger.warning(f"Rate limit hit for product unpublish: {retailer_id}")
            return MetaCatalogSyncResult(
                success=False,
                retailer_id=retailer_id,
                errors=[e.message],
                retry_after=e.retry_after,
            )

        except MetaCatalogError as e:
            logger.error(f"Failed to unpublish product {retailer_id}: {e.message}")
            return MetaCatalogSyncResult(
                success=False, retailer_id=retailer_id, errors=[e.message]
            )

    async def get_product_status(
        self, catalog_id: str, retailer_id: str, config: MetaCatalogConfig
    ) -> Optional[Dict[str, Any]]:
        """Get product status from Meta Commerce Catalog"""
        try:
            logger.debug(f"Getting product status from Meta catalog: {retailer_id}")

            async with self.circuit_breaker:
                response = await self._make_request(
                    method="GET",
                    endpoint=f"{catalog_id}/products",
                    config=config,
                    params={
                        "retailer_id": retailer_id,
                        "fields": "id,retailer_id,name,availability,review_status",
                    },
                )

            products = response.get("data", [])
            if products:
                return products[0]

            return None

        except MetaCatalogError as e:
            logger.error(f"Failed to get product status {retailer_id}: {e.message}")
            return None

    async def batch_sync_products(
        self,
        catalog_id: str,
        products: List[MetaCatalogProduct],
        config: MetaCatalogConfig,
        batch_size: int = 10,
    ) -> MetaCatalogBatchResult:
        """Batch sync multiple products to Meta Commerce Catalog"""
        logger.info(f"Starting batch sync of {len(products)} products")

        results = []
        success_count = 0
        error_count = 0

        # Process products in batches to respect rate limits
        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            batch_tasks = []

            for product in batch:
                task = self.create_product(catalog_id, product, config)
                batch_tasks.append(task)

            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch sync error: {str(result)}")
                    results.append(
                        MetaCatalogSyncResult(
                            success=False, retailer_id="unknown", errors=[str(result)]
                        )
                    )
                    error_count += 1
                else:
                    results.append(result)
                    if result.success:
                        success_count += 1
                    else:
                        error_count += 1

            # Rate limit protection: wait between batches
            if i + batch_size < len(products):
                await asyncio.sleep(1.0)

        logger.info(
            f"Batch sync completed: {success_count} success, {error_count} errors"
        )

        return MetaCatalogBatchResult(
            success_count=success_count, error_count=error_count, results=results
        )

    def generate_retailer_id(self, merchant_id: UUID, product_id: UUID) -> str:
        """Generate stable retailer_id for Meta catalog"""
        merchant_short = str(merchant_id).replace("-", "")[:10]
        product_short = str(product_id).replace("-", "")[:10]
        return f"meta_{merchant_short}_{product_short}"

    @retryable(config=RetryConfig(max_attempts=8, exponential_base=2.0, max_delay=3600))
    async def update_product_images(
        self,
        catalog_id: str,
        retailer_id: str,
        image_data: MetaCatalogImageUpdate,
        config: MetaCatalogConfig,
    ) -> MetaCatalogSyncResult:
        """Update product images using Meta Graph API batch endpoint"""
        start_time = datetime.now()

        try:
            logger.info(f"Updating product images in Meta catalog: {retailer_id}")

            # Validate image URLs before making API call
            try:
                await self._validate_image_urls(image_data)
            except Exception as e:
                logger.error(f"Image URL validation failed for {retailer_id}: {str(e)}")
                return MetaCatalogSyncResult(
                    success=False,
                    retailer_id=retailer_id,
                    errors=[f"Image validation failed: {str(e)}"],
                    idempotency_key="",
                    rate_limited=False,
                )

            # Create batch request for image update
            batch_request = MetaCatalogBatchImageRequest.create_image_update_request(
                retailer_id=retailer_id, image_data=image_data
            )

            async with self.circuit_breaker:
                response = await self._make_request(
                    method="POST",
                    endpoint=f"{catalog_id}/items_batch",
                    config=config,
                    data=batch_request.dict(),
                )

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Parse batch response
            batch_response = MetaCatalogBatchImageResponse(**response)

            if batch_response.is_success:
                meta_product_id = None
                if batch_response.data and len(batch_response.data) > 0:
                    meta_product_id = batch_response.data[0].get("id")

                logger.info(
                    f"Product images updated successfully: {retailer_id} -> {meta_product_id}"
                )

                return MetaCatalogSyncResult(
                    success=True,
                    retailer_id=retailer_id,
                    meta_product_id=meta_product_id,
                    duration_ms=duration_ms,
                    idempotency_key="",
                    rate_limited=False,
                )
            else:
                error_message = "Unknown error"
                if batch_response.error:
                    error_message = batch_response.error.get("message", error_message)

                logger.error(
                    f"Failed to update product images {retailer_id}: {error_message}"
                )

                return MetaCatalogSyncResult(
                    success=False,
                    retailer_id=retailer_id,
                    errors=[error_message],
                    duration_ms=duration_ms,
                    idempotency_key="",
                    rate_limited=batch_response.is_rate_limited,
                )

        except MetaCatalogRateLimitError as e:
            logger.warning(f"Rate limit hit for image update: {retailer_id}")
            return MetaCatalogSyncResult(
                success=False,
                retailer_id=retailer_id,
                errors=[e.message],
                retry_after=e.retry_after,
                rate_limited=True,
                idempotency_key="",
            )

        except MetaCatalogError as e:
            logger.error(f"Failed to update product images {retailer_id}: {e.message}")
            return MetaCatalogSyncResult(
                success=False,
                retailer_id=retailer_id,
                errors=[e.message],
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                idempotency_key="",
                rate_limited=False,
            )

    async def _validate_image_urls(self, image_data: MetaCatalogImageUpdate) -> None:
        """Validate that image URLs are accessible before API call"""
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                # HEAD request to primary image URL
                response = await client.head(image_data.image_url)
                if response.status_code != 200:
                    raise MetaCatalogError(
                        f"Primary image URL not accessible: {response.status_code}"
                    )

                # Check additional image URLs if present
                for url in image_data.additional_image_urls or []:
                    response = await client.head(url)
                    if response.status_code != 200:
                        logger.warning(
                            f"Additional image URL not accessible: {url} ({response.status_code})"
                        )
                        # Don't fail for additional images, just log warning

            except httpx.RequestError as e:
                raise MetaCatalogError(f"Image URL validation failed: {str(e)}")

    def classify_error(
        self, error_message: str, error_code: Optional[str] = None
    ) -> bool:
        """Classify if error is retryable or permanent"""
        if not error_message:
            return True  # Unknown errors are retryable

        error_lower = error_message.lower()

        # Permanent errors that should not be retried
        permanent_patterns = [
            "invalid retailer id",
            "catalog not found",
            "product not found",
            "invalid image format",
            "invalid url format",
            "permission denied",
            "access token expired",
            "invalid access token",
        ]

        for pattern in permanent_patterns:
            if pattern in error_lower:
                return False

        # Rate limit and temporary errors are retryable
        retryable_patterns = [
            "rate limit",
            "temporarily unavailable",
            "timeout",
            "connection",
            "network",
            "internal server error",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
        ]

        for pattern in retryable_patterns:
            if pattern in error_lower:
                return True

        # Rate limit error codes
        if error_code:
            rate_limit_codes = ["4", "17", "613", "80004"]
            if error_code in rate_limit_codes:
                return True

        # Default to retryable for unknown errors
        return True

    def format_product_for_meta(
        self, product_db: "ProductDB", merchant_config: Dict[str, Any]
    ) -> MetaCatalogProduct:
        """Convert database product to Meta catalog format"""
        from ..models.meta_catalog import ProductDB

        # Calculate availability
        availability = "in stock" if product_db.available_qty > 0 else "out of stock"

        # Format price with currency
        price_ngn = product_db.price_kobo / 100.0
        price_str = f"{price_ngn:.2f} NGN"

        # Generate product URL (could be merchant storefront URL)
        product_url = (
            merchant_config.get("storefront_url", "https://example.com")
            + f"/products/{product_db.id}"
        )

        return MetaCatalogProduct(
            retailer_id=product_db.retailer_id,
            name=product_db.title,
            description=product_db.description,
            url=product_url,
            image_url=product_db.image_url
            or "https://via.placeholder.com/400x400?text=No+Image",
            availability=availability,
            condition="new",
            price=price_str,
            brand=product_db.brand,  # Always included (satisfies Meta requirement)
            mpn=product_db.mpn,  # Always included (satisfies Meta requirement)
            category=product_db.category_path,
            inventory=(
                product_db.available_qty if product_db.available_qty > 0 else None
            ),
        )
