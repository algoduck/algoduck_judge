from pydantic import BaseModel

class SubmissionRequest(BaseModel):
    problemId: int
    language: str
    version: str
    timeLimitation: int  # ms
    memoryLimitation: int  # MB
    sourceCode: str

class SubmissionResponse(BaseModel):
    result: str  # "AC", "CE", "RE", "TLE", "MLE", "WA"
    message: str
    stdout: str
    stderr: str
    time_ms: int
    memory_kb: int
