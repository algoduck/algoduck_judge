from pydantic import BaseModel

class SubmissionRequest(BaseModel):
    problemId: int
    memberId: int
    language: int
    version: int
    timeLimitation: int
    memoryLimitation: int
    sourceCode: str

class SubmissionResponse(BaseModel):
    result: str  # "success", "compile_error", "runtime_error", "time_limit_exceeded", "memory_limit_exceeded", "wrong_answer"
    message: str
    stdout: str
    stderr: str