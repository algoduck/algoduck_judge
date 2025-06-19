from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import threading
import logging

from app.judge.core.judge_core import judge_submission
from app.judge.core.judge_ws import judge_websocket_handler
from app.util.cache_manager import load_metadata, save_metadata
from app.judge.model.models import SubmissionRequest, SubmissionResponse
from app.judge.queue.judge_consumer import start_consumer

# 전역 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    load_metadata()
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()

    yield  # 앱 실행 중

    # shutdown
    save_metadata()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge", response_model=SubmissionResponse)
def judge_code(req: SubmissionRequest):
    return judge_submission(req)

@app.websocket("/ws/judge")
async def judge_websocket(websocket: WebSocket):
    await judge_websocket_handler(websocket)
