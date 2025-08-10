from typing import List, Dict, Optional
import json
from app.services.embeddings import embed_texts
from app.services.vectorstores.milvus_store import ensure_collection, upsert_texts

def ingest_to_milvus(
    *,
    texts: List[str],
    metadatas: Optional[List[dict]],
    milvus_conf: Dict,
    emb_provider: str,
    emb_model: str,
    provider_key: Optional[str],
) -> Dict:
    vecs, dim = embed_texts(
        provider=emb_provider,
        model_name=emb_model,
        texts=texts,
        api_key=provider_key,
        mode="document",
    )

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

    rows = []
    for i, t in enumerate(texts):
        row = {"text": t, "embedding": vecs[i]}
        if metadatas:
            row["metadata"] = json.dumps(metadatas[i] or {}, ensure_ascii=False)
        rows.append(row)

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
    return {"upserted": len(rows), "dim": dim}