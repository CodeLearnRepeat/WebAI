import requests
import json

def test_voyage_embeddings():
    api_key = "pa-"
    model = "voyage-law-2"
    
    try:
        print("🚀 Testing VoyageAI embedding generation...")
        
        response = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": ["This is a test document for embedding generation"],
                "input_type": "document"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            embeddings = result["data"][0]["embedding"]
            print(f"✅ VoyageAI embedding successful!")
            print(f"📐 Embedding dimension: {len(embeddings)}")
            print(f"🎯 Model used: {model}")
            return True
        else:
            print(f"❌ VoyageAI API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ VoyageAI test failed: {e}")
        return False

if __name__ == "__main__":
    test_voyage_embeddings()
