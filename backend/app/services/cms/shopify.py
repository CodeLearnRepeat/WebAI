"""
Shopify CMS Connector
Fetch product and content data from Shopify stores
"""

import httpx
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ShopifyConnector:
    """Shopify API connector"""
    
    def __init__(self, shop_domain: str, access_token: str):
        """
        Initialize Shopify connector
        
        Args:
            shop_domain: Shopify store domain (e.g., mystore.myshopify.com)
            access_token: Shopify Admin API access token
        """
        # Ensure domain doesn't have protocol
        self.shop_domain = shop_domain.replace('https://', '').replace('http://', '')
        self.api_url = f"https://{self.shop_domain}/admin/api/2024-01"
        self.access_token = access_token
        
        logger.info(f"Shopify connector initialized for {self.shop_domain}")
    
    async def test_connection(self) -> Dict:
        """Test connection to Shopify API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/shop.json",
                    headers={'X-Shopify-Access-Token': self.access_token}
                )
                
                if response.status_code == 200:
                    shop_data = response.json().get('shop', {})
                    return {
                        "status": "success",
                        "shop_name": shop_data.get('name', 'Unknown'),
                        "email": shop_data.get('email', ''),
                        "domain": shop_data.get('domain', ''),
                        "currency": shop_data.get('currency', 'USD')
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            logger.error(f"Shopify connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def fetch_products(
        self,
        limit: int = 250,
        max_products: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch products from Shopify
        
        Args:
            limit: Number of products per API request (max 250)
            max_products: Maximum number of products to fetch (None = all)
            
        Returns:
            List of Shopify product objects
        """
        products = []
        since_id = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    params = {
                        'limit': min(limit, 250),
                        'since_id': since_id,
                        'status': 'active'
                    }
                    
                    response = await client.get(
                        f"{self.api_url}/products.json",
                        params=params,
                        headers={'X-Shopify-Access-Token': self.access_token}
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Shopify products API returned {response.status_code}")
                        break
                    
                    data = response.json()
                    batch_products = data.get('products', [])
                    
                    if not batch_products:
                        break
                    
                    products.extend(batch_products)
                    logger.info(f"Fetched {len(batch_products)} products (total: {len(products)})")
                    
                    # Check if we've reached max_products
                    if max_products and len(products) >= max_products:
                        products = products[:max_products]
                        break
                    
                    # Get last product ID for pagination
                    since_id = batch_products[-1]['id']
                    
                    # If we got fewer than limit, we're done
                    if len(batch_products) < limit:
                        break
                    
                except Exception as e:
                    logger.error(f"Error fetching Shopify products: {e}")
                    break
        
        logger.info(f"Total products fetched: {len(products)}")
        return products
    
    async def fetch_pages(
        self,
        limit: int = 250,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch pages from Shopify
        
        Args:
            limit: Number of pages per API request (max 250)
            max_pages: Maximum number of pages to fetch (None = all)
            
        Returns:
            List of Shopify page objects
        """
        pages = []
        since_id = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    params = {
                        'limit': min(limit, 250),
                        'since_id': since_id
                    }
                    
                    response = await client.get(
                        f"{self.api_url}/pages.json",
                        params=params,
                        headers={'X-Shopify-Access-Token': self.access_token}
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Shopify pages API returned {response.status_code}")
                        break
                    
                    data = response.json()
                    batch_pages = data.get('pages', [])
                    
                    if not batch_pages:
                        break
                    
                    pages.extend(batch_pages)
                    logger.info(f"Fetched {len(batch_pages)} pages (total: {len(pages)})")
                    
                    # Check if we've reached max_pages
                    if max_pages and len(pages) >= max_pages:
                        pages = pages[:max_pages]
                        break
                    
                    # Get last page ID for pagination
                    since_id = batch_pages[-1]['id']
                    
                    # If we got fewer than limit, we're done
                    if len(batch_pages) < limit:
                        break
                    
                except Exception as e:
                    logger.error(f"Error fetching Shopify pages: {e}")
                    break
        
        logger.info(f"Total pages fetched: {len(pages)}")
        return pages
    
    async def fetch_all_content(
        self,
        include_products: bool = True,
        include_pages: bool = True,
        max_items: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch all content from Shopify (products and pages)
        
        Args:
            include_products: Whether to fetch products
            include_pages: Whether to fetch pages
            max_items: Maximum total items to fetch
            
        Returns:
            List of all Shopify content items with type indicator
        """
        all_content = []
        
        if include_products:
            products = await self.fetch_products(max_products=max_items)
            # Add type indicator
            for product in products:
                product['_content_type'] = 'product'
            all_content.extend(products)
            logger.info(f"Fetched {len(products)} products")
        
        if include_pages:
            remaining = max_items - len(all_content) if max_items else None
            pages = await self.fetch_pages(max_pages=remaining)
            # Add type indicator
            for page in pages:
                page['_content_type'] = 'page'
            all_content.extend(pages)
            logger.info(f"Fetched {len(pages)} pages")
        
        logger.info(f"Total content items fetched: {len(all_content)}")
        return all_content