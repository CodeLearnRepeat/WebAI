"""
CMS Schema Adapters
Transform different CMS API responses into standardized format for ingestion
"""

from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re


class WordPressSchemaAdapter:
    """Transforms WordPress API response to standard format"""
    
    @staticmethod
    def clean_html(html_content: str) -> str:
        """Remove HTML tags and clean text"""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def transform_post(wp_post: Dict) -> Dict:
        """Convert WordPress post to standard format"""
        # Clean HTML from content
        clean_content = WordPressSchemaAdapter.clean_html(
            wp_post.get('content', {}).get('rendered', '')
        )
        
        # Extract title
        title = wp_post.get('title', {}).get('rendered', 'Untitled')
        
        # Combine title + content
        full_text = f"{title}\n\n{clean_content}"
        
        return {
            'text': full_text,
            'metadata': {
                'source': 'wordpress',
                'url': wp_post.get('link', ''),
                'title': title,
                'date': wp_post.get('date', ''),
                'post_id': str(wp_post.get('id', '')),
                'type': 'post'
            }
        }
    
    @staticmethod
    def transform_page(wp_page: Dict) -> Dict:
        """Convert WordPress page to standard format"""
        clean_content = WordPressSchemaAdapter.clean_html(
            wp_page.get('content', {}).get('rendered', '')
        )
        
        title = wp_page.get('title', {}).get('rendered', 'Untitled')
        
        return {
            'text': f"{title}\n\n{clean_content}",
            'metadata': {
                'source': 'wordpress',
                'url': wp_page.get('link', ''),
                'title': title,
                'date': wp_page.get('date', ''),
                'page_id': str(wp_page.get('id', '')),
                'type': 'page'
            }
        }


class ShopifySchemaAdapter:
    """Transforms Shopify API response to standard format"""
    
    @staticmethod
    def transform_product(shopify_product: Dict, shop_domain: str) -> Dict:
        """Convert Shopify product to standard format"""
        # Clean HTML from description
        clean_description = WordPressSchemaAdapter.clean_html(
            shopify_product.get('body_html', '')
        )
        
        # Build rich text with product details
        title = shopify_product.get('title', 'Untitled Product')
        vendor = shopify_product.get('vendor', '')
        product_type = shopify_product.get('product_type', '')
        
        # Get price from first variant
        variants = shopify_product.get('variants', [])
        price = variants[0].get('price', '') if variants else ''
        
        # Build comprehensive product text
        text_parts = [title]
        
        if vendor:
            text_parts.append(f"Brand: {vendor}")
        
        if product_type:
            text_parts.append(f"Type: {product_type}")
        
        if price:
            text_parts.append(f"Price: ${price}")
        
        if clean_description:
            text_parts.append(f"\n{clean_description}")
        
        full_text = "\n".join(text_parts)
        
        return {
            'text': full_text,
            'metadata': {
                'source': 'shopify',
                'url': f"https://{shop_domain}/products/{shopify_product.get('handle', '')}",
                'title': title,
                'product_id': str(shopify_product.get('id', '')),
                'type': 'product',
                'vendor': vendor,
                'price': price,
                'tags': shopify_product.get('tags', '')
            }
        }


class WebflowSchemaAdapter:
    """Transforms Webflow API response to standard format"""
    
    @staticmethod
    def transform_cms_item(
        webflow_item: Dict, 
        collection_name: str, 
        site_domain: str
    ) -> Dict:
        """Convert Webflow CMS item to standard format"""
        # Clean HTML from rich text fields
        post_body = webflow_item.get('post-body', '') or webflow_item.get('body', '')
        clean_content = WordPressSchemaAdapter.clean_html(post_body)
        
        name = webflow_item.get('name', 'Untitled')
        slug = webflow_item.get('slug', '')
        
        return {
            'text': f"{name}\n\n{clean_content}",
            'metadata': {
                'source': 'webflow',
                'url': f"https://{site_domain}/{slug}" if slug else '',
                'title': name,
                'item_id': webflow_item.get('_id', ''),
                'type': 'cms_item',
                'collection': collection_name
            }
        }


def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Simple text chunking - split on paragraphs
    
    Args:
        text: Text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Character overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    # Split on double newlines (paragraphs)
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        
        # If single paragraph is too large, split it
        if para_size > max_chunk_size:
            # Finish current chunk
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split large paragraph on sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            temp_chunk = []
            temp_size = 0
            
            for sentence in sentences:
                if temp_size + len(sentence) > max_chunk_size and temp_chunk:
                    chunks.append(' '.join(temp_chunk))
                    # Keep last sentence for overlap
                    temp_chunk = [temp_chunk[-1]] if temp_chunk else []
                    temp_size = len(temp_chunk[0]) if temp_chunk else 0
                
                temp_chunk.append(sentence)
                temp_size += len(sentence)
            
            if temp_chunk:
                chunks.append(' '.join(temp_chunk))
        
        # Normal paragraph
        elif current_size + para_size > max_chunk_size:
            # Save current chunk
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            # Start new chunk with overlap (keep last paragraph)
            current_chunk = [current_chunk[-1]] if current_chunk else []
            current_chunk.append(para)
            current_size = sum(len(p) for p in current_chunk)
        else:
            current_chunk.append(para)
            current_size += para_size
    
    # Add final chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks