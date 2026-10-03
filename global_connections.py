import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import pyTigerGraph as tg
from dotenv import load_dotenv
from storage_service import generate_secure_expiry_url

# 🔌 Load local configuration parameters from .env
load_dotenv()

# 🛠️ ENV CONFIGURATION & CONNECTIONS
raw_db_url = os.getenv("DATABASE_URL")

if not raw_db_url:
    raise ValueError("❌ CRITICAL: DATABASE_URL is missing from environment or .env file.")

# 🔧 AUTO-FIX PREFIX: Ensure SQLAlchemy uses the async driver even if env drops it
if raw_db_url.startswith("postgresql://"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_db_url.startswith("postgres://"):
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_db_url

TIGERGRAPH_HOST = os.getenv("TIGERGRAPH_HOST", "https://tgcloud.io")
TIGERGRAPH_TOKEN = os.getenv("TIGERGRAPH_TOKEN")
TIGERGRAPH_GRAPH = "CurriculumGraph"

# 1. Relational Database Connection Engine Pool
engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=2)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# 2. Global Graph Interface Initialization
graph_conn = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles thread-safe ecosystem initialization on startup."""
    global graph_conn
    
    # Initialize global graph runtime profile
    graph_conn = tg.TigerGraphConnection(
        host=TIGERGRAPH_HOST,
        graphname=TIGERGRAPH_GRAPH,
        apiToken=TIGERGRAPH_TOKEN
    )
    adapter = tg.requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    graph_conn.session.mount("https://", adapter)
    graph_conn.session.mount("http://", adapter)
    
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# ----------------------------------------------------
# 🔄 THREAD-SAFE LAZY INITIALIZATION PATTERN
# ----------------------------------------------------
def _sync_ensure_graph_node(student_id: int, email: str) -> str:
    """Internal blocking worker method intended to execute safely inside worker thread."""
    student_vertex_id = f"student_{student_id}"
    try:
        vertices = graph_conn.getVerticesById("Student", student_vertex_id)
        if not vertices:
            raise Exception("Vertex missing")
    except Exception:
        print(f"⚠️ Lazy Init: Synchronizing missing student node {student_vertex_id}...")
        graph_conn.upsertVertex(
            vertexType="Student",
            vertexId=student_vertex_id,
            attributes={"email": email, "created_at": "NOW()"}
        )
    return student_vertex_id

# ----------------------------------------------------
# 🚀 FULLY ASYNC PROTECTED ENDPOINT
# ----------------------------------------------------
@app.get("/api/dashboard/{user_id}")
async def load_student_dashboard(user_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Verification Logic Pipeline (Postgres)
    query = text("SELECT id, email, is_active, has_active_subscription FROM users WHERE id = :id")
    result = await db.execute(query, {"id": user_id})
    user = result.mappings().first()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=404, detail="User account not found.")

    if not user["has_active_subscription"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="💳 Active subscription required."
        )

    # 2. Non-blocking Lazy Sync Integration (Offloaded to a background thread pool)
    graph_node_id = await asyncio.to_thread(
        _sync_ensure_graph_node, user["id"], user["email"]
    )

    # 3. Graph Query Pathing Engine Execution (Offloaded to thread pool)
    try:
        next_steps = await asyncio.to_thread(
            graph_conn.runInstalledQuery, "GetNextRecommendedLesson", {"student_id": graph_node_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph runtime error: {str(e)}")

    # 🎬 NEW STEP 4: Get relative path from TigerGraph result and sign it for the UI
    # (If the graph mock doesn't send a path, we fall back to a default video path)
    relative_video_path = next_steps.get("recommended_next_lesson", "courses/default.mp4") + ".mp4"
    
    # This calls your aioboto3 function (which main.py will mock!)
    cdn_stream_url = await generate_secure_expiry_url(relative_video_path)

    
    return {
        "status": "success",
        "student_graph_id": graph_node_id,
        "stream_url": cdn_stream_url,  # The UI video player uses this direct link!
        "payload": next_steps
    }
