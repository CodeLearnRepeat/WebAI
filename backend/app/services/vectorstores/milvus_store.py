from functools import lru_cache
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

class MilvusRetriever:
    def __init__(self, uri: str, token: str | None, db_name: str | None, collection: str,
                 vector_field: str, text_field: str, metric_type: str = "IP"):
        self.uri = uri
        self.token = token
        self.db_name = db_name or "_default"
        self.collection_name = collection
        self.vector_field = vector_field
        self.text_field = text_field
        self.metric_type = metric_type
        self._connect()
        self.collection = Collection(self.collection_name, using=self._alias)
        try:
            self.collection.load()
        except Exception:
            pass

    @property
    def _alias(self) -> str:
        return f"conn_{abs(hash((self.uri, self.token or '', self.db_name or '_default')))%10_000_000}"

    def _connect(self):
        try:
            connections.connect(alias=self._alias, uri=self.uri, token=self.token, db_name=self.db_name)
        except Exception:
            try:
                connections.disconnect(self._alias)
            except Exception:
                pass
            connections.connect(alias=self._alias, uri=self.uri, token=self.token, db_name=self.db_name)

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[str, float]]:
        search_params = {"metric_type": self.metric_type, "params": {"nprobe": 10}}
        res = self.collection.search(
            data=[np.array(query_embedding, dtype="float32")],
            anns_field=self.vector_field,
            param=search_params,
            limit=top_k,
            output_fields=[self.text_field],  # include metadata if you need to display it
        )
        hits = []
        if res and len(res) > 0:
            for hit in res[0]:
                text = hit.entity.get(self.text_field)
                hits.append((text, float(hit.distance)))
        return hits

def ensure_collection(uri: str, token: str | None, db_name: str | None, collection: str,
                      vector_field: str, text_field: str, dim: int, metric_type: str = "IP",
                      metadata_field: Optional[str] = "metadata"):
    alias = f"conn_{abs(hash((uri, token or '', db_name or '_default')))%10_000_000}"
    try:
        connections.connect(alias=alias, uri=uri, token=token, db_name=db_name or "_default")
    except Exception:
        try:
            connections.disconnect(alias)
        except Exception:
            pass
        connections.connect(alias=alias, uri=uri, token=token, db_name=db_name or "_default")

    if not utility.has_collection(collection, using=alias):
        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name=text_field, dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name=vector_field, dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        if metadata_field:
            fields.append(FieldSchema(name=metadata_field, dtype=DataType.VARCHAR, max_length=8192))
        schema = CollectionSchema(fields, description="WebAI website chunks")
        coll = Collection(name=collection, schema=schema, using=alias)
        index_params = {"index_type": "IVF_FLAT", "metric_type": metric_type, "params": {"nlist": 1024}}
        coll.create_index(field_name=vector_field, index_params=index_params)
        coll.load()

def upsert_texts(
    *,
    uri: str,
    token: str | None,
    db_name: str | None,
    collection: str,
    vector_field: str,
    text_field: str,
    metadata_field: Optional[str],
    dim: int,
    metric_type: str,
    rows: List[Dict[str, Any]]
):
    # rows: {"text": str, "embedding": List[float], "metadata": Optional[str]}
    alias = f"conn_{abs(hash((uri, token or '', db_name or '_default')))%10_000_000}"
    coll = Collection(collection, using=alias)
    schema_field_names = {f.name for f in coll.schema.fields}
    texts = [r["text"] for r in rows]
    vecs = [np.array(r["embedding"], dtype="float32") for r in rows]
    insert_cols = [texts, vecs]
    if metadata_field and metadata_field in schema_field_names:
        metas = [r.get("metadata", None) or "" for r in rows]
        insert_cols.append(metas)
    coll.insert(insert_cols)
    coll.flush()

@lru_cache(maxsize=128)
def get_milvus_retriever(uri: str, token: str | None, db_name: str | None, collection: str,
                         vector_field: str, text_field: str, metric_type: str = "IP") -> MilvusRetriever:
    return MilvusRetriever(uri=uri, token=token, db_name=db_name, collection=collection,
                           vector_field=vector_field, text_field=text_field, metric_type=metric_type)