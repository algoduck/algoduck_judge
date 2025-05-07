from app.judge_core import judge_submission
from fastapi import FastAPI, HTTPException
from app.models import SubmissionRequest, SubmissionResponse
from pathlib import Path

from dotenv import load_dotenv # type: ignore

load_dotenv()  # .env 파일 로딩
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge", response_model=SubmissionResponse)
def judge_code(req: SubmissionRequest):
    return judge_submission(req)
