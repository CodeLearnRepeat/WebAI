"""
CMS Sync Routes
Endpoints for syncing content from various CMS platforms
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging

from app.services.cms.wordpress import WordPressConnector
from app.services.cms.shopify import ShopifyConnector
from app.services.cms.webflow import WebflowConnector
from app.services.cms.schemas import (
    WordPressSchemaAdapter,
    ShopifySchemaAdapter,
    WebflowSchemaAdapter,
    chunk_text
)
from app.services.rag_ingest import ingest_to_milvus_async
from app.services.tenants import get_tenant_config

router = APIRouter(prefix="/cms", tags=["CMS Sync"])
logger = logging.getLogger(__name__)


# Request Models
class WordPressCredentials(BaseModel):
    site_url: str = Field(..., description="WordPress site URL")
    username: Optional[str] = Field(None, description="WordPress username (optional)")
    app_password: Optional[str] = Field(None, description="WordPress application password (optional)")
    include_posts: bool = Field(True, description="Include posts")
    include_pages: bool = Field(True, description="Include pages")


class ShopifyCredentials(BaseModel):
    shop_domain: str = Field(..., description="Shopify store domain (e.g., mystore.myshopify.com)")
    access_token: str = Field(..., description="Shopify Admin API access token")
    include_products: bool = Field(True, description="Include products")
    include_pages: bool = Field(True, description="Include pages")


class WebflowCredentials(BaseModel):
    site_id: str = Field(..., description="Webflow site ID")
    api_token: str = Field(..., description="Webflow API token")
    site_domain: str = Field(..., description="Webflow site domain for URLs")
    collection_ids: Optional[List[str]] = Field(None, description="Specific collection IDs (None = all)")


# WordPress Endpoints
@router.post("/wordpress/test")
async def test_wordpress_connection(
    credentials: WordPressCredentials,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """Test WordPress connection"""
    try:
        connector = WordPressConnector(
            credentials.site_url,
            credentials.username,
            credentials.app_password
        )
        result = await connector.test_connection()
        return result
    except Exception as e:
        logger.error(f"WordPress connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wordpress/sync")
async def sync_wordpress_content(
    credentials: WordPressCredentials,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """Sync all WordPress content to RAG database"""
    try:
        # Get tenant configuration
        tenant_config = await get_tenant_config(tenant_id)
        
        if not tenant_config.get('rag', {}).get('enabled'):
            raise HTTPException(status_code=400, detail="RAG is not enabled for this tenant")
        
        # Initialize WordPress connector
        connector = WordPressConnector(
            credentials.site_url,
            credentials.username,
            credentials.app_password
        )
        
        # Fetch all content
        logger.info(f"Fetching WordPress content from {credentials.site_url}")
        raw_content = await connector.fetch_all_content(
            include_posts=credentials.include_posts,
            include_pages=credentials.include_pages
        )
        
        if not raw_content:
            return {
                "status": "success",
                "message": "No content found",
                "items_synced": 0,
                "chunks_created": 0
            }
        
        # Transform using WordPress adapter
        standardized = []
        for item in raw_content:
            try:
                # Determine if post or page
                if item.get('type') == 'page':
                    transformed = WordPressSchemaAdapter.transform_page(item)
                else:
                    transformed = WordPressSchemaAdapter.transform_post(item)
                standardized.append(transformed)
            except Exception as e:
                logger.warning(f"Failed to transform item {item.get('id')}: {e}")
                continue
        
        logger.info(f"Transformed {len(standardized)} items")
        
        # Chunk texts for better retrieval
        chunked_texts = []
        chunked_metadata = []
        
        for item in standardized:
            text = item['text']
            metadata = item['metadata']
            
            # Simple chunking (split long content)
            if len(text) > 1200:
                chunks = chunk_text(text, max_chunk_size=1200, overlap=150)
                for chunk in chunks:
                    if len(chunk.strip()) > 100:  # Skip very short chunks
                        chunked_texts.append(chunk)
                        chunked_metadata.append(metadata)
            else:
                if len(text.strip()) > 100:
                    chunked_texts.append(text)
                    chunked_metadata.append(metadata)
        
        logger.info(f"Created {len(chunked_texts)} chunks from {len(standardized)} items")
        
        if not chunked_texts:
            return {
                "status": "success",
                "message": "No valid content to index after chunking",
                "items_synced": len(standardized),
                "chunks_created": 0
            }
        
        # Ingest to Milvus using existing pipeline
        milvus_conf = tenant_config['rag']['milvus']
        rag_config = tenant_config['rag']
        
        result = await ingest_to_milvus_async(
            texts=chunked_texts,
            metadatas=chunked_metadata,
            milvus_conf=milvus_conf,
            emb_provider=rag_config['embedding_provider'],
            emb_model=rag_config['embedding_model'],
            provider_key=rag_config.get('provider_keys', {}).get(rag_config['embedding_provider'])
        )
        
        return {
            "status": "success",
            "platform": "wordpress",
            "site_url": credentials.site_url,
            "items_synced": len(standardized),
            "chunks_created": len(chunked_texts),
            "embeddings_generated": result.get('upserted', 0),
            "dimension": result.get('dim', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WordPress sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# Shopify Endpoints
@router.post("/shopify/test")
async def test_shopify_connection(
    credentials: ShopifyCredentials,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """Test Shopify connection"""
    try:
        connector = ShopifyConnector(
            credentials.shop_domain,
            credentials.access_token
        )
        result = await connector.test_connection()
        return result
    except Exception as e:
        logger.error(f"Shopify connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shopify/sync")
async def sync_shopify_content(
    credentials: ShopifyCredentials,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """Sync all Shopify content to RAG database"""
    try:
        # Get tenant configuration
        tenant_config = await get_tenant_config(tenant_id)
        
        if not tenant_config.get('rag', {}).get('enabled'):
            raise HTTPException(status_code=400, detail="RAG is not enabled for this tenant")
        
        # Initialize Shopify connector
        connector = ShopifyConnector(
            credentials.shop_domain,
            credentials.access_token
        )
        
        # Fetch all content
        logger.info(f"Fetching Shopify content from {credentials.shop_domain}")
        raw_content = await connector.fetch_all_content(
            include_products=credentials.include_products,
            include_pages=credentials.include_pages
        )
        
        if not raw_content:
            return {
                "status": "success",
                "message": "No content found",
                "items_synced": 0,
                "chunks_created": 0
            }
        
        # Transform using Shopify adapter
        standardized = []
        for item in raw_content:
            try:
                if item.get('_content_type') == 'product':
                    transformed = ShopifySchemaAdapter.transform_product(item, credentials.shop_domain)
                    standardized.append(transformed)
            except Exception as e:
                logger.warning(f"Failed to transform item: {e}")
                continue
        
        logger.info(f"Transformed {len(standardized)} items")
        
        # Extract texts and metadata
        texts = [item['text'] for item in standardized]
        metadatas = [item['metadata'] for item in standardized]
        
        # Ingest to Milvus
        milvus_conf = tenant_config['rag']['milvus']
        rag_config = tenant_config['rag']
        
        result = await ingest_to_milvus_async(
            texts=texts,
            metadatas=metadatas,
            milvus_conf=milvus_conf,
            emb_provider=rag_config['embedding_provider'],
            emb_model=rag_config['embedding_model'],
            provider_key=rag_config.get('provider_keys', {}).get(rag_config['embedding_provider'])
        )
        
        return {
            "status": "success",
            "platform": "shopify",
            "shop_domain": credentials.shop_domain,
            "items_synced": len(standardized),
            "chunks_created": len(texts),
            "embeddings_generated": result.get('upserted', 0),
            "dimension": result.get('dim', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Shopify sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# Webflow Endpoints
@router.post("/webflow/test")
async def test_webflow_connection(
    credentials: WebflowCredentials,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """Test Webflow connection"""
    try:
        connector = WebflowConnector(
            credentials.site_id,
            credentials.api_token
        )
        result = await connector.test_connection()
        return result
    except Exception as e:
        logger.error(f"Webflow connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webflow/sync")
async def sync_webflow_content(
    credentials: WebflowCredentials,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    """Sync all Webflow CMS content to RAG database"""
    try:
        # Get tenant configuration
        tenant_config = await get_tenant_config(tenant_id)
        
        if not tenant_config.get('rag', {}).get('enabled'):
            raise HTTPException(status_code=400, detail="RAG is not enabled for this tenant")
        
        # Initialize Webflow connector
        connector = WebflowConnector(
            credentials.site_id,
            credentials.api_token
        )
        
        # Fetch all content
        logger.info(f"Fetching Webflow content from site {credentials.site_id}")
        raw_content = await connector.fetch_all_content(
            collection_ids=credentials.collection_ids
        )
        
        if not raw_content:
            return {
                "status": "success",
                "message": "No content found",
                "items_synced": 0,
                "chunks_created": 0
            }
        
        # Transform using Webflow adapter
        standardized = []
        for item in raw_content:
            try:
                transformed = WebflowSchemaAdapter.transform_cms_item(
                    item,
                    item.get('_collection_name', 'Unknown'),
                    credentials.site_domain
                )
                standardized.append(transformed)
            except Exception as e:
                logger.warning(f"Failed to transform item: {e}")
                continue
        
        logger.info(f"Transformed {len(standardized)} items")
        
        # Extract texts and metadata
        texts = [item['text'] for item in standardized]
        metadatas = [item['metadata'] for item in standardized]
        
        # Ingest to Milvus
        milvus_conf = tenant_config['rag']['milvus']
        rag_config = tenant_config['rag']
        
        result = await ingest_to_milvus_async(
            texts=texts,
            metadatas=metadatas,
            milvus_conf=milvus_conf,
            emb_provider=rag_config['embedding_provider'],
            emb_model=rag_config['embedding_model'],
            provider_key=rag_config.get('provider_keys', {}).get(rag_config['embedding_provider'])
        )
        
        return {
            "status": "success",
            "platform": "webflow",
            "site_id": credentials.site_id,
            "items_synced": len(standardized),
            "chunks_created": len(texts),
            "embeddings_generated": result.get('upserted', 0),
            "dimension": result.get('dim', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webflow sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")