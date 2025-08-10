from functools import lru_cache
from typing import List, Tuple, Literal, Optional
from sentence_transformers import SentenceTransformer

EmbProvider = Literal["sentence_transformers", "openai", "voyageai"]

@lru_cache(maxsize=16)
def get_st_model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name)

def _embed_sentence_transformers(texts: List[str], model_name: str) -> Tuple[List[List[float]], int]:
    m = get_st_model(model_name)
    vecs = m.encode(texts, normalize_embeddings=True)
    if hasattr(vecs, "tolist"):
        vecs = vecs.tolist()
    dim = len(vecs[0]) if vecs else 0
    return vecs, dim

def _embed_openai(texts: List[str], model_name: str, api_key: str) -> Tuple[List[List[float]], int]:
    # OpenAI Python SDK v1
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    # Batched call: the SDK accepts a list input
    resp = client.embeddings.create(model=model_name, input=texts)
    vecs = [item.embedding for item in resp.data]
    dim = len(vecs[0]) if vecs else 0
    return vecs, dim

def _embed_voyage(texts: List[str], model_name: str, api_key: str, input_type: Literal["query", "document"]) -> Tuple[List[List[float]], int]:
    # VoyageAI SDK
    import voyageai as vo
    client = vo.Client(api_key=api_key)
    resp = client.embed(texts, model=model_name, input_type=input_type)
    vecs = resp.embeddings
    dim = len(vecs[0]) if vecs else 0
    return vecs, dim

def embed_texts(
    provider: EmbProvider,
    model_name: str,
    texts: List[str],
    *,
    api_key: Optional[str] = None,
    mode: Literal["query", "document"] = "query"
) -> Tuple[List[List[float]], int]:
    if provider == "sentence_transformers":
        return _embed_sentence_transformers(texts, model_name)
    if provider == "openai":
        if not api_key:
            raise ValueError("OpenAI embedding requires api_key")
        return _embed_openai(texts, model_name, api_key)
    if provider == "voyageai":
        if not api_key:
            raise ValueError("VoyageAI embedding requires api_key")
        return _embed_voyage(texts, model_name, api_key, input_type=mode)
    raise ValueError(f"Unsupported embedding provider: {provider}")

def embed_query(provider: EmbProvider, model_name: str, text: str, *, api_key: Optional[str] = None) -> Tuple[List[float], int]:
    vecs, dim = embed_texts(provider, model_name, [text], api_key=api_key, mode="query")
    return (vecs[0] if vecs else []), dim