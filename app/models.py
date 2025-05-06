from pydantic import BaseModel

class Submission(BaseModel):
    problemId: int
    memberId: int
    language: int
    version: int
    sourceCode: str