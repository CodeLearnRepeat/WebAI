#!/usr/bin/env python3
"""
Test script to verify the file upload fix for RAG ingestion.
"""

import requests
import json
import sys

def test_rag_ingestion():
    """Test the RAG ingestion endpoint with proper file upload."""
    
    url = "https://web3ai-backend-v33-api-180395924844.us-central1.run.app/rag/ingest-file-streaming"
    
    # File paths
    json_file_path = "/Users/finn/Desktop/WEBAII/backend/anotherone.json"
    schema_file_path = "/Users/finn/Desktop/WEBAII/backend/schema_config.json"
    
    # Read the schema
    try:
        with open(schema_file_path, 'r') as f:
            schema_content = f.read()
            print(f"Schema loaded: {len(schema_content)} chars")
    except FileNotFoundError:
        print(f"Error: Schema file not found at {schema_file_path}")
        return False
    
    # Prepare the files
    try:
        files = {
            'file': ('anotherone.json', open(json_file_path, 'rb'), 'application/json')
        }
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return False
    
    # Prepare the form data
    data = {
        'schema_json': schema_content,
        'embedding_provider': 'voyageai',
        'embedding_model': 'voyage-law-2',
        'enable_chunking_enhancement': 'true',
        'max_tokens_per_chunk': '1000'
    }
    
    # Headers
    headers = {
        'X-Tenant-Id': 'tenant_ikEWJmGOeFrj-cwLRKtWaw'
    }
    
    print("\n" + "="*50)
    print("Testing RAG Ingestion Upload")
    print("="*50)
    print(f"URL: {url}")
    print(f"Tenant ID: {headers['X-Tenant-Id']}")
    print(f"Embedding Provider: {data['embedding_provider']}")
    print(f"Embedding Model: {data['embedding_model']}")
    print("="*50 + "\n")
    
    try:
        # Make the request
        print("Sending request...")
        response = requests.post(url, headers=headers, files=files, data=data)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Try to parse JSON response
        try:
            result = response.json()
            print("\nResponse JSON:")
            print(json.dumps(result, indent=2))
            
            # Check if successful
            if result.get('status') == 'ok' or result.get('status') == 'completed':
                upserted = result.get('upserted', 0)
                if upserted > 0:
                    print(f"\n✅ SUCCESS: {upserted} items were ingested!")
                    return True
                else:
                    print("\n⚠️ WARNING: No items were ingested. Check the logs.")
                    return False
            else:
                print(f"\n❌ ERROR: {result.get('message', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            print("\nResponse Text:")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return False
    finally:
        # Close the file
        if 'files' in locals():
            for key, value in files.items():
                if hasattr(value[1], 'close'):
                    value[1].close()

def test_analyze_endpoint():
    """Test the analyze endpoint to verify file upload works."""
    
    url = "https://web3ai-backend-v33-api-180395924844.us-central1.run.app/rag/analyze-file"
    
    json_file_path = "/Users/finn/Desktop/WEBAII/backend/anotherone.json"
    
    try:
        files = {
            'file': ('anotherone.json', open(json_file_path, 'rb'), 'application/json')
        }
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return False
    
    headers = {
        'X-Tenant-Id': 'tenant_ikEWJmGOeFrj-cwLRKtWaw'
    }
    
    print("\n" + "="*50)
    print("Testing File Analysis Endpoint")
    print("="*50)
    
    try:
        response = requests.post(url, headers=headers, files=files)
        print(f"Status Code: {response.status_code}")
        
        try:
            result = response.json()
            print("\nFile Analysis Result:")
            print(json.dumps(result, indent=2))
            
            if result.get('status') == 'ok':
                file_analysis = result.get('file_analysis', {})
                print(f"\n✅ File successfully analyzed:")
                print(f"  - File size: {file_analysis.get('file_size_bytes', 0)} bytes")
                print(f"  - Estimated items: {file_analysis.get('estimated_items', 0)}")
                print(f"  - Detected format: {file_analysis.get('detected_format', 'unknown')}")
                return True
            else:
                print(f"\n❌ Analysis failed: {result.get('message', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            print("\nResponse Text:")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return False
    finally:
        if 'files' in locals():
            for key, value in files.items():
                if hasattr(value[1], 'close'):
                    value[1].close()

if __name__ == "__main__":
    print("RAG Ingestion File Upload Test")
    print("==============================\n")
    
    # First test the analyze endpoint to verify file upload
    print("Step 1: Testing file analysis...")
    if test_analyze_endpoint():
        print("\nFile upload is working!")
        
        # Now test the actual ingestion
        print("\nStep 2: Testing file ingestion...")
        if test_rag_ingestion():
            print("\n🎉 All tests passed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Ingestion test failed")
            sys.exit(1)
    else:
        print("\n❌ File analysis test failed")
        sys.exit(1)