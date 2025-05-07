from app.judge_core import judge_submission
from fastapi import FastAPI
from app.models import SubmissionRequest, SubmissionResponse
from dotenv import load_dotenv
import logging

load_dotenv()

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge", response_model=SubmissionResponse)
def judge_code(req: SubmissionRequest):
    return judge_submission(req)
