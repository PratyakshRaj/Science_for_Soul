import os
import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import pyTigerGraph as tg

# ----------------------------------------------------
# 🛠️ ENV CONFIGURATION & CONNECTIONS
# ----------------------------------------------------
# In production, route your Postgres URL through PgBouncer (e.g., port 5432 or 6432)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/tiger_data")
TIGERGRAPH_HOST = os.getenv("TIGERGRAPH_HOST", "https://tgcloud.io")
TIGERGRAPH_TOKEN = os.getenv("TIGERGRAPH_TOKEN", "YOUR_SECRET_TOKEN")
TIGERGRAPH_GRAPH = "CurriculumGraph"

# 1. Database Connections
# async_sessionmaker manages our transactional connections efficiently
engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# 2. Global TigerGraph Instance Configuration
# Reuses a single persistent HTTP/2 connection tunnel across all requests
graph_conn = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles app startup and shutdown logic."""
    global graph_conn
    # Initialize global graph engine instance on boot
    graph_conn = tg.TigerGraphConnection(
        host=TIGERGRAPH_HOST,
        graphname=TIGERGRAPH_GRAPH,
        apiToken=TIGERGRAPH_TOKEN
    )
    # 🔧 FIX: Manually boost the internal HTTP connection pool size 
    # to match your Postgres pool size (e.g., 20 max connections)
    adapter = tg.requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    graph_conn.session.mount("https://", adapter)
    graph_conn.session.mount("http://", adapter)
    yield
    # Clean up relational database connection engine pool on shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

# Dependency to get db session per request
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# ----------------------------------------------------
# 🔄 THE LAZY INITIALIZATION PATTERN
# ----------------------------------------------------
def ensure_graph_student_node(student_id: int, email: str):
    """
    Checks if a student exists in TigerGraph. 
    If they don't, it initializes their vertex dynamically.
    """
    student_vertex_id = f"student_{student_id}"
    try:
        # Check if vertex exists
        vertices = graph_conn.getVerticesById("Student", student_vertex_id)
        if not vertices:
            # If empty array returned, explicitly trigger creation logic
            raise Exception("Vertex not found")
    except Exception:
        # Lazy Initialization: Missing node is created dynamically on-demand
        print(f"⚠️ Student node {student_vertex_id} missing in TigerGraph. Creating on-the-fly...")
        graph_conn.upsertVertex(
            vertexType="Student",
            vertexId=student_vertex_id,
            attributes={"email": email, "created_at": "NOW()"}
        )
    return student_vertex_id