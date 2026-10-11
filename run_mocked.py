# run_mocked.py
import os
import sys
import uvicorn
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv
import pyTigerGraph as tg

# 🔌 Load local configuration parameters from .env before anything else
load_dotenv()

print("⚡ [SYSTEM INITIALIZATION] Injecting Cloud and Graph Mocks...")

# -------------------------------------------------------------------------
# 🌲 1. TIGERGRAPH MOCK INJECTION
# -------------------------------------------------------------------------
if not hasattr(tg, 'requests'):
    import requests
    tg.requests = requests

def mock_get_vertices_by_id(self, vertex_type, vertex_id):
    print(f"🌲 [Mock Graph Engine] Intercepted Vertex Lookup for: {vertex_id}")
    return [{"v_id": vertex_id, "attributes": {"email": "mock_student@test.com"}}]

def mock_upsert_vertex(self, vertexType, vertexId, attributes):
    print(f"🌲 [Mock Graph Engine] Lazy Upsert Triggered: {vertexId} -> {attributes}")
    return 1

def mock_run_installed_query(self, query_name, params):
    print(f"🌲 [Mock Graph Engine] Executing Algorithmic Pathfinding Query: {query_name}")
    return {
        "recommended_next_lesson": "VEC_02_Cross_Product",
        "target_student_id": params.get("student_id")
    }

def mock_upsert_edge(self, sourceVertexType, sourceVertexId, edgeType, targetVertexType, targetVertexId, attributes=None):
    print(f"🌲 [Mock Graph Engine] Telemetry Edge Created: {sourceVertexId} --({edgeType})--> {targetVertexId}")
    return 1

tg.TigerGraphConnection.getVerticesById = mock_get_vertices_by_id
tg.TigerGraphConnection.upsertVertex = mock_upsert_vertex
tg.TigerGraphConnection.runInstalledQuery = mock_run_installed_query
tg.TigerGraphConnection.upsertEdge = mock_upsert_edge

if not hasattr(tg.TigerGraphConnection, 'session'):
    mock_session = MagicMock()
    mock_session.mount = MagicMock(return_value=None)
    tg.TigerGraphConnection.session = mock_session

# -------------------------------------------------------------------------
# ☁️ 2. CLOUDFLARE R2 MOCK INJECTION
# -------------------------------------------------------------------------
class MockAioboto3Client:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass
    async def generate_presigned_url(self, client_method, Params, ExpiresIn):
        print(f"☁️ [Mock R2 Engine] Generating secure 60-min stream URL token for asset: '{Params['Key']}'")
        return f"https://cloudflare.net{Params['Bucket']}/{Params['Key']}?token=mock_secure_expiry_jwt"

class MockAioboto3Session:
    def client(self, service_name, **kwargs): return MockAioboto3Client()

mock_aioboto3 = MagicMock()
mock_aioboto3.Session = MockAioboto3Session
sys.modules['aioboto3'] = mock_aioboto3

# -------------------------------------------------------------------------
# 🔌 3. LIVE NEON DATABASE CONFIGURATION INTERCEPT 
# -------------------------------------------------------------------------
print("🔄 Patching live database engines for secure TLS channels...")
import global_connections

raw_url = global_connections.DATABASE_URL.split("?")[0]

if raw_url.startswith("postgresql://"):
    CLEANED_URL = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgres://"):
    CLEANED_URL = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    CLEANED_URL = raw_url

# Force your core app structure to route securely via encrypted asyncpg channels over TLS to Neon
global_connections.engine = create_async_engine(
    CLEANED_URL, 
    pool_size=5, 
    max_overflow=2,
    connect_args={"ssl": True}
)
global_connections.AsyncSessionLocal = async_sessionmaker(
    bind=global_connections.engine, 
    expire_on_commit=False
)

# -------------------------------------------------------------------------
# 🚀 4. LIVE WEB SERVER STARTUP
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print("🔌 Starting Local HTTP Server on Port 8000 for Frontend Development...")
    # This boots your patched app framework live on your machine's network ports
    uvicorn.run("global_connections:app", host="0.0.0.0", port=8000, reload=True)
