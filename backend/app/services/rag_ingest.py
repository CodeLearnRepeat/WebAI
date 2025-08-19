import asyncio
import tempfile
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, AsyncIterator, Union
from dataclasses import dataclass

from app.services.embeddings import embed_texts, embed_texts_async, BatchEmbeddingService
from app.services.vectorstores.milvus_store import ensure_collection, upsert_texts
from app.services.streaming_parser import StreamingJSONProcessor, ProcessedItem, process_json_file
from app.services.batch_manager import BatchProcessor, create_batch_processor
from app.services.token_counter import VoyageTokenCounter

logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    """Statistics for ingestion process."""
    total_items_processed: int = 0
    total_chunks_created: int = 0
    total_embeddings_generated: int = 0
    batches_processed: int = 0
    processing_time: float = 0.0
    errors_encountered: int = 0


def ingest_to_milvus(
    *,
    texts: List[str],
    metadatas: Optional[List[dict]],
    milvus_conf: Dict,
    emb_provider: str,
    emb_model: str,
    provider_key: Optional[str],
    use_batching: bool = True
) -> Dict:
    """
    Ingest texts to Milvus with optional intelligent batching.
    
    Args:
        texts: List of texts to embed and store
        metadatas: Optional metadata for each text
        milvus_conf: Milvus configuration
        emb_provider: Embedding provider
        emb_model: Embedding model name
        provider_key: API key for provider
        use_batching: Whether to use intelligent batching for VoyageAI
        
    Returns:
        Dictionary with ingestion results
    """
    if not texts:
        return {"upserted": 0, "dim": 0}
    
    logger.info(f"Ingesting {len(texts)} texts using {emb_provider}/{emb_model}")
    
    # Embed texts (with batching if using VoyageAI)
    vecs, dim = embed_texts(
        provider=emb_provider,
        model_name=emb_model,
        texts=texts,
        api_key=provider_key,
        mode="document",
        use_batching=use_batching
    )

    # Ensure collection exists
    ensure_collection(
        uri=milvus_conf["uri"],
        token=milvus_conf.get("token"),
        db_name=milvus_conf.get("db_name"),
        collection=milvus_conf["collection"],
        vector_field=milvus_conf.get("vector_field", "embedding"),
        text_field=milvus_conf.get("text_field", "text"),
        metadata_field=milvus_conf.get("metadata_field", "metadata"),
        dim=dim,
        metric_type=milvus_conf.get("metric_type", "IP"),
    )

    # Prepare rows for insertion
    rows = []
    for i, t in enumerate(texts):
        row = {"text": t, "embedding": vecs[i]}
        if metadatas and i < len(metadatas):
            row["metadata"] = json.dumps(metadatas[i] or {}, ensure_ascii=False)
        else:
            row["metadata"] = json.dumps({}, ensure_ascii=False)
        rows.append(row)

    # Insert into Milvus
    upsert_texts(
        uri=milvus_conf["uri"],
        token=milvus_conf.get("token"),
        db_name=milvus_conf.get("db_name"),
        collection=milvus_conf["collection"],
        vector_field=milvus_conf.get("vector_field", "embedding"),
        text_field=milvus_conf.get("text_field", "text"),
        metadata_field=milvus_conf.get("metadata_field", "metadata"),
        dim=dim,
        metric_type=milvus_conf.get("metric_type", "IP"),
        rows=rows,
    )
    
    logger.info(f"Successfully ingested {len(rows)} texts with dimension {dim}")
    return {"upserted": len(rows), "dim": dim}


