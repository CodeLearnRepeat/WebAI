import requests
import json

url = "https://web3ai-backend-v33-api-180395924844.us-central1.run.app/rag/ingest-file-streaming"

# Read the schema
with open('/Users/finn/Desktop/WEBAII/backend/schema_config.json', 'r') as f:
    schema = f.read()

# Prepare the files and data
files = {
    'file': ('anotherone.json', open('/Users/finn/Desktop/WEBAII/backend/anotherone.json', 'rb'), 'application/json')
}

data = {
    'schema_json': schema,
    'embedding_provider': 'voyageai',
    'embedding_model': 'voyage-law-2',
    'enable_chunking_enhancement': 'true',
    'max_tokens_per_chunk': '1000'
}

headers = {
    'X-Tenant-Id': 'tenant_ikEWJmGOeFrj-cwLRKtWaw'
}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
