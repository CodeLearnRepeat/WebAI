#!/usr/bin/env python3
import asyncio
import json
import tempfile
from pathlib import Path

async def test_full_ingestion_flow():
    """Test the complete ingestion flow with your exact configuration"""
    
    # Your exact tenant configuration
    tenant_config = {
        "rag": {
            "enabled": True,
            "provider": "milvus",
            "embedding_provider": "voyageai",
            "embedding_model": "voyage-law-2",
            "provider_keys": {
                "voyageai": "pa-bjQqpaOLZQ9Z8V35322F7XboWIYsVQklWdg_25RdNkK"
            },
            "milvus": {
                "uri": "https://in03-7b3940c7c2d29d3.serverless.gcp-us-west1.cloud.zilliz.com",
                "token": "8c8d4d5f6cb3926e46e39c6eeca8c69bb3601c7e5a1586be40c6add0b90bb60e71506ab78a2229c4fe27bc526a8ab1ad30d60a1b",
                "db_name": "RHTAI",
                "collection": "debug_test_collection",  # Use a test collection
                "vector_field": "embedding",
                "text_field": "text",
                "metadata_field": "metadata",
                "metric_type": "IP"
            }
        }
    }
    
    # Test data
    test_data = [
        {
            "raw_text": "This is a test document for debugging silent failures in the RAG ingestion system.",
            "source_url": "https://example.com/test1",
            "document_title": "Test Document 1"
        },
        {
            "raw_text": "Another test document to verify that the embedding and vector storage pipeline is working correctly.",
            "source_url": "https://example.com/test2", 
            "document_title": "Test Document 2"
        }
    ]
    
    schema_config = {
        "format": "json_array",
        "mapping": {
            "content_path": "raw_text",
            "metadata_paths": {
                "url": "source_url",
                "title": "document_title"
            }
        },
        "chunking": {
            "strategy": "recursive",
            "max_chars": 1200,
            "overlap": 150
        }
    }
    
    # Save test data to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file_path = f.name
    
    try:
        print("🧪 Starting comprehensive ingestion test...")
        
        # Import your services (adjust paths as needed)
        from app.services.rag_ingest import ingest_json_file_streaming
        
        # Run ingestion with maximum logging
        result = await ingest_json_file_streaming(
            file_path=temp_file_path,
            schema_config=schema_config,
            milvus_conf=tenant_config["rag"]["milvus"],
            emb_provider=tenant_config["rag"]["embedding_provider"],
            emb_model=tenant_config["rag"]["embedding_model"],
            provider_key=tenant_config["rag"]["provider_keys"]["voyageai"],
            batch_size=2  # Small batch for testing
        )
        
        print("📊 Ingestion Result:")
        print(json.dumps(result, indent=2))
        
        # Validate result
        if result.get("upserted", 0) > 0:
            print("✅ SUCCESS: Data was actually inserted into Milvus!")
        else:
            print("❌ SILENT FAILURE DETECTED: No data was inserted!")
            
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        Path(temp_file_path).unlink(missing_ok=True)

if __name__ == "__main__":
    asyncio.run(test_full_ingestion_flow())
