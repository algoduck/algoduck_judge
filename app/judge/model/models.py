from enum import Enum
from pydantic import BaseModel
from typing import Optional

class Status(str, Enum):
    AC = "AC"
    CE = "CE"
    RE = "RE"
    TLE = "TLE"
    MLE = "MLE"
    WA = "WA"
class SubmissionRequest(BaseModel):
    problemId: int
    submissionId: int
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
    executionTime: int
    memoryUsage: int
    percentage: int = 0

class JudgeProgressResponse(BaseModel):
    index: Optional[int] = None
    submissionId: int
    result: str
    message: str
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    executionTime: int = 0
    memoryUsage: int = 0
    percentage: int = 0
