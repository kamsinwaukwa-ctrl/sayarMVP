"""
Meta Feed Service for CSV feed generation with RLS bypass and rate limiting support
"""

import csv
import hashlib
import io
import os
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_
from sqlalchemy.sql import func

from ..models.meta_catalog import MetaFeedProduct, MetaFeedResponse, MetaFeedConfig, MetaFeedStats
from ..models.sqlalchemy_models import Product, Merchant
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer

logger = get_logger(__name__)

class MetaFeedService:
    """Service for generating Meta Commerce CSV feeds with RLS bypass"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = MetaFeedConfig(
            base_url=os.getenv("FRONTEND_BASE_URL", "https://app.sayar.com"),
            cdn_base_url=os.getenv("CDN_BASE_URL"),
            brand_name="",  # Set per merchant
            default_category="Health & Beauty",
            cache_ttl=3600,
            max_products_per_feed=50000
        )
    
    async def generate_feed_csv(self, merchant_slug: str) -> Tuple[str, MetaFeedResponse]:
        """
        Generate CSV feed for merchant using SECURITY DEFINER function to bypass RLS
        Returns (csv_content, feed_metadata)
        """
        start_time = datetime.now()
        
        try:
            # Get merchant and products using RLS bypass function
            merchant, products = await self._get_merchant_feed_data(merchant_slug)
            
            if not merchant:
                raise ValueError(f"Merchant with slug '{merchant_slug}' not found")
            
            # Format products for Meta CSV
            meta_products = await self._format_products_for_meta(products, merchant)
            
            # Generate CSV content
            csv_content = await self._generate_csv_content(meta_products)
            
            # Calculate metadata
            last_updated = max(
                (product.updated_at for product in products), 
                default=datetime.utcnow()
            ) if products else datetime.utcnow()
            
            etag = self._generate_etag(merchant_slug, last_updated, len(products))
            
            feed_metadata = MetaFeedResponse(
                merchant_slug=merchant_slug,
                product_count=len(products),
                last_updated=last_updated,
                cache_ttl=self.config.cache_ttl,
                etag=etag,
                content_length=len(csv_content.encode('utf-8'))
            )
            
            # Log success
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info("meta_feed_generated", extra={
                "merchant_slug": merchant_slug,
                "merchant_id": str(merchant.id) if merchant else None,
                "product_count": len(products),
                "max_updated_at": last_updated.isoformat(),
                "etag": etag,
                "duration_ms": duration_ms,
                "content_size": len(csv_content.encode('utf-8'))
            })
            
            increment_counter("meta_feeds_generated_total")
            record_timer("meta_feed_generation_duration_ms", duration_ms)
            
            return csv_content, feed_metadata
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error("meta_feed_error", extra={
                "merchant_slug": merchant_slug,
                "error": str(e),
                "duration_ms": duration_ms
            })
            increment_counter("meta_feeds_error_total")
            raise
    
    async def _get_merchant_feed_data(self, merchant_slug: str) -> Tuple[Optional[Merchant], List[Product]]:
        """
        Get merchant and products using SECURITY DEFINER function to safely bypass RLS
        This is the recommended approach for public endpoints that need controlled RLS bypass
        """
        try:
            # First, create the SECURITY DEFINER function if it doesn't exist
            await self._ensure_feed_function_exists()
            
            # Call the SECURITY DEFINER function that safely bypasses RLS
            result = await self.db.execute(
                text("SELECT * FROM get_merchant_feed_data(:slug)"),
                {"slug": merchant_slug}
            )
            
            rows = result.fetchall()
            
            if not rows:
                return None, []
            
            # Parse results - first row contains merchant data, rest are products
            merchant_row = rows[0]
            
            # Create merchant object
            merchant = Merchant(
                id=merchant_row.merchant_id,
                name=merchant_row.merchant_name,
                slug=merchant_row.merchant_slug
            )
            
            # Create product objects from remaining data
            products = []
            for row in rows:
                if row.product_id:  # Skip if no product data
                    product = Product(
                        id=row.product_id,
                        merchant_id=row.merchant_id,
                        title=row.title,
                        description=row.description,
                        price_kobo=row.price_kobo,
                        stock=row.stock,
                        available_qty=row.available_qty,
                        image_url=row.image_url,
                        retailer_id=row.retailer_id,
                        category_path=row.category_path,
                        status=row.status,
                        meta_catalog_visible=row.meta_catalog_visible,
                        created_at=row.created_at,
                        updated_at=row.updated_at
                    )
                    products.append(product)
            
            return merchant, products
            
        except Exception as e:
            logger.error("Failed to get merchant feed data", extra={
                "merchant_slug": merchant_slug,
                "error": str(e)
            })
            raise
    
    async def _ensure_feed_function_exists(self):
        """Create the SECURITY DEFINER function for RLS bypass if it doesn't exist"""
        function_sql = """
        CREATE OR REPLACE FUNCTION get_merchant_feed_data(merchant_slug_param TEXT)
        RETURNS TABLE (
            merchant_id UUID,
            merchant_name TEXT,
            merchant_slug TEXT,
            product_id UUID,
            title TEXT,
            description TEXT,
            price_kobo INTEGER,
            stock INTEGER,
            available_qty INTEGER,
            image_url TEXT,
            retailer_id TEXT,
            category_path TEXT,
            status TEXT,
            meta_catalog_visible BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            -- This function runs with the privileges of the function creator
            -- allowing it to bypass RLS policies for the specific use case of public feeds
            
            RETURN QUERY
            SELECT 
                m.id as merchant_id,
                m.name as merchant_name,
                m.slug as merchant_slug,
                p.id as product_id,
                p.title,
                p.description,
                p.price_kobo,
                p.stock,
                p.available_qty,
                p.image_url,
                p.retailer_id,
                p.category_path,
                p.status,
                p.meta_catalog_visible,
                p.created_at,
                p.updated_at
            FROM merchants m
            LEFT JOIN products p ON p.merchant_id = m.id 
                AND p.status = 'active' 
                AND p.meta_catalog_visible = true
            WHERE m.slug = merchant_slug_param;
        END;
        $$;
        """
        
        await self.db.execute(text(function_sql))
        await self.db.commit()
    
    async def _format_products_for_meta(self, products: List[Product], merchant: Merchant) -> List[MetaFeedProduct]:
        """Convert products to Meta feed format with proper URL generation"""
        meta_products = []
        
        for product in products:
            # Generate absolute URLs
            product_link = f"{self.config.base_url}/products/{product.id}"
            
            # Handle image URLs - use CDN if available, fallback to direct URL
            image_link = product.image_url or ""
            if image_link and not image_link.startswith(('http://', 'https://')):
                if self.config.cdn_base_url:
                    image_link = f"{self.config.cdn_base_url}/{image_link}"
                else:
                    image_link = f"{self.config.base_url}/{image_link}"
            
            # If no image, skip image_link per Meta rules (don't use empty string)
            if not image_link:
                image_link = None
            
            # Format price from kobo to currency string
            price_formatted = f"{product.price_kobo / 100:.2f} NGN"
            
            # Determine availability
            availability = "in stock" if (product.available_qty and product.available_qty > 0) else "out of stock"
            
            meta_product = MetaFeedProduct(
                id=product.retailer_id,
                title=product.title,
                description=product.description,
                availability=availability,
                condition="new",
                price=price_formatted,
                link=product_link,
                image_link=image_link or f"{self.config.base_url}/images/placeholder.jpg",  # Fallback image
                brand=merchant.name,
                inventory=product.available_qty,
                product_type=product.category_path or self.config.default_category,
                google_product_category=self.config.default_category
            )
            
            meta_products.append(meta_product)
        
        return meta_products
    
    async def _generate_csv_content(self, products: List[MetaFeedProduct]) -> str:
        """
        Generate CSV string from products with proper escaping and encoding
        Returns UTF-8 encoded CSV with CRLF line endings for compatibility
        """
        output = io.StringIO()
        
        # Define field names matching Meta Commerce requirements
        fieldnames = [
            'id', 'title', 'description', 'availability', 'condition',
            'price', 'link', 'image_link', 'brand', 'inventory',
            'product_type', 'google_product_category'
        ]
        
        writer = csv.DictWriter(
            output, 
            fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator='\r\n'  # CRLF for better compatibility
        )
        
        # Write header
        writer.writeheader()
        
        # Write product rows
        for product in products:
            # Convert to dict and handle None values
            row = product.model_dump()
            
            # Remove None values (empty fields are better than "None" strings)
            row = {k: v for k, v in row.items() if v is not None}
            
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    def _generate_etag(self, merchant_slug: str, last_updated: datetime, product_count: int) -> str:
        """
        Generate deterministic ETag for caching
        Format: W/"<merchant_slug>-<max_updated_at_iso>-<visible_count>"
        """
        etag_data = f"{merchant_slug}-{last_updated.isoformat()}-{product_count}"
        etag_hash = hashlib.md5(etag_data.encode('utf-8')).hexdigest()[:16]
        return f'W/"{etag_hash}"'
    
    async def get_feed_stats(self, merchant_slug: str) -> Optional[MetaFeedStats]:
        """Get statistics for merchant's feed"""
        try:
            # Use the same RLS bypass function for consistency
            merchant, products = await self._get_merchant_feed_data(merchant_slug)
            
            if not merchant:
                return None
            
            # Calculate stats
            total_products = len(products)
            visible_products = len([p for p in products if p.meta_catalog_visible])
            in_stock_products = len([p for p in products if p.available_qty and p.available_qty > 0])
            
            # Get last sync info (would need additional query for actual sync data)
            last_sync_at = max(
                (p.updated_at for p in products), 
                default=None
            ) if products else None
            
            return MetaFeedStats(
                total_products=total_products,
                visible_products=visible_products,
                in_stock_products=in_stock_products,
                last_sync_at=last_sync_at,
                sync_errors=0  # Would need actual sync error tracking
            )
            
        except Exception as e:
            logger.error("Failed to get feed stats", extra={
                "merchant_slug": merchant_slug,
                "error": str(e)
            })
            return None