"""
Webflow CMS Connector
Fetch CMS collection items from Webflow sites
"""

import httpx
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WebflowConnector:
    """Webflow API connector"""
    
    def __init__(self, site_id: str, api_token: str):
        """
        Initialize Webflow connector
        
        Args:
            site_id: Webflow site ID
            api_token: Webflow API token
        """
        self.site_id = site_id
        self.api_token = api_token
        self.api_url = "https://api.webflow.com"
        
        logger.info(f"Webflow connector initialized for site {site_id}")
    
    async def test_connection(self) -> Dict:
        """Test connection to Webflow API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/sites/{self.site_id}",
                    headers={'authorization': f'Bearer {self.api_token}'}
                )
                
                if response.status_code == 200:
                    site_data = response.json()
                    return {
                        "status": "success",
                        "site_name": site_data.get('name', 'Unknown'),
                        "short_name": site_data.get('shortName', ''),
                        "created_on": site_data.get('createdOn', '')
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            logger.error(f"Webflow connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def fetch_collections(self) -> List[Dict]:
        """
        Fetch all CMS collections for the site
        
        Returns:
            List of collection objects
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/sites/{self.site_id}/collections",
                    headers={'authorization': f'Bearer {self.api_token}'}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch collections: {response.status_code}")
                    return []
                
                collections = response.json()
                logger.info(f"Found {len(collections)} collections")
                return collections
                
        except Exception as e:
            logger.error(f"Error fetching Webflow collections: {e}")
            return []
    
    async def fetch_collection_items(
        self,
        collection_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch all items from a specific collection
        
        Args:
            collection_id: Webflow collection ID
            limit: Number of items per request (max 100)
            
        Returns:
            List of collection items
        """
        items = []
        offset = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    params = {
                        'limit': min(limit, 100),
                        'offset': offset
                    }
                    
                    response = await client.get(
                        f"{self.api_url}/collections/{collection_id}/items",
                        params=params,
                        headers={'authorization': f'Bearer {self.api_token}'}
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Webflow collection items API returned {response.status_code}")
                        break
                    
                    data = response.json()
                    batch_items = data.get('items', [])
                    
                    if not batch_items:
                        break
                    
                    items.extend(batch_items)
                    logger.info(f"Fetched {len(batch_items)} items from collection (total: {len(items)})")
                    
                    # Check if there are more items
                    total = data.get('total', 0)
                    if len(items) >= total:
                        break
                    
                    offset += len(batch_items)
                    
                except Exception as e:
                    logger.error(f"Error fetching Webflow collection items: {e}")
                    break
        
        return items
    
    async def fetch_all_content(
        self,
        collection_ids: Optional[List[str]] = None,
        max_items: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch all CMS content from Webflow
        
        Args:
            collection_ids: Specific collection IDs to fetch (None = all)
            max_items: Maximum total items to fetch
            
        Returns:
            List of all CMS items with collection metadata
        """
        all_items = []
        
        # Get all collections if not specified
        if collection_ids is None:
            collections = await self.fetch_collections()
            collection_ids = [c['_id'] for c in collections]
            
            # Store collection data for later reference
            collection_map = {c['_id']: c for c in collections}
        else:
            # Fetch collection metadata for specified IDs
            collections = await self.fetch_collections()
            collection_map = {c['_id']: c for c in collections if c['_id'] in collection_ids}
        
        # Fetch items from each collection
        for collection_id in collection_ids:
            if max_items and len(all_items) >= max_items:
                break
            
            items = await self.fetch_collection_items(collection_id)
            
            # Add collection metadata to each item
            collection_data = collection_map.get(collection_id, {})
            for item in items:
                item['_collection_name'] = collection_data.get('name', 'Unknown')
                item['_collection_id'] = collection_id
            
            all_items.extend(items)
            logger.info(f"Fetched {len(items)} items from collection {collection_data.get('name', collection_id)}")
            
            # Trim if we exceeded max_items
            if max_items and len(all_items) > max_items:
                all_items = all_items[:max_items]
                break
        
        logger.info(f"Total items fetched: {len(all_items)}")
        return all_items