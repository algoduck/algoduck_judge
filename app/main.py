from fastapi import FastAPI
from app.models import Submission
from app.judge_core import judge_submission

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge")
def judge(submission: Submission):
    return judge_submission(submission)