async def ingest_to_milvus_async(
    *,
    texts: List[str],
    metadatas: Optional[List[dict]],
    milvus_conf: Dict,
    emb_provider: str,
    emb_model: str,
    provider_key: Optional[str],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict:
    """
    Async version of ingest_to_milvus with progress tracking.
    
    Args:
        texts: List of texts to embed and store
        metadatas: Optional metadata for each text
        milvus_conf: Milvus configuration
        emb_provider: Embedding provider
        emb_model: Embedding model name
        provider_key: API key for provider
        progress_callback: Optional progress callback
        
    Returns:
        Dictionary with ingestion results
    """
    if not texts:
        return {"upserted": 0, "dim": 0}
    
    logger.info(f"Async ingesting {len(texts)} texts using {emb_provider}/{emb_model}")
    
    # Embed texts with progress tracking
    vecs, dim = await embed_texts_async(
        provider=emb_provider,
        model_name=emb_model,
        texts=texts,
        api_key=provider_key,
        mode="document",
        progress_callback=progress_callback
    )

    # Ensure collection exists
    await asyncio.to_thread(
        ensure_collection,
        uri=milvus_conf["uri"],
        token=milvus_conf.get("token"),
        db_name=milvus_conf.get("db_name"),
        collection=milvus_conf["collection"],
        vector_field=milvus_conf.get("vector_field", "embedding"),
        text_field=milvus_conf.get("text_field", "text"),
        metadata_field=milvus_conf.get("metadata_field", "metadata"),
        dim=dim,
        metric_type=milvus_conf.get("metric_type", "IP"),
    )

    # Prepare rows for insertion
    rows = []
    for i, t in enumerate(texts):
        row = {"text": t, "embedding": vecs[i]}
        if metadatas and i < len(metadatas):
            row["metadata"] = json.dumps(metadatas[i] or {}, ensure_ascii=False)
        else:
            row["metadata"] = json.dumps({}, ensure_ascii=False)
        rows.append(row)

    # Insert into Milvus
    await asyncio.to_thread(
        upsert_texts,
        uri=milvus_conf["uri"],
        token=milvus_conf.get("token"),
        db_name=milvus_conf.get("db_name"),
        collection=milvus_conf["collection"],
        vector_field=milvus_conf.get("vector_field", "embedding"),
        text_field=milvus_conf.get("text_field", "text"),
        metadata_field=milvus_conf.get("metadata_field", "metadata"),
        dim=dim,
        metric_type=milvus_conf.get("metric_type", "IP"),
        rows=rows,
    )
    
    logger.info(f"Successfully async ingested {len(rows)} texts with dimension {dim}")
    return {"upserted": len(rows), "dim": dim}


async def ingest_json_file_streaming(
    *,
    file_path: Union[str, Path],
    schema_config: Dict,
    milvus_conf: Dict,
    emb_provider: str,
    emb_model: str,
    provider_key: Optional[str],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    batch_size: int = 100
) -> Dict:
    """
    Ingest JSON file using streaming parser with token-aware batching.
    
    Args:
        file_path: Path to JSON file
        schema_config: Schema configuration for parsing
        milvus_conf: Milvus configuration
        emb_provider: Embedding provider
        emb_model: Embedding model name
        provider_key: API key for provider
        progress_callback: Optional progress callback
        batch_size: Number of texts to process in each Milvus batch
        
    Returns:
        Dictionary with ingestion results and statistics
    """
    logger.info(f"Starting streaming ingestion of {file_path}")
    
    stats = IngestStats()
    start_time = asyncio.get_event_loop().time()
    
    # Initialize embedding service
    embedding_service = BatchEmbeddingService(emb_provider, emb_model, provider_key)
    
    # Collection dimension tracking
    collection_dim = None
    collection_initialized = False
    
    # Batch accumulator for Milvus insertion
    text_batch = []
    metadata_batch = []
    
    try:
        # Process file with streaming parser
        async for item in process_json_file(file_path, schema_config):
            text_batch.append(item.text)
            metadata_batch.append(item.metadata)
            stats.total_chunks_created += 1
            
            # Process batch when it reaches batch_size
            if len(text_batch) >= batch_size:
                result = await _process_text_batch(
                    text_batch, metadata_batch, milvus_conf, embedding_service,
                    collection_dim, collection_initialized, stats
                )
                
                if not collection_initialized:
                    collection_dim = result["dim"]
                    collection_initialized = True
                
                # Clear batch
                text_batch = []
                metadata_batch = []
                
                # Progress callback
                if progress_callback:
                    progress_callback(stats.total_chunks_created, None)  # Total unknown in streaming
        
        # Process final batch
        if text_batch:
            result = await _process_text_batch(
                text_batch, metadata_batch, milvus_conf, embedding_service,
                collection_dim, collection_initialized, stats
            )
            
            if not collection_initialized:
                collection_dim = result["dim"]
        
        # Final statistics
        stats.processing_time = asyncio.get_event_loop().time() - start_time
        
        # Get embedding service statistics
        embedding_stats = embedding_service.get_batching_stats()
        
        logger.info(
            f"Completed streaming ingestion: {stats.total_chunks_created} chunks, "
            f"{stats.total_embeddings_generated} embeddings, "
            f"{stats.batches_processed} Milvus batches in {stats.processing_time:.2f}s"
        )
        
        return {
            "status": "completed",
            "upserted": stats.total_embeddings_generated,
            "dim": collection_dim or 0,
            "statistics": {
                "total_items_processed": stats.total_items_processed,
                "total_chunks_created": stats.total_chunks_created,
                "total_embeddings_generated": stats.total_embeddings_generated,
                "batches_processed": stats.batches_processed,
                "processing_time": stats.processing_time,
                "errors_encountered": stats.errors_encountered,
                "embedding_batching": embedding_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error during streaming ingestion: {e}")
        stats.errors_encountered += 1
        raise


async def _process_text_batch(
    texts: List[str],
    metadatas: List[Dict],
    milvus_conf: Dict,
    embedding_service: BatchEmbeddingService,
    collection_dim: Optional[int],
    collection_initialized: bool,
    stats: IngestStats
) -> Dict:
    """Process a batch of texts for embedding and storage."""
    if not texts:
        return {"upserted": 0, "dim": collection_dim or 0}
    
    # Embed texts
    vecs, dim = await embedding_service.embed_texts_with_batching(texts)
    stats.total_embeddings_generated += len(vecs)
    
    # Initialize collection if needed
    if not collection_initialized:
        await asyncio.to_thread(
            ensure_collection,
            uri=milvus_conf["uri"],
            token=milvus_conf.get("token"),
            db_name=milvus_conf.get("db_name"),
            collection=milvus_conf["collection"],
            vector_field=milvus_conf.get("vector_field", "embedding"),
            text_field=milvus_conf.get("text_field", "text"),
            metadata_field=milvus_conf.get("metadata_field", "metadata"),
            dim=dim,
            metric_type=milvus_conf.get("metric_type", "IP"),
        )
    
    # Prepare rows
    rows = []
    for i, text in enumerate(texts):
        row = {
            "text": text,
            "embedding": vecs[i],
            "metadata": json.dumps(metadatas[i] if i < len(metadatas) else {}, ensure_ascii=False)
        }
        rows.append(row)
    
    # Insert to Milvus
    await asyncio.to_thread(
        upsert_texts,
        uri=milvus_conf["uri"],
        token=milvus_conf.get("token"),
        db_name=milvus_conf.get("db_name"),
        collection=milvus_conf["collection"],
        vector_field=milvus_conf.get("vector_field", "embedding"),
        text_field=milvus_conf.get("text_field", "text"),
        metadata_field=milvus_conf.get("metadata_field", "metadata"),
        dim=dim,
        metric_type=milvus_conf.get("metric_type", "IP"),
        rows=rows,
    )
    
    stats.batches_processed += 1
    return {"upserted": len(rows), "dim": dim}


def create_enhanced_chunking_config(
    base_config: Dict,
    model_name: str = "voyage-large-2",
    max_tokens: int = 1000,
    overlap_tokens: int = 100
) -> Dict:
    """
    Create enhanced chunking configuration with token-aware settings.
    
    Args:
        base_config: Base schema configuration
        model_name: Model name for token counting
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap tokens between chunks
        
    Returns:
        Enhanced configuration with token-aware chunking
    """
    enhanced_config = base_config.copy()
    
    # Add token-aware chunking configuration
    enhanced_config["chunking"] = {
        "strategy": "token_aware",
        "max_tokens": max_tokens,
        "overlap_tokens": overlap_tokens,
        "model_name": model_name,
        # Fallback to character-based for non-VoyageAI models
        "fallback_max_chars": max_tokens * 4,  # Rough estimate: 4 chars per token
        "fallback_overlap": overlap_tokens * 4
    }
    
    return enhanced_config


def estimate_processing_time(
    file_size_bytes: int,
    estimated_items: int,
    emb_provider: str
) -> Dict[str, float]:
    """
    Estimate processing time based on file size and provider.
    
    Args:
        file_size_bytes: Size of file in bytes
        estimated_items: Estimated number of items
        emb_provider: Embedding provider
        
    Returns:
        Dictionary with time estimates
    """
    # Base processing rates (items per second)
    rates = {
        "sentence_transformers": 100,  # Local processing, faster
        "openai": 50,  # API-limited
        "voyageai": 30   # API-limited with batching overhead
    }
    
    base_rate = rates.get(emb_provider, 30)
    
    # Adjust for file size (larger files have overhead)
    size_factor = 1.0 + (file_size_bytes / (100 * 1024 * 1024))  # +100% for 100MB files
    
    estimated_seconds = (estimated_items / base_rate) * size_factor
    
    return {
        "estimated_seconds": estimated_seconds,
        "estimated_minutes": estimated_seconds / 60,
        "estimated_hours": estimated_seconds / 3600,
        "confidence": "low" if file_size_bytes > 50 * 1024 * 1024 else "medium"
    }