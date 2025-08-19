from functools import lru_cache
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import logging
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

logger = logging.getLogger(__name__)

class MilvusRetriever:
    def __init__(self, uri: str, token: str | None, db_name: str | None, collection: str,
                 vector_field: str, text_field: str, metric_type: str = "IP"):
        self.uri = uri
        self.token = token
        self.db_name = db_name if db_name is not None else "_default"
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
                      metadata_field: Optional[str] = "metadata") -> Dict[str, Any]:
    """
    Ensure collection exists and return status information.
    
    Returns:
        Dict with collection status and details
    """
    alias = f"conn_{abs(hash((uri, token or '', db_name or '_default')))%10_000_000}"
    
    try:
        # Try to connect
        try:
            connections.connect(alias=alias, uri=uri, token=token, db_name=db_name or "_default")
            logger.info(f"Connected to Milvus with alias {alias}")
        except Exception as e:
            logger.warning(f"Initial connection failed, retrying: {e}")
            try:
                connections.disconnect(alias)
            except Exception:
                pass
            connections.connect(alias=alias, uri=uri, token=token, db_name=db_name or "_default")
            logger.info(f"Reconnected to Milvus with alias {alias}")

        # Check if collection exists
        collection_exists = utility.has_collection(collection, using=alias)
        
        if not collection_exists:
            logger.info(f"Creating new collection: {collection}")
            fields = [
                FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name=text_field, dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name=vector_field, dtype=DataType.FLOAT_VECTOR, dim=dim),
            ]
            if metadata_field:
                fields.append(FieldSchema(name=metadata_field, dtype=DataType.VARCHAR, max_length=8192))
            
            schema = CollectionSchema(fields, description="WebAI website chunks")
            coll = Collection(name=collection, schema=schema, using=alias)
            
            # Create index
            index_params = {"index_type": "IVF_FLAT", "metric_type": metric_type, "params": {"nlist": 1024}}
            coll.create_index(field_name=vector_field, index_params=index_params)
            coll.load()
            logger.info(f"Created and loaded collection: {collection}")
            
            return {
                "status": "created",
                "collection": collection,
                "alias": alias,
                "dimension": dim,
                "exists": True
            }
        else:
            # Collection exists, verify it's accessible
            coll = Collection(collection, using=alias)
            try:
                coll.load()
                logger.info(f"Loaded existing collection: {collection}")
            except Exception as e:
                logger.warning(f"Collection exists but failed to load: {e}")
            
            return {
                "status": "exists",
                "collection": collection,
                "alias": alias,
                "dimension": dim,
                "exists": True
            }
            
    except Exception as e:
        logger.error(f"Failed to ensure collection {collection}: {e}")
        return {
            "status": "error",
            "collection": collection,
            "alias": alias,
            "error": str(e),
            "exists": False
        }

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
) -> Dict[str, Any]:
    """
    Insert texts and embeddings into Milvus collection.
    
    Returns:
        Dict with insertion status and details
    """
    if not rows:
        return {
            "status": "success",
            "inserted_count": 0,
            "collection": collection,
            "message": "No rows to insert"
        }
    
    alias = f"conn_{abs(hash((uri, token or '', db_name or '_default')))%10_000_000}"
    
    try:
        # Get collection and verify schema
        coll = Collection(collection, using=alias)
        schema_field_names = {f.name for f in coll.schema.fields}
        logger.info(f"Inserting {len(rows)} rows into collection {collection}")
        
        # Prepare data
        texts = [r["text"] for r in rows]
        vecs = [np.array(r["embedding"], dtype="float32") for r in rows]
        insert_cols = [texts, vecs]
        
        if metadata_field and metadata_field in schema_field_names:
            metas = [r.get("metadata", None) or "" for r in rows]
            insert_cols.append(metas)
            logger.debug(f"Including metadata field: {metadata_field}")
        
        # Perform insertion
        insert_result = coll.insert(insert_cols)
        
        # Validate insertion result
        if hasattr(insert_result, 'insert_count'):
            inserted_count = insert_result.insert_count
        elif hasattr(insert_result, 'primary_keys'):
            inserted_count = len(insert_result.primary_keys)
        else:
            # Fallback - assume all rows were inserted if no error
            inserted_count = len(rows)
        
        # Flush to ensure data is persisted
        coll.flush()
        logger.info(f"Successfully inserted {inserted_count} rows and flushed to collection {collection}")
        
        # Verify insertion by checking collection count (optional but good for validation)
        try:
            coll.load()  # Ensure collection is loaded for queries
            total_entities = coll.num_entities
            logger.debug(f"Collection {collection} now has {total_entities} total entities")
        except Exception as e:
            logger.warning(f"Could not verify entity count after insertion: {e}")
        
        return {
            "status": "success",
            "inserted_count": inserted_count,
            "requested_count": len(rows),
            "collection": collection,
            "message": f"Successfully inserted {inserted_count} entities"
        }
        
    except Exception as e:
        logger.error(f"Failed to upsert {len(rows)} texts to collection {collection}: {e}")
        return {
            "status": "error",
            "inserted_count": 0,
            "requested_count": len(rows),
            "collection": collection,
            "error": str(e),
            "message": f"Failed to insert entities: {str(e)}"
        }

@lru_cache(maxsize=128)
def get_milvus_retriever(uri: str, token: str | None, db_name: str | None, collection: str,
                         vector_field: str, text_field: str, metric_type: str = "IP") -> MilvusRetriever:
    return MilvusRetriever(uri=uri, token=token, db_name=db_name, collection=collection,
                           vector_field=vector_field, text_field=text_field, metric_type=metric_type)