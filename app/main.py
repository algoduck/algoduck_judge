from app.judge_core import judge_submission
from app.util.cache_manager import save_metadata
from fastapi import FastAPI
from app.models import SubmissionRequest, SubmissionResponse
from dotenv import load_dotenv
import logging

# 전역 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

load_dotenv()

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge", response_model=SubmissionResponse)
def judge_code(req: SubmissionRequest):
    return judge_submission(req)

@app.on_event("shutdown")
def shutdown_event():
    save_metadata()