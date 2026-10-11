# progress_service.py
import asyncio, sqlalchemy
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import global_connections  # Import your shared graph_conn

# ----------------------------------------------------
# 🔄 THREAD-SAFE GRAPH PROGRESS UPDATERS
# ----------------------------------------------------
def _sync_mark_video_complete(student_id: int, lesson_id: str) -> bool:
    """Tells TigerGraph to create a 'COMPLETED' edge between student and lesson."""
    student_vertex_id = f"student_{student_id}"
    try:
        # Expected GSQL edge connection logic
        global_connections.graph_conn.upsertEdge(
            sourceVertexType="Student",
            sourceVertexId=student_vertex_id,
            edgeType="COMPLETED_LESSON",
            targetVertexType="Lesson",
            targetVertexId=lesson_id,
            attributes={"completed_at": "NOW()"}
        )
        return True
    except Exception as e:
        print(f"⚠️ Graph Progress Sync Error (Video): {str(e)}")
        return False

def _sync_record_quiz_performance(student_id: int, quiz_id: str, score: float, passed: bool) -> bool:
    """Tells TigerGraph about quiz performance to flag knowledge gaps dynamically."""
    student_vertex_id = f"student_{student_id}"
    try:
        global_connections.graph_conn.upsertEdge(
            sourceVertexType="Student",
            sourceVertexId=student_vertex_id,
            edgeType="ATTEMPTED_QUIZ",
            targetVertexType="Quiz",
            targetVertexId=quiz_id,
            attributes={"score": score, "passed": passed, "attempted_at": "NOW()"}
        )
        return True
    except Exception as e:
        print(f"⚠️ Graph Progress Sync Error (Quiz): {str(e)}")
        return False

# ----------------------------------------------------
# 🚀 ASYNC SERVICE CONTROLLERS FOR FASTAPI
# ----------------------------------------------------
async def process_video_completion(user_id: int, lesson_id: str, db: AsyncSession) -> dict:
    # 1. Update relational status in Postgres (For basic analytics/state tracking)
    query = text("""
        INSERT INTO student_video_progress (user_id, lesson_id, completed, updated_at)
        VALUES (:user_id, :lesson_id, TRUE, NOW())
        ON CONFLICT (user_id, lesson_id) DO UPDATE SET completed = TRUE, updated_at = NOW()
    """)
    await db.execute(query, {"user_id": user_id, "lesson_id": lesson_id})
    await db.commit()

    # 2. Non-blocking graph update offloaded to thread pool
    graph_success = await asyncio.to_thread(_sync_mark_video_complete, user_id, lesson_id)
    
    return {"status": "success", "graph_synced": graph_success}

async def process_quiz_submission(user_id: int, quiz_id: str, answers: list, db: AsyncSession) -> dict:
    # 1. Grade the Quiz (Simulated grading engine mapping against relational DB)
    # In a real environment, you'd pull correct answers from a `quiz_questions` table.
    total_questions = len(answers)
    correct_count = sum(1 for ans in answers if ans.get("is_correct") is True)
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
    passed = score >= 70.0  # 70% threshold

    # 2. Write permanent log to Postgres
    query = text("""
        INSERT INTO quiz_attempts (user_id, quiz_id, score, passed, created_at)
        VALUES (:user_id, :quiz_id, :score, :passed, NOW())
    """)
    await db.execute(query, {"user_id": user_id, "quiz_id": quiz_id, "score": score, "passed": passed})
    await db.commit()

    # 3. Offload telemetry data to TigerGraph so the GSQL path-finder recognizes the score
    graph_success = await asyncio.to_thread(_sync_record_quiz_performance, user_id, quiz_id, score, passed)

    return {
        "status": "success",
        "score": score,
        "passed": passed,
        "graph_synced": graph_success
    }
