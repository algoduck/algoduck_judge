from pydantic import BaseModel

class SubmissionRequest(BaseModel):
    problemId: int
    memberId: int
    language: int
    version: int
    timeLimitation: int  # ms
    memoryLimitation: int  # MB
    sourceCode: str

class SubmissionResponse(BaseModel):
    result: str  # "AC", "CE", "RE", "TLE", "MLE", "WA"
    message: str
    stdout: str
    stderr: str
    time_ms: float
    memory_kb: int
