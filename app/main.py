from fastapi import FastAPI, HTTPException
from app.models import SubmissionRequest, SubmissionResponse
import subprocess
import uuid
import os
from pathlib import Path
import shutil

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/judge", response_model=SubmissionResponse)
def judge_code(req: SubmissionRequest):
    if req.language != 1:  # 예: Java = 1 이라는 내부 규칙
        raise HTTPException(status_code=400, detail="Only Java (language=1) is supported")

    temp_dir = Path(f"/tmp/judge_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # 1. 파일 저장
        java_file = temp_dir / "Main.java"
        with open(java_file, "w") as f:
            f.write(req.sourceCode)

        # 2. 컴파일
        compile_cmd = ["javac", str(java_file)]
        compile_proc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if compile_proc.returncode != 0:
            return SubmissionResponse(
                result="compile_error",
                message="Compilation failed",
                stdout=compile_proc.stdout.decode(),
                stderr=compile_proc.stderr.decode()
            )

        # 3. 실행
        run_cmd = ["java", "-cp", str(temp_dir), "Main"]
        run_proc = subprocess.run(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)

        if run_proc.returncode != 0:
            return SubmissionResponse(
                result="runtime_error",
                message="Runtime error occurred",
                stdout=run_proc.stdout.decode(),
                stderr=run_proc.stderr.decode()
            )

        # 4. 성공
        return SubmissionResponse(
            result="success",
            message="Execution succeeded",
            stdout=run_proc.stdout.decode(),
            stderr=run_proc.stderr.decode()
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
