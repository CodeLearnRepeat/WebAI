from typing import List, Dict, Tuple
import re

from app.services.openrouter import chat_completion
from app.services.embeddings import embed_query
from app.services.vectorstores.milvus_store import get_milvus_retriever

def _strip_to_keywords(s: str) -> str:
    return re.sub(r"[^A-Za-z]", "", s or "").lower()

def _yes_no(text: str) -> bool:
    t = _strip_to_keywords(text)
    return t.startswith("yes")

def _relevance(text: str) -> str:
    t = _strip_to_keywords(text)
    if t.startswith("relevant"):
        return "Relevant"
    return "Irrelevant"

def _support_rank(s: str) -> int:
    t = _strip_to_keywords(s)
    if "fullysupported" in t or t == "fullysupported":
        return 2
    if "partiallysupported" in t or "partiallysupported" in t:
        return 1
    return 0

async def _llm_text(api_key: str, model: str, system: str, user: str) -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    data = await chat_completion(messages, api_key=api_key, model=model)
    # OpenAI-compatible: choices[0].message.content
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return ""

async def selfrag_run(
    *,
    api_key: str,
    chat_model: str,
    tenant_system_prompt: str,
    query: str,
    rag_conf: Dict
) -> Tuple[str, Dict]:
    # Step 1: retrieval decision (unchanged)
    sys_prompt = "You are a controller that decides if external retrieval is needed for a user query. Answer strictly 'Yes' or 'No'."
    user_prompt = f"Given the query: '{query}', determine if retrieval is necessary. Answer strictly 'Yes' or 'No'."
    retrieval_decision_text = await _llm_text(api_key, chat_model, sys_prompt, user_prompt)
    do_retrieve = _yes_no(retrieval_decision_text)

    if not do_retrieve:
        gen_sys = tenant_system_prompt or "You are a helpful website assistant."
        gen_user = f"User question: {query}\nNo retrieval necessary."
        final = await _llm_text(api_key, chat_model, gen_sys, gen_user)
        return final, {"retrieval": False}

    # Step 2: retrieve
    top_k = rag_conf.get("top_k", 3)
    emb_provider = rag_conf.get("embedding_provider", "sentence_transformers")
    emb_model = rag_conf.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
    provider_keys = rag_conf.get("provider_keys", {})
    provider_key = None
    if emb_provider == "openai":
        provider_key = provider_keys.get("openai")
    elif emb_provider == "voyageai":
        provider_key = provider_keys.get("voyageai")

    milvus = rag_conf.get("milvus") or {}
    retriever = get_milvus_retriever(
        uri=milvus["uri"],
        token=milvus.get("token"),
        db_name=milvus.get("db_name"),
        collection=milvus["collection"],
        vector_field=milvus.get("vector_field", "embedding"),
        text_field=milvus.get("text_field", "text"),
        metric_type=milvus.get("metric_type", "IP"),
    )

    q_vec, _ = embed_query(emb_provider, emb_model, query, api_key=provider_key)
    pairs = retriever.search(q_vec, top_k=top_k)
    contexts = [t for (t, _) in pairs if t]
    # Step 3: Relevance filter
    rel_sys = "You judge if the provided context is relevant to the user's query. Answer strictly 'Relevant' or 'Irrelevant'."
    relevant_contexts: List[str] = []
    for ctx in contexts:
        rel_user = f"Query: {query}\nContext:\n{ctx}\nIs the context relevant? Answer strictly 'Relevant' or 'Irrelevant'."
        rel_text = await _llm_text(api_key, chat_model, rel_sys, rel_user)
        if _relevance(rel_text) == "Relevant":
            relevant_contexts.append(ctx)

    # If none relevant, generate without retrieval
    gen_sys = tenant_system_prompt or "You are a helpful website assistant."
    if not relevant_contexts:
        gen_user = f"User question: {query}\nNo relevant context found in retrieval."
        final = await _llm_text(api_key, chat_model, gen_sys, gen_user)
        return final, {"retrieval": True, "relevant": 0}

    # Step 4-6: Generate for each, evaluate support and utility, pick best
    support_sys = "You assess if a response is supported by a context. Answer 'Fully supported', 'Partially supported', or 'No support'."
    utility_sys = "You rate the utility of a response to a query from 1 to 5. Answer with a single number."

    candidates: List[Tuple[str, int, int]] = []  # (response, support_rank, utility)
    for ctx in relevant_contexts:
        # Generate
        gen_user = f"Use the following context to answer the user's question.\nContext:\n{ctx}\nQuestion: {query}\nAnswer:"
        resp = await _llm_text(api_key, chat_model, gen_sys, gen_user)
        # Support
        sup_user = f"Response:\n{resp}\n\nContext:\n{ctx}\nIs the response supported? Answer 'Fully supported', 'Partially supported', or 'No support'."
        sup_text = await _llm_text(api_key, chat_model, support_sys, sup_user)
        sup_rank = _support_rank(sup_text)
        # Utility
        util_user = f"Query: {query}\nResponse:\n{resp}\nRate the utility from 1 to 5. Answer with a single number."
        util_text = await _llm_text(api_key, chat_model, utility_sys, util_user)
        try:
            util_score = max(1, min(5, int(re.findall(r"-?\d+", util_text or "0")[0])))
        except Exception:
            util_score = 3
        candidates.append((resp, sup_rank, util_score))

    # Pick best by support, then utility
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best = candidates[0]
    return best[0], {"retrieval": True, "relevant": len(relevant_contexts), "support_rank": best[1], "utility": best[2]}