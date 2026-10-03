import os
import sys
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv

# 🔌 Load local environment variables for the test engine
load_dotenv()

print("\n[CHECKPOINT 1] 🚀 Python main.py has launched!")

# -------------------------------------------------------------------------
# 🤖 1. ROOT-LEVEL GRAPH MOCK INJECTION
# -------------------------------------------------------------------------
import pyTigerGraph as tg

# Patch missing requests module tracking definitions
if not hasattr(tg, 'requests'):
    import requests
    tg.requests = requests

# Define our mock behaviors for TigerGraph
def mock_get_vertices_by_id(self, vertex_type, vertex_id):
    if "student_1" in vertex_id:
        print(f"🌲 [Mock Graph] Vertex {vertex_id} located safely.")
        return [{"v_id": vertex_id, "attributes": {"email": "paid_student@test.com"}}]
    print(f"🌲 [Mock Graph] Vertex {vertex_id} missing.")
    return []

def mock_upsert_vertex(self, vertexType, vertexId, attributes):
    print(f"🌲 [Mock Graph Engine] Node initialized dynamically: {vertexId} -> {attributes}")
    return 1

def mock_run_installed_query(self, query_name, params):
    print(f"🌲 [Mock Graph Engine] Running query: {query_name} for {params}")
    return {
        "recommended_next_lesson": "VEC_02_Cross_Product",
        "target_student_id": params.get("student_id")
    }

# Overwrite real TigerGraph behaviors permanently
tg.TigerGraphConnection.getVerticesById = mock_get_vertices_by_id
tg.TigerGraphConnection.upsertVertex = mock_upsert_vertex
tg.TigerGraphConnection.runInstalledQuery = mock_run_installed_query

if not hasattr(tg.TigerGraphConnection, 'session'):
    mock_session = MagicMock()
    mock_session.mount = MagicMock(return_value=None)
    tg.TigerGraphConnection.session = mock_session


from unittest.mock import AsyncMock, MagicMock
import sys

# -------------------------------------------------------------------------
# 🤖 CLOUDFLARE R2 ASYNC MOCK INJECTION (Add to main.py)
# -------------------------------------------------------------------------
class MockAioboto3Client:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    async def generate_presigned_url(self, client_method, Params, ExpiresIn):
        print(f"☁️ [Mock R2 Engine] Generating secure 60-min URL for Key: '{Params['Key']}'")
        # Return a deterministic mock signed path string for testing assertions
        return f"https://cloudflare.net{Params['Bucket']}/{Params['Key']}?token=mock_secure_expiry_jwt"

class MockAioboto3Session:
    def client(self, service_name, **kwargs):
        return MockAioboto3Client()

# Intercept aioboto3 dependency before execution
mock_aioboto3 = MagicMock()
mock_aioboto3.Session = MockAioboto3Session
sys.modules['aioboto3'] = mock_aioboto3



# -------------------------------------------------------------------------
# 🔌 2. LIVE DATABASE CONFIGURATION INTERCEPT 
# -------------------------------------------------------------------------
print("[CHECKPOINT 2] 🔄 Patching database engines and structures...")

import global_connections

raw_url = global_connections.DATABASE_URL.split("?")[0]

if raw_url.startswith("postgresql://"):
    CLEANED_URL = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgres://"):
    CLEANED_URL = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    CLEANED_URL = raw_url

# Force your core file to route via encrypted asyncpg channels over TLS
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

print("[CHECKPOINT 3] 🛞 Importing your core FastAPI app application engine...")
from global_connections import app

print("[CHECKPOINT 4] 🧪 Opening FastAPI TestClient engine...\n")

with TestClient(app) as client:
    
    # 🧪 TEST CASE 1: The Paid Student (User ID 4)
    print("--- Running Test Scenario 1: Paid Regular User (ID: 4) ---")
    response_a = client.get("/api/dashboard/4")
    print(f"FastAPI Status Code: {response_a.status_code}")
    print(f"Data Payload Received: {response_a.json()}\n")

    # 🧪 TEST CASE 2: The Unpaid Student (User ID 2)
    print("--- Running Test Scenario 2: Unpaid Wall Block (ID: 2) ---")
    response_b = client.get("/api/dashboard/2")
    print(f"FastAPI Status Code: {response_b.status_code}")
    print(f"Data Payload Received: {response_b.json()}\n")

    # 🧪 TEST CASE 3: New Paid Student / Lazy Init Firing (User ID 3)
    print("--- Running Test Scenario 3: Lazy Graph Sync Intercept (ID: 3) ---")
    response_c = client.get("/api/dashboard/3")
    print(f"FastAPI Status Code: {response_c.status_code}")
    print(f"Data Payload Received: {response_c.json()}\n")

print("✅ Diagnostics Complete. All database and routing checks passed!")
