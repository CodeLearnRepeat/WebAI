#!/usr/bin/env python3
import os
import sys
import json
from pymilvus import connections, utility, Collection

def test_zilliz_connection():
    # Your exact configuration from tenant_setup.txt
    config = {
        "uri": "https://in03-7b3940c7c2d29d3.serverless.gcp-us-west1.cloud.zilliz.com",
        "token": "8c8d4d5f6cb3926e46e39c6eeca8c69bb3601c7e5a1586be40c6add0b90bb60e71506ab78a2229c4fe27bc526a8ab1ad30d60a1b",
        "db_name": "RHTAI",
        "collection": "website_info_23"  # Use your latest collection name
    }
    
    alias = "debug_test"
    
    try:
        print("🔗 Testing Zilliz Cloud connection...")
        connections.connect(
            alias=alias,
            uri=config["uri"],
            token=config["token"],
            db_name=config["db_name"]
        )
        print("✅ Connection successful!")
        
        # Test database access
        print(f"🗃️  Testing database '{config['db_name']}'...")
        collections = utility.list_collections(using=alias)
        print(f"📋 Available collections: {collections}")
        
        # Test specific collection
        collection_exists = utility.has_collection(config["collection"], using=alias)
        print(f"📁 Collection '{config['collection']}' exists: {collection_exists}")
        
        if collection_exists:
            coll = Collection(config["collection"], using=alias)
            try:
                coll.load()
                entity_count = coll.num_entities
                print(f"📊 Collection loaded successfully with {entity_count} entities")
            except Exception as e:
                print(f"❌ Failed to load collection: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False
    
    finally:
        try:
            connections.disconnect(alias)
        except:
            pass

if __name__ == "__main__":
    test_zilliz_connection()
