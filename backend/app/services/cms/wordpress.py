"""
WordPress CMS Connector
Fetch content from WordPress sites via REST API
"""

import httpx
import logging
from typing import List, Dict, Optional, AsyncIterator

logger = logging.getLogger(__name__)


class WordPressConnector:
    """WordPress REST API connector"""
    
    def __init__(
        self, 
        site_url: str, 
        username: Optional[str] = None, 
        app_password: Optional[str] = None
    ):
        """
        Initialize WordPress connector
        
        Args:
            site_url: WordPress site URL (e.g., https://example.com)
            username: WordPress username (optional, for private content)
            app_password: WordPress application password (optional)
        """
        self.site_url = site_url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/wp/v2"
        self.auth = (username, app_password) if username and app_password else None
        
        logger.info(f"WordPress connector initialized for {self.site_url}")
    
    async def test_connection(self) -> Dict:
        """Test connection to WordPress API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.site_url}/wp-json")
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "site_name": data.get("name", "Unknown"),
                        "description": data.get("description", ""),
                        "url": data.get("url", ""),
                        "wp_version": data.get("wp_version", "Unknown")
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            logger.error(f"WordPress connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def fetch_posts(
        self, 
        per_page: int = 100,
        status: str = "publish",
        max_posts: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch all published posts from WordPress
        
        Args:
            per_page: Number of posts per API request
            status: Post status (publish, draft, etc.)
            max_posts: Maximum number of posts to fetch (None = all)
            
        Returns:
            List of WordPress post objects
        """
        posts = []
        page = 1
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    params = {
                        'page': page,
                        'per_page': per_page,
                        'status': status,
                        '_embed': True  # Include featured images and other data
                    }
                    
                    response = await client.get(
                        f"{self.api_url}/posts",
                        params=params,
                        auth=self.auth
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"WordPress posts API returned {response.status_code}")
                        break
                    
                    page_posts = response.json()
                    
                    if not page_posts:
                        break
                    
                    posts.extend(page_posts)
                    logger.info(f"Fetched {len(page_posts)} posts from page {page}")
                    
                    # Check if we've reached max_posts
                    if max_posts and len(posts) >= max_posts:
                        posts = posts[:max_posts]
                        break
                    
                    # Check if there are more pages
                    total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                    if page >= total_pages:
                        break
                    
                    page += 1
                    
                except Exception as e:
                    logger.error(f"Error fetching WordPress posts page {page}: {e}")
                    break
        
        logger.info(f"Total posts fetched: {len(posts)}")
        return posts
    
    async def fetch_pages(
        self, 
        per_page: int = 100,
        status: str = "publish",
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch all published pages from WordPress
        
        Args:
            per_page: Number of pages per API request
            status: Page status (publish, draft, etc.)
            max_pages: Maximum number of pages to fetch (None = all)
            
        Returns:
            List of WordPress page objects
        """
        pages = []
        page_num = 1
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    params = {
                        'page': page_num,
                        'per_page': per_page,
                        'status': status,
                        '_embed': True
                    }
                    
                    response = await client.get(
                        f"{self.api_url}/pages",
                        params=params,
                        auth=self.auth
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"WordPress pages API returned {response.status_code}")
                        break
                    
                    page_items = response.json()
                    
                    if not page_items:
                        break
                    
                    pages.extend(page_items)
                    logger.info(f"Fetched {len(page_items)} pages from page {page_num}")
                    
                    # Check if we've reached max_pages
                    if max_pages and len(pages) >= max_pages:
                        pages = pages[:max_pages]
                        break
                    
                    # Check if there are more pages
                    total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                    if page_num >= total_pages:
                        break
                    
                    page_num += 1
                    
                except Exception as e:
                    logger.error(f"Error fetching WordPress pages page {page_num}: {e}")
                    break
        
        logger.info(f"Total pages fetched: {len(pages)}")
        return pages
    
    async def fetch_all_content(
        self,
        include_posts: bool = True,
        include_pages: bool = True,
        max_items: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch all content from WordPress (posts and pages)
        
        Args:
            include_posts: Whether to fetch posts
            include_pages: Whether to fetch pages
            max_items: Maximum total items to fetch
            
        Returns:
            List of all WordPress content items
        """
        all_content = []
        
        if include_posts:
            posts = await self.fetch_posts(max_posts=max_items)
            all_content.extend(posts)
            logger.info(f"Fetched {len(posts)} posts")
        
        if include_pages:
            remaining = max_items - len(all_content) if max_items else None
            pages = await self.fetch_pages(max_pages=remaining)
            all_content.extend(pages)
            logger.info(f"Fetched {len(pages)} pages")
        
        logger.info(f"Total content items fetched: {len(all_content)}")
        return all_content
    
    async def stream_content(
        self,
        include_posts: bool = True,
        include_pages: bool = True
    ) -> AsyncIterator[Dict]:
        """
        Stream content items one by one (memory efficient for large sites)
        
        Args:
            include_posts: Whether to fetch posts
            include_pages: Whether to fetch pages
            
        Yields:
            Individual WordPress content items
        """
        if include_posts:
            page = 1
            async with httpx.AsyncClient(timeout=30.0) as client:
                while True:
                    try:
                        response = await client.get(
                            f"{self.api_url}/posts",
                            params={'page': page, 'per_page': 100, 'status': 'publish'},
                            auth=self.auth
                        )
                        
                        if response.status_code != 200:
                            break
                        
                        posts = response.json()
                        if not posts:
                            break
                        
                        for post in posts:
                            yield post
                        
                        page += 1
                    except Exception as e:
                        logger.error(f"Error streaming posts: {e}")
                        break
        
        if include_pages:
            page = 1
            async with httpx.AsyncClient(timeout=30.0) as client:
                while True:
                    try:
                        response = await client.get(
                            f"{self.api_url}/pages",
                            params={'page': page, 'per_page': 100, 'status': 'publish'},
                            auth=self.auth
                        )
                        
                        if response.status_code != 200:
                            break
                        
                        pages_items = response.json()
                        if not pages_items:
                            break
                        
                        for page_item in pages_items:
                            yield page_item
                        
                        page += 1
                    except Exception as e:
                        logger.error(f"Error streaming pages: {e}")
                        break