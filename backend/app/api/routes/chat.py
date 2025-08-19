import json
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from app.core.rate_limit import check_rate_limit
from app.schemas.chat import ChatRequest
from app.services.tenants import get_tenant_config
from app.services.conversations import get_conversation_history, save_conversation_history
from app.services.openrouter import stream_openrouter_response
from app.services.selfrag import selfrag_run
from app.utils.domains import validate_origin

router = APIRouter()

@router.post("/chat/stream")
async def chat_stream(request_data: ChatRequest, request: Request, x_tenant_id: str = Header(None)):
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    tenant_config = get_tenant_config(x_tenant_id)
    if not tenant_config:
        raise HTTPException(status_code=403, detail="Unknown tenant")
    if not tenant_config.get("active", True):
        raise HTTPException(status_code=403, detail="Tenant is inactive")

    origin = request.headers.get("origin") or request.headers.get("referer")
    if not validate_origin(origin, tenant_config["allowed_domains"]):
        print(f"Origin validation failed: {origin} not in {tenant_config['allowed_domains']}")
        raise HTTPException(status_code=403, detail=f"Origin not allowed. Request from {origin} not in allowed domains.")

    rate_ok, rate_msg = await check_rate_limit(x_tenant_id, tenant_config)
    if not rate_ok:
        raise HTTPException(status_code=429, detail=rate_msg)

    try:
        # DEBUG: Log conversation retrieval
        print(f"[DEBUG] Session ID: {request_data.session_id}")
        print(f"[DEBUG] use_redis_conversations: {request_data.use_redis_conversations}")
        
        history = await get_conversation_history(x_tenant_id, request_data.session_id, request_data.use_redis_conversations)
        
        print(f"[DEBUG] Retrieved history length: {len(history)} messages")
        if history:
            print(f"[DEBUG] Last message in history: {history[-1] if history else 'None'}")

        # Build base messages (for non-RAG fallback streaming)
        messages = []
        if tenant_config.get("system_prompt"):
            messages.append({"role": "system", "content": tenant_config["system_prompt"]})
        messages.extend(history)
        messages.append({"role": "user", "content": request_data.message})

        # Decide if we run RAG
        rag_conf = (tenant_config.get("rag") or {})
        tenant_wants_rag = bool(rag_conf.get("enabled"))
        request_wants_rag = request_data.use_rag if request_data.use_rag is not None else tenant_wants_rag

        # If request overrides top_k
        if request_data.rag_top_k and request_data.rag_top_k > 0:
            rag_conf["top_k"] = int(request_data.rag_top_k)

        print(f"Chat request from tenant {x_tenant_id} (origin: {origin}) | RAG: {request_wants_rag}")

        async def generate():
            full_response = ""

            if request_wants_rag and rag_conf.get("provider") == "milvus":
                try:
                    final_text, dbg = await selfrag_run(
                        api_key=tenant_config["openrouter_api_key"],
                        chat_model=tenant_config["model"],
                        tenant_system_prompt=tenant_config.get("system_prompt") or "",
                        query=request_data.message,
                        rag_conf=rag_conf,
                    )
                    full_response = final_text or ""
                    # SSE in OpenAI delta-like shape for compatibility
                    if full_response:
                        chunk_obj = {"choices": [{"delta": {"content": full_response}}]}
                        yield f"data: {json.dumps(chunk_obj)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    print(f"SelfRAG pipeline error: {e}. Falling back to direct streaming.")
                    async for chunk in stream_openrouter_response(messages, tenant_config["openrouter_api_key"], tenant_config["model"]):
                        yield chunk
                        if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                            try:
                                data = json.loads(chunk[6:])
                                choices = data.get("choices") or []
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    if "content" in delta:
                                        full_response += delta["content"]
                            except Exception:
                                pass
            else:
                # Original pass-through streaming
                async for chunk in stream_openrouter_response(messages, tenant_config["openrouter_api_key"], tenant_config["model"]):
                    yield chunk
                    if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                        try:
                            data = json.loads(chunk[6:])
                            choices = data.get("choices") or []
                            if choices:
                                delta = choices[0].get("delta", {})
                                if "content" in delta:
                                    full_response += delta["content"]
                        except Exception:
                            pass

            # Save conversation
            if full_response:
                history.append({"role": "user", "content": request_data.message})
                history.append({"role": "assistant", "content": full_response})
                print(f"[DEBUG] Saving conversation with {len(history)} messages to Redis: {request_data.use_redis_conversations}")
                await save_conversation_history(x_tenant_id, request_data.session_id, history, request_data.use_redis_conversations)

        return StreamingResponse(generate(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error for tenant {x_tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")