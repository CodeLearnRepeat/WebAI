from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.tenants import router as tenants_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.debug import router as debug_router
from app.api.routes.rag import router as rag_router
from app.api.routes.api_keys import router as api_keys_router

app = FastAPI(title="WebAI API")

# CORS: allow all; we manually validate origin per-tenant inside chat route
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (paths preserved to avoid breaking clients)
app.include_router(tenants_router)
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(debug_router)
app.include_router(rag_router)
app.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])


# Run: uvicorn app.main:app --host 0.0.0.0 --port 8080