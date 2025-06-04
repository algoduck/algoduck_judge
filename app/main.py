from fastapi import FastAPI, WebSocket
from app.judge_core import judge_submission
from app.judge_ws import judge_websocket_handler
from app.util.cache_manager import load_metadata, save_metadata
from app.models import SubmissionRequest, SubmissionResponse
from dotenv import load_dotenv
import logging

# 전역 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

load_metadata() # 서버 시작 시 캐시 메타데이터 불러오기
load_dotenv()

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge", response_model=SubmissionResponse)
def judge_code(req: SubmissionRequest):
    return judge_submission(req)

# WebSocket 엔드포인트
@app.websocket("/ws/judge")
async def judge_websocket(websocket: WebSocket):
    await judge_websocket_handler(websocket)

@app.on_event("shutdown")
def shutdown_event():
    save_metadata()